"""Tests for the HTML helpers (escaping and safe links)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui import resource_card_html, safe_url, skill_bars_html, stepper_html  # noqa: E402
from src.config import TOPICS  # noqa: E402

ITEM = dict(order=1, title="<script>alert(1)</script>", provider="Prov & Co", topic="python",
            difficulty=1, format="Course", hours=2.5, url="https://example.com/a?b=1&c=2",
            reason='Because "quotes" <b>bold</b>')


class UiTests(unittest.TestCase):
    def test_text_is_escaped(self):
        out = resource_card_html(ITEM)
        self.assertNotIn("<script>", out)
        self.assertNotIn("<b>bold</b>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_safe_url_blocks_non_http(self):
        self.assertIsNone(safe_url("javascript:alert(1)"))
        self.assertIsNone(safe_url("data:text/html,hi"))
        self.assertEqual(safe_url(" https://ok.com "), "https://ok.com")

    def test_bad_link_is_dropped(self):
        out = resource_card_html({**ITEM, "url": "javascript:alert(1)"})
        self.assertNotIn("javascript:", out)
        self.assertNotIn("<a ", out)

    def test_skill_bars_and_stepper(self):
        bars = skill_bars_html({t: 0.5 for t in TOPICS})
        self.assertEqual(bars.count('class="skill"'), len(TOPICS))
        self.assertIn("active", stepper_html(1))
        self.assertIn("done", stepper_html(2))


if __name__ == "__main__":
    unittest.main()
