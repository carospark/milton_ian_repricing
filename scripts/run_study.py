"""Run the four-storm pipeline; network acquisition requires --acquire."""
import argparse
import os
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def source_identity(prediction_override=None):
    from milton_ian.paths import resolve_inputs
    records=[]
    for name,path in resolve_inputs().items():
        if name=='prediction_db' and prediction_override: path=prediction_override
        if path is None: continue
        stat=path.stat()
        digest=hashlib.sha256(path.read_bytes()).hexdigest() if stat.st_size<=128*1024*1024 else ''
        records.append({'input':name,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':digest})
        for suffix in ('-wal','-shm') if name=='prediction_db' else ():
            auxiliary=Path(str(path)+suffix)
            if auxiliary.exists():
                s=auxiliary.stat(); records.append({'input':name+suffix,'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'sha256':''})
    return records


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--acquire',action='store_true',help='Allow official NHC cache acquisition')
    parser.add_argument('--figures',action='store_true',help='Rebuild NOAA context figure; requires .[figures]')
    parser.add_argument('--refresh-prediction-snapshot',action='store_true',help='Freeze a new source read transaction rather than reuse the local snapshot')
    args=parser.parse_args(); env=os.environ.copy()
    from milton_ian.snapshot import run as freeze_predictions
    snapshot=ROOT/'data/raw/prediction_study_snapshot.sqlite3'
    if args.refresh_prediction_snapshot or not snapshot.exists(): snapshot=freeze_predictions()
    env['HURRICANE_PREDICTION_DB']=str(snapshot)
    started=datetime.now(timezone.utc).isoformat(); before=source_identity(snapshot)
    if not args.acquire: env['HURRICANE_OFFLINE']='1'
    else: env.pop('HURRICANE_OFFLINE',None)
    steps=[['-m','milton_ian.compare'],['-m','milton_ian.sample'],['-m','milton_ian.nhc'],
           ['-m','milton_ian.wsp']+(['--download'] if args.acquire else []),
           ['-m','milton_ian.forecast'],['-m','milton_ian.study'],['-m','milton_ian.review'],
           ['-m','milton_ian.focus'],['-m','milton_ian.loss'],['-m','milton_ian.match'],
           ['-m','milton_ian.repricing'],['-m','milton_ian.publish']]
    if args.figures:
        steps.append(['scripts/build_context_figure.py'])
        steps.append(['scripts/build_visual_summary.py'])
    steps.append(['scripts/build_story_report.py'])
    for step in steps:
        print('\nRunning '+' '.join(step),flush=True)
        subprocess.run([sys.executable,*step],cwd=ROOT,env=env,check=True)
        if step[:2]==['-m','milton_ian.wsp']:
            import pandas as pd
            inventory=pd.read_csv(ROOT/'data/derived/wsp_inventory.csv')
            if inventory.status.eq('listed_not_downloaded').any():
                raise RuntimeError('Listed WSP snapshots missing from cache; acquire them before a full rebuild')
    after=source_identity(snapshot)
    manifest={'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
              'sources_stable_during_run':before==after,'inputs_before':before,'inputs_after':after,
              'note':'Small inputs SHA256; large SQLite and sidecars checked by size/mtime, not full content hash'}
    (ROOT/'data/derived/study_run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if before!=after:
        raise RuntimeError('Source inputs changed during rebuild; outputs require a stable rerun before publication')


if __name__=='__main__': run()
