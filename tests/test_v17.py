"""Integration and privacy/security regression checks for 70Scholar.

Run: python3 -m unittest discover -s tests -v
All tests use temporary SQLite databases and a local HTTP server.
"""
from __future__ import annotations

import base64
import http.cookiejar
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['ADMIN_PASSWORD']='TestOwnerPassword123!'
os.environ.pop('BIRD_API_KEY',None)
os.environ.pop('SMTP_HOST',None)
import server

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

class Client:
    def __init__(self, base):
        self.base=base; self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.no_redirect=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())
    def request(self,path,data=None,follow=True,method=None,headers=None):
        if isinstance(data,dict): data=urllib.parse.urlencode(data).encode()
        req=urllib.request.Request(self.base+path,data=data,method=method,headers=headers or {})
        try:
            with (self.opener if follow else self.no_redirect).open(req,timeout=15) as r:
                return r.status,r.read().decode('utf-8',errors='replace'),r.headers
        except urllib.error.HTTPError as ex:
            return ex.code,ex.read().decode('utf-8',errors='replace'),ex.headers
    def get(self,path,follow=True): return self.request(path,follow=follow)
    def post(self,path,data,follow=True): return self.request(path,data=data,follow=follow)
    def json(self,path,payload,csrf):
        return self.request(path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':csrf})
    def csrf(self,path='/dashboard'):
        status,html,_=self.get(path)
        assert status==200,(path,status,html[:200])
        m=re.search(r"name=['\"]csrf['\"]\s+value=['\"]([^'\"]+)",html)
        assert m,(path,html[:200]);return m.group(1)

class ScholarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.ScholarHandler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_address[1]}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='70scholar-tests-')
        server.DB_PATH=Path(self.tmp.name)/'test.sqlite3';server.UPLOAD_DIR=Path(self.tmp.name)/'uploads'
        server.EMAIL_ENABLED=False
        server.init_db()
        self.admin=Client(self.base)
        status,_,_=self.admin.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':os.environ['ADMIN_PASSWORD']})
        self.assertEqual(status,200)
        self.admin_csrf=self.admin.csrf('/admin')
    def tearDown(self): self.tmp.cleanup()
    def db(self,sql,args=(),one=False):
        with server.db() as conn:
            rows=conn.execute(sql,args).fetchall()
        return rows[0] if one and rows else (None if one else rows)
    def signup(self,name,email,phone='+250 788 123 456',password='StudentPass123!'):
        c=Client(self.base)
        status,html,_=c.post('/signup',{'name':name,'email':email,'phone':phone,'password':password})
        self.assertEqual(status,200,html[:200])
        uid=self.db('SELECT id FROM users WHERE email=?',(email,),True)['id']
        return c,uid
    def grant_and_login(self,c,uid,email,password='StudentPass123!'):
        status,_,_=self.admin.post('/admin/user/action',{'csrf':self.admin_csrf,'user_id':uid,'action':'grant'})
        self.assertEqual(status,200)
        status,html,_=c.post('/login',{'email':email,'password':password})
        self.assertEqual(status,200,html[:200])
        return c.csrf()
    def user(self,name='Alice Builder',email='alice@example.test',phone='+250 788 123 456'):
        c,uid=self.signup(name,email,phone); csrf=self.grant_and_login(c,uid,email)
        return c,uid,csrf
    def submit_project(self,c,csrf,summary=None):
        status,html,_=c.post('/project/save',{'csrf':csrf,'title':'Learning Lab','category':'Education',
          'summary':summary or 'A collaborative study tool helping students prepare for university applications.',
          'details':'This project helps students organise study plans and share exercises. It will support learners who lack access to practice materials. Funding will pay for testing, hosting, and accessible design.',
          'goal_amount':'250','price':'0','status':'public'})
        self.assertEqual(status,200,html[:300])
        return self.db("SELECT id FROM projects WHERE title='Learning Lab'",one=True)['id']
    def approve(self,pid,revision=None,confirmed='1'):
        row=self.db('SELECT review_version FROM projects WHERE id=?',(pid,),True)
        status,html,_=self.admin.post('/admin/project/action',{'csrf':self.admin_csrf,'project_id':pid,'action':'approve','confirmed':confirmed,'review_version':str(row['review_version'] if revision is None else revision)})
        return status,html

    def test_cross_origin_login_rejected(self):
        c=Client(self.base)
        data=urllib.parse.urlencode({'email':server.OWNER_ADMIN_EMAIL,'password':os.environ['ADMIN_PASSWORD']}).encode()
        status,html,_=c.request('/login',data=data,headers={'Content-Type':'application/x-www-form-urlencoded','Origin':'https://attacker.invalid'})
        self.assertEqual(status,403);self.assertIn('Security check failed',html)
        status,_,_=c.request('/login',data=data,headers={'Content-Type':'application/x-www-form-urlencoded','Origin':self.base},follow=False)
        self.assertEqual(status,303)

    def test_public_home_private_programs_and_images(self):
        anon=Client(self.base); status,home,headers=anon.get('/')
        self.assertEqual(status,200);self.assertEqual(headers['Referrer-Policy'],'strict-origin')
        for absent in ('Real students. Real scholars. Real futures.','Real moments from real learners.','NESA','photo-gallery','students-library.jpg','https://africanscholars.yale.edu'):
            self.assertNotIn(absent,home)
        for present in ('Moments along the learning journey.','id="slideshow"','ilead-students.jpg','university-graduation.jpg','students-reading.jpg',server.HELPLINE_PHONE,server.HELPLINE_EMAIL): self.assertIn(present,home)
        self.assertEqual(len(server.SLIDESHOW_PHOTOS),17)
        status,_,headers=anon.get('/programs',False)
        self.assertEqual(status,303);self.assertTrue(headers['Location'].startswith('/login'))
        status,_,_=anon.request('/programs',method='HEAD',follow=False);self.assertEqual(status,303)
        status,page,_=self.admin.get('/programs'); self.assertEqual(status,200)
        for pr in server.FEATURED_PROGRAMS:
            self.assertIn(server.e(pr['title']),page)
            self.assertNotIn(pr['url'],home)
        self.assertEqual(server.FEATURED_PROGRAMS[1]['deadline'],'2027-01-06')
        status,version,_=anon.get('/version');self.assertEqual(status,200);self.assertIn(server.APP_VERSION,version)

    def test_signup_needs_phone_and_admin_grant_is_not_email_verification(self):
        anon=Client(self.base)
        status,html,_=anon.post('/signup',{'name':'Jane Person','email':'jane@example.test','password':'StudentPass123!'})
        self.assertEqual(status,400);self.assertIn('phone',html.lower())
        c,uid=self.signup('Jane Person','jane@example.test')
        status,html,_=c.post('/login',{'email':'jane@example.test','password':'StudentPass123!'})
        self.assertEqual(status,403);self.assertIn('owner',html.lower())
        row=self.db('SELECT * FROM users WHERE id=?',(uid,),True)
        self.assertEqual((row['email_verified'],row['admin_approved']),(0,0))
        status,admin_page,_=self.admin.get('/admin');self.assertIn('+250 788 123 456',admin_page)
        self.grant_and_login(c,uid,'jane@example.test')
        row=self.db('SELECT * FROM users WHERE id=?',(uid,),True)
        self.assertEqual((row['email_verified'],row['admin_approved']),(0,1))
        status,dash,_=c.get('/dashboard');self.assertIn('Access granted by the owner',dash)
        self.assertEqual(self.db('SELECT COUNT(*) n FROM sessions WHERE user_id=?',(uid,),True)['n'],1)
        self.admin.post('/admin/user/action',{'csrf':self.admin_csrf,'user_id':uid,'action':'revoke'})
        status,_,_=c.get('/dashboard',False);self.assertEqual(status,303)

    def test_real_verification_and_failed_delivery(self):
        sent=[]
        def fake_send(email,subject,body,html_body=None): sent.append((email,body))
        c=Client(self.base)
        with mock.patch.object(server,'EMAIL_ENABLED',True),mock.patch.object(server,'send_email',side_effect=fake_send):
            status,html,_=c.post('/signup',{'name':'Emilia Learner','email':'emilia@example.test','phone':'0788123456','password':'StudentPass123!'})
            self.assertEqual(status,200);self.assertIn('Check your email',html)
        self.assertEqual(len(sent),1)
        link=re.search(r'(/verify-email\?token=[^\s]+)',sent[0][1]).group(1)
        status,html,_=c.get(link);self.assertEqual(status,200);self.assertIn('Email verified',html)
        self.assertEqual(self.db('SELECT email_verified FROM users WHERE email=?',('emilia@example.test',),True)['email_verified'],1)
        status,_,_=c.post('/login',{'email':'emilia@example.test','password':'StudentPass123!'});self.assertEqual(status,200)
        fail=Client(self.base)
        with mock.patch.object(server,'EMAIL_ENABLED',True),mock.patch.object(server,'send_email',side_effect=RuntimeError('provider error')):
            status,html,_=fail.post('/signup',{'name':'Failed Mail','email':'failed@example.test','phone':'0788123456','password':'StudentPass123!'})
            self.assertEqual(status,200);self.assertIn('awaiting access',html)
            status,_,_=fail.post('/login',{'email':'failed@example.test','password':'StudentPass123!'});self.assertEqual(status,403)
        self.assertEqual(self.db('SELECT email_verified FROM users WHERE email=?',('failed@example.test',),True)['email_verified'],0)

    def test_verification_token_is_single_use_even_concurrently(self):
        _,uid=self.signup('Token Tester','token@example.test')
        token=server.create_email_token(uid,'verify_email')
        barrier=threading.Barrier(2);results=[];errors=[]
        def consume():
            try:
                barrier.wait(timeout=5)
                results.append(server.ScholarHandler.consume_email_token(None,token,'verify_email'))
            except Exception as ex: errors.append(ex)
        a=threading.Thread(target=consume);b=threading.Thread(target=consume)
        a.start();b.start();a.join(timeout=10);b.join(timeout=10)
        self.assertFalse(errors);self.assertEqual(sum(row is not None for row in results),1)

    def test_granted_user_can_verify_later_when_provider_is_available(self):
        user,uid,csrf=self.user('Verified Later','later@example.test')
        self.assertIn('Send a verification link',user.get('/account')[1])
        status,html,_=user.post('/account/verify-email',{'csrf':csrf})
        self.assertEqual(status,503);self.assertIn('remains unverified',html)
        sent=[]
        with mock.patch.object(server,'EMAIL_ENABLED',True),mock.patch.object(server,'send_email',side_effect=lambda email,subject,body,html_body=None:sent.append(body)):
            status,html,_=user.post('/account/verify-email',{'csrf':csrf})
        self.assertEqual(status,200);self.assertIn('verification link was sent',html)
        link=re.search(r'(/verify-email\?token=[^\s]+)',sent[0]).group(1)
        self.assertEqual(user.get(link)[0],200)
        self.assertEqual(self.db('SELECT email_verified FROM users WHERE id=?',(uid,),True)['email_verified'],1)
        self.admin.post('/admin/user/action',{'csrf':self.admin_csrf,'user_id':uid,'action':'revoke'})
        self.assertEqual(user.get('/dashboard')[0],200)

    def test_project_approval_revisions_uploads_and_privacy(self):
        builder,uid,csrf=self.user()
        status,wizard,_=builder.get('/workspace');self.assertIn('data-wizard="true"',wizard);self.assertIn('Guided steps',wizard);self.assertIn('Full form',wizard)
        status,full,_=builder.get('/workspace?mode=full');self.assertNotIn('data-wizard="true"',full)
        pid=self.submit_project(builder,csrf,'Alice Builder can be reached at alice@example.test or 0788123456 for this learning project.')
        row=self.db('SELECT * FROM projects WHERE id=?',(pid,),True);self.assertEqual(row['status'],'pending_review')
        self.assertEqual(self.approve(pid,confirmed='')[0],400)
        # Private legacy payout information must never be shown to other members.
        with server.db() as conn:
            conn.execute("UPDATE projects SET mobile_money_name='Alice Builder',mobile_money_number='0788123456',mobile_money_network='MTN' WHERE id=?",(pid,))
        data=base64.b64encode(b'private prototype content').decode()
        status,payload,_=builder.json('/api/upload',{'project_id':pid,'filename':'alice-secret.pdf','mime':'application/pdf','data':data},csrf)
        self.assertEqual(status,200);asset_id=int(re.search(r'id=(\d+)',json.loads(payload)['download_url']).group(1))
        self.assertEqual(self.approve(pid,revision=0)[0],400,'stale approval cannot publish a newer upload')
        stranger,_,_=self.user('Bob Supporter','bob@example.test','0788999123')
        self.assertEqual(stranger.get(f'/download?id={asset_id}')[0],403)
        self.assertEqual(self.admin.get(f'/download?id={asset_id}')[0],200)
        # A copied legacy flat upload can be found after moving to a persistent directory.
        old_path=self.db('SELECT stored_path FROM assets WHERE id=?',(asset_id,),True)['stored_path']
        with server.db() as conn:
            conn.execute('UPDATE assets SET stored_path=? WHERE id=?',('/old/render/uploads/'+Path(old_path).name,asset_id))
        self.assertEqual(self.admin.get(f'/download?id={asset_id}')[0],200)
        self.assertEqual(self.approve(pid)[0],200)
        _,detail,_=stranger.get(f'/project?id={pid}')
        for secret in ('Alice Builder','alice@example.test','0788123456','alice-secret.pdf','Creator Mobile Money'):
            self.assertNotIn(secret,detail)
        self.assertIn('[removed]',detail);self.assertIn('Project file 1',detail)
        status,body,headers=stranger.get(f'/download?id={asset_id}')
        self.assertEqual(status,200);self.assertNotIn('alice-secret',headers['Content-Disposition'])
        # Any upload to an approved project takes it out of public view.
        builder.json('/api/upload',{'project_id':pid,'filename':'new.pdf','mime':'application/pdf','data':data},csrf)
        self.assertEqual(self.db('SELECT status FROM projects WHERE id=?',(pid,),True)['status'],'pending_review')
        self.assertIn('not found',stranger.get(f'/project?id={pid}')[1].lower())
        self.assertEqual(self.approve(pid)[0],200)
        status,_,_=builder.post('/project/save',{'csrf':csrf,'project_id':pid,'title':'Learning Lab','category':'Education','summary':'A collaborative study tool helping students prepare for university applications.','details':'This project helps students organise study plans and share exercises. It will support learners who lack access to practice materials. Funding will pay for testing, hosting, and accessible design.','goal_amount':'250','price':'0','status':'public'})
        self.assertEqual(status,200);self.assertEqual(self.db('SELECT status FROM projects WHERE id=?',(pid,),True)['status'],'pending_review')

    def test_message_moderation_session_ban_review_and_alias(self):
        builder,_,bcsrf=self.user();pid=self.submit_project(builder,bcsrf);self.assertEqual(self.approve(pid)[0],200)
        sender,sid,csrf=self.user('Sam Sponsor','sam@example.test','0788333444')
        status,_,_=sender.post('/project/message',{'project_id':pid,'message':'Can you describe the testing plan?'})
        self.assertEqual(status,403);self.assertEqual(self.db('SELECT banned FROM users WHERE id=?',(sid,),True)['banned'],0)
        status,_,_=sender.post('/project/message',{'csrf':csrf,'project_id':pid,'message':'Can you describe the testing plan?'})
        self.assertEqual(status,200)
        _,inbox,_=builder.get('/messages');self.assertIn('Community member',inbox);self.assertNotIn('Sam Sponsor',inbox);self.assertNotIn('sam@example.test',inbox);self.assertNotIn('0788333444',inbox)
        status,html,_=sender.post('/project/message',{'csrf':csrf,'project_id':pid,'message':'Please contact me on +250 788 333 444.'})
        self.assertEqual(status,403);self.assertIn('removed',html.lower())
        self.assertEqual(self.db('SELECT banned FROM users WHERE id=?',(sid,),True)['banned'],1)
        self.assertEqual(self.db('SELECT COUNT(*) n FROM sessions WHERE user_id=?',(sid,),True)['n'],0)
        self.assertEqual(sender.get('/dashboard',False)[0],303)
        self.assertEqual(self.db('SELECT COUNT(*) n FROM project_messages WHERE project_id=?',(pid,),True)['n'],1)
        _,admin_page,_=self.admin.get('/admin');self.assertIn('0788',admin_page.replace(' ',''));self.assertIn('Flagged messages',admin_page)
        self.admin.post('/admin/user/action',{'csrf':self.admin_csrf,'user_id':sid,'action':'unban'})
        self.assertEqual(sender.post('/login',{'email':'sam@example.test','password':'StudentPass123!'})[0],200)
        self.admin.post('/admin/message/settings',{'csrf':self.admin_csrf,'blocked_phrases':'secret phrase'})
        csrf=sender.csrf()
        self.assertEqual(sender.post('/project/message',{'csrf':csrf,'project_id':pid,'message':'This contains a secret phrase for testing.'})[0],403)
        self.assertEqual(self.db('SELECT COUNT(*) n FROM message_incidents WHERE user_id=?',(sid,),True)['n'],2)

    def test_owner_payment_flow_pending_confirmation_and_disbursement(self):
        builder,_,bcsrf=self.user(); pid=self.submit_project(builder,bcsrf);self.assertEqual(self.approve(pid)[0],200)
        supporter,sid,csrf=self.user('Taylor Supporter','taylor@example.test','0788666777')
        self.assertIn('Funding is unavailable',supporter.get(f'/project?id={pid}')[1])
        self.assertEqual(supporter.post('/pledge',{'csrf':csrf,'project_id':pid,'amount':'25'})[0],503)
        self.assertEqual(self.admin.post('/admin/payment/settings',{'csrf':self.admin_csrf,'owner_payment_link':'http://example.org/pay'})[0],400)
        self.assertEqual(self.admin.post('/admin/payment/settings',{'csrf':self.admin_csrf,'owner_payment_link':'https://pay.example.org/owner'})[0],200)
        for invalid in ('NaN','Infinity','-4','1.001','999999999999'):
            self.assertEqual(supporter.post('/pledge',{'csrf':csrf,'project_id':pid,'amount':invalid})[0],400)
        self.assertEqual(supporter.post('/pledge',{'csrf':csrf,'project_id':pid,'amount':'12','provider':'momo'})[0],400)
        status,page,_=supporter.post('/pledge',{'csrf':csrf,'project_id':pid,'amount':'25.50'})
        self.assertEqual(status,200);self.assertIn('https://pay.example.org/owner',page);self.assertIn('remains pending',page)
        pledge=self.db('SELECT * FROM pledges WHERE user_id=?',(sid,),True);self.assertEqual(pledge['status'],'payment_pending')
        self.assertEqual(supporter.get(f"/payment/success?pledge_id={pledge['id']}")[0],200)
        self.assertEqual(self.db('SELECT status FROM pledges WHERE id=?',(pledge['id'],),True)['status'],'payment_pending')
        self.assertEqual(builder.get(f"/payment/start?pledge_id={pledge['id']}")[0],404)
        _,detail,_=supporter.get(f'/project?id={pid}');self.assertIn('$0.00',detail);self.assertNotIn('Taylor Supporter',detail)
        data={'csrf':self.admin_csrf,'pledge_id':pledge['id'],'action':'confirm'}
        self.assertEqual(self.admin.post('/admin/payment/action',data)[0],400)
        data['confirmed']='1';self.assertEqual(self.admin.post('/admin/payment/action',data)[0],200)
        self.assertEqual(self.db('SELECT status FROM pledges WHERE id=?',(pledge['id'],),True)['status'],'paid_confirmed')
        _,detail,_=builder.get(f'/project?id={pid}');self.assertIn('$25.50',detail);self.assertNotIn('taylor@example.test',detail)
        disb={'csrf':self.admin_csrf,'project_id':pid,'amount':'30','reference':'TRANSFER-A','confirmed':'1'}
        self.assertEqual(self.admin.post('/admin/disbursement',disb)[0],400)
        disb['amount']='20.25';status,html,_=self.admin.post('/admin/disbursement',disb)
        self.assertEqual(status,200);self.assertIn('did not transfer any money',html)
        self.assertEqual(self.db('SELECT amount FROM disbursements WHERE project_id=?',(pid,),True)['amount'],20.25)

    def test_legacy_migration_is_conservative_and_idempotent(self):
        c,uid,_=self.user('Legacy Person','legacy@example.test')
        now=server.now_iso()
        with server.db() as conn:
            conn.execute("UPDATE users SET email_verified=1,admin_approved=1 WHERE id=?",(uid,))
            cur=conn.execute("INSERT INTO projects(user_id,title,category,summary,details,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(uid,'Old Public','Education','Summary','Detail','public',now,now));pid=cur.lastrowid
            cur=conn.execute("INSERT INTO pledges(project_id,user_id,name,email,amount,status,created_at) VALUES(?,?,?,?,?,?,?)",(pid,uid,'Legacy Person','legacy@example.test',20,'paid_demo',now));pl=cur.lastrowid
            conn.execute("INSERT INTO project_messages(project_id,user_id,name,email,message,created_at,status) VALUES(?,?,?,?,?,?,?)",(pid,uid,'Legacy Person','legacy@example.test','Hello this is old.',now,'legacy_review'))
            conn.execute("DELETE FROM settings WHERE key='v18_privacy_migration'")
        server.init_db()
        user=self.db('SELECT * FROM users WHERE id=?',(uid,),True)
        self.assertEqual((user['email_verified'],user['admin_approved']),(0,0))
        self.assertEqual(self.db('SELECT status FROM projects WHERE id=?',(pid,),True)['status'],'pending_review')
        self.assertEqual(self.db('SELECT status FROM pledges WHERE id=?',(pl,),True)['status'],'legacy_unverified')
        self.assertEqual(c.get('/dashboard',False)[0],303)
        with server.db() as conn: conn.execute("UPDATE projects SET status='public' WHERE id=?",(pid,))
        server.init_db()
        self.assertEqual(self.db('SELECT status FROM projects WHERE id=?',(pid,),True)['status'],'public')
        self.assertEqual(self.db('SELECT status FROM project_messages WHERE project_id=?',(pid,),True)['status'],'legacy_review')

    def test_link_submission_review_and_ssrf_checks(self):
        c,_,csrf=self.user('Community Writer','writer@example.test')
        html="<html><head><meta property='og:title' content='Community STEM Fellowship'><meta property='og:description' content='A programme for students.'><meta property='og:image' content='/media/img.jpg'></head><body>Applications close 2027-04-30.</body></html>"
        with mock.patch.object(server,'safe_http_get',return_value=(html,'text/html')):
            status,body,_=c.post('/opportunity/submit-link',{'csrf':csrf,'url':'https://example.org/fellowship','note':'A good programme'})
        self.assertEqual(status,200);self.assertIn('Link received',body)
        sub=self.db('SELECT * FROM opportunity_submissions WHERE title=?',('Community STEM Fellowship',),True);self.assertEqual(sub['status'],'pending')
        _,admin,_=self.admin.get('/admin');self.assertIn(f"/admin/submission/preview?id={sub['id']}",admin);self.assertIn('What we found on the page',admin)
        data={'csrf':self.admin_csrf,'submission_id':sub['id'],'action':'approve'}
        self.assertEqual(self.admin.post('/admin/submission/action',data)[0],400)
        data.update({'confirmed':'1','title':'Reviewed Fellowship','provider':'Example','deadline':'2027-04-30','summary':'An opportunity reviewed by the owner.'})
        status,review_page,_=self.admin.post('/admin/submission/action',data)
        self.assertEqual(status,200)
        self.assertIsNotNone(self.db('SELECT id FROM opportunities WHERE title=?',('Reviewed Fellowship',),True))
        self.assertNotIn(f"/admin/submission/preview?id={sub['id']}",review_page)
        self.assertIn('Reviewed Fellowship',review_page)
        for bad in ('http://localhost/','http://127.0.0.1/','http://10.1.2.3/','file:///etc/passwd','https://public.example:8443/'):
            self.assertFalse(server.is_safe_public_url(bad),bad)
        with mock.patch.object(server.socket,'getaddrinfo',return_value=[(2,1,6,'',('93.184.216.34',443)),(2,1,6,'',('127.0.0.1',443))]):
            self.assertFalse(server.is_safe_public_url('https://example.org'))
        class Response:
            status=200
            def getheader(self,key): return 'text/html' if key=='Content-Type' else None
            def read(self,n): return b'<html>ok</html>'
        class Connection:
            def request(self,*a,**kw): pass
            def getresponse(self): return Response()
            def close(self): pass
        addresses=[(2,1,6,'',('93.184.216.34',443))]
        with mock.patch.object(server.socket,'getaddrinfo',return_value=addresses) as dns, mock.patch.object(server,'_PinnedHTTPSConnection',return_value=Connection()) as con:
            self.assertEqual(server.safe_http_get('https://example.org/x')[0],'<html>ok</html>')
            con.assert_called_once_with('example.org','93.184.216.34',443,10);self.assertEqual(dns.call_count,1)

    def test_concurrent_disbursements_cannot_overrecord(self):
        builder,_,csrf=self.user()
        pid=self.submit_project(builder,csrf)
        self.assertEqual(self.approve(pid)[0],200)
        now=server.now_iso()
        with server.db() as conn:
            conn.execute("INSERT INTO pledges(project_id,user_id,name,email,amount,status,created_at) VALUES(?,?,?,?,?,?,?)",
                         (pid,None,'','','25.00','paid_confirmed',now))
        other_admin=Client(self.base)
        self.assertEqual(other_admin.post('/login',{'email':server.OWNER_ADMIN_EMAIL,'password':os.environ['ADMIN_PASSWORD']})[0],200)
        other_csrf=other_admin.csrf('/admin')
        ready=threading.Barrier(2); results=[]; errors=[]
        def record(client,token,reference):
            try:
                ready.wait(timeout=5)
                results.append(client.post('/admin/disbursement',{'csrf':token,'project_id':pid,'amount':'20.00','reference':reference,'confirmed':'1'})[0])
            except Exception as ex: errors.append(ex)
        a=threading.Thread(target=record,args=(self.admin,self.admin_csrf,'external-a'))
        b=threading.Thread(target=record,args=(other_admin,other_csrf,'external-b'))
        a.start();b.start();a.join(timeout=15);b.join(timeout=15)
        self.assertFalse(errors);self.assertEqual(sorted(results),[200,400])
        self.assertEqual(self.db('SELECT SUM(amount) n FROM disbursements WHERE project_id=?',(pid,),True)['n'],20.0)

    def test_owner_message_violation_does_not_falsely_claim_ban(self):
        builder,_,csrf=self.user();pid=self.submit_project(builder,csrf);self.assertEqual(self.approve(pid)[0],200)
        self.admin.post('/admin/payment/settings',{'csrf':self.admin_csrf,'owner_payment_link':'https://pay.example.org/owner'})
        status,body,_=self.admin.post('/pledge',{'csrf':self.admin_csrf,'project_id':pid,'amount':'10','message':'Please call me on +250 788 123 456.'})
        self.assertEqual(status,403);self.assertIn('removed for owner review',body);self.assertNotIn('account is blocked',body)
        self.assertEqual(self.admin.get('/admin')[0],200)
        self.assertEqual(self.db('SELECT banned FROM users WHERE email=?',(server.OWNER_ADMIN_EMAIL,),True)['banned'],0)

    def test_untrusted_opportunity_links_cannot_become_script_urls(self):
        c,_,csrf=self.user('Opportunity Tester','opp@example.test')
        base={'csrf':csrf,'title':'Questionable link','summary':'A community submitted scholarship.'}
        for bad in ('javascript:alert(1)','https://','http://localhost/admin','https://user:pass@example.org/x'):
            data={**base,'url':bad}
            self.assertEqual(c.post('/opportunity/submit',data)[0],400,bad)
        now=server.now_iso()
        with server.db() as conn:
            conn.execute("INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         ('Scholarship','Legacy Bad Link','Unknown','Global','Students','See official page','javascript:alert(1)','An old imported opportunity.','legacy',now))
        html=c.get('/opportunities')[1]
        self.assertIn('Legacy Bad Link',html);self.assertNotIn('href="javascript:',html)
        self.assertEqual(server.anchor_url('https://example.org/path'),'https://example.org/path')
        self.assertEqual(server.anchor_url('javascript:alert(1)'),'#')

    def test_owner_can_page_through_all_accounts(self):
        salt,hashed=server.hash_password('BulkTestPassword!')
        with server.db() as conn:
            for i in range(53):
                conn.execute('INSERT INTO users(name,email,password_hash,salt,created_at) VALUES(?,?,?,?,?)',
                             (f'User {i}',f'bulk{i:02}@example.test',hashed,salt,server.now_iso()))
        first=self.admin.get('/admin?users_page=1')[1]
        second=self.admin.get('/admin?users_page=2')[1]
        self.assertIn('Page 1 of 2',first);self.assertIn('Page 2 of 2',second)
        self.assertNotIn('bulk00@example.test',first);self.assertIn('bulk00@example.test',second)

    def test_profile_photo_is_private_and_rejects_svg(self):
        c,_,csrf=self.user();other,_,_=self.user('Other Person','other@example.test')
        svg=base64.b64encode(b'<svg onload="alert(1)"></svg>').decode()
        self.assertEqual(c.json('/api/profile-photo',{'filename':'bad.svg','mime':'image/svg+xml','data':svg},csrf)[0],400)
        gif=base64.b64encode(b'GIF89a' + b'\x00'*20).decode()
        status,body,_=c.json('/api/profile-photo',{'filename':'safe.gif','mime':'image/gif','data':gif},csrf)
        self.assertEqual(status,200);url=json.loads(body)['url']
        self.assertEqual(c.get(url)[0],200);self.assertEqual(other.get(url)[0],403);self.assertEqual(Client(self.base).get(url,False)[0],303)
        self.assertEqual(self.admin.get(url)[0],200)

if __name__=='__main__': unittest.main()
