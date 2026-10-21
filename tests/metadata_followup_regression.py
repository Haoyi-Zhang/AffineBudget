"""Run directly to check current metadata corrections against retained records."""
import copy
import csv
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('reference_audit', ROOT / 'audit_references.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class MetadataFollowupRegression(unittest.TestCase):
    def setUp(self):
        self.entries = AUDIT.parse_bib(ROOT / 'scholarly/references.bib')
        with (ROOT / 'bibliography-audit.csv').open(encoding='utf-8', newline='') as stream:
            self.historical = {row['bib_key']: row for row in csv.DictReader(stream)}

    def test_current_two_corrections_are_bound(self):
        followup = AUDIT.current_metadata_followup(self.entries, self.historical)
        self.assertEqual(set(followup['records']), {'castro2015cere', 'li2020dramsim3'})
        self.assertEqual(followup['selected_identity_count'], 2)
        self.assertFalse(followup['full_text_read_complete'])
        self.assertFalse(followup['citation_entailment_validated'])
        record = followup['records']['li2020dramsim3']
        self.assertEqual(record['historical_audit_row'], self.historical['li2020dramsim3'])
        self.assertEqual(record['current_bibliographic_record']['pages'], '106--109')

    def test_old_page_range_cannot_pass_current_binding(self):
        entries = copy.deepcopy(self.entries)
        next(row for row in entries if row['bib_key'] == 'li2020dramsim3')['pages'] = '110--113'
        with self.assertRaisesRegex(ValueError, 'DRAMsim3'):
            AUDIT.current_metadata_followup(entries, self.historical)

    def test_current_audit_preserves_local_scope(self):
        report = AUDIT.audit()
        self.assertEqual(report['status'], 'pass', report['failures'])
        self.assertEqual(report['references'], 65)
        self.assertEqual(report['current_metadata_followup_count'], 2)
        self.assertFalse(report['full_text_read_by_this_check'])
        self.assertFalse(report['citation_entailment_validated_by_this_check'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
