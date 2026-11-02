"""Synthetic private-bucket, privacy, failure and cleanup tests; no provider is contacted."""
import base64
import io
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from PIL import Image

from test_v17 import Client
from test_v19_slideshow import multipart
import private_storage
import server


class FakeBucket:
    def __init__(self):
        self.objects = {}
        self.public = False
        self.fail_put = False
        self.fail_get = False
        self.fail_delete = False
    def verify_private(self):
        if self.public: raise private_storage.StorageError('not private')
    def put(self, key, content, mime):
        if self.fail_put: raise private_storage.StorageError('unavailable')
        if key in self.objects: raise private_storage.StorageError('duplicate')
        self.objects[key] = bytes(content)
    def get(self, key, max_bytes):
        if self.fail_get or key not in self.objects: raise private_storage.StorageError('unavailable')
        return self.objects[key]
    def delete(self, key):
        if self.fail_delete: raise private_storage.StorageError('unavailable')
        self.objects.pop(key, None)


class PrivateBucketClientTests(unittest.TestCase):
    def test_keys_urls_headers_and_privacy_checks(self):
        bucket = private_storage.PrivateBucket('https://project123.supabase.co', 'sb_secret_dummy', '70scholar-private')
        self.assertEqual(bucket._headers(), {'apikey':'sb_secret_dummy'})
        old = private_storage.PrivateBucket('https://project123.supabase.co', 'eyJabc.def.ghi', '70scholar-private')
        self.assertEqual(old._headers()['Authorization'], 'Bearer eyJabc.def.ghi')
        for invalid in ('http://project123.supabase.co', 'https://project123.supabase.co.attacker.test',
                        'https://user@project123.supabase.co', 'https://project123.supabase.co/path',
                        'https://project123.supabase.co:444'):
            with self.subTest(url=invalid), self.assertRaises(private_storage.StorageError):
                private_storage.PrivateBucket(invalid,'sb_secret_dummy','70scholar-private')
        for invalid in ('../hello', 'profiles//x', '/foo', 'foo/../bar', 'hello?token=x'):
            with self.subTest(key=invalid), self.assertRaises(private_storage.StorageError):
                bucket._key(invalid)
        with mock.patch.object(bucket, '_request', return_value=b'{"id":"70scholar-private","public":false}'):
            bucket.verify_private()
        with mock.patch.object(bucket, '_request', return_value=b'{"id":"70scholar-private","public":true}'):
            with self.assertRaisesRegex(private_storage.StorageError, 'not private'): bucket.verify_private()
        with mock.patch.object(bucket, '_request', return_value=b'{"id":"wrong","public":false}'):
            with self.assertRaises(private_storage.StorageError): bucket.verify_private()
        with mock.patch.object(bucket, '_request', return_value=b'not-json'):
            with self.assertRaises(private_storage.StorageError): bucket.verify_private()

    def test_requests_use_raw_bytes_and_never_redirect_credentials(self):
        bucket = private_storage.PrivateBucket('https://project123.supabase.co', 'sb_secret_dummy', '70scholar-private')
        calls=[]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return b'{"ok":true}'
        class Opener:
            def open(self, request, timeout): calls.append((request,timeout));return Response()
        bucket._opener=Opener()
        bucket.put('assets/1-a.pdf',b'raw bytes','application/pdf')
        req,_=calls.pop()
        self.assertEqual(req.full_url,'https://project123.supabase.co/storage/v1/object/70scholar-private/assets/1-a.pdf')
        self.assertEqual(req.data,b'raw bytes')
        self.assertEqual(req.get_header('Apikey'),'sb_secret_dummy')
        self.assertIsNone(req.get_header('Authorization'))
        self.assertEqual(req.get_header('Content-type'),'application/pdf')
        bucket.get('assets/1-a.pdf',1024)
        req,_=calls.pop();self.assertIn('/object/authenticated/70scholar-private/',req.full_url)
        self.assertIsNone(private_storage._NoRedirect().redirect_request(None,None,302,'',{},'https://attacker.test/'))
        class FailingOpener:
            def open(self, request, timeout): raise RuntimeError('sb_secret_dummy')
        bucket._opener=FailingOpener()
        with self.assertRaises(private_storage.StorageError) as error:bucket.get('assets/1-a.pdf',1024)
        self.assertNotIn('sb_secret_dummy',str(error.exception))

    def test_render_requires_complete_verified_storage_configuration(self):
        with mock.patch.object(server, 'DATABASE_URL', 'postgresql://example.invalid/db'), \
             mock.patch.dict(os.environ, {'RENDER':'true'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'private Supabase Storage'):
                server.configure_cloud_storage()
        with mock.patch.dict(os.environ, {'SUPABASE_URL':'https://project123.supabase.co'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'incomplete'): server.configure_cloud_storage()
        fake = FakeBucket()
        with mock.patch.dict(os.environ, {'RENDER':'true', 'SUPABASE_URL':'https://project123.supabase.co',
                                        'SUPABASE_SECRET_KEY':'sb_secret_dummy', 'SUPABASE_STORAGE_BUCKET':'private'}, clear=True), \
             mock.patch.object(private_storage, 'PrivateBucket', return_value=fake):
            self.assertIs(server.configure_cloud_storage(), fake)
            fake.public=True
            with self.assertRaises(private_storage.StorageError): server.configure_cloud_storage()


class PrivateBucketAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-bucket-test-');self.addCleanup(self.tmp.cleanup)
        self.fake=FakeBucket()
        for patch in [mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'db.sqlite3'),
                      mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads'),
                      mock.patch.object(server,'CLOUD_STORAGE',self.fake)]:
            patch.start();self.addCleanup(patch.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        self.owner=Client(self.base)
        self.assertEqual(self.owner.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':'TestOwnerPassword123!'})[0],200)
        self.acsrf=self.owner.csrf('/admin')
    def signup(self,email):
        client=Client(self.base)
        self.assertEqual(client.post('/signup',{'name':'Test Student','email':email,'password':'StudentPassword123!'})[0],200)
        with server.db() as c: uid=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
        self.assertEqual(self.owner.post('/admin/user/action',{'csrf':self.acsrf,'user_id':uid,'action':'grant'})[0],200)
        self.assertEqual(client.post('/login',{'email':email,'password':'StudentPassword123!'})[0],200)
        return client,uid,client.csrf()
    def photo(self):
        data=io.BytesIO();Image.new('RGB',(25,25),'#2378ab').save(data,'PNG');return data.getvalue()
    def cleanup_all(self):
        with server.db() as c: c.execute("UPDATE storage_cleanup_queue SET not_before='2000-01-01T00:00:00+00:00'")
        for _ in range(20):
            with server.db() as c: count=c.execute('SELECT COUNT(*) n FROM storage_cleanup_queue').fetchone()['n']
            if not count:return
            server.process_storage_cleanup()
        self.fail('cleanup did not finish')

    def test_restart_private_access_slides_and_cleanup(self):
        student,uid,csrf=self.signup('student@example.test')
        stranger,_,_=self.signup('stranger@example.test')
        raw=self.photo()
        status,data,_=student.json('/api/profile-photo',{'filename':'profile.png','mime':'image/png','data':base64.b64encode(raw).decode()},csrf)
        self.assertEqual(status,200);profile=json.loads(data)['url']
        with server.db() as c:
            row=c.execute('SELECT data FROM media_objects WHERE owner_id=? AND project_id IS NULL',(uid,)).fetchone()
            self.assertEqual(bytes(row['data']),b'')
            profile_key=c.execute("SELECT object_key FROM cloud_object_links WHERE kind='media'").fetchone()['object_key']
        self.assertEqual(self.fake.objects[profile_key],raw)
        self.assertEqual(student.get(profile)[0],200);self.assertEqual(self.owner.get(profile)[0],200)
        self.assertEqual(stranger.get(profile,False)[0],403);self.assertEqual(Client(self.base).get(profile,False)[0],303)
        form={'csrf':csrf,'title':'Private project','category':'Education','summary':'A project about education.',
              'details':'A longer synthetic project detail.','goal_amount':'10','price':'0','status':'draft'}
        self.assertEqual(student.post('/project/save',form)[0],200)
        with server.db() as c:pid=c.execute("SELECT id FROM projects WHERE title='Private project'").fetchone()['id']
        status,data,_=student.json('/api/upload',{'project_id':pid,'filename':'proof.pdf','mime':'application/pdf',
                                     'data':base64.b64encode(b'private project bytes').decode()},csrf)
        self.assertEqual(status,200);download=json.loads(data)['download_url']
        self.assertEqual(student.get(download)[0],200);self.assertEqual(self.owner.get(download)[0],200)
        self.assertEqual(stranger.get(download,False)[0],403);self.assertEqual(Client(self.base).get(download,False)[0],303)
        with server.db() as c:
            asset=c.execute('SELECT stored_path FROM assets WHERE project_id=?',(pid,)).fetchone()
            key=asset['stored_path'][3:]
            self.assertEqual(bytes(c.execute('SELECT data FROM media_objects WHERE storage_key=?',(key,)).fetchone()['data']),b'')
            self.assertEqual(c.execute("SELECT object_key FROM cloud_object_links WHERE record_key=?",(key,)).fetchone()['object_key'],key)
        self.assertEqual(self.fake.objects[key],b'private project bytes')
        payload,headers=multipart({'csrf':self.acsrf,'caption':'Test bucket photo'},raw,'slide.png','image/png')
        self.assertEqual(self.owner.request('/admin/slideshow/add',data=payload,headers=headers,follow=False)[0],303)
        with server.db() as c:
            slide_id=c.execute("SELECT id FROM slideshow_photos WHERE caption='Test bucket photo'").fetchone()['id']
            link=c.execute("SELECT object_key,object_size FROM cloud_object_links WHERE kind='slide' AND record_key=?",(str(slide_id),)).fetchone()
            slide_key=link['object_key']; self.assertGreater(link['object_size'],0)
        self.assertEqual(Client(self.base).get('/slide-image?id='+str(slide_id))[0],200)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        self.assertEqual(student.get(profile)[0],200);self.assertEqual(student.get(download)[0],200)
        # Replacing a profile makes the old URL unavailable and schedules deletion.
        status,data,_=student.json('/api/profile-photo',{'filename':'new.png','mime':'image/png','data':base64.b64encode(raw).decode()},csrf)
        self.assertEqual(status,200);self.assertEqual(student.get(profile,False)[0],404)
        self.assertEqual(self.owner.post('/admin/slideshow/remove',{'csrf':self.acsrf,'photo_id':slide_id},follow=False)[0],303)
        self.assertEqual(Client(self.base).get('/slide-image?id='+str(slide_id))[0],404)
        self.assertEqual(self.owner.post('/admin/project/action',{'csrf':self.acsrf,'project_id':pid,'action':'delete'})[0],200)
        self.assertEqual(student.get(download,False)[0],404)
        self.cleanup_all()
        self.assertNotIn(profile_key,self.fake.objects);self.assertNotIn(slide_key,self.fake.objects);self.assertNotIn(key,self.fake.objects)

    def test_provider_errors_fail_closed_and_cleanup_retries(self):
        student,uid,csrf=self.signup('failure@example.test');raw=self.photo()
        payload={'filename':'profile.png','mime':'image/png','data':base64.b64encode(raw).decode()}
        self.fake.public=True
        self.assertEqual(student.json('/api/profile-photo',payload,csrf)[0],503)
        self.assertFalse(self.fake.objects)
        self.fake.public=False; self.fake.fail_put=True
        self.assertEqual(student.json('/api/profile-photo',payload,csrf)[0],503)
        with server.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) n FROM media_objects WHERE owner_id=?',(uid,)).fetchone()['n'],0)
            self.assertEqual(c.execute('SELECT COUNT(*) n FROM storage_cleanup_queue').fetchone()['n'],1)
        self.fake.fail_put=False;self.fake.fail_delete=True
        with server.db() as c:c.execute("UPDATE storage_cleanup_queue SET not_before='2000-01-01T00:00:00+00:00'")
        server.process_storage_cleanup()
        with server.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) n FROM storage_cleanup_queue').fetchone()['n'],1)
        self.fake.fail_delete=False;self.cleanup_all()
        status,data,_=student.json('/api/profile-photo',payload,csrf);self.assertEqual(status,200)
        url=json.loads(data)['url'];self.fake.fail_get=True
        self.assertEqual(student.get(url,False)[0],503)

    def test_interrupted_database_commit_leaves_a_tracked_object_for_cleanup(self):
        key='slides/'+'a'*32+'.jpg'
        self.assertTrue(server.reserve_and_upload(key,b'synthetic object','image/jpeg'))
        with self.assertRaises(RuntimeError):
            with server.db() as c:
                c.execute('BEGIN IMMEDIATE')
                server.link_cloud_object(c,'slide','99999',key,len(b'synthetic object'))
                raise RuntimeError('simulate a failed transaction')
        with server.db() as c:
            self.assertTrue(c.execute('SELECT 1 FROM storage_cleanup_queue WHERE object_key=?',(key,)).fetchone())
            self.assertFalse(c.execute('SELECT 1 FROM cloud_object_links WHERE object_key=?',(key,)).fetchone())
        self.assertIn(key,self.fake.objects)
        self.cleanup_all();self.assertNotIn(key,self.fake.objects)

    def test_user_deletion_queues_private_profile_for_removal(self):
        student,uid,csrf=self.signup('deletion@example.test')
        raw=self.photo(); status,data,_=student.json('/api/profile-photo',{'filename':'x.png','mime':'image/png','data':base64.b64encode(raw).decode()},csrf)
        self.assertEqual(status,200)
        key=next(iter(self.fake.objects))
        self.assertEqual(self.owner.post('/admin/user/action',{'csrf':self.acsrf,'user_id':uid,'action':'delete'})[0],200)
        self.cleanup_all();self.assertNotIn(key,self.fake.objects)

    def test_large_body_and_upload_slot_are_rejected_before_reading(self):
        student,_,csrf=self.signup('limits@example.test')
        with mock.patch.object(server,'MAX_UPLOAD_REQUEST_BYTES',10):
            status,_,_=student.json('/api/profile-photo',{'filename':'x.png','mime':'image/png','data':'a'*80},csrf)
            self.assertEqual(status,413)
        with mock.patch.object(server,'UPLOAD_SLOTS',threading.BoundedSemaphore(1)):
            self.assertTrue(server.UPLOAD_SLOTS.acquire(False))
            try:
                status,_,_=student.json('/api/profile-photo',{'filename':'x.png','mime':'image/png','data':'a'},csrf)
                self.assertEqual(status,503)
            finally:server.UPLOAD_SLOTS.release()


if __name__=='__main__':unittest.main()
