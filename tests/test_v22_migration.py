"""Synthetic offline-v21 -> PostgreSQL migration tests; never use real data."""
import hashlib
import os
import secrets
import sqlite3
import tempfile
import threading
import unittest
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from contextlib import closing
from unittest import mock
from urllib.parse import urlparse

import pg_compat
import server
from migrate_sqlite import MigrationError, inspect_backup, migrate

TEST_URL = os.environ.get('SCHOLAR70_MIGRATION_TEST_URL', '')
LOCAL = (urlparse(TEST_URL).hostname or '').lower() in ('127.0.0.1', 'localhost', '::1')


@unittest.skipUnless(TEST_URL and LOCAL and pg_compat.psycopg, 'requires disposable local PostgreSQL')
class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='70scholar-migration-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'snapshot.sqlite3'
        self.uploads = self.root / 'uploads'
        self.schema = 'migrtest_' + secrets.token_hex(8)
        self.addCleanup(self.drop_test_schema)
        with mock.patch.object(server, 'DATABASE_URL', ''), \
             mock.patch.object(server, 'DB_PATH', self.source), \
             mock.patch.object(server, 'UPLOAD_DIR', self.uploads), \
             mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'SyntheticOwnerPass123!'}):
            server.init_db()
        photo_name = 'user-2-' + ('a' * 16) + '.png'
        self.profile = self.uploads / 'profiles' / photo_name
        self.profile.parent.mkdir()
        self.profile.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic image only')
        with closing(sqlite3.connect(self.source)) as c, c:
            c.execute('PRAGMA foreign_keys=ON')
            salt, password_hash = server.hash_password('SyntheticUserPass123!')
            c.execute("INSERT INTO users(id,name,email,password_hash,salt,role,email_verified,admin_approved,profile_photo_url,phone,created_at) VALUES(2,?,?,?,?,?,0,1,?,?,?)",
                      ('Synthetic Student', 'student@example.test', password_hash, salt, 'student', '/uploads/profiles/'+photo_name, '+250788111222', server.now_iso()))
            c.execute("INSERT INTO projects(id,user_id,title,category,summary,details,status,created_at,updated_at) VALUES(7,2,'Synthetic project','Education','Synthetic summary','Synthetic details','draft',?,?)", (server.now_iso(), server.now_iso()))
            asset_name = '7-' + ('b' * 16) + '-proof.pdf'
            self.asset = self.uploads / asset_name
            self.asset.write_bytes(b'private synthetic project file')
            c.execute("INSERT INTO assets(id,user_id,project_id,filename,stored_path,mime,size,created_at) VALUES(8,2,7,'proof.pdf',?,'application/pdf',?,?)", ('/opt/render/project/src/uploads/'+asset_name, self.asset.stat().st_size, server.now_iso()))
            c.execute("INSERT INTO slideshow_photos(id,bundled_path,data,caption,position,created_at) VALUES(100,'',?,'Synthetic saved photo',-1,?)", (b'synthetic slide bytes', server.now_iso()))
            c.execute("DELETE FROM slideshow_photos WHERE bundled_path='slide-01.jpg'")
            # SQLite retains this high-water mark even though the row is deleted.
            c.execute("INSERT INTO projects(id,user_id,title,category,summary,details,status,created_at,updated_at) VALUES(500,2,'Deleted synthetic','Education','x','x','draft',?,?)", (server.now_iso(), server.now_iso()))
            c.execute('DELETE FROM projects WHERE id=500')
            c.execute('DROP TABLE media_objects')  # v21 stored uploads as files, not in the database.
        (self.uploads / 'orphan-old.txt').write_text('unreferenced synthetic file')

    def drop_test_schema(self):
        from psycopg import sql
        with pg_compat._connect(TEST_URL) as c:
            c.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(self.schema)))

    def target_exists(self):
        with pg_compat._connect(TEST_URL) as c:
            return bool(c.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s', (self.schema,)).fetchone())

    def test_import_preserves_records_media_removals_and_sequence_high_water(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with mock.patch('pg_compat._connect', side_effect=AssertionError('unexpected network access')):
            inspected = inspect_backup(self.source, self.uploads)
        self.assertEqual(inspected['source_counts']['users'], 2)
        self.assertEqual(inspected['referenced_uploads'], 2)
        self.assertFalse(self.target_exists())
        result = migrate(self.source, self.uploads, TEST_URL, self.schema)
        self.assertEqual(result['referenced_uploads'], 2)
        self.assertEqual(result['unreferenced_uploads_in_backup'], 1)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)
        self.assertTrue(self.target_exists())
        with mock.patch.object(server, 'DATABASE_URL', TEST_URL), \
             mock.patch.object(server, 'PG_SCHEMA', self.schema), \
             mock.patch.object(server, 'UPLOAD_DIR', self.root / 'new-empty-uploads'), \
             mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'SyntheticOwnerPass123!'}):
            server.init_db()  # Repeat startup: no data should disappear or be re-seeded.
            with server.db() as c:
                user = c.execute('SELECT * FROM users WHERE id=?', (2,)).fetchone()
                self.assertTrue(server.verify_password('SyntheticUserPass123!', user['salt'], user['password_hash']))
                self.assertEqual(user['phone'], '+250788111222')
                self.assertEqual(c.execute('SELECT title FROM projects WHERE id=?', (7,)).fetchone()['title'], 'Synthetic project')
                asset = c.execute('SELECT stored_path FROM assets WHERE id=?', (8,)).fetchone()['stored_path']
                self.assertTrue(asset.startswith('db:assets/'))
                self.assertEqual(c.execute('SELECT data FROM media_objects WHERE storage_key=?', (asset[3:],)).fetchone()['data'], self.asset.read_bytes())
                self.assertEqual(c.execute('SELECT data FROM media_objects WHERE storage_key=?', (user['profile_photo_url'].removeprefix('/uploads/'),)).fetchone()['data'], self.profile.read_bytes())
                self.assertTrue(c.execute("SELECT 1 FROM slideshow_photos WHERE caption='Synthetic saved photo'").fetchone())
                self.assertFalse(c.execute("SELECT 1 FROM slideshow_photos WHERE bundled_path='slide-01.jpg'").fetchone())
                new = c.execute("INSERT INTO projects(user_id,title,category,summary,details,status,created_at,updated_at) VALUES(2,'After migration','Education','x','x','draft',?,?)", (server.now_iso(), server.now_iso()))
                self.assertGreater(new.lastrowid, 500, 'deleted IDs must not be reused')
            # Exercise the real routes with an empty local upload directory: the
            # migrated photos/files must come from PostgreSQL and stay private.
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{httpd.server_address[1]}'
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs): return None
            anonymous = urllib.request.build_opener(NoRedirect())
            try:
                login = urllib.parse.urlencode({'email':'student@example.test','password':'SyntheticUserPass123!'}).encode()
                with opener.open(base + '/login', data=login, timeout=10) as response:
                    self.assertEqual(response.status, 200)
                with opener.open(base + user['profile_photo_url'], timeout=10) as response:
                    self.assertEqual(response.read(), self.profile.read_bytes())
                with opener.open(base + '/download?id=8', timeout=10) as response:
                    self.assertEqual(response.read(), self.asset.read_bytes())
                for url in (user['profile_photo_url'], '/download?id=8'):
                    with self.assertRaises(urllib.error.HTTPError) as denied:
                        anonymous.open(base + url, timeout=10)
                    self.assertEqual(denied.exception.code, 303)
                with anonymous.open(base + '/', timeout=10) as response:
                    html = response.read().decode()
                    self.assertIn('Synthetic saved photo', html)
                    self.assertNotIn('slide-01.jpg', html)
            finally:
                httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)

    def test_existing_target_is_never_overwritten(self):
        from psycopg import sql
        with pg_compat._connect(TEST_URL) as c:
            c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
            c.execute(sql.SQL('CREATE TABLE {} (value text)').format(sql.Identifier(self.schema, 'sentinel')))
            c.execute(sql.SQL('INSERT INTO {} VALUES (%s)').format(sql.Identifier(self.schema, 'sentinel')), ('do not overwrite',))
        with self.assertRaisesRegex(MigrationError, 'already exists'):
            migrate(self.source, self.uploads, TEST_URL, self.schema)
        with pg_compat._connect(TEST_URL) as c:
            self.assertEqual(c.execute(sql.SQL('SELECT value FROM {}').format(sql.Identifier(self.schema, 'sentinel'))).fetchone()['value'], 'do not overwrite')

    def test_missing_upload_aborts_before_creating_target(self):
        self.asset.unlink()
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(MigrationError, 'missing'):
            migrate(self.source, self.uploads, TEST_URL, self.schema)
        self.assertFalse(self.target_exists())
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_failed_import_removes_only_its_temporary_schema(self):
        def temp_schemas():
            with pg_compat._connect(TEST_URL) as c:
                return {r['nspname'] for r in c.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'import\\_%' ESCAPE '\\'").fetchall()}
        previous = temp_schemas()
        with mock.patch('migrate_sqlite._verify_table_rows', side_effect=MigrationError('synthetic verification failure')):
            with self.assertRaisesRegex(MigrationError, 'synthetic verification failure'):
                migrate(self.source, self.uploads, TEST_URL, self.schema)
        self.assertFalse(self.target_exists())
        self.assertEqual(temp_schemas(), previous)


if __name__ == '__main__':
    unittest.main()
