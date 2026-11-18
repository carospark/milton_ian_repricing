"""Self-contained, scrollable research overview from public aggregate tables."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
TABLES={'coverage':'study_coverage','timing':'timing_summary','inventory':'wsp_inventory',
        'focus':'focus_review_summary','repricing':'repricing_summary','nhc':'nhc_intensity',
        'losses':'loss_audit_summary','scope':'beryl_scope_summary'}


def build():
    data={key:json.loads(pd.read_csv(ROOT/'data/derived'/f'public_{name}.csv').to_json(orient='records'))
          for key,name in TABLES.items()}
    template=(ROOT/'scripts/templates/research_briefing.html').read_text()
    encoded=json.dumps(data,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    return template.replace('@@DATA@@',encoded)


def run():
    page=build()
    for filename in ('Hurricane_Repricing_Summary.html','Hurricane_Options_Story.html'):
        path=ROOT/'docs'/filename; path.write_text(page,encoding='utf-8'); print(path)


if __name__=='__main__': run()
