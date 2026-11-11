"""Run optional Playwright password UI checks against a disposable local server.

Install Playwright and Chromium separately; then set NODE_PATH to its node_modules
and run `python3 tests/run_v24_password_browser.py`. Never uses production data.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Remove any live-service configuration before importing the app.
for key in ('DATABASE_URL', 'EMAIL_PROVIDER', 'BREVO_API_KEY', 'BREVO_FROM', 'BIRD_API_KEY', 'SMTP_HOST',
            'SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SUPABASE_STORAGE_BUCKET', 'RENDER', 'APP_BASE_URL', 'RENDER_EXTERNAL_URL'):
    os.environ.pop(key, None)
os.environ['ADMIN_PASSWORD'] = 'TestOwnerPassword123!'
import server

with tempfile.TemporaryDirectory(prefix='70scholar-browser-') as directory:
    server.DB_PATH = Path(directory) / 'test.sqlite3'
    server.UPLOAD_DIR = Path(directory) / 'uploads'
    server.CLOUD_STORAGE = None
    server.init_db()
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        env = os.environ.copy()
        env['SCHOLAR_BROWSER_TEST_URL'] = f'http://127.0.0.1:{httpd.server_address[1]}'
        subprocess.run(['node', str(ROOT / 'tests' / 'test_v24_password_browser.cjs')],
                       cwd=ROOT, env=env, check=True, timeout=90)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)
