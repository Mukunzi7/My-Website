"""Google ownership file: exact public bytes at root, with no private file exposure."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest import mock
import tempfile
import threading
import unittest

from test_v17 import Client
import server


class GoogleVerificationTests(unittest.TestCase):
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

    def test_file_is_public_at_its_exact_root_url_without_a_redirect(self):
        expected = b'google-site-verification: googleea85c8724f1d2440.html'
        self.assertEqual((server.ROOT / server.GOOGLE_VERIFICATION_FILE).read_bytes(), expected)
        anonymous = Client(self.base)
        status, text, headers = anonymous.get(server.GOOGLE_VERIFICATION_PATH, follow=False)
        self.assertEqual(status, 200)
        self.assertEqual(text.encode(), expected)
        self.assertEqual(headers.get('Content-Length'), str(len(expected)))
        self.assertEqual(headers.get('Content-Type'), 'text/html; charset=utf-8')
        self.assertIsNone(headers.get('Location'))

    def test_head_and_get_work_without_database_even_with_a_session_cookie(self):
        anonymous = Client(self.base)
        headers = {'Cookie': f'{server.SESSION_COOKIE}=invalid-test-session'}
        with mock.patch.object(server, 'db', side_effect=AssertionError('No database needed')):
            status, data, response = anonymous.request(server.GOOGLE_VERIFICATION_PATH, method='HEAD', headers=headers, follow=False)
            self.assertEqual(status, 200)
            self.assertEqual(data, '')
            self.assertEqual(response.get('Content-Length'), '53')
            status, data, response = anonymous.request(server.GOOGLE_VERIFICATION_PATH, headers=headers, follow=False)
            self.assertEqual(status, 200)
            self.assertEqual(data, 'google-site-verification: googleea85c8724f1d2440.html')

    def test_missing_file_returns_404_and_other_repository_files_are_not_public(self):
        anonymous = Client(self.base)
        with tempfile.TemporaryDirectory(prefix='70scholar-no-verification-') as directory, \
             mock.patch.object(server, 'ROOT', Path(directory)):
            for method in ('GET', 'HEAD'):
                status, _, _ = anonymous.request(server.GOOGLE_VERIFICATION_PATH, method=method, follow=False)
                self.assertEqual(status, 404)
        for path in ('/server.py', '/README.md', '/googleea85c8724f1d2441.html'):
            status, _, headers = anonymous.get(path, follow=False)
            self.assertEqual(status, 303)
            self.assertTrue(headers.get('Location', '').startswith('/login'))


if __name__ == '__main__':
    unittest.main()
