"""Inventory/download NHC all-basin, 0–120h cumulative wind-probability grids.

Cycle time is initialization, NOT product availability. These products combine
storms. No missing point is imputed as zero. Sampled points are geographic context,
not bond exposure weights or loss probabilities.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import re
import subprocess
import zipfile
from urllib.parse import urljoin

import pandas as pd
import shapefile
import yaml

from .nhc import fetch
from .paths import ROOT, output_dir

INDEX = 'https://www.nhc.noaa.gov/gis/archive_wsp.php'
# Fixed half-degree grid points, specified before inspecting probability values.
POINTS = {'beryl': [('houston_grid', 29.5, -95.5), ('galveston_grid', 29.5, -95.0)],
          'ian': [('fort_myers_grid', 26.5, -82.0), ('tampa_grid', 28.0, -82.5)],
          'milton': [('tampa_grid', 28.0, -82.5), ('sarasota_grid', 27.5, -82.5)],
          'idalia': [('big_bend_grid', 30.0, -83.5), ('tallahassee_grid', 30.5, -84.5)]}


def grid_values(content: bytes, cycle: str, threshold: int, points):
    """Return only exact grid-point matches; absence remains missing."""
    stem = f'{cycle}_wsp{threshold}knt120hr_halfDeg'
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if not any(name.startswith(stem) for name in z.namelist()):
            return [{'location': name, 'latitude': lat, 'longitude': lon,
                     'probability_pct': None, 'point_status': 'threshold_layer_absent_not_imputed'}
                    for name, lat, lon in points]
        metadata = z.read(stem+'.shp.xml').decode('latin1')
        if 'PWIND120' not in metadata or '0-120' not in metadata:
            raise ValueError('Unrecognized probability/horizon metadata')
        reader = shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),
                                  shx=io.BytesIO(z.read(stem+'.shx')),
                                  dbf=io.BytesIO(z.read(stem+'.dbf')))
        values = {}
        for record in reader.iterShapeRecords():
            lon, lat = record.shape.points[0]
            value = float(record.record.as_dict()['PWIND120'])
            if not 0 <= value <= 100:
                raise ValueError(f'Invalid probability: {value}')
            key = (round(lat, 6), round(lon, 6))
            if key in values:
                raise ValueError('Duplicate grid point')
            values[key] = value
    return [{'location': name, 'latitude': lat, 'longitude': lon,
             'probability_pct': values.get((lat, lon)),
             'point_status': 'observed' if (lat, lon) in values else 'absent_from_product_not_imputed'}
            for name, lat, lon in points]


def run(download=False):
    out = output_dir(); raw = ROOT/'data/raw/nhc/wsp'
    page = fetch(INDEX, raw/'index.html')
    links = sorted(set(re.findall(r'href="([^"]*\d{10}_wsp_120hrhalfDeg\.zip)"', page)))
    definitions = yaml.safe_load((ROOT/'config_comparison.yaml').read_text())['storms']
    selected = yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    inventory = []; observations = []
    for storm in selected:
        t0 = pd.Timestamp(definitions[storm]['landfall'], tz='UTC')
        # Nine complete UTC dates, landfall minus seven through plus one.
        start = t0-pd.Timedelta(days=7); end = t0+pd.Timedelta(days=2)
        candidates = {}
        for link in links:
            cycle = re.search(r'(\d{10})_wsp', link)[1]
            initialized = pd.to_datetime(cycle, format='%Y%m%d%H', utc=True)
            if not start <= initialized < end:
                continue
            candidates[cycle] = (link, initialized)
        expected = pd.date_range(start, end, freq='6h', inclusive='left')
        for initialized in expected:
            cycle = initialized.strftime('%Y%m%d%H')
            row = {'storm_context': storm, 'cycle_utc': initialized.isoformat(),
                   'scope': 'all_basins_all_active_storms', 'thresholds_knots': '34;50;64',
                   'horizon_hours': 120, 'resolution_degrees': 0.5,
                   'availability_time_utc': '', 'timing_status': 'initialization only; publication time unverified',
                   'status': 'not_listed_in_cached_index', 'source_url': '', 'sha256': ''}
            if cycle in candidates:
                link, _ = candidates[cycle]; url = urljoin(INDEX, link)
                row.update(source_url=url, status='listed_not_downloaded')
                path = raw/(cycle+'_wsp_120hrhalfDeg.zip')
                if download and not path.exists():
                    temporary = path.with_suffix('.zip.part')
                    subprocess.run(['curl', '-L', '--fail', '--silent', '--show-error', '--retry', '2', '--max-time', '40', '-o', str(temporary), url], check=True)
                    with zipfile.ZipFile(temporary) as z:
                        if z.testzip() is not None:
                            raise ValueError('Corrupt archive')
                    temporary.replace(path)
                if path.exists():
                    content = path.read_bytes(); row['sha256'] = hashlib.sha256(content).hexdigest()
                    row['status'] = 'cached_and_parsed'
                    for threshold in (34, 50, 64):
                        points = grid_values(content, cycle, threshold, POINTS[storm])
                        for point in points:
                            observations.append({**row, 'threshold_knots': threshold, **point})
            inventory.append(row)
        print(f'{storm}: {len(candidates)}/{len(expected)} cycles indexed', flush=True)
    pd.DataFrame(inventory).to_csv(out/'wsp_inventory.csv', index=False)
    pd.DataFrame(observations, columns=[*inventory[0].keys(),'threshold_knots','location',
                                      'latitude','longitude','probability_pct','point_status']).to_csv(out/'wsp_location_context.csv', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--download', action='store_true')
    run(parser.parse_args().download)
