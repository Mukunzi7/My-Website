"""Footer contact links and compose behavior for 70Scholar."""
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest import mock
import os
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from test_v17 import Client
import server


class ContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-contact-');self.addCleanup(self.tmp.cleanup)
        p1=mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'db.sqlite3')
        p2=mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads')
        p1.start();p2.start();self.addCleanup(p1.stop);self.addCleanup(p2.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}): server.init_db()
    @staticmethod
    def href(page, cls):
        match=re.search(r'<a class="'+re.escape(cls)+r'" href="([^"]+)"',page)
        if not match: raise AssertionError('Missing contact link: '+cls)
        return unescape(match.group(1))

    def test_phone_and_email_are_on_all_public_pages(self):
        for path in ('/','/login','/signup'):
            status,page,_=Client(self.base).get(path);self.assertEqual(status,200)
            self.assertIn('+250 783 958 599',page);self.assertNotIn('0726495648',page)
            self.assertEqual(self.href(page,'helpline-phone'),'tel:+250783958599')
            self.assertEqual(self.href(page,'helpline-email-app'),'mailto:honoremukunzi6@gmail.com')
            compose=urlparse(self.href(page,'helpline-email'));self.assertEqual((compose.scheme,compose.netloc,compose.path),('https','mail.google.com','/mail/'))
            params=parse_qs(compose.query);self.assertEqual(params.get('view'),['cm']);self.assertEqual(params.get('fs'),['1']);self.assertEqual(params.get('to'),['honoremukunzi6@gmail.com'])
            self.assertLess(page.index('class="helpline-phone"'),page.index('class="helpline-email"'))
            self.assertIn('target="_blank" rel="noopener noreferrer"',page)
            self.assertIn('Use email app',page)
        css=(server.STATIC_DIR/'styles.css').read_text()
        self.assertRegex(css,r'\.helpline-contacts\s*\{[^}]*flex-direction:\s*column')

    def test_configured_email_is_escaped_and_enters_compose_recipient(self):
        with mock.patch.object(server,'HELPLINE_EMAIL','help+notes@example.test'):
            page=server.render_home(None)
        params=parse_qs(urlparse(self.href(page,'helpline-email')).query)
        self.assertEqual(params['to'],['help+notes@example.test'])
        self.assertEqual(self.href(page,'helpline-email-app'),'mailto:help+notes@example.test')
        self.assertIn('help+notes@example.test',page)

if __name__=='__main__': unittest.main()
