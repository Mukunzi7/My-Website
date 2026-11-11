"""Account-email and password-control regressions using disposable databases only."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import urlparse

import server
from test_v17 import Client


class Controls(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.inputs = {}
        self.buttons = {}
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('type') == 'password':
            self.inputs[attrs.get('id')] = attrs
        if tag == 'button' and 'data-password-toggle' in attrs:
            self.buttons[attrs.get('aria-controls')] = attrs


class LinkAndDiagnosticsTests(unittest.TestCase):
    def test_base_precedence_and_never_uses_request_host(self):
        self.assertEqual(server.choose_app_base_url({'APP_BASE_URL': ' https://custom.example.org/ ',
                                                     'RENDER_EXTERNAL_URL': 'https://fallback.onrender.com/'}),
                         'https://custom.example.org')
        self.assertEqual(server.choose_app_base_url({'APP_BASE_URL': '   ',
                                                     'RENDER_EXTERNAL_URL': 'https://fallback.onrender.com/'}),
                         'https://fallback.onrender.com')
        self.assertEqual(server.choose_app_base_url({'HTTP_HOST': 'attacker.invalid'}),
                         f'http://{server.HOST}:{server.PORT}')

    def test_https_guard_rejects_obviously_unsafe_or_unusable_link_bases(self):
        valid = ['https://seven0scholar-7cjc.onrender.com', 'https://school.example.org/',
                 'https://example.org:443', 'https://1.1.1.1', 'https://[2606:4700:4700::1111]']
        invalid = ['', 'http://example.org', 'https://localhost', 'https://host.local',
                   'https://127.0.0.1', 'https://10.1.2.3', 'https://192.168.001.001',
                   'https://[::1]', 'https://user:pass@example.org', 'https://example.org:bad',
                   'https://example.org:99999', 'https://example.org:0', 'https://example.org:',
                   'https://example.org/somewhere', 'https://example.org?x=1',
                   'https://example.org?', 'https://example.org#section', 'https://example.org#',
                   'https://not..a.domain', 'https://-wrong.example.org',
                   'https://example.org\\evil.com', 'https://example.org\n.evil.com']
        for value in valid:
            with self.subTest(valid=value): self.assertTrue(server.is_public_https_url(value))
        for value in invalid:
            with self.subTest(invalid=value): self.assertFalse(server.is_public_https_url(value))
        with mock.patch.dict(os.environ, {'RENDER': 'true'}), mock.patch.object(server, 'APP_BASE_URL', 'http://localhost:8080'):
            with self.assertRaises(RuntimeError): server.require_valid_email_link_base()
        with mock.patch.dict(os.environ, {'RENDER': ''}), mock.patch.object(server, 'APP_BASE_URL', 'http://localhost:8080'):
            server.require_valid_email_link_base()  # Local development remains usable.

    def test_diagnostics_contain_only_safe_categories(self):
        key = 'bk_us1_SUPERSECRET_KEY_SENTINEL'
        sender = 'secret-sender@example.org'
        with mock.patch.object(server, 'BIRD_API_KEY', key), mock.patch.object(server, 'BIRD_FROM', sender), \
             mock.patch.object(server, 'BIRD_REGION', 'eu1'), mock.patch.object(server, 'SMTP_HOST', ''), \
             mock.patch.object(server, 'APP_BASE_URL', 'https://school.example.org'):
            diag = server.email_setup_diagnostics()
            self.assertEqual((diag['provider'], diag['sender_mode'], diag['bird_region']), ('bird', 'custom', 'mismatch'))
            self.assertTrue(diag['public_https_link'])
            text = json.dumps(diag)
            for secret in (key, sender, 'school.example.org'):
                self.assertNotIn(secret, text)
        with mock.patch.object(server, 'BIRD_API_KEY', key), mock.patch.object(server, 'BIRD_FROM', 'onboarding@messagebird.dev'), \
             mock.patch.object(server, 'BIRD_REGION', ''):
            self.assertEqual(server.email_setup_diagnostics()['sender_mode'], 'sandbox')
        with mock.patch.object(server, 'BIRD_API_KEY', ''), mock.patch.object(server, 'SMTP_HOST', 'private-smtp.example.org'), \
             mock.patch.object(server, 'SMTP_FROM', 'noreply@70scholar.local'), mock.patch.object(server, 'SMTP_PORT', 587), \
             mock.patch.dict(os.environ, {'RENDER': 'true'}):
            diag = server.email_setup_diagnostics()
            self.assertEqual((diag['provider'], diag['sender_mode']), ('smtp', 'missing'))
            self.assertTrue(diag['render_smtp_restricted_port'])
            self.assertNotIn('private-smtp.example.org', json.dumps(diag))


class AccountEmailHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='70scholar-v24-test-')
        self.addCleanup(self.tmp.cleanup)
        # A PostgreSQL test URL, when explicitly set, must refer to a disposable local server.
        pg_url = os.environ.get('SCHOLAR70_TEST_DATABASE_URL', '')
        if pg_url and (urlparse(pg_url).hostname or '').lower() not in ('127.0.0.1', 'localhost', '::1'):
            raise RuntimeError('Tests must never use a non-local PostgreSQL database.')
        values = {'DB_PATH': Path(self.tmp.name) / 'test.sqlite3', 'UPLOAD_DIR': Path(self.tmp.name) / 'uploads',
                  'DATABASE_URL': pg_url, 'CLOUD_STORAGE': None, 'EMAIL_ENABLED': False,
                  'BIRD_API_KEY': '', 'BIRD_FROM': 'onboarding@messagebird.dev', 'BIRD_REGION': '',
                  'SMTP_HOST': '', 'APP_BASE_URL': self.base}
        for key, value in values.items():
            patcher = mock.patch.object(server, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'TestOwnerPassword123!', 'RENDER': ''})
        patcher.start()
        self.addCleanup(patcher.stop)
        server.init_db()
        self.owner = Client(self.base)
        self.assertEqual(self.owner.post('/login', {'email': server.OWNER_ADMIN_EMAIL,
                                                   'password': 'TestOwnerPassword123!'})[0], 200)
        self.csrf = self.owner.csrf('/admin')

    def row(self, sql, values=()):
        with server.db() as conn:
            return conn.execute(sql, values).fetchone()

    def result(self):
        row = self.row("SELECT value FROM settings WHERE key='system_email_last_test_v1'")
        return None if row is None else json.loads(row['value'])

    def student(self):
        client = Client(self.base)
        status, _, _ = client.post('/signup', {'name': 'Learner', 'email': 'learner@example.test',
                                               'password': 'StudentPassword123!'})
        self.assertEqual(status, 200)
        uid = self.row('SELECT id FROM users WHERE email=?', ('learner@example.test',))['id']
        self.assertEqual(self.owner.post('/admin/user/action', {'csrf': self.csrf, 'user_id': uid,
                                                               'action': 'grant'})[0], 200)
        self.assertEqual(client.post('/login', {'email': 'learner@example.test',
                                               'password': 'StudentPassword123!'})[0], 200)
        return client, uid

    def test_all_password_forms_masked_without_js_and_have_unique_accessible_controls(self):
        expected = {
            '/signup': {'signup-password': ('password', 'new-password')},
            '/login': {'login-password': ('password', 'current-password')},
            '/reset-password?token=fake': {'reset-password': ('password', 'new-password')},
            '/account': {'account-current-password': ('current_password', 'current-password'),
                         'account-new-password': ('new_password', 'new-password')},
        }
        all_ids = set()
        for path, fields in expected.items():
            status, html, _ = self.owner.get(path)
            self.assertEqual(status, 200)
            controls = Controls(html)
            self.assertEqual(set(controls.inputs), set(fields), path)
            self.assertEqual(set(controls.buttons), set(fields), path)
            for field_id, (name, autocomplete) in fields.items():
                self.assertNotIn(field_id, all_ids)
                all_ids.add(field_id)
                field, button = controls.inputs[field_id], controls.buttons[field_id]
                self.assertEqual((field['name'], field['autocomplete']), (name, autocomplete))
                self.assertIn('required', field)
                self.assertIn('hidden', button)  # It becomes available only if JS initializes.
                self.assertEqual(button['type'], 'button')
                self.assertTrue(button['aria-label'].startswith('Show '))
        self.assertIn('email, not SMS', self.owner.get('/signup')[1])

    def test_startup_stores_only_sanitized_diagnostics(self):
        key = 'bk_eu1_SUPERSECRET_SENTINEL'
        with mock.patch.object(server, 'BIRD_API_KEY', key), mock.patch.object(server, 'BIRD_FROM', 'hidden-sender@example.org'), \
             mock.patch.object(server, 'APP_BASE_URL', 'https://mysite.example.org'):
            server.init_db()
        raw = self.row("SELECT value FROM settings WHERE key='system_email_setup_diagnostics_v1'")['value']
        diag = json.loads(raw)
        self.assertEqual((diag['provider'], diag['sender_mode']), ('bird', 'custom'))
        self.assertTrue(diag['public_https_link'])
        for private in (key, 'hidden-sender@example.org', 'mysite.example.org'):
            self.assertNotIn(private, raw)

    def test_invalid_production_base_never_sends_a_token_or_grants_access(self):
        student = Client(self.base)
        real_guard = server.require_valid_email_link_base
        def production_guard():
            # Simulate Render only while checking the link. The disposable local
            # PostgreSQL connection must remain subject to its own local guard.
            with mock.patch.dict(os.environ, {'RENDER': 'true'}): real_guard()
        with mock.patch.object(server, 'require_valid_email_link_base', side_effect=production_guard), \
             mock.patch.object(server, 'APP_BASE_URL', 'http://localhost:8080'), \
             mock.patch.object(server, 'EMAIL_ENABLED', True), \
             mock.patch.object(server, 'send_email') as send:
            status, html, _ = student.post('/signup', {'name': 'Local Link', 'email': 'local-link@example.test',
                                                       'password': 'StudentPassword123!'})
            self.assertEqual(status, 200)
            self.assertIn('not yet verified', html)
            self.assertEqual(student.post('/login', {'email': 'local-link@example.test',
                                                    'password': 'StudentPassword123!'})[0], 403)
            send.assert_not_called()
        row = self.row('SELECT id,email_verified,admin_approved FROM users WHERE email=?', ('local-link@example.test',))
        self.assertEqual((row['email_verified'], row['admin_approved']), (0, 0))
        self.assertEqual(self.row('SELECT count(*) n FROM email_tokens WHERE user_id=?', (row['id'],))['n'], 0)

    def test_successful_verification_and_reset_are_single_use_and_invalidate_sessions(self):
        student = Client(self.base)
        sent = []
        def fake_send(email, subject, body, html_body=None):
            sent.append((email, subject, body))
        real_guard = server.require_valid_email_link_base
        def production_guard():
            with mock.patch.dict(os.environ, {'RENDER': 'true'}): real_guard()
        with mock.patch.object(server, 'require_valid_email_link_base', side_effect=production_guard), \
             mock.patch.object(server, 'APP_BASE_URL', 'https://seven0scholar-7cjc.onrender.com'), \
             mock.patch.object(server, 'EMAIL_ENABLED', True), mock.patch.object(server, 'send_email', side_effect=fake_send):
            status, html, _ = student.post('/signup', {'name': 'Email Learner', 'email': 'mail@example.test',
                                                       'password': 'StudentPassword123!'})
            self.assertEqual(status, 200)
            self.assertIn('requested', html)
            self.assertIn('spam', html)
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0][0], 'mail@example.test')
            link = re.search(r'https://seven0scholar-7cjc\.onrender\.com(/verify-email\?token=[^\s]+)', sent[0][2]).group(1)
            token = link.split('token=', 1)[1]
            row = self.row('SELECT token_hash FROM email_tokens WHERE purpose=?', ('verify_email',))
            self.assertNotEqual(row['token_hash'], token)
            self.assertEqual(student.get(link)[0], 200)
            self.assertEqual(student.get(link)[0], 400)
            self.assertEqual(student.post('/login', {'email': 'mail@example.test',
                                                    'password': 'StudentPassword123!'})[0], 200)
            self.assertEqual(student.post('/forgot-password', {'email': 'mail@example.test'})[0], 200)
            self.assertEqual(len(sent), 2)
            reset_token = re.search(r'/reset-password\?token=([^\s]+)', sent[1][2]).group(1)
            self.assertEqual(student.post('/reset-password', {'token': reset_token,
                                                              'password': 'NewPassword123!'})[0], 200)
            self.assertEqual(student.get('/dashboard', follow=False)[0], 303)
            self.assertEqual(student.post('/reset-password', {'token': reset_token,
                                                              'password': 'AnotherPassword123!'})[0], 400)
            self.assertEqual(student.post('/login', {'email': 'mail@example.test',
                                                    'password': 'NewPassword123!'})[0], 200)

    def test_only_owner_with_valid_csrf_and_origin_can_send_test(self):
        student, _ = self.student()
        student_csrf = student.csrf()
        anonymous = Client(self.base)
        with mock.patch.object(server, 'EMAIL_ENABLED', True), mock.patch.object(server, 'send_email') as send:
            self.assertEqual(anonymous.post('/admin/email/test', {'csrf': self.csrf}, follow=False)[0], 303)
            self.assertEqual(student.post('/admin/email/test', {'csrf': student_csrf}, follow=False)[0], 403)
            self.assertEqual(self.owner.post('/admin/email/test', {'csrf': 'wrong'}, follow=False)[0], 403)
            self.assertEqual(self.owner.request('/admin/email/test', data={'csrf': self.csrf}, follow=False,
                                                headers={'Origin': 'https://attacker.invalid'})[0], 403)
            send.assert_not_called()
            self.assertIsNone(self.result())
            status, html, _ = self.owner.post('/admin/email/test', {'csrf': self.csrf, 'email': 'attacker@example.test'})
            self.assertEqual(status, 200)
            self.assertIn('provider accepted', html)
            self.assertIn('does not guarantee delivery', html)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[0], server.OWNER_ADMIN_EMAIL)
            self.assertEqual(self.result()['status'], 'provider_accepted')
        self.assertEqual(student.get('/admin', follow=False)[0], 403)

    def test_test_results_and_failure_logs_do_not_expose_provider_secrets(self):
        secret = 'EXAMPLE_SECRET_DO_NOT_EXPOSE'
        http_error = HTTPError('https://provider.invalid/?key=' + secret, 401, secret, {}, io.BytesIO(secret.encode()))
        for problem, expected in [(http_error, 'provider_rejected'), (RuntimeError(secret), 'failed')]:
            with self.subTest(expected=expected), mock.patch.object(server, 'EMAIL_ENABLED', True), \
                 mock.patch.object(server, 'BIRD_API_KEY', 'bk_us1_' + secret), \
                 mock.patch.object(server, 'BIRD_FROM', secret + '@example.org'), \
                 mock.patch.object(server, 'send_email', side_effect=problem):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    status, html, _ = self.owner.post('/admin/email/test', {'csrf': self.csrf})
                self.assertEqual(status, 200)
                result = self.result()
                self.assertEqual(result['status'], expected)
                if expected == 'provider_rejected': self.assertEqual(result['http_status'], 401)
                self.assertNotIn(secret, json.dumps(result))
                self.assertNotIn(secret, html)
                self.assertNotIn(secret, stderr.getvalue())
        with mock.patch.object(server, 'EMAIL_ENABLED', False), mock.patch.object(server, 'send_email') as send:
            status, html, _ = self.owner.post('/admin/email/test', {'csrf': self.csrf})
            self.assertEqual(status, 200)
            self.assertIn('No email provider is configured', html)
            self.assertEqual(self.result()['status'], 'not_configured')
            send.assert_not_called()

    def test_account_email_failures_are_generic_and_do_not_verify(self):
        secret = 'PROVIDER_RAW_EXCEPTION_SECRET'
        student = Client(self.base)
        with mock.patch.object(server, 'EMAIL_ENABLED', True), \
             mock.patch.object(server, 'send_email', side_effect=RuntimeError(secret)):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status, html, _ = student.post('/signup', {'name': 'Delivery Failed', 'email': 'failed@example.test',
                                                           'password': 'StudentPassword123!'})
                self.assertEqual(status, 200)
                self.assertIn('not yet verified', html)
                self.assertEqual(student.post('/login', {'email': 'failed@example.test',
                                                        'password': 'StudentPassword123!'})[0], 403)
                self.assertEqual(student.post('/forgot-password', {'email': 'failed@example.test'})[0], 200)
            self.assertNotIn(secret, html)
            self.assertNotIn(secret, stderr.getvalue())
        row = self.row('SELECT email_verified,admin_approved FROM users WHERE email=?', ('failed@example.test',))
        self.assertEqual((row['email_verified'], row['admin_approved']), (0, 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
