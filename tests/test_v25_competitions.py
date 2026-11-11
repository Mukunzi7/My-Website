"""Separate competition and opportunity views without migrating or deleting listings."""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlparse

import server
from test_v17 import Client


def listing_cards(page):
    return re.findall(r'<article class="listing-card">.*?</article>', page, re.S)


class CompetitionClassificationTests(unittest.TestCase):
    def test_explicit_types_and_legacy_competition_titles(self):
        samples = [
            ({'type': 'Competition', 'title': 'International Physics Realm'}, True),
            ({'type': ' Hackathon ', 'title': 'GirlCode'}, True),
            ({'type': 'Olympiad', 'title': 'International Physics'}, True),
            ({'type': 'Grant', 'title': 'Competition for Youth-Led Projects'}, True),
            ({'type': 'Opportunity', 'title': 'Mathematics Olympiad'}, True),
            ({'type': 'Opportunity', 'title': 'Regional Robotics Tournament'}, True),
            ({'type': 'Grant', 'title': 'Youth Spaces Grant'}, False),
            ({'type': 'Scholarship', 'title': 'Scholarship for Competition Winners'}, False),
            ({'type': 'Internship', 'title': 'Contest Organizer Internship'}, False),
        ]
        for item, expected in samples:
            with self.subTest(item=item): self.assertEqual(server.is_competition_listing(item), expected)

    def test_new_imports_recognize_competitions_before_funding_terms(self):
        for title, expected in [('Global Physics Olympiad', 'Competition'),
                                ('A grant competition for young inventors', 'Competition'),
                                ('Hackathon for student scholarship winners', 'Hackathon'),
                                ('Foundation Scholarship', 'Scholarship'),
                                ('Climate Research Grant', 'Grant'),
                                ('Engineering Internship', 'Internship')]:
            with self.subTest(title=title): self.assertEqual(server.infer_type(title), expected)


class CompetitionHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=3)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='70scholar-v25-test-')
        self.addCleanup(self.tmp.cleanup)
        pg_url = os.environ.get('SCHOLAR70_TEST_DATABASE_URL', '')
        if pg_url and (urlparse(pg_url).hostname or '').lower() not in ('localhost', '127.0.0.1', '::1'):
            raise RuntimeError('Only a disposable local PostgreSQL database may be used in tests.')
        for key, value in {'DATABASE_URL': pg_url, 'DB_PATH': Path(self.tmp.name) / 'db.sqlite3',
                           'UPLOAD_DIR': Path(self.tmp.name) / 'uploads', 'CLOUD_STORAGE': None,
                           'EMAIL_ENABLED': False, 'BIRD_API_KEY': '', 'SMTP_HOST': ''}.items():
            p = mock.patch.object(server, key, value); p.start(); self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'TestOwnerPassword123!', 'RENDER': ''})
        p.start(); self.addCleanup(p.stop)
        server.init_db()
        self.owner = Client(self.base)
        self.assertEqual(self.owner.post('/login', {'email': server.OWNER_ADMIN_EMAIL,
                                                   'password': 'TestOwnerPassword123!'})[0], 200)
        self.csrf = self.owner.csrf('/admin')
        self.physics = self.insert('Competition', 'International Physics Olympiad Test', 'physics global')
        self.contest_grant = self.insert('Grant', 'Competition for Renewable Energy Test', 'energy global')
        self.scholar = self.insert('Scholarship', 'Scholarship for Competition Winners Test', 'education')
        self.hack = self.insert('Hackathon', 'International Student Hackathon Test', 'coding')

    def insert(self, kind, title, tags=''):
        with server.db() as conn:
            return conn.execute('''INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                  (kind, title, 'Test organization', 'Global', 'Students', 'See official page',
                   'https://example.org/test', 'A local test listing.', tags, 'Test', server.now_iso())).lastrowid

    def get_row(self, sql, args=()):
        with server.db() as conn: return conn.execute(sql, args).fetchone()

    def student(self):
        c = Client(self.base)
        self.assertEqual(c.post('/signup', {'name': 'Test Student', 'email': 'student-v25@example.test',
                                            'password': 'StudentPassword123!'})[0], 200)
        uid = self.get_row('SELECT id FROM users WHERE email=?', ('student-v25@example.test',))['id']
        self.assertEqual(self.owner.post('/admin/user/action', {'csrf': self.csrf, 'user_id': uid,
                                                               'action': 'grant'})[0], 200)
        self.assertEqual(c.post('/login', {'email': 'student-v25@example.test',
                                           'password': 'StudentPassword123!'})[0], 200)
        return c, c.csrf()

    def test_pages_are_separate_and_legacy_contest_grants_stay_with_competitions(self):
        status, comp, _ = self.owner.get('/competitions')
        self.assertEqual(status, 200)
        comp_cards = '\n'.join(listing_cards(comp))
        for title in ('International Physics Olympiad Test', 'Competition for Renewable Energy Test',
                      'International Student Hackathon Test', 'AI for SDGs Global Youth AI Future Innovation Competition 2026',
                      'Competition for Youth-Led Projects 2026–2027', 'GirlCode Pan-African Hackathon 2026'):
            self.assertIn(server.e(title), comp_cards)
        self.assertIn('Competition · Grant', comp_cards)
        self.assertNotIn('Scholarship for Competition Winners Test', comp_cards)
        self.assertNotIn('University of Rwanda Mastercard', comp_cards)
        status, opp, _ = self.owner.get('/opportunities')
        self.assertEqual(status, 200)
        opp_cards = '\n'.join(listing_cards(opp))
        self.assertIn('Scholarship for Competition Winners Test', opp_cards)
        self.assertIn('University of Rwanda Mastercard', opp_cards)
        self.assertIn('Africa-Europe Youth Spaces Grant Program', opp_cards)
        for title in ('International Physics Olympiad Test', 'Competition for Renewable Energy Test',
                      'International Student Hackathon Test', 'Competition for Youth-Led Projects 2026–2027',
                      'GirlCode Pan-African Hackathon 2026'):
            self.assertNotIn(server.e(title), opp_cards)
        self.assertIn('href="/competitions"', opp)
        self.assertIn('href="/opportunities"', comp)
        self.assertNotIn('value="Competition">Competitions</option>', opp)
        self.assertNotIn('value="Hackathon">Hackathons</option>', opp)
        # Classification moves the cards only; it does not mutate a legacy record.
        self.assertEqual(self.get_row('SELECT type FROM opportunities WHERE id=?', (self.contest_grant,))['type'], 'Grant')

    def test_navigation_and_pages_retain_existing_sign_in_gate(self):
        anon = Client(self.base)
        status, home, _ = anon.get('/')
        self.assertEqual(status, 200)
        self.assertIn('href="/competitions"', home)
        self.assertIn('>Competitions</a>', home)
        self.assertNotIn('Competitions &amp; grants', home)
        self.assertNotIn('International Physics Olympiad Test', home)
        for path in ('/competitions', '/competitions?q=physics', '/opportunities'):
            status, _, headers = anon.get(path, follow=False)
            self.assertEqual(status, 303, path)
            self.assertTrue(headers['Location'].startswith('/login?next='), path)
        status, _, _ = anon.request('/competitions', method='HEAD', follow=False)
        self.assertEqual(status, 303)
        self.assertEqual(self.owner.get('/competitions')[0], 200)

    def test_search_and_filters_cannot_mix_the_two_sections(self):
        _, page, _ = self.owner.get('/competitions?' + urlencode({'q': 'PhYsIcS'}))
        self.assertIn('International Physics Olympiad Test', '\n'.join(listing_cards(page)))
        self.assertNotIn('Competition for Renewable Energy Test', '\n'.join(listing_cards(page)))
        _, hack, _ = self.owner.get('/competitions?type=Hackathon')
        self.assertIn('International Student Hackathon Test', '\n'.join(listing_cards(hack)))
        self.assertNotIn('International Physics Olympiad Test', '\n'.join(listing_cards(hack)))
        _, contests, _ = self.owner.get('/competitions?type=Competition')
        self.assertIn('Competition for Renewable Energy Test', '\n'.join(listing_cards(contests)))
        self.assertNotIn('International Student Hackathon Test', '\n'.join(listing_cards(contests)))
        _, malicious_type, _ = self.owner.get('/competitions?type=Scholarship')
        self.assertNotIn('Scholarship for Competition Winners Test', '\n'.join(listing_cards(malicious_type)))
        _, grants, _ = self.owner.get('/opportunities?type=Grant')
        self.assertIn('Africa-Europe Youth Spaces Grant Program', '\n'.join(listing_cards(grants)))
        self.assertNotIn('Competition for Renewable Energy Test', '\n'.join(listing_cards(grants)))
        _, escaped, _ = self.owner.get('/competitions?' + urlencode({'q':'<script>alert(1)</script>'}))
        self.assertNotIn('<script>alert(1)</script>', escaped)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', escaped)

    def test_old_competition_filter_links_redirect_safely(self):
        for old, kind in [('Competition', 'Competition'), ('Hackathon', 'Hackathon')]:
            url = '/opportunities?' + urlencode({'type': old, 'q': 'physics & maths'})
            status, _, headers = self.owner.get(url, follow=False)
            self.assertEqual(status, 303)
            location = urlparse(headers['Location'])
            self.assertEqual(location.path, '/competitions')
            self.assertEqual(parse_qs(location.query), {'type':[kind], 'q':['physics & maths']})
        # Unauthenticated visitors must still authenticate, without losing search filters.
        anon = Client(self.base)
        old_link = '/opportunities?' + urlencode({'type': 'Competition', 'q': 'physics & maths'})
        status, _, headers = anon.get(old_link, follow=False)
        self.assertEqual(status, 303)
        login_location = headers['Location']
        self.assertTrue(login_location.startswith('/login?next='))
        self.assertEqual(parse_qs(urlparse(login_location).query)['next'], [old_link])
        status, login_page, _ = anon.get(login_location)
        self.assertEqual(status, 200)
        self.assertIn('physics+%26+maths', login_page)
        status, _, headers = anon.post('/login', {'email': server.OWNER_ADMIN_EMAIL,
                                                  'password': 'TestOwnerPassword123!',
                                                  'next': old_link}, follow=False)
        self.assertEqual((status, headers['Location']), (303, old_link))
        status, _, headers = anon.get(old_link, follow=False)
        self.assertEqual(status, 303)
        self.assertEqual(parse_qs(urlparse(headers['Location']).query),
                         {'type':['Competition'], 'q':['physics & maths']})

    def test_bookmarks_return_to_correct_page_and_remain_separate_on_dashboard(self):
        csrf = self.owner.csrf('/competitions')
        for oid, target in ((self.physics, '/competitions'), (self.contest_grant, '/competitions'),
                            (self.scholar, '/opportunities')):
            status, _, headers = self.owner.post('/bookmark', {'csrf': csrf, 'opportunity_id': oid}, follow=False)
            self.assertEqual(status, 303)
            self.assertEqual(headers['Location'], target)
        _, dashboard, _ = self.owner.get('/dashboard')
        opp_section = dashboard.split('<h2>Saved opportunities</h2>', 1)[1].split('</div>', 1)[0]
        comp_section = dashboard.split('<h2>Saved competitions</h2>', 1)[1].split('</div>', 1)[0]
        self.assertIn('Scholarship for Competition Winners Test', opp_section)
        self.assertNotIn('International Physics Olympiad Test', opp_section)
        self.assertIn('International Physics Olympiad Test', comp_section)
        self.assertIn('Competition for Renewable Energy Test', comp_section)
        self.assertNotIn('Scholarship for Competition Winners Test', comp_section)
        self.assertEqual(self.owner.post('/bookmark', {'csrf': 'wrong', 'opportunity_id': self.physics}, follow=False)[0], 403)
        status, _, headers = self.owner.post('/bookmark', {'csrf': csrf, 'opportunity_id': self.physics}, follow=False)
        self.assertEqual((status, headers['Location']), (303, '/competitions'))
        self.assertEqual(self.get_row('SELECT COUNT(*) n FROM bookmarks')['n'], 2)
        for invalid in ('9' * 100, '999999999999', '-1', '²', 'not-a-number'):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.owner.post('/bookmark', {'csrf': csrf, 'opportunity_id': invalid}, follow=False)[0], 303)
        self.assertEqual(self.get_row('SELECT COUNT(*) n FROM bookmarks')['n'], 2)

    def test_owner_reviews_category_before_a_competition_is_published(self):
        c, csrf = self.student()
        title = 'International Student Innovation Event Test'
        data = {'csrf': csrf, 'type': 'Opportunity', 'title': title, 'provider': 'Test group',
                'country': 'Global', 'level': 'Students', 'deadline': 'See official page',
                'url': 'https://example.org/event', 'summary': 'A student competition for innovations.'}
        self.assertEqual(c.post('/opportunity/submit', data)[0], 200)
        sid = self.get_row('SELECT id FROM opportunity_submissions WHERE title=?', (title,))['id']
        self.assertNotIn(title, '\n'.join(listing_cards(c.get('/competitions')[1])))
        admin_page = self.owner.get('/admin')[1]
        self.assertIn('Listing type<select name=\'type\'>', admin_page)
        self.assertEqual(c.post('/admin/submission/action', {'csrf': csrf, 'submission_id': sid,
                                                             'action': 'approve', 'confirmed': '1',
                                                             'type': 'Competition'}, follow=False)[0], 403)
        invalid = self.owner.post('/admin/submission/action', {'csrf': self.csrf, 'submission_id': sid,
                                                              'action': 'approve', 'confirmed': '1', 'type': 'Invalid <type>'})
        self.assertEqual(invalid[0], 400)
        self.assertEqual(self.get_row('SELECT status FROM opportunity_submissions WHERE id=?', (sid,))['status'], 'pending')
        approved = self.owner.post('/admin/submission/action', {'csrf': self.csrf, 'submission_id': sid,
                                                               'action': 'approve', 'confirmed': '1', 'type': 'Competition'})
        self.assertEqual(approved[0], 200)
        self.assertEqual(self.get_row('SELECT type FROM opportunities WHERE title=?', (title,))['type'], 'Competition')
        self.assertEqual(self.get_row('SELECT type FROM opportunity_submissions WHERE id=?', (sid,))['type'], 'Competition')
        self.assertIn(title, '\n'.join(listing_cards(c.get('/competitions')[1])))
        self.assertNotIn(title, '\n'.join(listing_cards(c.get('/opportunities')[1])))

    def test_owner_adds_hackathon_and_restart_keeps_ids_and_saved_records(self):
        title = 'International Admin Hackathon Test'
        data = {'csrf': self.csrf, 'type': 'Hackathon', 'title': title, 'provider': 'Test organizer',
                'country': 'Global', 'level': 'Students', 'deadline': 'See official page',
                'url': 'https://example.org/hack', 'summary': 'A local test hackathon.', 'tags': 'coding'}
        self.assertEqual(self.owner.post('/admin/opportunity/add', data)[0], 200)
        oid = self.get_row('SELECT id FROM opportunities WHERE title=?', (title,))['id']
        self.assertIn(title, '\n'.join(listing_cards(self.owner.get('/competitions')[1])))
        self.assertNotIn(title, '\n'.join(listing_cards(self.owner.get('/opportunities')[1])))
        self.assertEqual(self.owner.post('/bookmark', {'csrf': self.csrf, 'opportunity_id': oid}, follow=False)[0], 303)
        def snapshot():
            with server.db() as conn:
                records = conn.execute('SELECT id,type,title,url,summary FROM opportunities ORDER BY id').fetchall()
                bookmarks = conn.execute('SELECT user_id,opportunity_id FROM bookmarks ORDER BY opportunity_id').fetchall()
                return ([tuple(r[k] for k in ('id','type','title','url','summary')) for r in records],
                        [tuple(r[k] for k in ('user_id','opportunity_id')) for r in bookmarks])
        before, saved_before = snapshot()
        server.init_db()
        after, saved_after = snapshot()
        self.assertEqual(before, after)
        self.assertEqual(saved_before, saved_after)


if __name__ == '__main__': unittest.main(verbosity=2)
