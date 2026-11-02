"""Bootcamp content, gated browsing, filters and repeat-start safety."""
from pathlib import Path
import os
import tempfile
import threading
import unittest
from unittest import mock
from http.server import ThreadingHTTPServer
from urllib.parse import quote

from test_v17 import Client
import server


class BootcampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-camps-');self.addCleanup(self.tmp.cleanup)
        p1=mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'test.sqlite3')
        p2=mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads')
        p1.start();p2.start();self.addCleanup(p1.stop);self.addCleanup(p2.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        self.admin=Client(self.base)
        status,_,_=self.admin.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':'TestOwnerPassword123!'})
        self.assertEqual(status,200)
    def test_groups_are_gated_and_show_official_cost_and_status(self):
        anon=Client(self.base)
        for path in ['/programs','/opportunities?type=Summer%20bootcamp']:
            status,_,headers=anon.get(path,False);self.assertEqual(status,303);self.assertTrue(headers['Location'].startswith('/login'))
        _,home,_=anon.get('/')
        for item in server.SUMMER_BOOTCAMPS:self.assertNotIn(item['url'],home)
        status,page,_=self.admin.get('/programs');self.assertEqual(status,200)
        self.assertIn('id="summer-bootcamps"',page)
        for item in server.SUMMER_BOOTCAMPS:
            self.assertIn(server.e(item['title']),page);self.assertIn(server.e(item['url']),page)
            self.assertLess(page.index(server.e(item['title'])),page.index('id="more-programs"'))
        self.assertIn('2026 application is closed',page)
        self.assertIn('US $2,800',page)
        self.assertIn('some programmes are free',page.lower())
        self.assertIn('not yet announced',page.lower())
    def test_search_filter_and_idempotent_restart(self):
        with server.db() as db:
            count=db.execute("SELECT count(*) FROM opportunities WHERE type='Summer bootcamp' AND source='featured_program'").fetchone()[0]
        self.assertEqual(count,5)
        status,page,_=self.admin.get('/opportunities?type='+quote('Summer bootcamp'))
        self.assertEqual(status,200)
        for item in server.SUMMER_BOOTCAMPS:self.assertIn(server.e(item['title']),page)
        self.assertNotIn('Yale Young African Scholars (YYAS) 2027',page)
        self.assertIn('value="Summer bootcamp">Summer bootcamps</option>',page)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        with server.db() as db:
            rows=db.execute("SELECT title,COUNT(*) FROM opportunities WHERE type='Summer bootcamp' GROUP BY title").fetchall()
        self.assertEqual(len(rows),5);self.assertTrue(all(row[1]==1 for row in rows))

if __name__=='__main__':unittest.main()
