"""Guardrails for durable storage; all records and credentials here are synthetic."""
import hashlib
import os
import re
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pg_compat
import server


class StorageSafetyTests(unittest.TestCase):
    def test_render_refuses_implicit_ephemeral_sqlite(self):
        with tempfile.TemporaryDirectory(prefix='70scholar-guard-') as d:
            path = Path(d) / 'ephemeral.sqlite3'
            with mock.patch.object(server, 'DATABASE_URL', ''), \
                 mock.patch.object(server, 'DB_PATH', path), \
                 mock.patch.object(server, 'UPLOAD_DIR', Path(d) / 'uploads'), \
                 mock.patch.dict(os.environ, {'RENDER': 'true', 'PERSISTENT_DISK_MOUNT': d}):
                with self.assertRaisesRegex(RuntimeError, 'Persistent storage is required'):
                    server.init_db()
            self.assertFalse(path.exists(), 'Refusal must happen before creating an empty database')

    def test_render_refuses_loopback_postgres_without_tls(self):
        if pg_compat.psycopg is None:
            self.skipTest('psycopg is not installed')
        with mock.patch.dict(os.environ, {'RENDER': 'true'}):
            with self.assertRaisesRegex(RuntimeError, 'TLS-authenticated'):
                pg_compat._connect('postgresql://fake@127.0.0.1:55432/fake')

    def test_remote_postgres_verifies_the_server(self):
        if pg_compat.psycopg is None:
            self.skipTest('psycopg is not installed')
        with mock.patch.dict(os.environ, {'PG_SSL_ROOT_CERT': 'system'}, clear=True), \
             mock.patch.object(pg_compat.psycopg, 'connect') as connect:
            pg_compat._connect('postgresql://fake@db.example.test/postgres')
            self.assertEqual(connect.call_args.kwargs['sslmode'], 'verify-full')
            self.assertEqual(connect.call_args.kwargs['sslrootcert'], 'system')

    def test_bundled_supabase_ca_is_pinned_and_used_only_for_pooler(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            path = Path(pg_compat._ssl_root('aws-0-eu-central-1.pooler.supabase.com'))
            pem = path.read_text()
            self.assertEqual(pem.count('-----BEGIN CERTIFICATE-----'), 1)
            self.assertNotIn('PRIVATE KEY', pem)
            digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()
            self.assertEqual(digest, '807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa')
            self.assertEqual(pg_compat._ssl_root('different-provider.example'), 'system')
            self.assertEqual(pg_compat._ssl_root('notpooler.supabase.com'), 'system')

    def test_custom_pem_is_validated_and_written_with_restricted_permissions(self):
        cafile = ssl.get_default_verify_paths().cafile
        if not cafile or not Path(cafile).is_file():
            self.skipTest('system certificate bundle unavailable')
        bundle = Path(cafile).read_text()
        match = re.search(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', bundle, re.S)
        if not match:
            self.skipTest('system certificate unavailable')
        pem = match.group(0)
        with mock.patch.object(pg_compat, '_CA_FILE', None), \
             mock.patch.dict(os.environ, {'SUPABASE_DB_CA_PEM': pem}, clear=True):
            path = Path(pg_compat._ssl_root())
            try:
                self.assertEqual(path.read_text().strip(), pem)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            finally:
                path.unlink(missing_ok=True)
        with mock.patch.object(pg_compat, '_CA_FILE', None), \
             mock.patch.dict(os.environ, {'SUPABASE_DB_CA_PEM': 'not a certificate'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'valid PEM'):
                pg_compat._ssl_root()


class PostgreSQLPrivacyTests(unittest.TestCase):
    def test_private_tables_and_schema_are_not_granted_to_api_roles(self):
        if not server.DATABASE_URL:
            self.skipTest('requires synthetic PostgreSQL')
        with tempfile.TemporaryDirectory(prefix='70scholar-schema-') as d, \
             mock.patch.object(server, 'DB_PATH', Path(d) / 'db.sqlite3'), \
             mock.patch.object(server, 'UPLOAD_DIR', Path(d) / 'uploads'), \
             mock.patch.dict(os.environ, {'ADMIN_PASSWORD': 'TestOwnerPassword123!'}):
            server.init_db()
            with pg_compat._connect(server.DATABASE_URL) as c:
                roles = c.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')").fetchall()
                for row in roles:
                    role = row['rolname']
                    grants = c.execute('SELECT has_schema_privilege(%s,%s,\'USAGE\') AS schema_ok, has_table_privilege(%s,%s,\'SELECT\') AS table_ok',
                                       (role, server.PG_SCHEMA, role, server.PG_SCHEMA + '.users')).fetchone()
                    self.assertFalse(grants['schema_ok'], role)
                    self.assertFalse(grants['table_ok'], role)


if __name__ == '__main__':
    unittest.main()
