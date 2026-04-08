#!/usr/bin/env python3
"""CLI tool to check RTC-S1 accountability from SLC products."""

from datetime import datetime, timedelta

import click
from shapely.geometry import box

from .rtc_s1_accountability import check_rtc_s1_accountability


@click.command()
@click.option(
    '--start',
    type=click.DateTime(formats=['%Y-%m-%d', '%Y%m%d']),
    default=None,
    help='Start time (default: 4 days ago)',
)
@click.option(
    '--stop', type=click.DateTime(formats=['%Y-%m-%d', '%Y%m%d']), default=None, help='Stop time (default: 2 days ago)'
)
@click.option('--bbox', type=str, default=None, help='Bounding box as "minx,miny,maxx,maxy" (default: None for global)')
@click.option('--output', type=click.Path(), default=None, help='Output CSV file for missing products (optional)')
def check_rtc_s1_from_input_slcs(
    start: datetime | None = None,
    stop: datetime | None = None,
    bbox: str | None = None,
    output: str | None = None,
) -> None:
    if start is None:
        start = datetime.now() - timedelta(days=12)
    if stop is None:
        stop = datetime.now() - timedelta(days=2)

    bounds = None if bbox is None else box(*[float(x) for x in bbox.split(',')])

    df_rtc_check_deduped = check_rtc_s1_accountability(start_time=start, stop_time=stop, bbox=bounds)

    if df_rtc_check_deduped.empty:
        click.echo('No SLC products found for the specified time range and geometry.')
        return

    df_missing = df_rtc_check_deduped[df_rtc_check_deduped['rtc_opera_id'].isnull()]
    n_missing_bursts = df_missing.shape[0]
    total_bursts = df_rtc_check_deduped.shape[0]

    slc_ids_with_missing_rtc = df_missing['slc_id'].unique().tolist()
    total_slc_ids = len(df_rtc_check_deduped['slc_id'].unique().tolist())

    missing_burst_ids = df_missing['jpl_burst_id'].tolist()

    click.echo(f'{start.strftime("%Y-%m-%d")} to {stop.strftime("%Y-%m-%d")}:')

    slc_missing_str = ', '.join(slc_ids_with_missing_rtc) if slc_ids_with_missing_rtc else 'None'
    click.echo(f'SLC IDs with missing RTC-S1 ({len(slc_ids_with_missing_rtc)}/{total_slc_ids}): {slc_missing_str}')

    burst_missing_str = ', '.join(missing_burst_ids) if missing_burst_ids else 'None'
    click.echo(f'RTC-S1 Burst IDs with Missing RTC-S1 ({n_missing_bursts}/{total_bursts}): {burst_missing_str}')

    if output and n_missing_bursts > 0:
        df_missing.to_csv(output, index=False)
        click.echo(f'\nMissing products saved to: {output}')


if __name__ == '__main__':
    check_rtc_s1_from_input_slcs()
