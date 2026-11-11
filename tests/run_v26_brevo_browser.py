"""Run Brevo-code browser checks against a disposable local app and fake mail only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Never read or use live provider, database or storage settings in this test.
for key in ('DATABASE_URL', 'EMAIL_PROVIDER', 'BREVO_API_KEY', 'BREVO_FROM', 'BIRD_API_KEY',
            'SMTP_HOST', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SUPABASE_STORAGE_BUCKET',
            'RENDER', 'APP_BASE_URL', 'RENDER_EXTERNAL_URL'):
    os.environ.pop(key, None)
os.environ['ADMIN_PASSWORD'] = 'TestOwnerPassword123!'
import server

with tempfile.TemporaryDirectory(prefix='70scholar-v26-browser-') as directory:
    temp = Path(directory)
    server.DB_PATH = temp / 'test.sqlite3'
    server.UPLOAD_DIR = temp / 'uploads'
    server.CLOUD_STORAGE = None
    server.EMAIL_PROVIDER = 'brevo'
    server.BREVO_API_KEY = 'fake-browser-only-key'
    server.BREVO_FROM = 'owner@example.test'
    server.EMAIL_ENABLED = True
    captured = temp / 'synthetic-mail.json'
    def fake_send(email, subject, body, html_body=None):
        # Synthetic data only; no API call and nothing is sent to any real mailbox.
        captured.write_text(json.dumps({'to': email, 'subject': subject, 'body': body, 'html': html_body}),
                            encoding='utf-8')
    server.send_email = fake_send
    server.init_db()
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
    server.APP_BASE_URL = f'http://127.0.0.1:{httpd.server_address[1]}'
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        env = os.environ.copy()
        env['SCHOLAR_BROWSER_TEST_URL'] = server.APP_BASE_URL
        env['SCHOLAR_BROWSER_TEST_MAIL'] = str(captured)
        subprocess.run(['node', str(ROOT / 'tests' / 'test_v26_brevo_browser.cjs')],
                       cwd=ROOT, env=env, check=True, timeout=120)
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)
