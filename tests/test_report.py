import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_story_report',ROOT/'scripts/build_story_report.py')
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class Structure(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.anchors=[];self.dependencies=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag=='a' and attrs.get('href','').startswith('#'):self.anchors.append(attrs['href'][1:])
        if tag in ('img','iframe') or (tag=='script' and 'src' in attrs) or (tag=='link' and attrs.get('rel')=='stylesheet'):
            self.dependencies.append(tag)


class ReportTests(unittest.TestCase):
    def test_standalone_report_has_working_anchor_structure_and_no_external_assets(self):
        page=report.build(); parser=Structure();parser.feed(page)
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertTrue(set(parser.anchors)<=set(parser.ids))
        self.assertEqual(parser.dependencies,[])
        self.assertNotIn('@@DATA@@',page)
        data=json.loads(re.search(r'const DATA=(.*?);\nconst names=',page,re.S)[1])
        self.assertEqual({r['storm'] for r in data['coverage']},{'ian','milton','idalia','beryl'})

    def test_summary_matches_generator_and_options_file_is_absent(self):
        expected=report.build()
        self.assertEqual((ROOT/'docs/Hurricane_Repricing_Summary.html').read_text(),expected)
        self.assertFalse((ROOT/'docs/Hurricane_Options_Story.html').exists())
