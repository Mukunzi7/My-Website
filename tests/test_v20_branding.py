"""Logo, browser icon and full-bleed homepage branding regressions."""
from pathlib import Path
import os
import tempfile
import threading
import unittest
import urllib.request
from unittest import mock
from http.server import ThreadingHTTPServer
from PIL import Image

from test_v17 import Client
import server


class BrandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-brand-');self.addCleanup(self.tmp.cleanup)
        db=mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'test.sqlite3')
        up=mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads')
        db.start();up.start();self.addCleanup(db.stop);self.addCleanup(up.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}): server.init_db()

    def test_homepage_uses_owner_emblem_and_full_bleed_photo(self):
        status,home,headers=Client(self.base).get('/')
        self.assertEqual(status,200);self.assertEqual(headers['Referrer-Policy'],'strict-origin')
        self.assertIn('<img class="hero-background" src="/static/images/hero-school-group.jpg?',home)
        self.assertIn('alt="Students and educators together at a school award event"',home)
        self.assertIn('<img class="hero-logo" src="/static/images/seven-scholars-mark.jpg?',home)
        self.assertIn('alt="Seven Scholars logo"',home)
        self.assertNotIn('class="brand-display"',home)
        self.assertIn("There's a version of your future",home)
        self.assertIn('still waiting to be found.',home)
        self.assertIn("<span class='logo-first'>70</span><span class='logo-last'>Scholar</span>",home)
        self.assertIn('id="slideshow"',home)
        css=(server.STATIC_DIR/'styles.css').read_text()
        self.assertIn('.hero-background',css);self.assertIn('object-fit: cover',css)
        self.assertIn('.hero::before',css);self.assertNotIn('hoverTooltip',css)
        self.assertEqual(server.APP_NAME,'70Scholar')
        for path in ('/','/login','/signup'):
            status,page,_=Client(self.base).get(path)
            self.assertEqual(status,200)
            self.assertIn('/static/images/seven-scholars-mark.jpg?',page)
            self.assertIn('/static/favicon.png?',page)
            self.assertIn('/favicon.ico?',page)
            self.assertNotIn('/static/favicon.svg',page)

    def test_logo_and_favicons_are_public_images_with_correct_metadata(self):
        files=[('/static/images/seven-scholars-mark.jpg','images/seven-scholars-mark.jpg','image/jpeg'),
               ('/static/favicon.png','favicon.png','image/png'),
               ('/favicon.ico','favicon.ico','image/')]
        for url,rel,mime in files:
            with urllib.request.urlopen(self.base+url,timeout=10) as response:
                body=response.read();self.assertEqual(response.status,200)
                self.assertTrue(response.headers['Content-Type'].startswith(mime))
                self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
                self.assertEqual(body,(server.STATIC_DIR/rel).read_bytes())
            request=urllib.request.Request(self.base+url,method='HEAD')
            with urllib.request.urlopen(request,timeout=10) as response:
                self.assertEqual(response.status,200)
                self.assertTrue(response.headers['Content-Type'].startswith(mime))
                self.assertEqual(int(response.headers['Content-Length']),len(body))
                self.assertEqual(response.read(),b'')
        with Image.open(server.STATIC_DIR/'images/seven-scholars-mark.jpg') as logo:
            self.assertEqual(logo.size,(720,720));self.assertEqual(len(logo.getexif()),0)
        with Image.open(server.STATIC_DIR/'favicon.png') as favicon:
            self.assertEqual(favicon.size,(192,192));self.assertEqual(favicon.mode,'RGBA')
            self.assertEqual(favicon.getpixel((0,0))[3],0)
        with Image.open(server.STATIC_DIR/'favicon.ico') as favicon:
            self.assertIn((16,16),favicon.info['sizes'])
            self.assertIn((256,256),favicon.info['sizes'])

if __name__=='__main__': unittest.main()
