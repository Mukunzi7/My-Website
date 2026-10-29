"""Owner slideshow and homepage regressions, using isolated temporary databases."""
from pathlib import Path
from io import BytesIO
import os
import re
import tempfile
import threading
import unittest
from unittest import mock
from http.server import ThreadingHTTPServer
from PIL import Image

from test_v17 import Client
import server


def photo_bytes(fmt='JPEG', size=(2400, 1000), animated=False):
    image=Image.new('RGB',size,(39,98,150))
    exif=Image.Exif(); exif[274]=6; exif[315]='private metadata'
    buf=BytesIO()
    kwargs={'exif':exif} if fmt == 'JPEG' else {}
    if animated:
        kwargs={'save_all':True,'append_images':[Image.new('RGB',size,(255,10,10))], 'duration':100, 'loop':0}
    image.save(buf,format=fmt,**kwargs)
    return buf.getvalue()


def multipart(fields, content, filename='photo.jpg', mime='image/jpeg'):
    boundary='70scholar-test-boundary'
    parts=[]
    for name, value in fields.items():
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode('utf-8'))
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode('utf-8')+content+b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), {'Content-Type':f'multipart/form-data; boundary={boundary}'}


class SlideshowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-slides-')
        self.addCleanup(self.tmp.cleanup)
        self.dbpatch=mock.patch.object(server,'DB_PATH',Path(self.tmp.name)/'test.sqlite3')
        self.uppatch=mock.patch.object(server,'UPLOAD_DIR',Path(self.tmp.name)/'uploads')
        self.dbpatch.start();self.uppatch.start()
        self.addCleanup(self.dbpatch.stop);self.addCleanup(self.uppatch.stop)
        with mock.patch.dict(os.environ,{'ADMIN_PASSWORD':'TestOwnerPassword123!'}):
            server.init_db()
        self.owner=Client(self.base)
        status,_,_=self.owner.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':'TestOwnerPassword123!'})
        self.assertEqual(status,200)
        self.csrf=self.owner.csrf('/admin')
    def rows(self, sql, args=()):
        with server.db() as c: return c.execute(sql,args).fetchall()
    def add(self, client, data, csrf=None, caption='', filename='photo.jpg', mime='image/jpeg', origin=None):
        raw,headers=multipart({'csrf':self.csrf if csrf is None else csrf,'caption':caption},data,filename,mime)
        if origin: headers['Origin']=origin
        return client.request('/admin/slideshow/add',data=raw,headers=headers,follow=False)

    def test_hero_and_tooltips_removed_everywhere(self):
        anon=Client(self.base)
        status,home,_=anon.get('/')
        self.assertEqual(status,200)
        self.assertIn('hero-school-group.jpg',home)
        self.assertIn("There's a version of your future",home)
        self.assertIn('still waiting to be found.',home)
        self.assertIn('id="slideshow"',home)
        for path in ('/','/opportunities','/courses','/exams','/programs','/admin'):
            status,html,_=self.owner.get(path)
            self.assertEqual(status,200,path)
            self.assertNotIn('data-tooltip=',html)
            self.assertNotIn('Hover any',html)
        self.assertNotIn('hoverTooltip',(server.STATIC_DIR/'app.js').read_text())
        self.assertNotIn('#hoverTooltip',(server.STATIC_DIR/'styles.css').read_text())
        self.assertIn("aria-label='Account settings'",self.owner.get('/admin')[1])
        hero=Image.open(server.STATIC_DIR/'images/hero-school-group.jpg')
        self.assertEqual(hero.size,(1600,1066));self.assertFalse(hero.getexif())

    def test_admin_upload_normalizes_and_publishes_then_removes(self):
        source=photo_bytes()
        result,_,headers=self.add(self.owner,source,caption='<b>School & friends</b>',filename='../../untrusted.html',mime='text/html')
        self.assertEqual(result,303);self.assertIn('slide_result=added',headers['Location'])
        row=self.rows("SELECT * FROM slideshow_photos WHERE bundled_path='' ORDER BY id DESC")[0]
        pid=row['id']
        image=Image.open(BytesIO(row['data']))
        self.assertEqual(image.format,'JPEG')
        self.assertEqual(image.size,(800,1920),'EXIF orientation should be applied before resizing')
        self.assertFalse(image.getexif(),'private metadata must not be published')
        self.assertNotIn(b'private metadata',row['data'])
        status,home,_=Client(self.base).get('/')
        self.assertEqual(status,200);self.assertIn(f'/slide-image?id={pid}',home)
        self.assertIn('&lt;b&gt;School &amp; friends&lt;/b&gt;',home)
        self.assertNotIn('<b>School & friends</b>',home)
        self.assertRegex(home,rf'<figure class="slide is-active"[^>]*>\s*<img src="/slide-image\?id={pid}"')
        with Client(self.base).opener.open(self.base+f'/slide-image?id={pid}') as response:
            image_bytes=response.read()
            self.assertEqual(response.headers['Content-Type'],'image/jpeg')
            self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertEqual(image_bytes,row['data'])
        status,_,headers=Client(self.base).request(f'/slide-image?id={pid}',method='HEAD')
        self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'image/jpeg')
        server.init_db()
        self.assertEqual(len(self.rows('SELECT * FROM slideshow_photos WHERE id=?',(pid,))),1)
        status,_,_=self.owner.post('/admin/slideshow/remove',{'csrf':self.csrf,'photo_id':pid},follow=False)
        self.assertEqual(status,303)
        self.assertEqual(Client(self.base).get(f'/slide-image?id={pid}')[0],404)
        self.assertNotIn(f'/slide-image?id={pid}',Client(self.base).get('/')[1])
        server.init_db()
        self.assertEqual(len(self.rows('SELECT * FROM slideshow_photos WHERE id=?',(pid,))),0)

    def test_removing_bundled_photos_and_empty_slideshow_survive_restarts(self):
        initial=self.rows('SELECT id,bundled_path FROM slideshow_photos ORDER BY position,id')
        self.assertEqual(len(initial),len(server.SLIDESHOW_PHOTOS))
        first=initial[0]
        direct_url='/static/images/slides/'+first['bundled_path']
        self.assertEqual(Client(self.base).get(direct_url)[0],200)
        status,_,_=self.owner.post('/admin/slideshow/remove',{'csrf':self.csrf,'photo_id':first['id']},follow=False)
        self.assertEqual(status,303)
        self.assertNotIn(first['bundled_path'],Client(self.base).get('/')[1])
        self.assertEqual(Client(self.base).get(direct_url)[0],404)
        server.init_db()
        self.assertEqual(Client(self.base).get(direct_url)[0],404)
        self.assertEqual(len(self.rows('SELECT * FROM slideshow_photos')),len(initial)-1)
        for row in initial[1:]:
            self.assertEqual(self.owner.post('/admin/slideshow/remove',{'csrf':self.csrf,'photo_id':row['id']},follow=False)[0],303)
        server.init_db()
        self.assertEqual(len(self.rows('SELECT * FROM slideshow_photos')),0)
        status,home,_=Client(self.base).get('/')
        self.assertEqual(status,200);self.assertNotIn('id="slideshow"',home)
        self.assertIn('hero-school-group.jpg',home)
        self.assertIn('No slideshow photos yet',self.owner.get('/admin')[1])
        self.assertEqual(self.add(self.owner,photo_bytes(),caption='A new start')[0],303)
        self.assertIn('id="slideshow"',Client(self.base).get('/')[1])

    def test_only_owner_with_csrf_can_modify_slideshow(self):
        initial=len(self.rows('SELECT id FROM slideshow_photos'))
        image=photo_bytes(size=(20,20))
        anon=Client(self.base)
        self.assertEqual(self.add(anon,image)[0],303)
        self.assertEqual(anon.post('/admin/slideshow/remove',{'csrf':self.csrf,'photo_id':'1'},follow=False)[0],303)
        self.assertEqual(self.add(self.owner,image,csrf='wrong')[0],403)
        self.assertEqual(self.add(self.owner,image,csrf='💥')[0],403)
        self.assertEqual(self.owner.post('/admin/slideshow/remove',{'csrf':'wrong','photo_id':'1'},follow=False)[0],403)
        self.assertEqual(self.add(self.owner,image,origin='https://attacker.invalid')[0],403)
        # A granted, authenticated student is still not the owner.
        student=Client(self.base)
        self.assertEqual(student.post('/signup',{'name':'Student','email':'student@example.test','phone':'0788123456','password':'StudentPass123!'})[0],200)
        uid=self.rows("SELECT id FROM users WHERE email='student@example.test'")[0]['id']
        self.assertEqual(self.owner.post('/admin/user/action',{'csrf':self.csrf,'user_id':uid,'action':'grant'})[0],200)
        self.assertEqual(student.post('/login',{'email':'student@example.test','password':'StudentPass123!'})[0],200)
        student_csrf=student.csrf()
        self.assertEqual(student.get('/admin')[0],403)
        self.assertEqual(self.add(student,image,csrf=student_csrf)[0],403)
        self.assertEqual(student.post('/admin/slideshow/remove',{'csrf':student_csrf,'photo_id':'1'},follow=False)[0],403)
        self.assertEqual(len(self.rows('SELECT id FROM slideshow_photos')),initial)
        for path in ['/slide-image','/slide-image?id=abc','/slide-image?id=99999999999999999999999','/slide-image?id=1']:
            self.assertEqual(anon.get(path)[0],404)

    def test_validation_and_storage_limits(self):
        initial=len(self.rows('SELECT id FROM slideshow_photos'))
        self.assertEqual(self.add(self.owner,b'<svg onload="alert(1)"></svg>',filename='photo.jpg')[0],400)
        self.assertEqual(self.add(self.owner,b'\x89PNG\r\n\x1a\nnot-a-real-image')[0],400)
        self.assertEqual(self.add(self.owner,photo_bytes(fmt='GIF',size=(10,10),animated=True),filename='x.webp',mime='image/webp')[0],400)
        self.assertEqual(self.add(self.owner,photo_bytes(size=(20,20)),caption='x'*161)[0],400)
        with mock.patch.object(server,'MAX_SLIDE_UPLOAD_BYTES',10):
            self.assertEqual(self.add(self.owner,photo_bytes(size=(20,20)))[0],400)
        with mock.patch.object(server,'MAX_SLIDE_REQUEST_BYTES',10):
            self.assertEqual(self.add(self.owner,photo_bytes(size=(20,20)))[0],413)
        with mock.patch.object(server,'MAX_SLIDES',initial):
            self.assertEqual(self.add(self.owner,photo_bytes(size=(20,20)))[0],400)
        with mock.patch.object(server,'MAX_SLIDE_STORAGE_BYTES',1):
            self.assertEqual(self.add(self.owner,photo_bytes(size=(20,20)))[0],400)
        self.assertEqual(len(self.rows('SELECT id FROM slideshow_photos')),initial)
        for fmt,mime in [('PNG','image/png'),('WEBP','image/webp')]:
            self.assertEqual(self.add(self.owner,photo_bytes(fmt=fmt,size=(20,20)),filename='photo.'+fmt.lower(),mime=mime)[0],303,fmt)
        self.assertEqual(len(self.rows("SELECT id FROM slideshow_photos WHERE bundled_path=''")),2)


if __name__=='__main__': unittest.main()
