import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from milton_ian import snapshot


class SnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_all_metadata_and_only_relevant_prices_without_source_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'live.sqlite3'; out=root/'derived'; out.mkdir()
            with sqlite3.connect(source) as c:
                c.execute('CREATE TABLE contracts(platform TEXT,contract_id TEXT,event_id TEXT,series_id TEXT,title TEXT,classification TEXT,metadata_json TEXT)')
                c.execute('CREATE TABLE price_points(platform TEXT,contract_id TEXT,outcome_id TEXT,timestamp INTEGER,price TEXT)')
                c.executemany('INSERT INTO contracts VALUES(?,?,?,?,?,?,?)',[
                    ('test','a','','','Storm','hurricane_or_named_storm','{}'),
                    ('test','b','','','Will Beryl make landfall?','unclassified','{}'),
                    ('test','c','','','Unrelated','other','{}')])
                c.executemany('INSERT INTO price_points VALUES(?,?,?,?,?)',[
                    ('test',cid,'Yes',1,'.5') for cid in ('a','b','c')])
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            with patch.object(snapshot,'ROOT',root),patch.object(snapshot,'require',return_value=source),patch.object(snapshot,'output_dir',return_value=out):
                target=snapshot.run()
            with sqlite3.connect(target) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM contracts').fetchone()[0],3)
                self.assertEqual(c.execute('SELECT count(*) FROM price_points').fetchone()[0],2)
                self.assertEqual(c.execute('SELECT contract_id FROM price_points ORDER BY contract_id').fetchall(),[('a',),('b',)])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
