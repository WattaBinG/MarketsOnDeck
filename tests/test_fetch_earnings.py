"""Unit tests for the earnings-calendar fetcher (validation + fail-closed)."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_earnings import (  # noqa: E402
    _parse_money,
    atomic_write,
    build_payload,
    parse_entry,
    validate,
)


TODAY = date(2026, 10, 9)


def _row(**kw):
    base = {
        "symbol": "JPM",
        "name": "J P Morgan Chase & Co",
        "epsForecast": "$5.94",
        "time": "time-pre-market",
        "marketCap": "$880,976,070,000",
    }
    base.update(kw)
    return base


class ParseEntry(unittest.TestCase):
    def test_bmo_slot_and_eps(self):
        e = parse_entry(_row(), "2026-10-09", "t")
        self.assertEqual(e["slot"], "BMO")
        self.assertEqual(e["epsEst"], 5.94)
        self.assertEqual(e["ticker"], "JPM")

    def test_amc_slot(self):
        e = parse_entry(_row(time="time-after-hours"), "2026-10-09", "t")
        self.assertEqual(e["slot"], "AMC")

    def test_unknown_slot_not_guessed(self):
        e = parse_entry(_row(time="time-not-supplied"), "2026-10-09", "t")
        self.assertIsNone(e["slot"])

    def test_missing_symbol_dropped(self):
        self.assertIsNone(parse_entry(_row(symbol="  "), "2026-10-09", "t"))

    def test_missing_company_dropped(self):
        self.assertIsNone(parse_entry(_row(name=""), "2026-10-09", "t"))

    def test_provenance_present(self):
        e = parse_entry(_row(), "2026-10-09", "t")
        self.assertIn("nasdaq.com", e["sourceUrl"])
        self.assertTrue(e["source"])
        self.assertEqual(e["fetchedAt"], "t")

    def test_money_parse(self):
        self.assertEqual(_parse_money("$12.90"), 12.90)
        self.assertEqual(_parse_money("-$0.44"), -0.44)
        self.assertIsNone(_parse_money("n/a"))
        self.assertIsNone(_parse_money(None))


class BuildPayload(unittest.TestCase):
    def test_today_and_week_split(self):
        # Keith's Mon-Fri "Coming up" contract (2026-10-19): on a Friday run
        # the week scope is already over, so a Saturday row does NOT appear.
        # Clock injected so the test is a pure function of its inputs.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        friday_9am = datetime(2026, 10, 9, 9, 0, tzinfo=et)
        rows = {
            "2026-10-09": [_row(symbol="AAA"), _row(symbol="BBB")],
            "2026-10-10": [_row(symbol="CCC")],
        }
        p = build_payload(TODAY, rows, now_et=friday_9am)
        self.assertEqual(p["date"], "2026-10-09")
        self.assertEqual({e["ticker"] for e in p["today"]}, {"AAA", "BBB"})
        self.assertEqual(p["weekAhead"], [])
        # Same rows on a Tuesday run: a same-week Thursday row IS coming up.
        tuesday_9am = datetime(2026, 10, 6, 9, 0, tzinfo=et)
        rows2 = {
            "2026-10-06": [_row(symbol="AAA")],
            "2026-10-08": [_row(symbol="CCC")],
        }
        p2 = build_payload(date(2026, 10, 6), rows2, now_et=tuesday_9am)
        self.assertEqual([e["ticker"] for e in p2["weekAhead"]], ["CCC"])

    def test_week_boundary_matrix(self):
        # Injected clocks pin the week scope at each boundary, including
        # Keith's Sunday 6pm ET roll-forward to next week.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        def run(day, extra_days, clock):
            rows = {day.isoformat(): [_row(symbol="TOD")]}
            for d, tick in extra_days.items():
                rows[d] = [_row(symbol=tick)]
            p = build_payload(day, rows, now_et=clock)
            return [e["ticker"] for e in p["weekAhead"]]

        # Monday Oct 5, 9am: same-week Wednesday kept, next Monday dropped.
        self.assertEqual(
            run(date(2026, 10, 5), {"2026-10-07": "WED", "2026-10-12": "NXM"},
                datetime(2026, 10, 5, 9, 0, tzinfo=et)), ["WED"])
        # Friday Oct 9, 9am: week over, nothing ahead.
        self.assertEqual(
            run(date(2026, 10, 9), {"2026-10-12": "NXM"},
                datetime(2026, 10, 9, 9, 0, tzinfo=et)), [])
        # Saturday Oct 10, 9am: still the finished week, nothing ahead.
        self.assertEqual(
            run(date(2026, 10, 10), {"2026-10-12": "NXM"},
                datetime(2026, 10, 10, 9, 0, tzinfo=et)), [])
        # Sunday Oct 11, 17:59 ET: roll has not happened yet.
        self.assertEqual(
            run(date(2026, 10, 11), {"2026-10-12": "MON", "2026-10-13": "TUE"},
                datetime(2026, 10, 11, 17, 59, tzinfo=et)), [])
        # Sunday Oct 11, 18:00 ET: rolls forward, next week's list posts.
        self.assertEqual(
            run(date(2026, 10, 11), {"2026-10-12": "MON", "2026-10-13": "TUE"},
                datetime(2026, 10, 11, 18, 0, tzinfo=et)), ["MON", "TUE"])

    def test_ranking_keeps_biggest_caps(self):
        rows = {
            "2026-10-09": [
                _row(symbol="S", marketCap="$1,000"),
                _row(symbol="L", marketCap="$9,000"),
            ]
        }
        p = build_payload(TODAY, rows)
        self.assertEqual(p["today"][0]["ticker"], "L")
        for e in p["today"]:
            self.assertNotIn("_cap", e)


class Validate(unittest.TestCase):
    def _good(self):
        return build_payload(
            TODAY,
            {
                "2026-10-09": [_row()],
                "2026-10-10": [_row(symbol="GS")],
            },
        )

    def test_good_payload(self):
        self.assertEqual(validate(self._good(), TODAY), [])

    def test_zero_usable_entries_rejected(self):
        p = self._good()
        p["today"] = []
        p["weekAhead"] = []
        errs = validate(p, TODAY)
        self.assertTrue(any("zero usable" in e for e in errs))

    def test_missing_ticker_rejected(self):
        p = self._good()
        p["today"][0]["ticker"] = ""
        self.assertTrue(any("ticker" in e for e in validate(p, TODAY)))

    def test_missing_provenance_rejected(self):
        p = self._good()
        del p["today"][0]["source"]
        self.assertTrue(any("provenance" in e for e in validate(p, TODAY)))

    def test_out_of_window_rejected(self):
        p = self._good()
        p["today"][0]["date"] = "2025-01-01"
        self.assertTrue(any("outside window" in e for e in validate(p, TODAY)))

    def test_wrong_run_date_rejected(self):
        p = self._good()
        p["date"] = "2026-10-01"
        self.assertTrue(any("run date" in e for e in validate(p, TODAY)))


class AtomicWrite(unittest.TestCase):
    def test_round_trip(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "earnings.json"
            payload = {"date": "2026-10-09", "today": []}
            atomic_write(path, payload)
            self.assertEqual(json.loads(path.read_text()), payload)
            self.assertFalse(list(Path(d).glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
