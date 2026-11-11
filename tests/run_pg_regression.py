"""Run the compatible app regression suite against LOCAL disposable PostgreSQL only.

Example: SCHOLAR70_TEST_DATABASE_URL=postgresql://testowner@127.0.0.1:55432/postgres \
         python3 tests/run_pg_regression.py

Each test receives a separate randomly named schema. Never point this runner at real
Supabase or other user data. The URL is intentionally limited to loopback hosts.
"""
import hashlib
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'tests')]
url = os.environ.get('SCHOLAR70_TEST_DATABASE_URL', 'postgresql://testowner@127.0.0.1:55432/postgres')
if (urlparse(url).hostname or '').lower() not in ('localhost', '127.0.0.1', '::1'):
    raise SystemExit('This test runner only permits a disposable local PostgreSQL server.')
os.environ['ADMIN_PASSWORD'] = 'TestOwnerPassword123!'

import server
server.DATABASE_URL = url
real_init = server.init_db


def init_for_isolated_schema():
    server.PG_SCHEMA = 'test_' + hashlib.sha256(str(server.DB_PATH).encode()).hexdigest()[:20]
    return real_init()


server.init_db = init_for_isolated_schema
names = ['test_v17', 'test_v18_security.EmailAndFetchTests', 'test_v19_slideshow',
         'test_v20_branding', 'test_v21_contact', 'test_v22_bootcamps',
         'test_v22_persistence', 'test_v22_storage_safety',
         'test_v23_daily_verse', 'test_v23_private_storage', 'test_v24_auth']
suite = unittest.TestLoader().loadTestsFromNames(names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
