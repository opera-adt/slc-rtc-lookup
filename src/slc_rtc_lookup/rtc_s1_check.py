import concurrent.futures

import pandas as pd
from dist_s1_enumerator.asf import get_rtc_s1_ts_metadata_by_burst_ids
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm import tqdm

from slc_rtc_lookup.exceptions import RETRY_EXCEPTIONS
from slc_rtc_lookup.slc_metadata import get_burst_metadata_from_one_slc_id


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
)
def check_rtc_s1_by_one_slc_id(slc_id: str, buffer_days: int = 1) -> pd.DataFrame:
    sensing_time = pd.Timestamp(slc_id.split('_')[5])
    start_time = sensing_time - pd.Timedelta(days=buffer_days)
    stop_time = sensing_time + pd.Timedelta(days=buffer_days)

    df_burst_slc = get_burst_metadata_from_one_slc_id(slc_id)
    df_burst_slc = df_burst_slc[[col for col in df_burst_slc.columns if col not in ['geometry']]]
    burst_ids = df_burst_slc['jpl_burst_id'].unique().tolist()

    df_rtc = get_rtc_s1_ts_metadata_by_burst_ids(
        burst_ids, start_acq_dt=start_time, stop_acq_dt=stop_time, include_single_polarization=True
    )
    df_rtc = df_rtc.rename(
        columns={col: f'rtc_{col}' for col in df_rtc.columns if col not in ['jpl_burst_id', 'geometry']}
    )

    # Left is important here so we don't lose any SLCs that don't have an RTC-S1 product
    df_out = pd.merge(df_burst_slc, df_rtc, on=['jpl_burst_id'], how='left')
    return df_out


def check_rtc_s1_by_many_slc_ids(slc_ids: list[str], buffer_days: int = 1, max_workers: int = 10) -> pd.DataFrame:
    if isinstance(slc_ids, str):
        slc_ids = [slc_ids]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        out = list(
            tqdm(
                executor.map(
                    check_rtc_s1_by_one_slc_id,
                    slc_ids,
                    [buffer_days] * len(slc_ids),
                ),
                total=len(slc_ids),
                desc='Checking RTC-S1 for SLCs',
            ),
        )
    df_out = pd.concat(out, axis=0, ignore_index=True)
    return df_out
