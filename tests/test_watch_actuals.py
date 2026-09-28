import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import econ_bea as bea
import econ_official as official


class WatchActuals(unittest.TestCase):
    def test_bea_gdp_and_pce_guards(self):
        for kind, label, period, headline in (
            ('gdp', 'GDP (Second Estimate), 2nd Quarter 2026', '2nd Quarter 2026',
             'Real gross domestic product (GDP) increased at an annual rate of 1.5 percent in the second quarter of 2026.'),
            ('pce', 'Personal Income and Outlays, July 2026', 'July 2026',
             'From the preceding month, the PCE price index for July increased 0.2 percent.'),
        ):
            title = 'GDP (Second Estimate), 2nd Quarter 2026' if kind == 'gdp' else label
            listing = f'<tr class="release-row"><td><a href="/news/2026/example">{title}</a></td><td><time datetime="2026-08-26T08:30:00-04:00">August 26</time></td></tr>'
            page = f'EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Wednesday, August 26, 2026 {title} {headline}'
            result = bea.value(kind, label, date(2026, 8, 26), listing, page)
            self.assertIn('1.5%' if kind == 'gdp' else '0.2%', result)
            with self.assertRaises(ValueError): bea.value(kind, label, date(2026, 8, 27), listing, page)
            with self.assertRaises(ValueError): bea.value(kind, label, date(2026, 8, 26), listing, page.replace('August 26, 2026', 'August 25, 2026'))
            with self.assertRaises(ValueError): bea.value(kind, label.replace(period, '1st Quarter 2026' if kind == 'gdp' else 'June 2026'), date(2026, 8, 26), listing, page)

    def test_eia_gas_date_and_week(self):
        import json
        doc = {'release_name': 'Weekly Natural Gas Storage Report', 'release_date': '2026-Sep-24 00:00:00',
               'current_week': '2026-09-18', 'week_ago': '2026-09-11',
               'series': [{'series_id': 'png.nw2_epg0_swo_r48_bcf.w', 'source': 'U.S. Energy Information Administration',
                           'units': 'billion cubic feet', 'calculated': {'net_change': 53},
                           'data': [['2026-09-18', 3351], ['2026-09-11', 3298]]}]}
        self.assertEqual(official.eia_gas(date(2026, 9, 24), payload=json.dumps(doc)), 'natural gas +53 Bcf')
        with self.assertRaises(ValueError): official.eia_gas(date(2026, 10, 1), payload=json.dumps(doc))
        doc['current_week'] = '2026-09-11'
        with self.assertRaises(ValueError): official.eia_gas(date(2026, 9, 24), payload=json.dumps(doc))


if __name__ == '__main__': unittest.main()
