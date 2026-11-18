"""Cache official forecast advisories and extract their stated issue times.

Issue times are NOT verified publication times. Corrected archive products can
replace original versions; they must not establish intraday information precedence.
Wind probabilities are a separate acquisition, not inferred from forecast tracks.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import yaml

from .paths import ROOT, output_dir


def parse_advisory(page: str) -> dict:
    match = re.search(r'<pre[^>]*>(.*?)</pre>', page, re.S | re.I)
    if not match:
        raise ValueError('Missing advisory text')
    body = html.unescape(re.sub(r'<[^>]+>', '', match[1]))
    stamp = re.search(r'^(\d{4}) UTC \w{3} (\w{3})\s+(\d{1,2}) (\d{4})\s*$', body, re.M)
    number = re.search(r'FORECAST/ADVISORY NUMBER\s+(\d+)', body)
    if not stamp or not number:
        raise ValueError('Unrecognized advisory number or UTC issue time')
    hm, month, day, year = stamp.groups()
    months = {m.upper(): i for i, m in enumerate(calendar.month_abbr) if m}
    issued = datetime(int(year), months[month], int(day), int(hm[:2]), int(hm[2:]), tzinfo=timezone.utc)
    return {'advisory_number': int(number[1]), 'issue_time_utc': issued.isoformat(),
            'corrected': 'CORRECTED' in body.upper(),
            'timing_status': 'stated issue time; publication time unverified',
            'text': body}


def fetch(url: str, path: Path):
    if not path.exists():
        if os.environ.get('HURRICANE_OFFLINE')=='1':
            raise FileNotFoundError(f'Offline cache missing: {path}; acquire NHC sources explicitly')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.part')
        subprocess.run(['curl', '-L', '--fail', '--silent', '--show-error',
                        '--retry', '2', '--max-time', '40', '-o', str(temporary), url], check=True)
        temporary.replace(path)
    return path.read_text()


def run(storms=None):
    definitions = yaml.safe_load((ROOT/'config_comparison.yaml').read_text())['storms']
    selected = yaml.safe_load((ROOT/'config_study.yaml').read_text())['storms']
    records = []
    for storm in storms or selected:
        if storm not in selected:
            raise ValueError(f'{storm} is outside the selected study')
        definition = definitions[storm]; sid = definition['nhc_id']
        base = f'https://www.nhc.noaa.gov/archive/{sid[4:]}/{sid[:4]}/'
        cache = ROOT/'data/raw/nhc'/storm
        page = fetch(base, cache/'index.html')
        links = sorted(set(re.findall(r'href=[\"\x27]([^\"\x27]*' + sid + r'\.fstadv\.\d+\.shtml)[\"\x27]', page)))
        if not links:
            raise ValueError(f'No forecast advisory links found for {storm}')
        for link in links:
            url = urljoin(base, link); path = cache/Path(link).name
            text = fetch(url, path); parsed = parse_advisory(text)
            (cache/(path.stem+'.txt')).write_text(parsed.pop('text'))
            records.append({'storm': storm, 'source_url': url, 'cache_path': str(path.relative_to(ROOT)),
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **parsed})
        print(f'{storm}: {len(links)} forecast advisories cached', flush=True)
    frame = pd.DataFrame(records)
    if frame.duplicated(['storm', 'advisory_number']).any():
        raise ValueError('Duplicate storm/advisory identity')
    # Merge incremental acquisitions without discarding other selected storms.
    target = output_dir()/'nhc_advisories.csv'
    if target.exists():
        old = pd.read_csv(target)
        frame = pd.concat([old[~old.storm.isin(frame.storm.unique())], frame], ignore_index=True)
    frame.sort_values(['storm', 'issue_time_utc']).to_csv(target, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--storms', nargs='+')
    run(parser.parse_args().storms)
