"""Deterministic freshness tests for keyless official weekly releases."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import econ_official as eo

class OfficialTests(unittest.TestCase):
    def test_eia_release_and_week(self):
        doc = {'metadata': {'source': 'U.S. Energy Information Administration',
               'release_name': 'Weekly Petroleum Status Report', 'release_date': '2026-09-23'},
               'data': {'U.S.': {'sourcekey': 'WCESTUS1', 'units': 'thousand barrels',
               'time_series': [{'date': '2026-09-11', 'value': 423429, 'suppression_flag': None},
                               {'date': '2026-09-18', 'value': 426398, 'suppression_flag': None}]}}}
        payload = json.dumps(doc).encode()
        self.assertEqual(eo.eia(date(2026, 9, 23), payload=payload), 'crude stocks +3.0M bbl')
        self.assertEqual(eo.eia(date(2026, 9, 30), actual=False, payload=payload), 'crude stocks +3.0M bbl')
        with self.assertRaisesRegex(ValueError, 'not expected date'):
            eo.eia(date(2026, 9, 30), payload=payload)
        doc['data']['U.S.']['time_series'][-1]['date'] = '2026-09-17'
        with self.assertRaisesRegex(ValueError, 'reference week'):
            eo.eia(date(2026, 9, 23), payload=json.dumps(doc).encode())

    def test_dol_release_and_week(self):
        page = ('EMBARGOED UNTIL 8:30 A.M. (Eastern) Thursday, September 24, 2026 '
                'UNEMPLOYMENT INSURANCE WEEKLY CLAIMS SEASONALLY ADJUSTED DATA '
                'In the week ending September 19, the advance figure for seasonally adjusted '
                'initial claims was 197,000, a decrease of 1,000 from the previous week')
        with patch.object(eo, '_dol_text', return_value=page):
            self.assertEqual(eo.dol(date(2026, 9, 24), payload=b'dummy'), '197K')
            with self.assertRaisesRegex(ValueError, 'not expected date'):
                eo.dol(date(2026, 10, 1), payload=b'dummy')
        with patch.object(eo, '_dol_text', return_value=page.replace('September 19', 'September 12')):
            with self.assertRaisesRegex(ValueError, 'reference week'):
                eo.dol(date(2026, 9, 24), payload=b'dummy')

    def test_strict_mapping(self):
        self.assertEqual(eo.kind_for('Initial Jobless Claims'), 'initial_claims')
        self.assertEqual(eo.kind_for('EIA Weekly Petroleum Status Report'), 'crude_stocks')
        self.assertIsNone(eo.kind_for('EIA Weekly Natural Gas Storage Report'))

if __name__ == '__main__': unittest.main()
