"""End-to-end checks for the v17 feature batch.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import http.cookiejar
from contextlib import closing
import os
import re
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

TMP = tempfile.TemporaryDirectory(prefix="70scholar-v17-test-")
os.environ["DB_PATH"] = str(Path(TMP.name) / "test.sqlite3")
os.environ["UPLOAD_DIR"] = str(Path(TMP.name) / "uploads")
os.environ["ADMIN_PASSWORD"] = "V17AdminPass123!"
os.environ.pop("BIRD_API_KEY", None)
os.environ.pop("SMTP_HOST", None)

import server  # noqa: E402  (environment must be configured first)


class Client:
    def __init__(self, base: str):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path: str, data: dict | None = None):
        url = self.base + path
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body)
        try:
            with self.opener.open(req, timeout=10) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def get(self, path: str):
        return self.request(path)

    def post(self, path: str, data: dict):
        return self.request(path, data)

    def csrf(self, path: str = "/dashboard") -> str:
        status, html = self.get(path)
        assert status == 200, (path, status)
        match = re.search(r"name=['\"]csrf['\"]\s+value=['\"]([^'\"]+)", html)
        assert match, f"CSRF token not found in {path}"
        return match.group(1)


class V17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.init_db()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.ScholarHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)
        TMP.cleanup()

    def db(self):
        return closing(sqlite3.connect(server.DB_PATH))

    def test_01_featured_programs_are_seeded(self):
        with self.db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) c FROM opportunities WHERE source='featured_program'"
            ).fetchone()[0]
        self.assertEqual(count, len(server.FEATURED_PROGRAMS))
        self.assertGreaterEqual(count, 16)
        titles = [p["title"] for p in server.FEATURED_PROGRAMS]
        for expected in ("YYAS", "YYGS", "RSI"):
            self.assertTrue(any(expected in t for t in titles), expected)

    def test_02_public_pages_show_helpline_and_new_homepage_order(self):
        for path in ("/", "/login", "/signup", "/programs"):
            status, html = Client(self.base).get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(server.HELPLINE_PHONE, html, path)
            self.assertIn(server.HELPLINE_EMAIL, html, path)
        _, home = Client(self.base).get("/")
        order = [
            home.index('class="hero"'),
            home.index('class="journey-section"'),
            home.index('class="opportunities-section"'),
            home.index('class="programs-section"'),
            home.index('class="gap-section"'),
            home.index('class="workspace-section"'),
            home.index('class="story-section"'),
            home.index('class="final-cta"'),
        ]
        self.assertEqual(order, sorted(order))

    def test_03_programs_page_is_public_and_lists_all_cards(self):
        client = Client(self.base)
        status, html = client.get("/programs")
        self.assertEqual(status, 200)
        for prog in server.FEATURED_PROGRAMS:
            self.assertIn(server.e(prog["title"]), html)
        self.assertRegex(html, r"16 real programmes|%d real programmes" % len(server.FEATURED_PROGRAMS))

    def test_04_signup_has_optional_profile_fields(self):
        client = Client(self.base)
        _, html = client.get("/signup")
        for field in ("name", "email", "password", "account_type", "career", "education_level"):
            self.assertIn(f'name="{field}"', html)
        self.assertIn("Only your name and email are required", html)
        for field in ("account_type", "career", "education_level"):
            tag = re.search(r"<(?:input|select)[^>]*name=\"%s\"[^>]*>" % field, html)
            self.assertIsNotNone(tag, field)
            self.assertNotIn("required", tag.group(0))

    def test_05_ssrf_guard_blocks_private_urls(self):
        for unsafe in ("http://localhost/", "http://127.0.0.1/", "file:///etc/passwd", "http://10.0.0.1/"):
            self.assertFalse(server.is_safe_public_url(unsafe), unsafe)

    def test_06_fetch_page_metadata_extracts_preview(self):
        html = """<html><head>
          <meta property='og:title' content='Bright Future Scholarship 2027'>
          <meta property='og:description' content='A fully funded scholarship for African STEM students.'>
          <meta property='og:image' content='/images/preview.jpg'>
          <meta property='og:site_name' content='Opportunity Example'>
          </head><body><h1>Bright Future Scholarship 2027</h1><p>Apply before 15 March 2027.</p></body></html>"""
        with mock.patch.object(server, "safe_http_get", return_value=(html, "text/html; charset=utf-8")):
            info = server.fetch_page_metadata("https://example.org/scholarship")
        self.assertEqual(info["title"], "Bright Future Scholarship 2027")
        self.assertIn("fully funded scholarship", info["summary"])
        self.assertEqual(info["image"], "/images/preview.jpg")
        self.assertEqual(info["site"], "Opportunity Example")

    def test_07_signup_login_and_link_submission_approval(self):
        # Sign up with only compulsory name/email/password, plus one optional field.
        client = Client(self.base)
        status, html = client.post("/signup", {
            "name": "V17 Student", "email": "v17-student@example.com",
            "password": "StudentPass123!", "career": "Engineering",
        })
        self.assertEqual(status, 200)
        self.assertIn("You&#x27;re in", html)  # account ready, no email provider configured

        status, html = client.post("/login", {
            "email": "v17-student@example.com", "password": "StudentPass123!",
        })
        self.assertEqual(status, 200)
        status, dashboard = client.get("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("class='nav-profile", dashboard)
        self.assertIn("/static/images/default-avatar.svg", dashboard)
        self.assertIn(server.HELPLINE_PHONE, dashboard)

        with self.db() as conn:
            row = conn.execute(
                "SELECT career, account_type, education_level, email_verified FROM users WHERE email=?",
                ("v17-student@example.com",),
            ).fetchone()
        self.assertEqual(row[0], "Engineering")
        self.assertEqual(row[1], "Other")
        self.assertEqual(row[2], "")
        self.assertEqual(row[3], 1)

        # Link submission uses a mocked remote page (no external network in tests).
        csrf = client.csrf()
        source_html = """<html><head>
          <meta property='og:title' content='Community STEM Fellowship'>
          <meta property='og:description' content='A verified fellowship for secondary school innovators.'>
          <meta property='og:image' content='/media/fellowship.jpg'>
          <meta property='og:site_name' content='Example Foundation'>
          </head><body><h1>Community STEM Fellowship</h1><p>Applications close 2027-04-30.</p></body></html>"""
        with mock.patch.object(server, "safe_http_get", return_value=(source_html, "text/html")):
            status, html = client.post("/opportunity/submit-link", {
                "csrf": csrf, "url": "https://example.org/fellowship",
                "note": "Great fit for Rwandan students",
            })
        self.assertEqual(status, 200)
        self.assertIn("Link received", html)

        with self.db() as conn:
            conn.row_factory = sqlite3.Row
            submission = conn.execute(
                "SELECT * FROM opportunity_submissions WHERE title='Community STEM Fellowship'"
            ).fetchone()
        self.assertIsNotNone(submission)
        self.assertEqual(submission["status"], "pending")
        self.assertEqual(submission["source_mode"], "link")
        self.assertIn("Great fit for Rwandan students", submission["fetched_summary"])
        self.assertEqual(submission["fetched_image"], "https://example.org/media/fellowship.jpg")

        # Not public before approval.
        with self.db() as conn:
            public = conn.execute(
                "SELECT COUNT(*) c FROM opportunities WHERE title='Community STEM Fellowship'"
            ).fetchone()[0]
        self.assertEqual(public, 0)

        # Admin sees organized workspace + fetched preview.
        admin = Client(self.base)
        status, html = admin.post("/login", {
            "email": server.OWNER_ADMIN_EMAIL, "password": os.environ["ADMIN_PASSWORD"],
        })
        self.assertEqual(status, 200)
        status, admin_html = admin.get("/admin")
        self.assertEqual(status, 200)
        for marker in ("admin-shell", "admin-sidebar", "Review queue", "Content &amp; catalogue",
                       "What we found on the page", "Community STEM Fellowship"):
            self.assertIn(marker, admin_html)
        self.assertIn("I checked the official page", admin_html)

        # Admin must confirm before publishing.
        admin_csrf = admin.csrf("/admin")
        status, html = admin.post("/admin/submission/action", {
            "csrf": admin_csrf, "submission_id": str(submission["id"]), "action": "approve",
        })
        self.assertEqual(status, 400)
        self.assertIn("Please confirm", html)
        with self.db() as conn:
            self.assertEqual(conn.execute(
                "SELECT status FROM opportunity_submissions WHERE id=?", (submission["id"],)
            ).fetchone()[0], "pending")

        # Admin edits the fetched title and publishes.
        status, html = admin.post("/admin/submission/action", {
            "csrf": admin_csrf, "submission_id": str(submission["id"]), "action": "approve",
            "confirmed": "1", "title": "Community STEM Fellowship (Reviewed)",
            "provider": "Example Foundation", "deadline": "2027-04-30",
            "summary": "Reviewed and approved for the public opportunity list.",
        })
        self.assertEqual(status, 200)
        self.assertIn("Approved and published", html)
        with self.db() as conn:
            opp = conn.execute(
                "SELECT * FROM opportunities WHERE title='Community STEM Fellowship (Reviewed)'"
            ).fetchone()
            state = conn.execute(
                "SELECT status FROM opportunity_submissions WHERE id=?", (submission["id"],)
            ).fetchone()[0]
        self.assertIsNotNone(opp)
        self.assertEqual(opp[8], "Reviewed and approved for the public opportunity list.")
        self.assertEqual(state, "approved")

    def test_08_default_avatar_and_version(self):
        client = Client(self.base)
        status, svg = client.get("/static/images/default-avatar.svg")
        self.assertEqual(status, 200)
        self.assertIn("<svg", svg)
        status, version = client.get("/version")
        self.assertEqual(status, 200)
        self.assertIn("v17-programs", version)


if __name__ == "__main__":
    unittest.main()
