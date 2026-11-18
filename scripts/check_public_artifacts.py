"""Check explicit public-export schemas and exclude accidental data disclosure."""
from pathlib import Path
import re
import subprocess
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'cusip','cusip_id','trade_date','trade_time','volume','source_cache','scope_evidence',
           'bridge_evidence_json','class_title_evidence','accession','title','price','price_bond','price_market'}


def run():
    files=list((ROOT/'data/derived').glob('public_*.csv'))
    if len(files)!=8: raise ValueError('Unexpected public export set')
    for file in files:
        frame=pd.read_csv(file)
        if FORBIDDEN & set(frame.columns): raise ValueError(f'Detailed field in public export: {file}')
    pairs=pd.read_csv(ROOT/'data/derived/public_repricing_summary.csv')
    assert pairs.loc[pairs.paired_cusips.lt(5),'median_change_price_points'].isna().all()
    report=(ROOT/'docs/Hurricane_Options_Story.html').read_text()
    assert not re.search(r'\b[A-Z0-9]{8}\d\b',report), 'Possible individual CUSIP in public report'
    assert 'scope_evidence' not in report and 'cusip_id' not in report
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    for name in tracked:
        if name.startswith(('data/raw/','data/cache/')) or name.endswith(('.sqlite3','.db','.Rhistory')):
            raise ValueError(f'Private cache staged/tracked: {name}')
        if name.startswith('data/derived/') and name not in {
            'data/derived/.gitkeep','data/derived/coverage_summary_milton.csv','data/derived/coverage_summary_ian.csv',
            'data/derived/milton_contracts.csv','data/derived/hurricane_coverage_comparison.csv','data/derived/comparison_contracts.csv',
            *[str(p.relative_to(ROOT)) for p in files]}:
            raise ValueError(f'Non-allowlisted derived file: {name}')
    print('Public artifact schemas, suppression, report and tracked-file checks passed')


if __name__=='__main__': run()
