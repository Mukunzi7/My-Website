"""Run optional Playwright section checks on a disposable, local SQLite instance."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for key in ('DATABASE_URL', 'BIRD_API_KEY', 'SMTP_HOST', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY',
            'SUPABASE_STORAGE_BUCKET', 'RENDER', 'APP_BASE_URL', 'RENDER_EXTERNAL_URL'):
    os.environ.pop(key, None)
os.environ['ADMIN_PASSWORD'] = 'TestOwnerPassword123!'
import server

with tempfile.TemporaryDirectory(prefix='70scholar-v25-browser-') as directory:
    server.DB_PATH = Path(directory) / 'test.sqlite3'
    server.UPLOAD_DIR = Path(directory) / 'uploads'
    server.CLOUD_STORAGE = None
    server.init_db()
    with server.db() as conn:
        conn.execute('''INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                     ('Competition', 'International Physics Olympiad Test', 'Test organizer', 'Worldwide',
                      'Students', 'See official page', 'https://example.org/physics',
                      'A physics competition for students.', 'physics,competition', 'Test', server.now_iso()))
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.ScholarHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        env = os.environ.copy()
        env['SCHOLAR_BROWSER_TEST_URL'] = f'http://127.0.0.1:{httpd.server_address[1]}'
        subprocess.run(['node', str(ROOT / 'tests' / 'test_v25_competitions_browser.cjs')],
                       cwd=ROOT, env=env, check=True, timeout=120)
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)
