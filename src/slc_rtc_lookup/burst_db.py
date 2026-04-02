from functools import cache
from pathlib import Path

import geopandas as gpd


@cache
def get_esa_jpl_lut() -> gpd.GeoDataFrame:
    data_dir = Path(__file__).parent / 'data'
    parquet_path = data_dir / 'esa_jpl_lut.parquet'
    return gpd.read_parquet(parquet_path)


def get_burst_by_jpl_id(burst_ids: str | list[str]) -> gpd.GeoDataFrame:
    df_burst = get_esa_jpl_lut()

    if isinstance(burst_ids, str):
        burst_ids = [burst_ids]

    return df_burst[df_burst['jpl_burst_id'].isin(burst_ids)].reset_index(drop=True)


def get_burst_by_ogc_fids(ogc_fids: int | list[int]) -> gpd.GeoDataFrame:
    df_burst = get_esa_jpl_lut()

    if isinstance(ogc_fids, int):
        ogc_fids = [ogc_fids]

    return df_burst[df_burst['ogc_fid'].isin(ogc_fids)].reset_index(drop=True)
