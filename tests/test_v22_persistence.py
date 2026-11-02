"""Persistence and privacy after app reinitialization; uses isolated data only."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest import mock
import base64, io, json, os, re, tempfile, threading, unittest
from PIL import Image
from test_v17 import Client
from test_v19_slideshow import multipart
import server

class PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-persist-');self.addCleanup(self.tmp.cleanup)
        a=mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'db.sqlite3')
        b=mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads')
        a.start();b.start();self.addCleanup(a.stop);self.addCleanup(b.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        self.admin=Client(self.base)
        self.assertEqual(self.admin.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':'TestOwnerPassword123!'})[0],200)
        self.acsrf=self.admin.csrf('/admin')
    def test_account_media_slides_and_project_survive_restart_with_access_controls(self):
        student=Client(self.base)
        email='retained@example.test'; password='StudentPassword123!'
        self.assertEqual(student.post('/signup',{'name':'Sample Student','email':email,'phone':'+250788111222','password':password})[0],200)
        with server.db() as c:
            uid=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
        self.assertEqual(self.admin.post('/admin/user/action',{'csrf':self.acsrf,'user_id':uid,'action':'grant'})[0],200)
        self.assertEqual(student.post('/login',{'email':email,'password':password})[0],200)
        csrf=student.csrf()
        image=io.BytesIO();Image.new('RGB',(32,24),'#235b8e').save(image,'PNG')
        status,data,_=student.json('/api/profile-photo',{'filename':'profile.png','mime':'image/png','data':base64.b64encode(image.getvalue()).decode()},csrf)
        self.assertEqual(status,200);url=json.loads(data)['url']
        self.assertEqual(student.get(url)[0],200);self.assertEqual(Client(self.base).get(url,False)[0],303)
        photo=io.BytesIO();Image.new('RGB',(42,30),'#f0a130').save(photo,'JPEG')
        raw,headers=multipart({'csrf':self.acsrf,'caption':'Saved across restart'},photo.getvalue(),'uploaded.jpg','image/jpeg')
        self.assertEqual(self.admin.request('/admin/slideshow/add',data=raw,headers=headers,follow=False)[0],303)
        with server.db() as c:
            uploaded=c.execute("SELECT id FROM slideshow_photos WHERE caption=?",('Saved across restart',)).fetchone()['id']
            removed=c.execute("SELECT id FROM slideshow_photos WHERE bundled_path=?",('slide-01.jpg',)).fetchone()['id']
        self.assertEqual(self.admin.post('/admin/slideshow/remove',{'csrf':self.acsrf,'photo_id':removed},follow=False)[0],303)
        form={'csrf':csrf,'title':'Saved project','category':'Education','summary':'A useful learning project for students.','details':'A detailed plan for a learning project that can be restored after restarting the server.','goal_amount':'10','price':'0','status':'draft'}
        self.assertEqual(student.post('/project/save',form)[0],200)
        with server.db() as c: pid=c.execute('SELECT id FROM projects WHERE title=?',('Saved project',)).fetchone()['id']
        up={'project_id':pid,'filename':'proof.pdf','mime':'application/pdf','data':base64.b64encode(b'private retained file').decode()}
        status,body,_=student.json('/api/upload',up,csrf);self.assertEqual(status,200);asset=json.loads(body)['download_url']
        # A new application startup uses the same persisted database; no local upload file is needed.
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):server.init_db()
        new_client=Client(self.base);self.assertEqual(new_client.post('/login',{'email':email,'password':password})[0],200)
        self.assertEqual(new_client.get(url)[0],200);self.assertEqual(new_client.get(asset)[0],200)
        stranger=Client(self.base);self.assertEqual(stranger.get(asset,False)[0],303)
        status,home,_=stranger.get('/');self.assertEqual(status,200)
        self.assertIn('Saved across restart',home);self.assertIn(f'/slide-image?id={uploaded}',home);self.assertNotIn('slide-01.jpg',home)
        with server.db() as c:
            row=c.execute('SELECT phone,profile_photo_url FROM users WHERE id=?',(uid,)).fetchone()
        self.assertEqual(row['phone'],'+250788111222');self.assertEqual(row['profile_photo_url'],url)
        self.assertFalse(any(server.UPLOAD_DIR.rglob('*')),'new media should not depend on ephemeral local files')

if __name__=='__main__':unittest.main()
