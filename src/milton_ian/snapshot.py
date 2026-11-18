"""Freeze complete contract metadata and study-relevant price rows in one RO transaction.

The live archive can keep updating. Source SQLite is never modified. The local
snapshot omits unrelated price histories, raw price payloads and execution tables;
its scope is explicit in its ignored manifest. No prediction trades are inferred.
"""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from .paths import ROOT, require, output_dir

NAMED=re.compile(r'\b(?:ian|milton|idalia|beryl)\b',re.I)


def run():
    source_path=require('prediction_db'); folder=ROOT/'data/raw'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/'prediction_study_snapshot.sqlite3'
    temporary=folder/'prediction_study_snapshot.partial.sqlite3'
    if temporary.exists():
        raise FileExistsError(f'Incomplete snapshot exists; inspect before retrying: {temporary}')
    started=datetime.now(timezone.utc).isoformat()
    source=sqlite3.connect(f'file:{source_path}?mode=ro',uri=True)
    source.execute('PRAGMA query_only=ON'); source.execute('BEGIN')
    destination=sqlite3.connect(temporary)
    destination.execute('PRAGMA journal_mode=OFF'); destination.execute('PRAGMA synchronous=OFF')
    schema=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='contracts'").fetchone()[0]
    destination.execute(schema)
    destination.execute('CREATE TABLE price_points(platform TEXT,contract_id TEXT,outcome_id TEXT,timestamp INTEGER,price TEXT,PRIMARY KEY(platform,contract_id,outcome_id,timestamp))')
    cursor=source.execute('SELECT * FROM contracts'); columns=[x[0] for x in cursor.description]
    slots=','.join('?' for _ in columns); relevant=[]; contracts=0; prices=0
    while True:
        batch=cursor.fetchmany(500)
        if not batch: break
        destination.executemany(f'INSERT INTO contracts VALUES({slots})',batch)
        contracts+=len(batch)
        for record in batch:
            row=dict(zip(columns,record))
            searchable=' '.join(str(row.get(k) or '') for k in ('contract_id','event_id','series_id','title','metadata_json'))
            if 'hurricane_or_named_storm' in str(row['classification']) or str(row['contract_id']).startswith('HUR') or NAMED.search(searchable) or str(row['contract_id'])=='509459':
                relevant.append((row['platform'],row['contract_id']))
        if contracts%10000==0: print(f'Copied {contracts} contract metadata rows',flush=True)
    destination.commit()
    for platform,cid in relevant:
        query=source.execute('SELECT platform,contract_id,outcome_id,timestamp,price FROM price_points WHERE platform=? AND contract_id=?',(platform,cid))
        while True:
            batch=query.fetchmany(5000)
            if not batch: break
            destination.executemany('INSERT INTO price_points VALUES(?,?,?,?,?)',batch); prices+=len(batch)
    destination.commit(); source.rollback(); source.close()
    result=destination.execute('PRAGMA quick_check').fetchone()[0]
    if result!='ok': raise ValueError(f'Snapshot check failed: {result}')
    destination.close(); temporary.replace(target)
    digest=hashlib.sha256()
    with target.open('rb') as handle:
        for block in iter(lambda:handle.read(8*1024*1024),b''): digest.update(block)
    manifest={'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
              'source_path':str(source_path),'snapshot_path':str(target),'snapshot_sha256':digest.hexdigest(),
              'complete_contract_metadata_rows':contracts,'selected_price_contracts':len(relevant),'selected_price_rows':prices,
              'scope':'All contract metadata; prices for hurricane classification, HUR identifiers, named-storm metadata matches and explicit broad proxy. No execution tables or raw price payloads.',
              'consistency':'single source read-only SQLite transaction; concurrent source writes allowed'}
    (output_dir()/'prediction_snapshot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_path','snapshot_path')},indent=2))
    return target


if __name__=='__main__': run()
