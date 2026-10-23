"""Unit tests for the earnings badge thresholds and block rendering."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from refresh_earnings import (
    BIG_BEAT_SURPRISE,
    BIG_MISS_SURPRISE,
    badge_for,
    render_earnings_block,
)


class BadgeThresholds(unittest.TestCase):
    def test_big_beat(self):
        self.assertEqual(badge_for(0.50, 0.44), "Big Beat")

    def test_beat(self):
        self.assertEqual(badge_for(0.46, 0.44), "Beat")

    def test_inline_above(self):
        self.assertEqual(badge_for(0.445, 0.44), "In-line")

    def test_inline_below(self):
        self.assertEqual(badge_for(0.435, 0.44), "In-line")

    def test_miss(self):
        self.assertEqual(badge_for(0.41, 0.44), "Miss")

    def test_big_miss(self):
        self.assertEqual(badge_for(0.38, 0.44), "Big Miss")

    def test_boundary_big_beat_is_strict(self):
        # Exactly +10% is a Beat; only strictly greater is a Big Beat.
        self.assertEqual(badge_for(1.10, 1.00), "Beat")
        self.assertEqual(badge_for(1.101, 1.00), "Big Beat")

    def test_boundary_big_miss_is_strict(self):
        # Exactly -10% is a Miss; only strictly worse is a Big Miss.
        self.assertEqual(badge_for(0.90, 1.00), "Miss")
        self.assertEqual(badge_for(0.899, 1.00), "Big Miss")

    def test_negative_estimate_beats(self):
        # Smaller-than-expected loss is a beat.
        self.assertEqual(badge_for(-0.02, -0.04), "Big Beat")

    def test_no_actual_gives_no_badge(self):
        self.assertIsNone(badge_for(None, 0.44))

    def test_no_estimate_gives_no_badge(self):
        self.assertIsNone(badge_for(0.50, None))

    def test_zero_estimate_gives_no_badge(self):
        self.assertIsNone(badge_for(0.50, 0))

    def test_threshold_constants_sane(self):
        self.assertGreater(BIG_BEAT_SURPRISE, 0)
        self.assertLess(BIG_MISS_SURPRISE, 0)


class BlockRendering(unittest.TestCase):
    def setUp(self):
        self.data = {
            "date": "2026-10-01",
            "dateLabel": "Thursday, October 1",
            "today": [
                {
                    "ticker": "NKE", "company": "NIKE, Inc.", "slot": "AMC",
                    "epsEst": 0.44, "actualEps": 0.50,
                    "link": "https://investors.nike.com",
                },
                {
                    "ticker": "ACN", "company": "Accenture plc", "slot": "BMO",
                    "epsEst": 3.18, "actualEps": None,
                    "link": "http://investor.accenture.com",
                },
            ],
            "weekAhead": [
                {
                    "date": "2026-10-08", "dayLabel": "Thu, Oct 8",
                    "ticker": "PEP", "company": "PepsiCo, Inc.", "slot": "BMO",
                    "epsEst": None, "link": "https://www.pepsico.com/investors",
                },
            ],
        }

    def test_markers_present(self):
        block = render_earnings_block(self.data, today=self.data["date"])
        self.assertIn("EARNINGS_TODAY_START", block)
        self.assertIn("<!-- EARNINGS_TODAY_END -->", block)

    def test_badge_shown_with_actual(self):
        block = render_earnings_block(self.data, today=self.data["date"])
        self.assertIn("earn-badge-big-beat", block)
        self.assertIn("Big Beat", block)

    def test_no_badge_without_actual(self):
        # ACN row renders an em-dash for the missing actual, never a badge.
        block = render_earnings_block(self.data, today=self.data["date"])
        acn_row = [ln for ln in block.splitlines() if "ACN" in ln][0]
        self.assertIn("&mdash;", acn_row)
        self.assertNotIn("earn-badge", acn_row)

    def test_legend_explains_jargon(self):
        block = render_earnings_block(self.data, today=self.data["date"])
        self.assertIn('class="legend"', block)
        self.assertIn("Before Market Open", block)
        self.assertIn("After Market Close", block)
        self.assertIn("earnings per share", block)
        self.assertIn("Big Miss", block)

    def test_week_ahead_rendered(self):
        block = render_earnings_block(self.data, today=self.data["date"])
        self.assertIn("Coming up", block)
        self.assertIn("Thu, Oct 8", block)

    def test_links_target_blank(self):
        block = render_earnings_block(self.data, today=self.data["date"])
        self.assertIn('target="_blank" rel="noopener"', block)


class EarningsRollover(unittest.TestCase):
    def test_old_schedule_is_not_today(self):
        block = render_earnings_block({"date":"2026-10-01"}, today="2026-10-07")
        self.assertIn("No current earnings feed", block)
        self.assertNotIn("Earnings Today", block)
        self.assertNotIn("earn-list", block)



class RenderDatePin(unittest.TestCase):
    """The box can never wear a fresher date than the feed behind it."""

    def _feed(self):
        return {
            "date": "2026-10-05",
            "dateLabel": "Monday, October 05",
            "today": [
                {"ticker": "XYZ", "company": "Xylem Test Co", "slot": "BMO",
                 "epsEst": 1.00, "actualEps": None,
                 "link": "https://example.com", "date": "2026-10-05"},
            ],
            "weekAhead": [],
        }

    def test_box_date_equals_feed_date(self):
        # Rendering with no explicit date must pin to the feed date, not the
        # wall clock - even days later.
        block = render_earnings_block(self._feed())
        self.assertIn('data-earn-date="2026-10-05"', block)
        self.assertIn("XYZ", block)

    def test_render_index_uses_feed_date(self):
        import tempfile
        feed = self._feed()
        with tempfile.TemporaryDirectory() as d:
            idx = Path(d) / "index.html"
            idx.write_text("a <!-- EARNINGS_TODAY_START -->old<!-- EARNINGS_TODAY_END --> b")
            from refresh_earnings import render_index
            render_index(idx, feed)
            out = idx.read_text()
        self.assertIn('data-earn-date="2026-10-05"', out)
        self.assertIn("XYZ", out)


class StateSeparation(unittest.TestCase):
    """A genuinely empty CURRENT week is not the same thing as a stale feed."""

    def test_fresh_empty_week_is_not_stale(self):
        block = render_earnings_block(
            {"date": "2026-10-05", "today": [], "weekAhead": []},
            today="2026-10-05")
        self.assertIn("No major earnings", block)
        self.assertNotIn("No current earnings feed", block)

    def test_stale_feed_says_so(self):
        block = render_earnings_block({"date": "2026-10-01"}, today="2026-10-07")
        self.assertIn("No current earnings feed", block)
        self.assertIn("Last schedule: 2026-10-01", block)
        self.assertNotIn("Earnings Today", block)

    def test_undated_rows_render_on_feed_date(self):
        # Legacy/hand-seeded rows with no 'date' belong to the feed date and
        # must not vanish silently.
        block = render_earnings_block(
            {"date": "2026-10-05",
             "today": [{"ticker": "LEG", "company": "Legacy Row Co",
                        "slot": None, "epsEst": None, "actualEps": None,
                        "link": "https://example.com"}],
             "weekAhead": []})
        self.assertIn("LEG", block)


if __name__ == "__main__":
    unittest.main()
