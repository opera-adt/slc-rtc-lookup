"""Functions for checking RTC-S1 accountability from SLC products."""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from shapely.geometry import box

from .daac import query_slc_metadata_by_geometry
from .rtc_s1_check import check_rtc_s1_by_many_slc_ids


def check_rtc_s1_accountability(
    start_time: Optional[datetime] = None,
    stop_time: Optional[datetime] = None,
    bbox: Optional[box] = None,
) -> pd.DataFrame:
    """Check RTC-S1 accountability for SLC products in a time range.

    Parameters
    ----------
    start_time : datetime, optional
        Start time for query (default: 4 days ago)
    stop_time : datetime, optional
        Stop time for query (default: 2 days ago)
    bbox : shapely.geometry.box, optional
        Bounding box for spatial query (default: None for global search)

    Returns
    -------
    pd.DataFrame
        Deduped dataframe with columns:
        - jpl_burst_id: JPL burst ID
        - rtc_opera_id: OPERA RTC-S1 granule ID (or None if missing)
        - slc_id: Source SLC granule ID
        - Additional metadata columns
    """
    # Set defaults
    if start_time is None:
        start_time = datetime.now() - timedelta(days=4)
    if stop_time is None:
        stop_time = datetime.now() - timedelta(days=2)

    # Query SLC metadata
    df_slc = query_slc_metadata_by_geometry(
        geometry=bbox,
        start_time=start_time,
        stop_time=stop_time
    )

    if df_slc.empty:
        return pd.DataFrame()

    # Get unique SLC IDs
    slc_ids = df_slc['slc_id'].unique().tolist()

    # Check RTC-S1 products
    df_rtc_check = check_rtc_s1_by_many_slc_ids(slc_ids)

    # Deduplicate by burst ID
    df_rtc_check_deduped = df_rtc_check.drop_duplicates(
        subset=['jpl_burst_id']
    ).reset_index(drop=True)

    return df_rtc_check_deduped
