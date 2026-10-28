"""v18 upgrade, bootstrap, mail and SSRF regression tests.

The fixture is the actual SQLite schema emitted by v17 commit 3e153da, with no user data.
No test sends an email or connects to an external service.
"""
from pathlib import Path
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='70scholar-upgrade-')
        self.addCleanup(self.temp.cleanup)
        p1 = mock.patch.object(server, 'DB_PATH', Path(self.temp.name) / 'old.sqlite3')
        p2 = mock.patch.object(server, 'UPLOAD_DIR', Path(self.temp.name) / 'uploads')
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)
        con = sqlite3.connect(server.DB_PATH)
        con.executescript((ROOT / 'tests/fixtures/v17_schema.sql').read_text())
        con.close()

    def rows(self, sql, values=()):
        with server.db() as c:
            return c.execute(sql, values).fetchall()

    def add_v17_user(self, name, email, password, verified=1, role='student'):
        salt, hashed = server.hash_password(password)
        with server.db() as c:
            return c.execute('INSERT INTO users(name,email,password_hash,salt,role,email_verified,created_at) VALUES(?,?,?,?,?,?,?)',
                             (name,email,hashed,salt,role,verified,server.now_iso())).lastrowid

    def test_actual_v17_schema_upgrade_preserves_and_restricts_records(self):
        owner_id = self.add_v17_user('Old Owner',server.OWNER_ADMIN_EMAIL,'Admin123!',role='admin')
        unchecked = self.add_v17_user('Prior User','prior@example.test','StudentPassword1!')
        proven = self.add_v17_user('Verified User','proven@example.test','StudentPassword1!')
        now = server.now_iso()
        with server.db() as c:
            c.execute("INSERT INTO email_tokens(user_id,token_hash,purpose,created_at,expires_at,used_at) VALUES(?,?,?,?,?,?)",
                      (proven,'previous-token-hash','verify_email',now,now,now))
            c.execute("INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES(?,?,?,?,?)",('old-owner',owner_id,'old-csrf',now,'2099-01-01'))
            c.execute("INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES(?,?,?,?,?)",('old-user',unchecked,'old-csrf',now,'2099-01-01'))
            pid=c.execute("INSERT INTO projects(user_id,title,category,summary,details,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                          (unchecked,'Legacy Project','Education','Old summary','Old detail','public',now,now)).lastrowid
            c.execute("INSERT INTO project_messages(project_id,user_id,name,email,message,created_at) VALUES(?,?,?,?,?,?)",
                      (pid,unchecked,'Prior User','prior@example.test','Old private message',now))
            c.execute("INSERT INTO pledges(project_id,user_id,name,email,amount,status,created_at) VALUES(?,?,?,?,?,?,?)",
                      (pid,unchecked,'Prior User','prior@example.test',50,'paid_demo',now))
            c.execute("INSERT INTO assets(user_id,project_id,filename,stored_path,mime,size,created_at) VALUES(?,?,?,?,?,?,?)",
                      (unchecked,pid,'private-name.pdf','abc.pdf','application/pdf',10,now))
            prog=server.FEATURED_PROGRAMS[1]
            c.execute("INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,source,created_at,auto_description) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (prog['type'],prog['title'],prog['provider'],prog['country'],prog['level'],'2020-01-01',prog['url'],prog['summary'],'featured_program',now,'stale tooltip'))
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'UpgradeOwnerPassword!'}):
            server.init_db()
        owner=self.rows('SELECT * FROM users WHERE id=?',(owner_id,))[0]
        self.assertTrue(server.verify_password('UpgradeOwnerPassword!',owner['salt'],owner['password_hash']))
        self.assertFalse(server.verify_password('Admin123!',owner['salt'],owner['password_hash']))
        self.assertEqual(self.rows('SELECT email_verified FROM users WHERE id=?',(unchecked,))[0]['email_verified'],0)
        self.assertEqual(self.rows('SELECT email_verified FROM users WHERE id=?',(proven,))[0]['email_verified'],1)
        self.assertEqual(self.rows('SELECT status FROM projects WHERE id=?',(pid,))[0]['status'],'pending_review')
        self.assertEqual(self.rows('SELECT status FROM project_messages WHERE project_id=?',(pid,))[0]['status'],'legacy_review')
        self.assertEqual(self.rows('SELECT status FROM pledges WHERE project_id=?',(pid,))[0]['status'],'legacy_unverified')
        self.assertEqual(len(self.rows('SELECT * FROM assets WHERE project_id=?',(pid,))),1)
        program=self.rows('SELECT * FROM opportunities WHERE title=?',(server.FEATURED_PROGRAMS[1]['title'],))[0]
        self.assertEqual(program['deadline'],'2027-01-06');self.assertIn('2027-01-06',program['auto_description'])
        self.assertNotIn('stale tooltip',program['auto_description'])
        self.assertEqual(len(self.rows("SELECT * FROM sessions WHERE token_hash IN ('old-owner','old-user')")),0)
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'UnrelatedNewEnvPassword!'}):
            server.init_db()
        owner2=self.rows('SELECT * FROM users WHERE id=?',(owner_id,))[0]
        self.assertTrue(server.verify_password('UpgradeOwnerPassword!',owner2['salt'],owner2['password_hash']))

    def test_insecure_existing_owner_locks_without_password_and_recovers_once(self):
        owner_id=self.add_v17_user('Old Owner',server.OWNER_ADMIN_EMAIL,'Admin123!',role='admin')
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':''}):
            server.init_db()
            first=self.rows('SELECT * FROM users WHERE id=?',(owner_id,))[0]
            self.assertFalse(server.verify_password('Admin123!',first['salt'],first['password_hash']))
            self.assertTrue(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))
            server.init_db()
            self.assertTrue(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'MyRecoveryPassword!'}):
            server.init_db()
        unlocked=self.rows('SELECT * FROM users WHERE id=?',(owner_id,))[0]
        self.assertTrue(server.verify_password('MyRecoveryPassword!',unlocked['salt'],unlocked['password_hash']))
        self.assertFalse(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))
        salt,hashed=server.hash_password('ManuallyChangedPassword!')
        with server.db() as c: c.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,owner_id))
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'AnotherEnvPassword!'}): server.init_db()
        changed=self.rows('SELECT * FROM users WHERE id=?',(owner_id,))[0]
        self.assertTrue(server.verify_password('ManuallyChangedPassword!',changed['salt'],changed['password_hash']))
        self.assertFalse(server.verify_password('AnotherEnvPassword!',changed['salt'],changed['password_hash']))

    def test_new_owner_without_config_is_locked_until_configured(self):
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':''}): server.init_db()
        self.assertTrue(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'Admin123!'}): server.init_db()
        row=self.rows('SELECT * FROM users WHERE email=?',(server.OWNER_ADMIN_EMAIL,))[0]
        self.assertFalse(server.verify_password('Admin123!',row['salt'],row['password_hash']))
        self.assertTrue(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))
        with mock.patch.dict(os.environ, {'ADMIN_PASSWORD':'NewOwnerPassword!'}): server.init_db()
        row=self.rows('SELECT * FROM users WHERE email=?',(server.OWNER_ADMIN_EMAIL,))[0]
        self.assertTrue(server.verify_password('NewOwnerPassword!',row['salt'],row['password_hash']))
        self.assertFalse(self.rows("SELECT * FROM settings WHERE key='admin_bootstrap_locked'"))


class EmailAndFetchTests(unittest.TestCase):
    def test_bird_transactional_payload_disables_tracking(self):
        class Accepted:
            status=202
            def __enter__(self): return self
            def __exit__(self,*_): pass
        with mock.patch.object(server,'BIRD_API_KEY','bk_us1_fake'), \
             mock.patch.object(server,'BIRD_REGION','us1'), \
             mock.patch.object(server,'BIRD_FROM','noreply@sender.example'), \
             mock.patch.object(server.urllib.request,'urlopen',return_value=Accepted()) as send:
            server.send_email('recipient@example.test','Verify email','Verification link')
        req=send.call_args.args[0]
        body=json.loads(req.data)
        self.assertEqual(req.full_url,'https://us1.platform.bird.com/v1/email/messages')
        self.assertEqual(body['category'],'transactional')
        self.assertIs(body['track_clicks'],False)
        self.assertIs(body['track_opens'],False)
        self.assertEqual(body['to'],['recipient@example.test'])
        self.assertEqual(body['from'],'noreply@sender.example')

    def test_unconfigured_email_is_not_written_to_a_local_outbox(self):
        with mock.patch.object(server,'BIRD_API_KEY',''),mock.patch.object(server,'SMTP_HOST',''):
            with self.assertRaises(RuntimeError): server.send_email('x@example.test','test','secret link')

    def test_redirect_to_private_address_is_rejected(self):
        class Redirect:
            status=302
            def getheader(self,k): return 'http://127.0.0.1/private' if k=='Location' else None
        class Connection:
            def request(self,*a,**kw): pass
            def getresponse(self): return Redirect()
            def close(self): pass
        def lookup(host,port,**kwargs):
            return [(2,1,6,'',(host if host=='127.0.0.1' else '93.184.216.34',port))]
        with mock.patch.object(server.socket,'getaddrinfo',side_effect=lookup), \
             mock.patch.object(server,'_PinnedHTTPSConnection',return_value=Connection()):
            with self.assertRaises(ValueError): server.safe_http_get('https://example.org/redirect')

    def test_request_logs_redact_token(self):
        fake=mock.Mock();fake.log_date_time_string.return_value='time'
        out=io.StringIO()
        with mock.patch.object(sys,'stderr',out):
            server.ScholarHandler.log_message(fake,'%s','GET /verify-email?token=sensitive&next=x HTTP/1.1')
        self.assertNotIn('sensitive',out.getvalue())
        self.assertIn('token=[redacted]',out.getvalue())

if __name__ == '__main__': unittest.main()
