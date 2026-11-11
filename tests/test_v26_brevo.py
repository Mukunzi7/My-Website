"""Brevo API, provider-selection and account-code regressions.

All network sends are mocked; HTTP flows use disposable SQLite or local PostgreSQL.
Never send an actual production email or connect to a non-local test database.
"""
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
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import urlparse

import server
from test_v17 import Client


class Accepted:
    status = 201
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class CaptureOpener:
    def __init__(self, error=None):
        self.calls = []
        self.error = error
    def open(self, req, timeout=None):
        self.calls.append((req, timeout))
        if self.error:
            raise self.error
        return Accepted()


def payload(call):
    return json.loads(call[0].data.decode('utf-8'))


def extract_code(body):
    match = re.search(r'(?<![A-F0-9])(?:[A-F0-9]{4}-){7}[A-F0-9]{4}(?![A-F0-9])', body)
    if not match:
        raise AssertionError('Expected a grouped 128-bit email code')
    return match.group(0)


class BrevoConfigurationTests(unittest.TestCase):
    def test_provider_selection_is_explicit_and_preserves_legacy_priority(self):
        values = {'EMAIL_PROVIDER': '', 'BREVO_API_KEY': 'xkeysib_test_secret',
                  'BREVO_FROM': 'sender@example.test', 'BIRD_API_KEY': 'bk_us1_test',
                  'SMTP_HOST': 'smtp.example.test'}
        with mock.patch.multiple(server, **values):
            self.assertEqual(server.selected_email_provider(), 'bird')
            self.assertTrue(server.email_configuration_ready())
            with mock.patch.object(server, 'BIRD_API_KEY', ''):
                self.assertEqual(server.selected_email_provider(), 'smtp')
                with mock.patch.object(server, 'SMTP_HOST', ''):
                    self.assertEqual(server.selected_email_provider(), 'none')
                    self.assertFalse(server.email_configuration_ready())
            for name in ('brevo', 'bird', 'smtp'):
                with mock.patch.object(server, 'EMAIL_PROVIDER', name):
                    self.assertEqual(server.selected_email_provider(), name)
                    self.assertTrue(server.email_configuration_ready())
            with mock.patch.object(server, 'EMAIL_PROVIDER', 'surprise'):
                self.assertEqual(server.selected_email_provider(), 'invalid')
                self.assertFalse(server.email_configuration_ready())

    def test_incomplete_or_invalid_explicit_choice_never_falls_back(self):
        cases = [
            {'EMAIL_PROVIDER': 'brevo', 'BREVO_API_KEY': '', 'BREVO_FROM': 'sender@example.test'},
            {'EMAIL_PROVIDER': 'brevo', 'BREVO_API_KEY': 'private-brevo-key', 'BREVO_FROM': ''},
            {'EMAIL_PROVIDER': 'bird', 'BIRD_API_KEY': ''},
            {'EMAIL_PROVIDER': 'smtp', 'SMTP_HOST': ''},
            {'EMAIL_PROVIDER': 'unknown'},
        ]
        defaults = {'EMAIL_PROVIDER': '', 'BREVO_API_KEY': 'private-brevo-key',
                    'BREVO_FROM': 'sender@example.test', 'BIRD_API_KEY': 'bk_us1_other',
                    'SMTP_HOST': 'smtp.example.test'}
        for case in cases:
            with self.subTest(case=case['EMAIL_PROVIDER']), mock.patch.multiple(server, **(defaults | case)), \
                 mock.patch.object(server.urllib.request, 'urlopen') as bird, \
                 mock.patch.object(server.urllib.request, 'build_opener') as brevo, \
                 mock.patch.object(server.smtplib, 'SMTP') as smtp:
                self.assertFalse(server.email_configuration_ready())
                with self.assertRaises(RuntimeError):
                    server.send_email('recipient@example.test', 'subject', 'body')
                bird.assert_not_called(); brevo.assert_not_called(); smtp.assert_not_called()

    def test_brevo_http_payload_headers_no_redirect_and_safe_failures(self):
        fake = CaptureOpener()
        values = {'EMAIL_PROVIDER': 'brevo', 'BREVO_API_KEY': 'xkeysib_SECRET_SENTINEL',
                  'BREVO_FROM': 'owner@example.test', 'BIRD_API_KEY': 'bk_us1_other',
                  'SMTP_HOST': 'smtp.example.test'}
        with mock.patch.multiple(server, **values), \
             mock.patch.object(server.urllib.request, 'build_opener', return_value=fake) as build, \
             mock.patch.object(server.urllib.request, 'urlopen') as bird, \
             mock.patch.object(server.smtplib, 'SMTP') as smtp:
            server.send_email('recipient@example.test', 'Welcome', 'Plain <body>', '<p>Welcome</p>')
            self.assertEqual(len(fake.calls), 1)
            req, timeout = fake.calls[0]
            self.assertEqual((req.full_url, req.method, timeout), ('https://api.brevo.com/v3/smtp/email', 'POST', 15))
            self.assertEqual(req.get_header('Api-key'), 'xkeysib_SECRET_SENTINEL')
            self.assertEqual(req.get_header('Content-type'), 'application/json')
            self.assertEqual(payload(fake.calls[0]), {
                'sender': {'name': '70Scholar', 'email': 'owner@example.test'},
                'replyTo': {'email': 'owner@example.test'},
                'to': [{'email': 'recipient@example.test'}], 'subject': 'Welcome',
                'textContent': 'Plain <body>', 'htmlContent': '<p>Welcome</p>',
            })
            self.assertNotIn('SECRET_SENTINEL', req.data.decode())
            self.assertIsInstance(build.call_args.args[0], server._NoEmailApiRedirect)
            self.assertIsNone(server._NoEmailApiRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid'))
            bird.assert_not_called(); smtp.assert_not_called()
            # A non-template message always includes HTML, even for the owner test.
            server.send_email('recipient@example.test', 'Test', 'First <line>\nSecond')
            self.assertEqual(payload(fake.calls[-1])['htmlContent'], '<p>First &lt;line&gt;<br>Second</p>')
            failing = CaptureOpener(HTTPError('https://api.brevo.com/', 401, 'rejected', {}, io.BytesIO()))
            with mock.patch.object(server.urllib.request, 'build_opener', return_value=failing):
                with self.assertRaises(HTTPError):
                    server.send_email('recipient@example.test', 'Test', 'body')
            bird.assert_not_called(); smtp.assert_not_called()

    def test_brevo_diagnostics_are_non_secret_and_incomplete_is_visible(self):
        secret = 'KEY_SENTINEL'
        sender = 'private-sender@example.org'
        with mock.patch.multiple(server, EMAIL_PROVIDER='brevo', BREVO_API_KEY=secret,
                                 BREVO_FROM=sender, BIRD_API_KEY='bk_us1_hidden',
                                 APP_BASE_URL='https://school.example.org'):
            diag = server.email_setup_diagnostics()
            self.assertEqual((diag['provider'], diag['sender_mode'], diag['configuration_ready']),
                             ('brevo', 'custom', True))
            panel = server.render_email_setup_panel('safe-csrf')
            for private in (secret, sender, 'school.example.org', 'bk_us1_hidden'):
                self.assertNotIn(private, json.dumps(diag))
                self.assertNotIn(private, panel)
            self.assertIn('Brevo', panel)
            self.assertIn('delivery has not been verified', panel)
            self.assertIn('track email opens and clicks', panel)
            with mock.patch.object(server, 'BREVO_API_KEY', ''):
                self.assertFalse(server.email_setup_diagnostics()['configuration_ready'])
                self.assertIn('incomplete', server.render_email_setup_panel('safe-csrf'))

    def test_code_normalization_requires_128_bits(self):
        raw = '0123456789ABCDEF0123456789ABCDEF'
        grouped = server.display_email_code(raw)
        self.assertEqual(grouped, '0123-4567-89AB-CDEF-0123-4567-89AB-CDEF')
        self.assertEqual(server.normalize_email_code('  ' + grouped.lower() + '\n'), raw)
        for bad in ('', '0123', 'Z' * 32, 'A' * 31, 'A' * 33, 'A' * 101, 'A' * 30 + '?B'):
            self.assertEqual(server.normalize_email_code(bad), '')


class BrevoAccountHTTPTests(unittest.TestCase):
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
        self.tmp = tempfile.TemporaryDirectory(prefix='70scholar-v26-test-')
        self.addCleanup(self.tmp.cleanup)
        pg_url = os.environ.get('SCHOLAR70_TEST_DATABASE_URL', '')
        if pg_url and (urlparse(pg_url).hostname or '').lower() not in ('127.0.0.1', 'localhost', '::1'):
            raise RuntimeError('Tests must never use a non-local PostgreSQL database.')
        values = {'DB_PATH': Path(self.tmp.name) / 'test.sqlite3',
                  'UPLOAD_DIR': Path(self.tmp.name) / 'uploads', 'DATABASE_URL': pg_url,
                  'CLOUD_STORAGE': None, 'EMAIL_ENABLED': True, 'EMAIL_PROVIDER': 'brevo',
                  'BREVO_API_KEY': 'xkeysib_test_only', 'BREVO_FROM': 'owner@example.test',
                  'BIRD_API_KEY': 'bk_us1_other', 'SMTP_HOST': 'smtp.example.test',
                  'APP_BASE_URL': self.base}
        for name, value in values.items():
            p = mock.patch.object(server, name, value); p.start(); self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'TestOwnerPassword123!', 'RENDER': ''})
        p.start(); self.addCleanup(p.stop)
        server.init_db()
        self.owner = Client(self.base)
        self.assertEqual(self.owner.post('/login', {'email': server.OWNER_ADMIN_EMAIL,
                                                   'password': 'TestOwnerPassword123!'})[0], 200)
        self.csrf = self.owner.csrf('/admin')

    def row(self, sql, args=()):
        with server.db() as conn:
            return conn.execute(sql, args).fetchone()

    def signup(self, client, email='student@example.test'):
        return client.post('/signup', {'name': 'Student Tester', 'email': email, 'password': 'InitialPass123!'})

    def test_mocked_api_signup_verification_and_password_reset(self):
        student = Client(self.base)
        fake = CaptureOpener()
        stderr = io.StringIO()
        with mock.patch.object(server.urllib.request, 'build_opener', return_value=fake), \
             contextlib.redirect_stderr(stderr):
            status, body, _ = self.signup(student)
            self.assertEqual(status, 200)
            self.assertIn('Check your email', body)
            self.assertIn('enter your code', body)
            self.assertEqual(len(fake.calls), 1)
            mail = payload(fake.calls[-1]); code = extract_code(mail['textContent'])
            normalized = server.normalize_email_code(code)
            self.assertIn(code, mail['htmlContent'])
            self.assertEqual(mail['to'], [{'email': 'student@example.test'}])
            self.assertIn(self.base + '/verify-email', mail['textContent'])
            self.assertNotIn('?token=', mail['textContent'])
            hrefs = re.findall(r'href=[\'"]([^\'"]+)', mail['htmlContent'])
            self.assertEqual(hrefs, [self.base + '/verify-email'])
            self.assertTrue(all(code not in href and normalized not in href for href in hrefs))
            user = self.row('SELECT id,email_verified,admin_approved FROM users WHERE email=?', ('student@example.test',))
            self.assertEqual((user['email_verified'], user['admin_approved']), (0, 0))
            stored = self.row('SELECT token_hash,expires_at FROM email_tokens WHERE user_id=? AND purpose=?',
                              (user['id'], 'verify_email'))
            self.assertEqual(stored['token_hash'], server.token_hash(normalized))
            self.assertNotIn(normalized, stored['token_hash'])
            remaining = datetime.fromisoformat(stored['expires_at']) - datetime.now(timezone.utc)
            self.assertTrue(47 * 3600 < remaining.total_seconds() <= 48 * 3600)
            self.assertIn('Verification code', student.get('/verify-email')[1])
            self.assertEqual(student.post('/verify-email', {'code': 'wrong'})[0], 400)
            # A verification code cannot be used as a reset token or consumed in the wrong flow.
            self.assertEqual(student.post('/reset-password', {'code': code, 'password': 'NewPass123!'})[0], 400)
            self.assertEqual(student.post('/verify-email', {'code': ' \n' + code.lower() + ' '})[0], 200)
            self.assertEqual(student.post('/verify-email', {'code': code})[0], 400)
            self.assertEqual(self.row('SELECT email_verified FROM users WHERE id=?', (user['id'],))['email_verified'], 1)
            self.assertEqual(student.post('/login', {'email': 'student@example.test', 'password': 'InitialPass123!'})[0], 200)
            self.assertEqual(student.post('/forgot-password', {'email': 'student@example.test'})[0], 200)
            reset_mail = payload(fake.calls[-1]); reset_code = extract_code(reset_mail['textContent'])
            self.assertEqual(re.findall(r'href=[\'"]([^\'"]+)', reset_mail['htmlContent']), [self.base + '/reset-password'])
            self.assertNotIn('?token=', reset_mail['textContent'])
            self.assertIn('Reset code', student.get('/reset-password')[1])
            with server.db() as conn:
                conn.execute('UPDATE email_tokens SET expires_at=? WHERE user_id=? AND purpose=?',
                             ('2000-01-01T00:00:00+00:00', user['id'], 'password_reset'))
            self.assertEqual(student.post('/reset-password', {'code': reset_code, 'password': 'NewPass123!'})[0], 400)
            self.assertEqual(student.post('/forgot-password', {'email': 'student@example.test'})[0], 200)
            new_reset_code = extract_code(payload(fake.calls[-1])['textContent'])
            self.assertNotEqual(reset_code, new_reset_code)
            self.assertEqual(student.post('/reset-password', {'code': new_reset_code, 'password': 'NewPass123!'})[0], 200)
            self.assertEqual(student.get('/dashboard', follow=False)[0], 303)
            self.assertEqual(student.post('/reset-password', {'code': new_reset_code, 'password': 'OtherPass123!'})[0], 400)
            self.assertEqual(student.post('/login', {'email': 'student@example.test', 'password': 'NewPass123!'})[0], 200)
        self.assertNotIn(code, stderr.getvalue())
        self.assertNotIn(new_reset_code, stderr.getvalue())
        self.assertNotIn('xkeysib_test_only', stderr.getvalue())

    def test_admin_grant_and_resend_do_not_mark_email_verified(self):
        student = Client(self.base)
        with mock.patch.object(server, 'EMAIL_ENABLED', False):
            status, body, _ = self.signup(student, 'granted@example.test')
        self.assertEqual(status, 200); self.assertIn('not yet verified', body)
        user = self.row('SELECT id,email_verified,admin_approved FROM users WHERE email=?', ('granted@example.test',))
        self.assertEqual((user['email_verified'], user['admin_approved']), (0, 0))
        self.assertEqual(self.owner.post('/admin/user/action', {'csrf': self.csrf, 'user_id': user['id'], 'action': 'grant'})[0], 200)
        row = self.row('SELECT email_verified,admin_approved FROM users WHERE id=?', (user['id'],))
        self.assertEqual((row['email_verified'], row['admin_approved']), (0, 1))
        self.assertEqual(student.post('/login', {'email': 'granted@example.test', 'password': 'InitialPass123!'})[0], 200)
        self.assertIn('Send a verification code', student.get('/account')[1])
        csrf = student.csrf('/account'); fake = CaptureOpener()
        with mock.patch.object(server.urllib.request, 'build_opener', return_value=fake):
            status, body, _ = student.post('/account/verify-email', {'csrf': csrf})
        self.assertEqual(status, 200); self.assertIn('verification code was requested', body)
        self.assertEqual(self.row('SELECT email_verified FROM users WHERE id=?', (user['id'],))['email_verified'], 0)
        code = extract_code(payload(fake.calls[0])['textContent'])
        self.assertEqual(student.post('/verify-email', {'code': code})[0], 200)
        row = self.row('SELECT email_verified,admin_approved FROM users WHERE id=?', (user['id'],))
        self.assertEqual((row['email_verified'], row['admin_approved']), (1, 1))

    def test_existing_link_tokens_still_work_after_switching_provider(self):
        student = Client(self.base)
        with mock.patch.object(server, 'EMAIL_ENABLED', False):
            self.signup(student, 'legacy@example.test')
        user = self.row('SELECT id FROM users WHERE email=?', ('legacy@example.test',))
        verify = server.create_email_token(user['id'], 'verify_email', 48)
        self.assertEqual(student.get('/verify-email?token=' + verify)[0], 200)
        self.assertEqual(student.get('/verify-email?token=' + verify)[0], 400)
        reset = server.create_email_token(user['id'], 'password_reset', 2)
        self.assertEqual(student.get('/reset-password?token=' + reset)[0], 200)
        self.assertEqual(student.post('/reset-password', {'token': reset, 'password': 'LegacyNewPass123!'})[0], 200)
        self.assertEqual(student.post('/login', {'email': 'legacy@example.test', 'password': 'LegacyNewPass123!'})[0], 200)

    def test_rejected_api_keeps_account_unverified_and_owner_diagnostics_safe(self):
        student = Client(self.base)
        secret = 'RAW_PROVIDER_SECRET_SENTINEL'
        error = HTTPError('https://api.brevo.com/?secret=' + secret, 401, secret, {}, io.BytesIO(secret.encode()))
        fake = CaptureOpener(error)
        stderr = io.StringIO()
        with mock.patch.object(server.urllib.request, 'build_opener', return_value=fake), \
             contextlib.redirect_stderr(stderr):
            status, body, _ = self.signup(student, 'failure@example.test')
            self.assertEqual(status, 200); self.assertIn('not yet verified', body)
            self.assertEqual(student.post('/login', {'email': 'failure@example.test', 'password': 'InitialPass123!'})[0], 403)
            status, panel, _ = self.owner.post('/admin/email/test', {'csrf': self.csrf})
        self.assertEqual(status, 200)
        self.assertIn('HTTP 401', panel)
        record = self.row('SELECT value FROM settings WHERE key=?', ('system_email_last_test_v1',))['value']
        self.assertEqual(json.loads(record)['status'], 'provider_rejected')
        self.assertEqual(json.loads(record)['http_status'], 401)
        for text in (body, panel, record, stderr.getvalue()):
            self.assertNotIn(secret, text)
            self.assertNotIn('xkeysib_test_only', text)
        row = self.row('SELECT email_verified,admin_approved FROM users WHERE email=?', ('failure@example.test',))
        self.assertEqual((row['email_verified'], row['admin_approved']), (0, 0))

    def test_owner_test_is_restricted_to_owner_and_valid_csrf(self):
        student = Client(self.base); fake = CaptureOpener()
        with mock.patch.object(server.urllib.request, 'build_opener', return_value=fake):
            self.assertEqual(student.post('/admin/email/test', {'csrf': self.csrf}, follow=False)[0], 303)
            self.assertEqual(self.owner.post('/admin/email/test', {'csrf': 'wrong'}, follow=False)[0], 403)
            self.assertEqual(self.owner.request('/admin/email/test', data={'csrf': self.csrf}, follow=False,
                                                headers={'Origin': 'https://attacker.invalid'})[0], 403)
            self.assertEqual(len(fake.calls), 0)
            status, body, _ = self.owner.post('/admin/email/test', {'csrf': self.csrf, 'email': 'attacker@example.test'})
        self.assertEqual(status, 200); self.assertIn('provider accepted', body)
        self.assertIn('does not guarantee delivery', body)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(payload(fake.calls[0])['to'], [{'email': server.OWNER_ADMIN_EMAIL}])
        self.assertNotIn('attacker@example.test', json.dumps(payload(fake.calls[0])))

    def test_codes_are_single_use_even_when_consumed_concurrently(self):
        student = Client(self.base)
        with mock.patch.object(server, 'EMAIL_ENABLED', False):
            self.signup(student, 'race@example.test')
        user = self.row('SELECT id FROM users WHERE email=?', ('race@example.test',))
        code = server.create_email_token(user['id'], 'verify_email', as_code=True)
        barrier = threading.Barrier(2); results = []; errors = []
        def consume():
            try:
                barrier.wait(timeout=5)
                results.append(server.ScholarHandler.consume_email_token(None, code, 'verify_email'))
            except Exception as ex:
                errors.append(ex)
        first = threading.Thread(target=consume); second = threading.Thread(target=consume)
        first.start(); second.start(); first.join(timeout=10); second.join(timeout=10)
        self.assertFalse(errors)
        self.assertEqual(sum(row is not None for row in results), 1)


if __name__ == '__main__':
    unittest.main()
