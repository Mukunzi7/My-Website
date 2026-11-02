"""Homepage Bible verse, with deterministic local date and no external runtime API."""
import re
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import server


class DailyVerseTests(unittest.TestCase):
    def test_collection_uses_public_domain_source_and_full_references(self):
        self.assertGreaterEqual(len(server.DAILY_VERSES), 30)
        refs = set()
        for passage in server.DAILY_VERSES:
            self.assertTrue(passage['text'].strip())
            self.assertRegex(passage['reference'], r'^.+ \d+:\d+$')
            self.assertRegex(passage['source'], r'^https://ebible\.org/engwebp/[A-Z0-9]+\.htm#V\d+$')
            self.assertNotIn(passage['reference'], refs)
            refs.add(passage['reference'])
        selected = {p['reference']: p['text'] for p in server.DAILY_VERSES}
        self.assertEqual(selected['Psalm 23:1'], 'The LORD is my shepherd; I shall lack nothing.')
        self.assertEqual(selected['1 Corinthians 16:14'], 'Let all that you do be done in love.')

    def test_rollover_occurs_at_midnight_in_kigali_not_midnight_utc(self):
        before = datetime(2026, 11, 2, 21, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 11, 2, 22, 0, 0, tzinfo=timezone.utc)
        first, day1 = server.daily_verse(before)
        second, day2 = server.daily_verse(after)
        self.assertEqual(day1.isoformat(), '2026-11-02')
        self.assertEqual(day2.isoformat(), '2026-11-03')
        self.assertNotEqual(first['reference'], second['reference'])
        self.assertEqual(server.daily_verse(after), server.daily_verse(after.astimezone(timezone(timedelta(hours=-5)))))
        self.assertEqual(server.daily_verse(after), server.daily_verse(after + timedelta(hours=4)))

    def test_rollover_across_leap_day_and_new_year(self):
        for start in [datetime(2028, 2, 28, 22, tzinfo=timezone.utc),
                      datetime(2028, 2, 29, 22, tzinfo=timezone.utc),
                      datetime(2028, 12, 31, 22, tzinfo=timezone.utc)]:
            (a, day_a), (b, day_b) = server.daily_verse(start), server.daily_verse(start + timedelta(days=1))
            self.assertEqual(day_b - day_a, timedelta(days=1))
            self.assertNotEqual(a['reference'], b['reference'])
        with self.assertRaisesRegex(ValueError, 'timezone-aware'):
            server.daily_verse(datetime(2028, 1, 1))

    def test_semantic_html_escapes_text_and_links_to_source(self):
        fixture = {'reference': 'Test 1:1', 'text': '<script>alert(1)</script>',
                   'source': 'https://ebible.org/engwebp/TST01.htm#V1'}
        with mock.patch.object(server, 'DAILY_VERSES', (fixture,)):
            html = server.render_daily_verse(datetime(2026, 11, 2, 22, tzinfo=timezone.utc))
        self.assertIn('aria-labelledby="daily-verse-title"', html)
        self.assertIn('<blockquote>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('datetime="2026-11-03"', html)
        self.assertIn('November 3, 2026', html)
        self.assertIn('World English Bible', html)
        self.assertIn('rel="noopener noreferrer"', html)


if __name__ == '__main__':
    unittest.main()
