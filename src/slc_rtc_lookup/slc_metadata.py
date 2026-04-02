import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from warnings import warn

import fsspec
import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm import tqdm

from slc_rtc_lookup.burst_db import get_burst_by_ogc_fids
from slc_rtc_lookup.exceptions import RETRY_EXCEPTIONS


def get_slc_url(slc_id: str) -> str:
    return f'https://datapool.asf.alaska.edu/SLC/SA/{slc_id}.zip'


def get_esa_burst_metadata_from_slc_id(slc_id: str) -> list[dict]:
    url = get_slc_url(slc_id)

    storage_options = {'https': {'client_kwargs': {'trust_env': True}}}

    fs = fsspec.filesystem('zip', fo=url, target_options=storage_options['https'])

    all_files = fs.find('')
    annotation_paths = sorted(
        [
            f
            for f in all_files
            if 'annotation/s1' in f and f.endswith('.xml') and not any(x in f for x in ['calibration', 'noise'])
        ]
    )

    burst_metadata = []

    for path in annotation_paths:
        # Stream the XML directly from the zip into the parser
        with fs.open(path) as f:
            tree = ET.parse(f)
            root = tree.getroot()

        # Get the swath for this specific file (e.g., IW1)
        swath = root.findtext('.//swath')

        # Loop through bursts and build the list of dictionaries
        for i, burst in enumerate(root.findall('.//burstList/burst')):
            burst_metadata.append(
                {
                    'burst_index': i,
                    'ogc_fid': int(burst.findtext('burstId')),
                    'sensing_time': burst.findtext('azimuthTime'),
                    'slc_id': slc_id,
                    'subswath': swath,
                }
            )

    return burst_metadata


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
)
def get_burst_metadata_from_one_slc_id(slc_id: str) -> pd.DataFrame:
    burst_metadata = get_esa_burst_metadata_from_slc_id(slc_id)
    df_burst = pd.DataFrame(burst_metadata)
    ogc_fids = df_burst['ogc_fid'].unique().tolist()
    df_lut = get_burst_by_ogc_fids(ogc_fids)
    if ogc_fids and df_lut.empty:
        warn(f'No bursts over land for SLC {slc_id} found in LUT')
    df_burst = pd.merge(df_burst, df_lut, on=['ogc_fid', 'subswath'], how='inner')
    return df_burst


def get_burst_metadata_from_many_slc_ids(slc_ids: list[str], max_workers: int = 10) -> pd.DataFrame:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        out = executor.map(
            get_burst_metadata_from_one_slc_id,
            tqdm(slc_ids, total=len(slc_ids), desc='Getting burst metadata from SLC IDs'),
        )
    df_many = pd.concat(out, axis=0, ignore_index=True)
    return df_many
