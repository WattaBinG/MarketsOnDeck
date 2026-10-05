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
        block = render_earnings_block(self.data)
        self.assertIn("EARNINGS_TODAY_START", block)
        self.assertIn("<!-- EARNINGS_TODAY_END -->", block)

    def test_badge_shown_with_actual(self):
        block = render_earnings_block(self.data)
        self.assertIn("earn-badge-big-beat", block)
        self.assertIn("Big Beat", block)

    def test_no_badge_without_actual(self):
        # ACN row renders an em-dash for the missing actual, never a badge.
        block = render_earnings_block(self.data)
        acn_row = [ln for ln in block.splitlines() if "ACN" in ln][0]
        self.assertIn("&mdash;", acn_row)
        self.assertNotIn("earn-badge", acn_row)

    def test_legend_explains_jargon(self):
        block = render_earnings_block(self.data)
        self.assertIn('class="legend"', block)
        self.assertIn("Before Market Open", block)
        self.assertIn("After Market Close", block)
        self.assertIn("earnings per share", block)
        self.assertIn("Big Miss", block)

    def test_week_ahead_rendered(self):
        block = render_earnings_block(self.data)
        self.assertIn("Coming up", block)
        self.assertIn("Thu, Oct 8", block)

    def test_links_target_blank(self):
        block = render_earnings_block(self.data)
        self.assertIn('target="_blank" rel="noopener"', block)


if __name__ == "__main__":
    unittest.main()
