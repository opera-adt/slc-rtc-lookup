from datetime import datetime

import asf_search as asf
import geopandas as gpd
import pandas as pd
from asf_search import ASFSearchResults
from rasterio.crs import CRS
from shapely.geometry import Polygon, shape


def slc_properties_formatter(props: dict) -> dict:
    props_out = {}
    props_out['slc_id'] = props['sceneName']
    props_out['orbit_pass'] = props['flightDirection']
    props_out['slc_polarizations'] = props['polarization']
    props_out['track_number'] = int(props['pathNumber'])
    props_out['start_time'] = pd.Timestamp(props['startTime'])
    props_out['url'] = props['url']
    props_out['s3_uri'] = props['s3Urls'][0]
    props_out['size_gb'] = int(props['bytes']) / 1024 / 1024 / 1024
    return props_out


def transform_results_to_geodataframe(results: ASFSearchResults) -> gpd.GeoDataFrame:
    props = [d.properties for d in results]
    geometry = [shape(d.geometry) for d in results]
    props_f = list(map(slc_properties_formatter, props))
    geometry = [shape(r.geojson()['geometry']) for r in results]
    df_results = gpd.GeoDataFrame(props_f, geometry=geometry, crs=CRS.from_epsg(4326))
    return df_results


def query_slc_metadata_by_geometry(
    *,
    geometry: Polygon | None = None,
    track_numbers: list[int] | None = None,
    allowable_polarizations: list[str] = None,
    start_time: datetime = None,
    stop_time: datetime = None,
    max_results_per_frame: int = 100_000,
) -> gpd.GeoDataFrame:
    if allowable_polarizations is None:
        allowable_polarizations = ['VV', 'VV+VH']
    results = asf.geo_search(
        platform=[asf.PLATFORM.SENTINEL1],
        intersectsWith=geometry.wkt if geometry else None,
        maxResults=max_results_per_frame,
        relativeOrbit=track_numbers,
        polarization=allowable_polarizations,
        beamMode=[asf.BEAMMODE.IW],
        processingLevel=[asf.PRODUCT_TYPE.SLC],
        start=start_time,
        end=stop_time,
    )
    df_results = transform_results_to_geodataframe(results)
    return df_results


def query_slc_metadata_by_id(slc_ids: list[str]) -> gpd.GeoDataFrame:
    results = asf.granule_search(
        granuleId=slc_ids,
        platform=[asf.PLATFORM.SENTINEL1],
        processingLevel=[asf.PRODUCT_TYPE.SLC],
        beamMode=[asf.BEAMMODE.IW],
    )
    df_results = transform_results_to_geodataframe(results)
    return df_results
