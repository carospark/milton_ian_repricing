import hashlib
import importlib.util
from pathlib import Path
import re
import unittest
from test_report import Structure

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_status_report',ROOT/'scripts/build_status_report.py')
status=importlib.util.module_from_spec(spec);spec.loader.exec_module(status)


class StatusReportTests(unittest.TestCase):
    def test_status_edition_preserves_original_and_embedded_data(self):
        path=ROOT/'docs/Hurricane_Repricing_Summary.html'
        original=path.read_text(); digest=hashlib.sha256(path.read_bytes()).hexdigest()
        alternate=status.build()
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
        extract=lambda page:re.search(r'const DATA=(.*?);\nconst names=',page,re.S)[1]
        self.assertEqual(extract(original),extract(alternate))
        self.assertEqual((ROOT/'docs/Hurricane_Repricing_Status.html').read_text(),alternate)

    def test_status_edition_has_unique_anchors_offline_assets_and_table_controls(self):
        page=status.build(); parser=Structure();parser.feed(page)
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertTrue(set(parser.anchors)<=set(parser.ids))
        self.assertEqual(parser.dependencies,[])
        self.assertNotIn('@@RUNTIME@@',page)
        self.assertIn('prefers-color-scheme:dark',page)
        self.assertIn('data-table="forecast-detail"',page)
