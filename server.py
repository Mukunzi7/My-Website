#!/usr/bin/env python3
"""70Scholar MVP: landing + authentication + opportunities + builder workspace + funding marketplace.
Run: python3 server.py  then open http://127.0.0.1:8080
No external Python packages required.
"""
from __future__ import annotations
import base64, hashlib, html, json, mimetypes, os, re, secrets, sqlite3, sys, smtplib, threading, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from email.message import EmailMessage
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse, urlencode

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", str(ROOT / "edubridge.sqlite3")))
STATIC_DIR = ROOT / "static"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(ROOT / "uploads")))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
APP_NAME = "70Scholar"
APP_VERSION = "v16-features"
COMPANY_NAME = "Nexus Company Ltd"
APP_TAGLINE = "Find the opportunity. Show the build. Start the conversation."
OWNER_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "honoremukunzi6@gmail.com").strip().lower()
ADMIN_EMAIL_ALLOWLIST = ("honoremukunzi6@gmail.com",)
if OWNER_ADMIN_EMAIL not in ADMIN_EMAIL_ALLOWLIST:
    OWNER_ADMIN_EMAIL = ADMIN_EMAIL_ALLOWLIST[0]
SESSION_COOKIE = "edubridge_session"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "0"))  # 0 means no 70Scholar app limit for project/media uploads

PAYMENT_LINKS = {
    "flutterwave": os.environ.get("FLUTTERWAVE_PAYMENT_LINK", ""),
    "stripe": os.environ.get("STRIPE_PAYMENT_LINK", ""),
    "paypal": os.environ.get("PAYPAL_PAYMENT_LINK", ""),
    "momo": os.environ.get("MOMO_PAYMENT_LINK", ""),
}
MOMO_INSTRUCTIONS = os.environ.get("MOMO_PAYMENT_INSTRUCTIONS", "Set MOMO_PAYMENT_INSTRUCTIONS in your environment, for example: MTN MoMo pay merchant code XXXXX and include the pledge reference.")
RSS_SOURCES = [
    "https://www.opportunitiesforafricans.com/feed/",
    "https://www.globalsouthopportunities.com/feed/",
]
# Platform commission used to sponsor other student projects.
PLATFORM_FEE_PERCENT = float(os.environ.get("PLATFORM_FEE_PERCENT", "5"))
# Words cycled by the homepage typewriter animation.
TYPEWRITER_WORDS = [
    "Scholarships", "Internships", "Competitions", "Pre-university courses",
    "University exam prep", "Grants", "Project funding", "Student applications",
    "Mentorship", "Marketplace", "Research opportunities", "A future you can build",
]
# Auto-import is stored in the DB so the owner can toggle it from /admin.
AUTO_SYNC_INTERVAL_SECONDS = 1800
# Pages reachable without an account. Everything else requires sign-in.
PUBLIC_GET_PATHS = {"/", "/login", "/signup", "/verify-email", "/forgot-password",
                    "/reset-password", "/robots.txt", "/sitemap.xml", "/version"}
PUBLIC_POST_PATHS = {"/login", "/signup", "/forgot-password", "/reset-password"}
PREUNI_COURSES = [
    {"title":"Academic English for University","category":"Pre-university","level":"Secondary → University","duration":"8 weeks","summary":"Essay writing, academic reading, citation, and presentation skills for university study.","topics":["Academic vocabulary","Essay structure","Referencing","Seminar speaking"]},
    {"title":"Foundation Mathematics","category":"Pre-university","level":"Secondary → University","duration":"10 weeks","summary":"Algebra, functions, trigonometry and introductory calculus to bridge into STEM degrees.","topics":["Algebra","Functions","Trigonometry","Limits"]},
    {"title":"Introduction to Programming (Python)","category":"Pre-university","level":"Beginner","duration":"12 weeks","summary":"A practical first course in computational thinking and Python for future CS applicants.","topics":["Variables","Loops","Functions","Data structures"]},
    {"title":"Study Skills & Research Methods","category":"Pre-university","level":"All levels","duration":"6 weeks","summary":"How to plan a research project, evaluate sources, manage time, and write a literature review.","topics":["Research questions","Source evaluation","Note-taking","Time management"]},
    {"title":"Physics & Chemistry Bridge","category":"Pre-university","level":"Secondary → University","duration":"10 weeks","summary":"Core lab concepts and problem solving for engineering and health-science applicants.","topics":["Mechanics","Electricity","Stoichiometry","Lab reporting"]},
    {"title":"University Application Masterclass","category":"Pre-university","level":"Final-year students","duration":"4 weeks","summary":"Personal statements, choosing courses, references, and building a portfolio that stands out.","topics":["Personal statement","Course selection","Portfolio","References"]},
]
EXAM_PREP = [
    {"title":"SAT","category":"University entrance exam","level":"International","duration":"Self-paced","summary":"Evidence-based reading, writing and maths for US undergraduate applications.","topics":["Reading","Writing & Language","Math","Practice tests"]},
    {"title":"ACT","category":"University entrance exam","level":"International","duration":"Self-paced","summary":"English, mathematics, reading and science reasoning practice for US admissions.","topics":["English","Math","Reading","Science"]},
    {"title":"IELTS / TOEFL","category":"English proficiency","level":"International","duration":"6–12 weeks","summary":"Listening, reading, writing and speaking preparation for English-taught universities.","topics":["Listening","Reading","Writing","Speaking"]},
    {"title":"AP / IB / A-Level revision","category":"School-leaving exams","level":"Secondary","duration":"Term-based","summary":"Structured revision plans, past papers and marking-scheme practice.","topics":["Past papers","Revision plan","Exam technique","Mark schemes"]},
    {"title":"University aptitude & entrance tests","category":"Admissions test","level":"Varies","duration":"8 weeks","summary":"Problem solving, critical thinking and timed practice for competitive programmes.","topics":["Critical thinking","Numerical reasoning","Timed practice","Mock exams"]},
    {"title":"Scholarship aptitude tests","category":"Scholarship selection","level":"Varies","duration":"6 weeks","summary":"Quantitative and verbal reasoning practice common in scholarship screening tests.","topics":["Quantitative reasoning","Verbal reasoning","Essay writing","Interviews"]},
]

APP_BASE_URL = os.environ.get("APP_BASE_URL", f"http://{HOST}:{PORT}").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@70scholar.local")
SMTP_TLS = os.environ.get("SMTP_TLS", "1") != "0"
# Bird / MessageBird email API. Keep the API key in environment variables, never in code.
BIRD_API_KEY = os.environ.get("BIRD_API_KEY", "")
BIRD_FROM = os.environ.get("BIRD_FROM", "onboarding@messagebird.dev")
BIRD_REGION = os.environ.get("BIRD_REGION", "")
MAIL_OUTBOX = ROOT / "mail_outbox.log"
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)

def money(value: Any) -> str:
    try: amount = float(value or 0)
    except Exception: amount = 0
    return f"${amount:,.0f}"

def slugify_filename(name: str) -> str:
    name = unquote(name or "upload.bin").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name[:120] or "upload.bin"

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

OPPORTUNITY_SEEDS = [
 {"type":"Scholarship","title":"University of Rwanda Mastercard Foundation Scholars Program 2026/2027","provider":"University of Rwanda + Mastercard Foundation","country":"Rwanda / Africa","level":"Master's students, African citizens","deadline":"2026-08-22","url":"https://www.opportunitiesforafricans.com/university-of-rwanda-mastercard-foundation-scholars-program-2026-2027-for-young-africans/","summary":"Fully funded master's scholarships at the University of Rwanda, with tuition, mentoring, leadership development, and internships. Verify final eligibility on the official portal before applying.","tags":"rwanda,mastercard,graduate,fully-funded,stem,leadership","source":"Opportunities for Africans, published 2026-07-29"},
 {"type":"Internship","title":"African Union Internship Program 2026","provider":"African Union","country":"AU member states / Ethiopia","level":"Students and recent graduates","deadline":"2026-12-31","url":"https://www.globalsouthopportunities.com/2026/07/06/internship-106/","summary":"Professional experience across African Union departments for students and recent graduates from AU Member States. Good fit for policy, governance, research, communications, and development interests.","tags":"africa,internship,policy,governance,recent-graduate","source":"Global South Opportunities, published 2026-07-06"},
 {"type":"Internship","title":"World Bank Group Pioneers Internship Program 2026/2027","provider":"World Bank Group","country":"Global / remote and office roles vary","level":"Undergraduate and postgraduate students","deadline":"2026-08-12","url":"https://www.opportunitiesforafricans.com/world-bank-group-wbg-pioneers-internship-program-fall-winter-cycle-for-undergraduate-postgraduate-students/","summary":"Structured internship exposure to World Bank Group operations and corporate support functions. Check the official WBG application page from the listing.","tags":"internship,world-bank,development,undergraduate,postgraduate","source":"Opportunities for Africans, published 2026-07-15"},
 {"type":"Competition","title":"AI for SDGs Global Youth AI Future Innovation Competition 2026","provider":"United Nations University Global AI Network","country":"Global","level":"Young innovators, researchers, entrepreneurs, teams","deadline":"2026-09-15","url":"https://www.globalsouthopportunities.com/2026/07/31/global-168/","summary":"Global AI innovation competition focused on education, AI literacy, and SDG impact, with staged judging and a final in Macau.","tags":"ai,sdgs,education,innovation,global,competition","source":"Global South Opportunities, published 2026-07-31"},
 {"type":"Grant","title":"Competition for Youth-Led Projects 2026–2027","provider":"WMO/APFM, GWP/IDMP, Water Youth Network","country":"Global","level":"Youth-led student / young professional projects","deadline":"2026-08-31","url":"https://www.opportunitiesforafricans.com/competition-for-youth-led-projects-2026-2027/","summary":"Two CHF 3,000 awards plus expert support for youth-led flood and drought resilience projects. Strong fit for climate, water, early warning, and community resilience ideas.","tags":"grant,climate,water,youth-led,community,resilience","source":"Opportunities for Africans, published 2026-07-31"},
 {"type":"Grant","title":"Africa-Europe Youth Spaces Grant Program","provider":"Africa-Europe Youth Academy","country":"Selected African countries","level":"Youth-led or youth-focused organisations","deadline":"2026-08-07","url":"https://www2.fundsforngos.org/innovation/open-call-for-africa-europe-youth-spaces-grant-program/amp/","summary":"Grant funding, capacity building, and technical support for youth spaces. Round 1 can provide €10,000, with higher follow-on support for top performers. Check country eligibility before investing time.","tags":"grant,youth,organisation,capacity-building,africa-europe","source":"fundsforNGOs, published 2026-07-30"},
 {"type":"Hackathon","title":"GirlCode Pan-African Hackathon 2026","provider":"GirlCode","country":"Botswana, South Africa, Kenya, Tanzania, Uganda, Ghana","level":"Young women developers and female tech founders","deadline":"2026-09-01","url":"https://www.bizcommunity.com/article/girlcode-opens-applications-for-2026-pan-african-hackathon-064455a","summary":"Pan-African coding, fintech, and AI hackathon expanding to include female technology founders. Event dates vary by country from August to September 2026.","tags":"hackathon,women-in-tech,africa,ai,fintech,founders","source":"Bizcommunity, published 2026-07-08"}
]
DEMO_PROJECTS = [
 {"title":"Solar Homework Hub","category":"Education + Clean Energy","summary":"A low-cost solar charging and evening study station for rural secondary students.","details":"Prototype includes a bill of materials, 3D-printable housing notes, and an operations plan for a school club. Looking for early funders and pilot schools.","goal_amount":1200,"price":0,"asset_url":"","demo_url":"","repo_url":"","status":"public"},
 {"title":"Kinyarwanda Revision Cards App","category":"Mobile App","summary":"A flashcard app that helps lower-secondary students revise science terms in Kinyarwanda and English.","details":"MVP screens are ready. The team is raising funds for content review, Android packaging, and school testing.","goal_amount":800,"price":15,"asset_url":"","demo_url":"","repo_url":"","status":"public"}
]

def hash_password(password: str, salt_b64: str | None = None):
    if salt_b64 is None:
        salt_b64 = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), 240_000)
        return salt_b64, base64.b64encode(digest).decode("ascii")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), 240_000)
    return base64.b64encode(digest).decode("ascii")

def verify_password(password: str, salt: str, expected: str) -> bool:
    return secrets.compare_digest(hash_password(password, salt), expected)

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def bird_api_host() -> str:
    """Return the correct Bird API host for the key region."""
    region = (BIRD_REGION or "").strip().lower()
    if not region:
        if BIRD_API_KEY.startswith("bk_eu1_"):
            region = "eu1"
        else:
            region = "us1"
    return f"https://{region}.platform.bird.com/v1/email/messages"

def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> None:
    """Send email through Bird first, SMTP second, or local outbox in development."""
    if BIRD_API_KEY:
        payload = {
            "from": BIRD_FROM,
            "to": [to_email],
            "subject": subject,
            "text": body,
            "html": html_body or "<p>" + e(body).replace("\n", "<br>") + "</p>",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            bird_api_host(),
            data=data,
            headers={
                "Authorization": f"Bearer {BIRD_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Bird returns 202 Accepted when it accepts the email for delivery.
            if resp.status not in (200, 201, 202):
                raise RuntimeError(f"Bird email API returned status {resp.status}")
        return
    if SMTP_HOST:
        msg = EmailMessage()
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as smtp:
            if SMTP_TLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with MAIL_OUTBOX.open("a", encoding="utf-8") as f:
            f.write("\n--- 70Scholar development email ---\n")
            f.write(f"To: {to_email}\nSubject: {subject}\n\n{body}\n")
            if html_body:
                f.write(f"\nHTML:\n{html_body}\n")
            f.write("--- end ---\n")

def create_email_token(user_id: int, purpose: str, hours: int = 24) -> str:
    token = secrets.token_urlsafe(36)
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    with db() as conn:
        conn.execute("DELETE FROM email_tokens WHERE user_id=? AND purpose=?", (user_id, purpose))
        conn.execute("INSERT INTO email_tokens(user_id,token_hash,purpose,created_at,expires_at) VALUES(?,?,?,?,?)", (user_id, token_hash(token), purpose, now_iso(), expires.isoformat(timespec="seconds")))
    return token

def send_verification_email(user_id: int, email: str, name: str) -> None:
    token = create_email_token(user_id, "verify_email", 48)
    link = f"{APP_BASE_URL}/verify-email?token={token}"
    text = f"Hi {name},\n\nWelcome to 70Scholar. Please verify your email address using this link:\n\n{link}\n\nIf you did not create this account, ignore this email.\n\n70Scholar"
    html_msg = f"<p>Hi {e(name)},</p><p>Welcome to 70Scholar. Please verify your email address:</p><p><a href='{e(link)}'>Verify my email</a></p><p>If you did not create this account, ignore this email.</p><p>70Scholar</p>"
    send_email(email, "Verify your 70Scholar email", text, html_msg)

def send_password_reset_email(user_id: int, email: str, name: str) -> None:
    token = create_email_token(user_id, "password_reset", 2)
    link = f"{APP_BASE_URL}/reset-password?token={token}"
    text = f"Hi {name},\n\nUse this link to reset your 70Scholar password. It expires in 2 hours:\n\n{link}\n\nIf you did not ask for this, ignore this email.\n\n70Scholar"
    html_msg = f"<p>Hi {e(name)},</p><p>Use this link to reset your 70Scholar password. It expires in 2 hours:</p><p><a href='{e(link)}'>Reset my password</a></p><p>If you did not ask for this, ignore this email.</p><p>70Scholar</p>"
    send_email(email, "Reset your 70Scholar password", text, html_msg)

def cloudinary_upload(filename: str, mime: str, content: bytes) -> str:
    if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET):
        return ""
    boundary = "----70Scholar" + secrets.token_hex(12)
    def part(name, value, file_name=None, content_type=None):
        head = f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\""
        if file_name:
            head += f"; filename=\"{file_name}\""
        head += "\r\n"
        if content_type:
            head += f"Content-Type: {content_type}\r\n"
        head += "\r\n"
        data = value if isinstance(value, bytes) else str(value).encode()
        return head.encode() + data + b"\r\n"
    body = b"".join([
        part("upload_preset", CLOUDINARY_UPLOAD_PRESET),
        part("file", content, filename, mime or "application/octet-stream"),
        f"--{boundary}--\r\n".encode(),
    ])
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/auto/upload"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("secure_url", "")

def init_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True); STATIC_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,salt TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'student',email_verified INTEGER NOT NULL DEFAULT 0,profile_photo_url TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS opportunities(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,title TEXT NOT NULL UNIQUE,provider TEXT NOT NULL,country TEXT NOT NULL,level TEXT NOT NULL,deadline TEXT NOT NULL,url TEXT NOT NULL,summary TEXT NOT NULL,tags TEXT NOT NULL DEFAULT '',source TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,title TEXT NOT NULL,category TEXT NOT NULL,summary TEXT NOT NULL,details TEXT NOT NULL,goal_amount REAL NOT NULL DEFAULT 0,price REAL NOT NULL DEFAULT 0,asset_url TEXT NOT NULL DEFAULT '',demo_url TEXT NOT NULL DEFAULT '',repo_url TEXT NOT NULL DEFAULT '',mobile_money_name TEXT NOT NULL DEFAULT '',mobile_money_number TEXT NOT NULL DEFAULT '',mobile_money_network TEXT NOT NULL DEFAULT '',payout_notes TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'draft',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,filename TEXT NOT NULL,stored_path TEXT NOT NULL,external_url TEXT NOT NULL DEFAULT '',mime TEXT NOT NULL,size INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS pledges(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,name TEXT NOT NULL,email TEXT NOT NULL,amount REAL NOT NULL,message TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pledged',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bookmarks(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,created_at TEXT NOT NULL,PRIMARY KEY(user_id,opportunity_id));
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,pledge_id INTEGER NOT NULL REFERENCES pledges(id) ON DELETE CASCADE,provider TEXT NOT NULL,reference TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',checkout_url TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sync_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,imported INTEGER NOT NULL DEFAULT 0,message TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS email_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,token_hash TEXT NOT NULL UNIQUE,purpose TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,used_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS moderation_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,action TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS project_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,name TEXT NOT NULL,email TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS feed_sources(id INTEGER PRIMARY KEY AUTOINCREMENT,url TEXT NOT NULL UNIQUE,added_at TEXT NOT NULL,last_fetched TEXT NOT NULL DEFAULT '',enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS opportunity_submissions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,type TEXT NOT NULL,title TEXT NOT NULL,provider TEXT NOT NULL,country TEXT NOT NULL,level TEXT NOT NULL,deadline TEXT NOT NULL,url TEXT NOT NULL,summary TEXT NOT NULL,tags TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,reviewed_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS course_enrolments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course_key TEXT NOT NULL,kind TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,course_key,kind));''')
        # Lightweight migrations for older local SQLite files.
        for col, ddl in {
            "mobile_money_name": "ALTER TABLE projects ADD COLUMN mobile_money_name TEXT NOT NULL DEFAULT ''",
            "mobile_money_number": "ALTER TABLE projects ADD COLUMN mobile_money_number TEXT NOT NULL DEFAULT ''",
            "mobile_money_network": "ALTER TABLE projects ADD COLUMN mobile_money_network TEXT NOT NULL DEFAULT ''",
            "payout_notes": "ALTER TABLE projects ADD COLUMN payout_notes TEXT NOT NULL DEFAULT ''",
            "email_verified": "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0",
            "profile_photo_url": "ALTER TABLE users ADD COLUMN profile_photo_url TEXT NOT NULL DEFAULT ''",
            "external_url": "ALTER TABLE assets ADD COLUMN external_url TEXT NOT NULL DEFAULT ''",
            "platform_fee": "ALTER TABLE pledges ADD COLUMN platform_fee REAL NOT NULL DEFAULT 0",
            "creator_amount": "ALTER TABLE pledges ADD COLUMN creator_amount REAL NOT NULL DEFAULT 0",
            "auto_description": "ALTER TABLE opportunities ADD COLUMN auto_description TEXT NOT NULL DEFAULT ''",
        }.items():
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass

        for item in OPPORTUNITY_SEEDS:
            conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at) VALUES(:type,:title,:provider,:country,:level,:deadline,:url,:summary,:tags,:source,:created_at)""", {**item, "created_at": now_iso()})
        demo = conn.execute("SELECT id FROM users WHERE email=?", ("demo@70scholar.local",)).fetchone()
        if demo:
            demo_id = demo["id"]
            conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (demo_id,))
        else:
            salt, hashed = hash_password("ChangeMe123!")
            cur = conn.execute("INSERT INTO users(name,email,password_hash,salt,role,email_verified,created_at) VALUES(?,?,?,?,?,?,?)", ("70Scholar Demo Studio","demo@70scholar.local",hashed,salt,"maker",1,now_iso()))
            demo_id = cur.lastrowid
        if conn.execute("SELECT COUNT(*) c FROM projects WHERE user_id=?", (demo_id,)).fetchone()["c"] == 0:
            for p in DEMO_PROJECTS:
                conn.execute("""INSERT INTO projects(user_id,title,category,summary,details,goal_amount,price,asset_url,demo_url,repo_url,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (demo_id,p["title"],p["category"],p["summary"],p["details"],p["goal_amount"],p["price"],p["asset_url"],p["demo_url"],p["repo_url"],p["status"],now_iso(),now_iso()))
        admin_email = OWNER_ADMIN_EMAIL
        admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
        existing_admin = conn.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
        if not existing_admin:
            salt, hashed = hash_password(admin_password)
            conn.execute("INSERT INTO users(name,email,password_hash,salt,role,email_verified,created_at) VALUES(?,?,?,?,?,?,?)", ("70Scholar Owner Admin", admin_email, hashed, salt, "admin", 1, now_iso()))
        else:
            conn.execute("UPDATE users SET role='admin', email_verified=1 WHERE email=?", (admin_email,))
        # Only the configured owner email may remain admin. Others are downgraded.
        conn.execute("UPDATE users SET role='maker' WHERE role='admin' AND lower(email)<>lower(?)", (admin_email,))
        # Defense in depth: no account outside the allowlist can keep admin role.
        conn.execute("UPDATE users SET role='maker' WHERE role='admin' AND lower(email) NOT IN (%s)" % ",".join("?"*len(ADMIN_EMAIL_ALLOWLIST)), ADMIN_EMAIL_ALLOWLIST)
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_sync','0')")
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('platform_fund','0')")
        for src in RSS_SOURCES:
            conn.execute("INSERT OR IGNORE INTO feed_sources(url,added_at) VALUES(?,?)", (src, now_iso()))
        # Backfill auto-generated descriptions for seeded opportunities.
        for row in conn.execute("SELECT id,type,title,provider,country,level,deadline,summary,auto_description FROM opportunities WHERE auto_description=''").fetchall():
            conn.execute("UPDATE opportunities SET auto_description=? WHERE id=?", (make_auto_description(row), row["id"]))

def get_setting(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    with db() as conn:
        conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def make_auto_description(row) -> str:
    """Build a rich hover description from whatever fields exist."""
    typ = (row["type"] if "type" in row.keys() else "Opportunity") or "Opportunity"
    title = row["title"] or "Opportunity"
    provider = (row["provider"] if "provider" in row.keys() else "") or "Provider to verify"
    country = (row["country"] if "country" in row.keys() else "") or "Global / verify"
    level = (row["level"] if "level" in row.keys() else "") or "Students"
    deadline = (row["deadline"] if "deadline" in row.keys() else "") or "See official page"
    summary = (row["summary"] if "summary" in row.keys() else "") or ""
    bits = [f"{title} — a {typ.lower()} opportunity from {provider}.",
            f"Eligible level: {level}. Location: {country}. Deadline: {deadline}."]
    if summary: bits.append(summary.strip())
    bits.append("Hover for details; always confirm dates and eligibility on the official page before applying.")
    return " ".join(bits)

def fetch_feed_items(url: str, timeout: int = 10) -> list[dict]:
    """Fetch RSS/Atom or a plain HTML page and return candidate opportunities."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https links are supported.")
    req = urllib.request.Request(url, headers={"User-Agent": "70ScholarBot/1.0 (+https://www.nesa.gov.rw/)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(2_000_000)
        ctype = (resp.headers.get("Content-Type") or "").lower()
    text = raw.decode("utf-8", errors="replace")
    items = []
    if "xml" in ctype or text.lstrip().startswith("<?xml") or "<rss" in text[:600] or "<feed" in text[:600]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            root = None
        if root is not None:
            nodes = root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for n in nodes[:40]:
                def txt(*names):
                    for name in names:
                        v = n.findtext(name)
                        if v: return v.strip()
                    return ""
                title = strip_tags(txt("title", "{http://www.w3.org/2005/Atom}title"))
                link = txt("link")
                if not link:
                    le = n.find("{http://www.w3.org/2005/Atom}link")
                    link = le.get("href", "") if le is not None else ""
                desc = strip_tags(txt("description", "summary", "{http://www.w3.org/2005/Atom}summary"))
                if title:
                    items.append({"title": title[:200], "url": (link or url)[:500], "summary": desc[:600]})
    if not items:
        # Basic HTML link extraction for pages that are not feeds.
        for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
            href, label = m.group(1), strip_tags(m.group(2))
            if len(label) < 12 or href.startswith(("#", "javascript:", "mailto:")):
                continue
            if href.startswith("/"):
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                continue
            if re.search(r"scholar|grant|intern|compet|fellow|award|program|applic|bursar|fund", label, re.I):
                items.append({"title": label[:200], "url": href[:500], "summary": f"Found on {parsed.netloc}. Verify details on the source page."})
            if len(items) >= 30: break
    return items

def import_feed_items(items: list[dict], source: str) -> int:
    added = 0
    with db() as conn:
        for it in items:
            title = (it.get("title") or "").strip()
            link = (it.get("url") or source).strip()
            if not title or len(title) < 8: continue
            desc = (it.get("summary") or "").strip() or "Auto-imported listing. Verify eligibility and deadline on the source page."
            typ = infer_type(title)
            deadline = infer_deadline(title + " " + desc)
            provider = urlparse(link).netloc.replace("www.", "") or "Community source"
            desc_full = desc + f" Source: {provider}."
            cur = conn.execute("INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                               (typ, title, provider, "Global / verify", "Students, youth, builders", deadline, link, desc[:600], "auto", source, now_iso()))
            if cur.rowcount:
                added += 1
                conn.execute("UPDATE opportunities SET auto_description=? WHERE id=?", (make_auto_description({"type":typ,"title":title,"provider":provider,"country":"Global / verify","level":"Students, youth, builders","deadline":deadline,"summary":desc}), cur.lastrowid))
        conn.execute("INSERT INTO sync_logs(source,imported,message,created_at) VALUES(?,?,?,?)", (source, added, "OK", now_iso()))
    return added

def run_auto_sync() -> tuple[int, list[str]]:
    """Import from all enabled saved links. Called by the toggle and background worker."""
    total = 0; notes = []
    with db() as conn:
        sources = [r["url"] for r in conn.execute("SELECT url FROM feed_sources WHERE enabled=1").fetchall()]
    for src in sources:
        try:
            n = import_feed_items(fetch_feed_items(src), src)
            total += n; notes.append(f"{n} from {src}")
        except Exception as ex:
            notes.append(f"failed {src}: {str(ex)[:80]}")
    return total, notes

def auto_sync_worker() -> None:
    """Background loop: while auto_sync is ON, refresh saved links periodically."""
    while True:
        time.sleep(60)
        try:
            if get_setting("auto_sync", "0") != "1": continue
            last = float(get_setting("auto_sync_last", "0") or 0)
            if time.time() - last < AUTO_SYNC_INTERVAL_SECONDS: continue
            run_auto_sync()
            set_setting("auto_sync_last", str(time.time()))
        except Exception as ex:
            print("auto-sync error:", ex, file=sys.stderr)

def deadline_badge(deadline: str) -> str:
    try:
        days = (datetime.fromisoformat(deadline).date() - datetime.now(timezone.utc).date()).days
        if days < 0: return "Closed / verify"
        if days == 0: return "Due today"
        if days <= 30: return f"{days} days left"
        return datetime.fromisoformat(deadline).strftime("%d %b %Y")
    except Exception: return "Verify deadline"

def flash(message: str, kind: str = "info") -> str:
    return f"<div class='flash {e(kind)}'>{e(message)}</div>" if message else ""

def brand_logo() -> str:
    return f"""<img class="logo-img" src="/static/images/logo.svg?v={APP_VERSION}" alt="70Scholar logo" width="68" height="68"><span class='logo-text'><span class='logo-first'>70</span><span class='logo-last'>Scholar</span></span>"""


def page_shell(title: str, body: str, user: sqlite3.Row | None = None, active: str = "") -> str:
    logo = brand_logo()
    if user:
        if "profile_photo_url" in user.keys() and user["profile_photo_url"]:
            avatar = f"<img src='{e(user['profile_photo_url'])}' alt='Profile photo'>"
        else:
            initials = ''.join([part[0].upper() for part in user['name'].split()[:2]]) or 'U'
            avatar = f"<span>{e(initials)}</span>"
        profile_link = f"<a class='nav-profile {'is-active' if active=='account' else ''}' href='/account' title='Account settings'>{avatar}</a>"
        admin_link = f"<a class='nav-link {'is-active' if active=='admin' else ''}' href='/admin'>Admin</a>" if is_admin(user) else ''
        nav_auth = f"""<a class="nav-link {'is-active' if active=='dashboard' else ''}" href="/dashboard">Dashboard</a><a class="nav-link {'is-active' if active=='workspace' else ''}" href="/workspace">Workspace</a><a class="nav-link {'is-active' if active=='messages' else ''}" href="/messages">Messages</a><a class="nav-link {'is-active' if active=='submit' else ''}" href="/submit">Add opportunity</a><a class="nav-link {'is-active' if active=='account' else ''}" href="/account">Account</a>{admin_link}{profile_link}<form class="logout-form" action="/logout" method="post"><input type="hidden" name="csrf" value="{e(user['csrf'])}"><button>Log out</button></form>"""
    else:
        nav_auth = "<a class='nav-link' href='/login'>Log in</a><a class='pill small' href='/signup'>Create account</a>"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{e(title)} — {APP_NAME}</title><meta name="description" content="{APP_NAME} helps students discover opportunities, showcase projects, connect with sponsors, and build what comes next."><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,500;0,600;1,400;1,500&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet"><link rel="icon" type="image/svg+xml" href="/static/favicon.svg?v={APP_VERSION}"><link rel="stylesheet" href="/static/styles.css?v={APP_VERSION}"></head><body><header class="site-header"><a href="/" class="logo">{logo}</a><nav class="top-nav" aria-label="Primary navigation"><a class="nav-link {'is-active' if active=='opportunities' else ''}" href="/opportunities">Opportunities</a><a class="nav-link {'is-active' if active=='courses' else ''}" href="/courses">Courses</a><a class="nav-link {'is-active' if active=='exams' else ''}" href="/exams">Exam prep</a><a class="nav-link {'is-active' if active=='marketplace' else ''}" href="/marketplace">Marketplace</a>{nav_auth}</nav></header><main>{body}</main><footer class="footer"><div class="logo">{logo}</div><p>{APP_TAGLINE}</p><p class="copyright">© {datetime.now(timezone.utc).year} {COMPANY_NAME}. All rights reserved.</p></footer><script src="/static/app.js?v={APP_VERSION}"></script></body></html>"""

HOMEPAGE_PHOTOS = [
    {"file": "students-library.jpg", "w": 1200, "h": 801,
     "alt": "Rwandan students studying together in a school library",
     "caption": "Rwanda's students", "note": "Learning side by side"},
    {"file": "students-classroom.jpg", "w": 1200, "h": 801,
     "alt": "A classroom of Rwandan students in school uniform",
     "caption": "In the classroom", "note": "Where futures begin"},
    {"file": "student-chalkboard.jpg", "w": 1200, "h": 801,
     "alt": "A Rwandan student writing at the chalkboard",
     "caption": "Every scholar has a voice", "note": "Confidence to step forward"},
    {"file": "students-collaborating.jpg", "w": 1200, "h": 801,
     "alt": "Students collaborating around a table in a school library",
     "caption": "Learning together", "note": "Peers who push each other"},
    {"file": "teacher-and-students.jpg", "w": 1200, "h": 801,
     "alt": "A teacher leading a Rwandan class at the chalkboard",
     "caption": "Teachers who open doors", "note": "Guidance that lasts"},
    {"file": "official-with-student.jpg", "w": 1000, "h": 785,
     "alt": "An education official handing an exam paper to a young student",
     "caption": "Leaders investing in learners", "note": "Education as a national priority"},
    {"file": "education-leaders.jpg", "w": 1200, "h": 640,
     "alt": "Rwandan education leaders launching national examination results",
     "caption": "National commitment", "note": "Building a system that works"},
]

def render_photo_gallery() -> str:
    cards = "".join([
        f"""<figure class="gallery-card">
          <img src="/static/images/{e(photo['file'])}?v={APP_VERSION}" alt="{e(photo['alt'])}"
               loading="lazy" decoding="async" width="{photo.get('w', 1200)}" height="{photo.get('h', 800)}">
          <figcaption><strong>{e(photo['caption'])}</strong><span>{e(photo['note'])}</span></figcaption>
        </figure>""" for photo in HOMEPAGE_PHOTOS
    ])
    return f"""<section class="photo-gallery" id="community">
      <div class="gallery-inner">
        <p class="eyebrow eyebrow-dark">The people behind the mission</p>
        <h2>Real students. Real scholars. Real futures.</h2>
        <p class="gallery-intro">Real students, teachers and education leaders from Rwanda —
        the community 70Scholar is built to serve.</p>
        <div class="gallery-grid">{cards}</div>
      </div>
    </section>"""

def render_home(user):
    with db() as conn:
        stats = {
            "opportunities": conn.execute("SELECT COUNT(*) c FROM opportunities").fetchone()["c"],
            "projects": conn.execute("SELECT COUNT(*) c FROM projects WHERE status='public'").fetchone()["c"],
            "pledged": conn.execute("SELECT COALESCE(SUM(amount),0) c FROM pledges").fetchone()["c"],
        }
    story_section = f'''<section class="story-section"><div class="story-inner"><p class="eyebrow eyebrow-dark">The story 70Scholar is building</p><h2>A path for the student who almost gave up searching.</h2><p>70Scholar was created for students who keep asking, "Where are the scholarships, internships, competitions, sponsors, and people who will believe in my project?" The goal is to make answers easier to find, applications easier to prepare, and student projects easier to support.</p><p>As more students use 70Scholar, this section will grow into a verified wall of wins: scholarships found, internships applied for, jobs reached, sponsors connected, and projects funded. We will count real success only when students confirm it — because trust matters.</p><div class="impact-stats"><div><strong>{stats['opportunities']}</strong><span>opportunities currently listed</span></div><div><strong>{stats['projects']}</strong><span>student projects published</span></div><div><strong>{money(stats['pledged'])}</strong><span>pledges recorded for builders</span></div></div></div></section>'''
    body = '''<section class="hero" id="hero"><div class="hero-bg-beyond" aria-hidden="true"></div><div class="hero-bg-now" aria-hidden="true"></div><div class="hero-content"><p class="brand-display"><span class="brand-num">70</span><span class="brand-word">Scholar</span></p><p class="eyebrow">Matched to your level. Built to launch.</p><h1>There's a version of your future<br>still waiting to be found.</h1><p class="subhead">70Scholar finds scholarships, internships, grants, and competitions built for where you stand — then gives you a secure workspace to build the projects that get you noticed, funded, or sold.</p><div class="hero-actions"><a href="/opportunities" class="cta-primary">See real open opportunities <span class="arrow">→</span></a><a href="/marketplace" class="cta-secondary">Fund or buy student projects</a></div><p class="hero-micro">Real listings, refreshed from trusted opportunity feeds.</p></div><div class="scroll-hint" aria-hidden="true"><span></span></div></section>''' + render_typewriter() + story_section + render_slideshow() + render_photo_gallery() + render_extra_features() + '''
<section class="gap-section"><p class="eyebrow eyebrow-dark">Why most students miss out</p><p class="gap-statement">Most scholarships don't go unclaimed because nobody qualified. They go unclaimed because the right student never found them — or found them too late to build something strong.</p></section>
<section class="journey-section" id="journey"><div class="journey-header"><p class="eyebrow">The path across</p><h2>Discover. Build. Launch. Fund.</h2></div><div class="journey-path"><div class="journey-step"><span class="step-number">01</span><h3>Discover</h3><p>Browse real openings and save the ones that fit your country, field, deadline, and level.</p></div><div class="journey-step"><span class="step-number">02</span><h3>Build</h3><p>Keep drafts, pitch text, links, files, and project details in your private account so unfinished work stays safe.</p></div><div class="journey-step"><span class="step-number">03</span><h3>Launch</h3><p>Publish a project to the marketplace, attach a demo or release file, and invite buyers, donors, mentors, or funders.</p></div></div></section>
<section class="opportunities-section"><div class="opp-header"><p class="eyebrow eyebrow-dark">What's waiting on the other side</p><h2>Every door, sorted by which one actually opens for you.</h2></div><div class="opportunity-cards feature-cards"><div class="opp-card"><div class="icon-dot">🎓</div><h3>Scholarships</h3><p>Funding matched to your field, level, and country, with deadlines you can track.</p></div><div class="opp-card"><div class="icon-dot">💼</div><h3>Internships</h3><p>Roles sized for where you actually are in school, not five-year-experience traps.</p></div><div class="opp-card"><div class="icon-dot">🏆</div><h3>Competitions & grants</h3><p>Contests and small grants your project can realistically compete for.</p></div></div></section>
<section class="workspace-section"><div class="workspace-inner"><div class="workspace-visual" aria-hidden="true"><div class="ws-card c1"></div><div class="ws-card c2"></div><div class="ws-card c3"></div></div><div class="workspace-copy"><p class="eyebrow">Where the work actually happens</p><h2>Not just a plan. A place to build it.</h2><p>Create an account, save unfinished project drafts, upload a release file, and later publish the project for funding or sale. Funders can pledge support, buyers can contact makers, and students can continue from where they stopped.</p></div></div></section>
<section class="final-cta" id="final-cta"><h2>Cross over.</h2><p>Somewhere on the other side, there's a deadline that hasn't found you yet. Better to be early.</p><a href="/signup" class="cta-primary">Create your free workspace <span class="arrow">→</span></a></section>'''
    return page_shell("Future waiting to be found", body, user)

SLIDESHOW_PHOTOS = [
    ("slide-01.jpg", "Students studying together in a school library"),
    ("slide-02.jpg", "A student working at the chalkboard"),
    ("slide-03.jpg", "Education leaders at a national event"),
    ("slide-04.jpg", "Students collaborating around a table"),
    ("slide-05.jpg", "School leaders and partners"),
    ("slide-06.jpg", "A classroom of students in uniform"),
    ("slide-07.jpg", "A teacher teaching at the chalkboard"),
    ("slide-08.jpg", "Education stakeholders at a national dialogue"),
    ("slide-09.jpg", "Delegates at an education conference"),
    ("slide-10.jpg", "A ministerial address on education policy"),
    ("slide-11.jpg", "Examination materials presented to a student"),
    ("slide-12.jpg", "Students sitting national examinations"),
]

def hover_card(inner: str, description: str, extra_class: str = "") -> str:
    """Wrap content with a cursor-following auto-description tooltip."""
    return f'<div class="hover-card {extra_class}" data-tooltip="{e(description)}">{inner}</div>'

def render_slideshow() -> str:
    slides = "".join([
        f'<figure class="slide {"is-active" if i == 0 else ""}" data-index="{i}">'
        f'<img src="/static/images/slides/{f}?v={APP_VERSION}" alt="{e(alt)}" loading="{"eager" if i == 0 else "lazy"}" decoding="async">'
        f'<figcaption>{e(alt)}</figcaption></figure>'
        for i, (f, alt) in enumerate(SLIDESHOW_PHOTOS)
    ])
    dots = "".join([f'<button class="slide-dot {"is-active" if i == 0 else ""}" data-go="{i}" aria-label="Show photo {i+1}"></button>' for i in range(len(SLIDESHOW_PHOTOS))])
    return f"""<section class="slideshow-section" id="gallery">
      <div class="slideshow-head"><p class="eyebrow eyebrow-dark">Inside Rwanda's classrooms</p>
      <h2>Real moments from real learners.</h2></div>
      <div class="slideshow" id="slideshow">
        <div class="slides">{slides}</div>
        <button class="slide-nav prev" data-dir="-1" aria-label="Previous photo">‹</button>
        <button class="slide-nav next" data-dir="1" aria-label="Next photo">›</button>
        <div class="slide-dots">{dots}</div>
        <span class="slide-counter"><strong id="slideCurrent">1</strong> / {len(SLIDESHOW_PHOTOS)}</span>
      </div>
    </section>"""

def render_typewriter() -> str:
    return """<section class="typewriter-band"><p class="typewriter-label">Everything you need, in one place</p>
      <p class="typewriter-line"><span id="typewriter"></span><span class="typewriter-caret" aria-hidden="true"></span></p>
      <p class="typewriter-sub">Opportunities, courses, exam prep, applications and funding — built for students who are ready to move.</p></section>"""

def render_extra_features() -> str:
    """Extra homepage sections: feature grid, live stats, how-it-works, FAQ, CTA."""
    return """<section class="feature-section" id="features">
      <div class="feature-inner"><p class="eyebrow eyebrow-dark">Built for the whole journey</p>
      <h2>One account. Every step from discovery to funding.</h2>
      <div class="feature-grid">
        <a class="feature-tile" href="/opportunities" data-tooltip="Browse verified scholarships, internships, competitions, grants and applications. Hover any listing for an instant description."><span class="feature-icon">🔎</span><h3>Opportunity finder</h3><p>Search by country, level, field and deadline. Save what fits.</p></a>
        <a class="feature-tile" href="/courses" data-tooltip="Pre-university courses in academic English, foundation maths, programming, research methods and university applications."><span class="feature-icon">📚</span><h3>Pre-university courses</h3><p>Close the gap before you apply with short, focused courses.</p></a>
        <a class="feature-tile" href="/exams" data-tooltip="Prepare for SAT, ACT, IELTS, TOEFL, AP/IB/A-Levels and scholarship aptitude tests with structured study plans."><span class="feature-icon">📝</span><h3>Exam preparation</h3><p>Practice plans for the tests that unlock university offers.</p></a>
        <a class="feature-tile" href="/submit" data-tooltip="Found an opportunity? Submit it for admin review. Nothing is published until the owner approves it."><span class="feature-icon">➕</span><h3>Community submissions</h3><p>Add a scholarship or competition and help other students find it.</p></a>
        <a class="feature-tile" href="/marketplace" data-tooltip="Publish your project, attach files, and let sponsors support you directly. 5% of each contribution funds other student projects."><span class="feature-icon">🚀</span><h3>Project marketplace</h3><p>Show your build, find sponsors, and get funded.</p></a>
        <a class="feature-tile" href="/signup" data-tooltip="Create a free account to unlock opportunities, courses, exam prep, submissions and the builder workspace."><span class="feature-icon">🔐</span><h3>Your private workspace</h3><p>Drafts, uploads, saved listings and messages in one place.</p></a>
      </div></div></section>
    <section class="trust-section"><div class="trust-inner">
      <div class="trust-stat"><strong data-count="37">0</strong><span>opportunities listed</span></div>
      <div class="trust-stat"><strong data-count="12">0</strong><span>photos of real learners</span></div>
      <div class="trust-stat"><strong data-count="6">0</strong><span>pre-university courses</span></div>
      <div class="trust-stat"><strong data-count="6">0</strong><span>exam prep tracks</span></div>
    </div></section>
    <section class="faq-section"><div class="faq-inner"><p class="eyebrow eyebrow-dark">Good to know</p><h2>Questions students ask us.</h2>
      <details class="faq-item"><summary>Do I need an account to see opportunities?</summary><p>Yes. Create a free account or log in to browse opportunities, courses, exam prep, the marketplace and your workspace. The homepage stays open to everyone.</p></details>
      <details class="faq-item"><summary>Are the courses and exam prep free?</summary><p>Joining a course or exam track is free. It saves your place so study materials and practice plans can be added to your dashboard.</p></details>
      <details class="faq-item"><summary>Can I add an opportunity?</summary><p>Yes. Use “Add opportunity” after signing in. Your submission stays private until the admin approves it.</p></details>
      <details class="faq-item"><summary>How does the 5% platform contribution work?</summary><p>When a sponsor supports a project, a 5% platform contribution is recorded for the 70Scholar Future Fund, which sponsors other student projects. The rest goes to the creator.</p></details>
      <details class="faq-item"><summary>Where do the photos come from?</summary><p>Real photographs from Rwanda's National Examination and School Inspection Authority (NESA) website.</p></details>
    </div></section>
    <section class="cta-band"><h2>Your next opportunity is already out there.</h2><p>Join 70Scholar and start building the future you can see.</p><div class="hero-actions"><a class="cta-primary" href="/signup">Create your free account <span class="arrow">→</span></a><a class="cta-secondary dark" href="/login">Log in</a></div></section>"""

def render_courses(user, msg: str = ""):
    cards = "".join([
        hover_card(
            f"""<article class="course-card"><span class="tag">{e(c['category'])}</span><h3>{e(c['title'])}</h3>
            <p class="provider">{e(c['level'])} · {e(c['duration'])}</p><p>{e(c['summary'])}</p>
            <ul class="check-list">{''.join(f'<li>{e(t)}</li>' for t in c['topics'])}</ul>
            <form method="post" action="/course/enrol" class="inline-form">
            <input type="hidden" name="csrf" value="{e(user['csrf'])}">
            <input type="hidden" name="course_key" value="{e(c['title'])}">
            <input type="hidden" name="kind" value="course">
            <button class="cta-primary slim" type="submit">Join this course</button></form></article>""",
            f"{c['title']}: {c['summary']} Level: {c['level']}. Duration: {c['duration']}. Covers " + ", ".join(c['topics']) + ".",
            "course-wrap") for c in PREUNI_COURSES
    ])
    body = f"""<section class="page-hero compact"><p class="eyebrow">Pre-university academy</p>
      <h1>Get ready before you apply.</h1><p>Short, practical courses that close the gap between secondary school and university.</p></section>
      <section class="panel-section">{flash(msg,'success') if msg else ''}
      <div class="course-grid">{cards}</div></section>"""
    return page_shell("Pre-university courses", body, user, "courses")

def render_exams(user, msg: str = ""):
    cards = "".join([
        hover_card(
            f"""<article class="course-card exam-card"><span class="tag">{e(c['category'])}</span><h3>{e(c['title'])}</h3>
            <p class="provider">{e(c['level'])} · {e(c['duration'])}</p><p>{e(c['summary'])}</p>
            <ul class="check-list">{''.join(f'<li>{e(t)}</li>' for t in c['topics'])}</ul>
            <form method="post" action="/course/enrol" class="inline-form">
            <input type="hidden" name="csrf" value="{e(user['csrf'])}">
            <input type="hidden" name="course_key" value="{e(c['title'])}">
            <input type="hidden" name="kind" value="exam">
            <button class="cta-primary slim" type="submit">Start preparing</button></form></article>""",
            f"{c['title']}: {c['summary']} Level: {c['level']}. Duration: {c['duration']}. Focus areas: " + ", ".join(c['topics']) + ".",
            "course-wrap") for c in EXAM_PREP
    ])
    body = f"""<section class="page-hero compact"><p class="eyebrow">Exam preparation</p>
      <h1>Walk into the exam ready.</h1><p>Structured preparation for university entrance exams, English proficiency tests and scholarship selection.</p></section>
      <section class="panel-section">{flash(msg,'success') if msg else ''}
      <div class="course-grid">{cards}</div></section>"""
    return page_shell("Exam preparation", body, user, "exams")

def render_submit(user, msg: str = "", kind: str = "success"):
    opts = "".join(f"<option>{t}</option>" for t in ["Scholarship","Internship","Competition","Grant","Hackathon","Application","Opportunity"])
    with db() as conn:
        mine = conn.execute("SELECT * FROM opportunity_submissions WHERE user_id=? ORDER BY id DESC LIMIT 10", (user["id"],)).fetchall()
    rows = "".join([f"<li><strong>{e(r['title'])}</strong> <span class='tag'>{e(r['status'])}</span><br><span>{e(r['type'])} · {e(r['deadline'])}</span></li>" for r in mine])
    body = f"""<section class="page-hero compact"><p class="eyebrow">Community submissions</p>
      <h1>Add an opportunity.</h1><p>Found a scholarship, competition or application others should know about? Submit it here. The admin reviews every submission before it appears publicly.</p></section>
      <section class="panel-section">{flash(msg,kind) if msg else ''}
      <div class="submit-layout">
        <form method="post" action="/opportunity/submit" class="builder-form">
          <input type="hidden" name="csrf" value="{e(user['csrf'])}">
          <h2>Opportunity details</h2>
          <div class="form-row"><label>Type<select name="type">{opts}</select></label>
          <label>Deadline<input name="deadline" placeholder="e.g. 2026-12-31 or Rolling" required></label></div>
          <label>Title<input name="title" required maxlength="200" placeholder="Official opportunity name"></label>
          <div class="form-row"><label>Provider / organisation<input name="provider" required maxlength="160"></label>
          <label>Country<input name="country" required maxlength="100" placeholder="Rwanda / Global"></label></div>
          <label>Eligible level<input name="level" required maxlength="160" placeholder="e.g. Final-year secondary, undergraduates"></label>
          <label>Official URL<input name="url" type="url" required placeholder="https://"></label>
          <label>Short summary<textarea name="summary" required maxlength="1200" placeholder="Who can apply, what it offers, and why it matters"></textarea></label>
          <label>Tags<input name="tags" maxlength="200" placeholder="STEM, women, Africa"></label>
          <button class="cta-primary" type="submit">Submit for review</button>
        </form>
        <div class="builder-panel"><h2>Your submissions</h2>
        <ul class="clean-list">{rows if rows else '<li>Nothing submitted yet.</li>'}</ul>
        <p class="muted">Pending items are visible only to you and the admin until approved.</p></div>
      </div></section>"""
    return page_shell("Submit an opportunity", body, user, "submit")


def render_auth(mode: str, msg: str = "", next_url: str = ""):
    is_signup = mode == "signup"; title = "Create your account" if is_signup else "Log in"; action = "/signup" if is_signup else "/login"
    safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else ""
    hidden_next = f"<input type='hidden' name='next' value='{e(safe_next)}'>" if safe_next and not is_signup else ""
    extra = '<label>Full name<input required name="name" autocomplete="name" placeholder="Your name"></label>' if is_signup else ''
    switch = "Already have an account? <a href='/login'>Log in</a>." if is_signup else "New here? <a href='/signup'>Create an account</a>."
    forgot = "" if is_signup else "<p class='muted'><a href='/forgot-password'>Forgot password?</a></p>"
    body = f"""<section class="auth-wrap"><form class="auth-card" method="post" action="{action}"><p class="eyebrow eyebrow-dark">Secure workspace</p><h1>{title}</h1>{flash(msg,'error') if msg else ''}{hidden_next}{extra}<label>Email<input required type="email" name="email" autocomplete="email" placeholder="you@example.com"></label><label>Password<input required type="password" name="password" autocomplete="{'new-password' if is_signup else 'current-password'}" minlength="8" placeholder="At least 8 characters"></label><button class="cta-primary auth-button" type="submit">{title}</button>{forgot}<p class="muted">{switch}</p></form></section>"""
    return page_shell(title, body, None)

def render_notice(title: str, message: str, user=None):
    body = f"""<section class='auth-wrap'><div class='auth-card'><p class='eyebrow eyebrow-dark'>70Scholar</p><h1>{e(title)}</h1><p>{e(message)}</p><p class='muted'>In local development, emails are saved in <strong>mail_outbox.log</strong>.</p><div class='form-actions'><a class='cta-primary' href='/login'>Log in</a><a class='ghost-button' href='/'>Home</a></div></div></section>"""
    return page_shell(title, body, user)

def render_forgot_password(msg: str = ""):
    body = f"""<section class='auth-wrap'><form class='auth-card' method='post' action='/forgot-password'><p class='eyebrow eyebrow-dark'>Account recovery</p><h1>Reset your password</h1>{flash(msg,'success') if msg else ''}<p class='muted'>Enter your account email. We will send a reset link.</p><label>Email<input required type='email' name='email' autocomplete='email'></label><button class='cta-primary auth-button' type='submit'>Send reset link</button><p class='muted'><a href='/login'>Back to login</a></p></form></section>"""
    return page_shell("Forgot password", body, None)

def render_reset_password(token: str, msg: str = ""):
    body = f"""<section class='auth-wrap'><form class='auth-card' method='post' action='/reset-password'><p class='eyebrow eyebrow-dark'>Account recovery</p><h1>Choose a new password</h1>{flash(msg,'error') if msg else ''}<input type='hidden' name='token' value='{e(token)}'><label>New password<input required type='password' minlength='8' name='password' autocomplete='new-password'></label><button class='cta-primary auth-button' type='submit'>Reset password</button></form></section>"""
    return page_shell("Reset password", body, None)

def render_account(user, msg=""):
    photo = user["profile_photo_url"] if "profile_photo_url" in user.keys() else ""
    if photo:
        avatar = f"<img src='{e(photo)}' alt='Profile photo'>"
    else:
        initials = ''.join([part[0].upper() for part in user['name'].split()[:2]]) or 'U'
        avatar = f"<span>{e(initials)}</span>"
    body = f"""
    <section class='page-hero compact'><p class='eyebrow'>Account settings</p><h1>Your profile and security.</h1><p>Update your display name, profile photo, and password.</p></section>
    <section class='account-grid'>
      {flash(msg,'success') if msg else ''}
      <div class='account-card'>
        <div class='profile-avatar' id='profileAvatar'>{avatar}</div>
        <h2>{e(user['name'])}</h2><p class='muted'>{e(user['email'])}</p>
        <div class='upload-box profile-upload' data-account-csrf='{e(user['csrf'])}'>
          <h3>Profile photo</h3><p>Upload a square photo or logo for your builder profile. Max 10 MB.</p>
          <input type='file' id='profilePhoto' accept='image/*'>
          <button class='ghost-button' type='button' id='uploadProfilePhoto'>Upload profile photo</button>
          <p class='upload-status' id='profileUploadStatus'></p>
        </div>
      </div>
      <div class='builder-panel'>
        <form method='post' action='/account/name' class='builder-form'>
          <input type='hidden' name='csrf' value='{e(user['csrf'])}'>
          <h2>Change account name</h2>
          <label>Display name<input required name='name' value='{e(user['name'])}'></label>
          <button class='cta-primary' type='submit'>Save name</button>
        </form>
        <hr class='soft-divider'>
        <form method='post' action='/account/password' class='builder-form'>
          <input type='hidden' name='csrf' value='{e(user['csrf'])}'>
          <h2>Change password</h2>
          <label>Current password<input required type='password' name='current_password' autocomplete='current-password'></label>
          <label>New password<input required type='password' name='new_password' minlength='8' autocomplete='new-password'></label>
          <button class='cta-primary' type='submit'>Update password</button>
        </form>
      </div>
    </section>
    """
    return page_shell("Account", body, user, "account")

def render_opportunities(user, query):
    q = (query.get("q", [""])[0] or "").strip(); typ = (query.get("type", [""])[0] or "").strip(); params=[]; where=["1=1"]
    if q:
        like=f"%{q}%"; where.append("(title LIKE ? OR provider LIKE ? OR country LIKE ? OR level LIKE ? OR tags LIKE ? OR summary LIKE ?)"); params += [like]*6
    if typ: where.append("type=?"); params.append(typ)
    with db() as conn:
        items = conn.execute(f"SELECT * FROM opportunities WHERE {' AND '.join(where)} ORDER BY deadline ASC", params).fetchall()
        bookmarks = {r["opportunity_id"] for r in conn.execute("SELECT opportunity_id FROM bookmarks WHERE user_id=?", (user["id"],)).fetchall()} if user else set()
    cards=[]
    for item in items:
        if user:
            saved = item["id"] in bookmarks
            save_button = f"""<form method="post" action="/bookmark" class="inline-form"><input type="hidden" name="csrf" value="{e(user['csrf'])}"><input type="hidden" name="opportunity_id" value="{item['id']}"><button class="ghost-button" type="submit">{'Saved ✓' if saved else 'Save'}</button></form>"""
        else: save_button = "<a class='ghost-button' href='/login'>Log in to save</a>"
        cards.append(f"""<article class="listing-card" data-tooltip="{e(item['auto_description'] if 'auto_description' in item.keys() and item['auto_description'] else make_auto_description(item))}"><div class="listing-top"><span class="tag">{e(item['type'])}</span><span class="deadline">{e(deadline_badge(item['deadline']))}</span></div><h3>{e(item['title'])}</h3><p class="provider">{e(item['provider'])} · {e(item['country'])}</p><p>{e(item['summary'])}</p><dl class="mini-meta"><div><dt>Level</dt><dd>{e(item['level'])}</dd></div><div><dt>Deadline</dt><dd>{e(item['deadline'])}</dd></div></dl><p class="source">Source: {e(item['source'])}</p><div class="card-actions"><a class="cta-primary slim" target="_blank" rel="noopener" href="{e(item['url'])}">Apply on source ↗</a>{save_button}</div></article>""")
    def sel(x): return "selected" if typ == x else ""
    body = f"""<section class="page-hero compact"><p class="eyebrow">Opportunity finder</p><h1>Real applications, contests, internships, and grants.</h1><p>These seed listings are current starting points for August 2026. Always verify the final deadline and eligibility on the official page before applying.</p></section><section class="panel-section"><form class="filter-bar" method="get" action="/opportunities"><input name="q" value="{e(q)}" placeholder="Search Rwanda, AI, climate, internship..."><select name="type"><option value="">All types</option><option {sel('Scholarship')} value="Scholarship">Scholarships</option><option {sel('Internship')} value="Internship">Internships</option><option {sel('Competition')} value="Competition">Competitions</option><option {sel('Grant')} value="Grant">Grants</option><option {sel('Hackathon')} value="Hackathon">Hackathons</option></select><button class="cta-primary slim" type="submit">Filter</button></form><div class="listing-grid">{''.join(cards) if cards else '<p class="empty">No matches yet. Try a different search.</p>'}</div></section>"""
    return page_shell("Opportunities", body, user, "opportunities")

def render_dashboard(user):
    with db() as conn:
        projects = conn.execute("SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC", (user["id"],)).fetchall()
        saved = conn.execute("SELECT o.* FROM bookmarks b JOIN opportunities o ON o.id=b.opportunity_id WHERE b.user_id=? ORDER BY o.deadline ASC", (user["id"],)).fetchall()
        pledges = conn.execute("SELECT pl.*, p.title FROM pledges pl JOIN projects p ON p.id=pl.project_id WHERE pl.user_id=? ORDER BY pl.created_at DESC", (user["id"],)).fetchall()
        inbox = conn.execute("SELECT m.*, p.title FROM project_messages m JOIN projects p ON p.id=m.project_id WHERE p.user_id=? ORDER BY m.created_at DESC LIMIT 8", (user["id"],)).fetchall()
    project_cards = [f"<article class='mini-card'><span class='tag'>{e(p['status'].replace('_',' ').title())}</span><h3>{e(p['title'])}</h3><p>{e(p['summary'])}</p><a href='/workspace?edit={p['id']}'>Continue work →</a></article>" for p in projects]
    saved_cards = [f"<li><a target='_blank' rel='noopener' href='{e(o['url'])}'>{e(o['title'])}</a><span>{e(deadline_badge(o['deadline']))}</span></li>" for o in saved]
    pledge_cards = [f"<li>{money(pl['amount'])} pledged to <a href='/project?id={pl['project_id']}'>{e(pl['title'])}</a></li>" for pl in pledges]
    inbox_cards = [f"<li><a href='/project?id={m['project_id']}'>{e(m['title'])}</a><span>{e(m['name'])}: {e(m['message'][:90])}</span></li>" for m in inbox]
    verify_banner = "" if user["email_verified"] else "<div class='flash error'>Please verify your email address. Check your inbox or mail_outbox.log in local development.</div>"
    body = f"""<section class="page-hero compact dashboard-hero"><p class="eyebrow">Welcome back, {e(user['name'].split()[0])}</p><h1>Continue your unfinished work.</h1><p>Your saved opportunities, drafts, uploads, and funding activity live here.</p><a href="/workspace" class="cta-primary">Open builder workspace →</a></section><section class="dashboard-grid">{verify_banner}<div class="dash-panel large"><div class="panel-head"><h2>Your projects</h2><a href="/workspace">New project</a></div><div class="mini-grid">{''.join(project_cards) if project_cards else '<p class="empty">No drafts yet. Start one in the workspace.</p>'}</div></div><div class="dash-panel"><h2>Saved opportunities</h2><ul class="clean-list">{''.join(saved_cards) if saved_cards else '<li>No saved opportunities yet.</li>'}</ul></div><div class="dash-panel"><h2>Funding activity</h2><ul class="clean-list">{''.join(pledge_cards) if pledge_cards else '<li>No pledges recorded yet.</li>'}</ul></div><div class="dash-panel"><h2>Sponsor messages</h2><ul class="clean-list">{''.join(inbox_cards) if inbox_cards else '<li>No sponsor questions yet.</li>'}</ul></div><div class="dash-panel"><h2>Builder checklist</h2><ol class="check-list"><li>Save an opportunity.</li><li>Create a project draft.</li><li>Upload a prototype or add a demo link.</li><li>Publish when ready for funding or sale.</li></ol></div></section>"""
    return page_shell("Dashboard", body, user, "dashboard")

def render_workspace(user, query):
    edit_id = query.get("edit", [""])[0]
    with db() as conn:
        projects = conn.execute("SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC", (user["id"],)).fetchall()
        project = conn.execute("SELECT * FROM projects WHERE id=? AND user_id=?", (int(edit_id), user["id"])).fetchone() if edit_id.isdigit() else None
        assets = conn.execute("SELECT * FROM assets WHERE project_id=? ORDER BY created_at DESC", (project["id"],)).fetchall() if project else []
    side=[]
    for row in projects:
        klass = "project-link active" if project and row["id"] == project["id"] else "project-link"
        side.append(f"<a class='{klass}' href='/workspace?edit={row['id']}'><strong>{e(row['title'])}</strong><span>{'Published' if row['status']=='public' else 'Draft'} · {e(row['updated_at'][:10])}</span></a>")
    def val(key, default=""):
        return e(project[key]) if project else default
    def selected(s):
        return "selected" if project and project["status"] == s else ("selected" if not project and s == "draft" else "")
    if project:
        asset_items = [f"<li><a href='/download?id={a['id']}'>{e(a['filename'])}</a><span>{a['size']//1024 + 1} KB</span></li>" for a in assets]
        asset_box = f"""<div class="upload-box" data-project-id="{project['id']}" data-csrf="{e(user['csrf'])}"><h3>Upload project photos, videos, or release files</h3><p>Add images, videos, ZIP files, PDF pitch decks, program files, or app releases. 70Scholar no longer adds an app upload limit for project files; your host/browser may still have practical limits.</p><input type="file" id="assetFile" accept="image/*,video/*,.zip,.pdf,.apk,.py,.js,.html,.css"><button class="ghost-button" type="button" id="uploadAsset">Upload file</button><p class="upload-status" id="uploadStatus"></p><ul class="clean-list asset-list">{''.join(asset_items) if asset_items else '<li>No uploaded files yet.</li>'}</ul></div>"""
    else:
        asset_box = "<div class='upload-box'><h3>Upload project photos, videos, or release files</h3><p>Save the project once, then reopen it to attach photos, videos, and files. 70Scholar does not add an app upload limit for project files.</p></div>"
    body = f"""<section class="page-hero compact"><p class="eyebrow">Builder workspace</p><h1>Draft, save, upload, publish.</h1><p>This is the authenticated place where a student can leave and return later.</p></section><section class="workspace-grid"><aside class="project-sidebar"><a href="/workspace" class="cta-primary slim full">+ New project</a><div class="side-list">{''.join(side) if side else '<p class="empty">Your drafts will appear here.</p>'}</div></aside><div class="builder-panel"><form method="post" action="/project/save" class="builder-form"><input type="hidden" name="csrf" value="{e(user['csrf'])}"><input type="hidden" name="project_id" value="{project['id'] if project else ''}"><div class="form-row"><label>Project title<input required name="title" value="{val('title')}" placeholder="Kinyarwanda Revision Cards App"></label><label>Category<input required name="category" value="{val('category')}" placeholder="AI, education, climate, fintech..."></label></div><label>Short summary<textarea required name="summary" rows="3" placeholder="Explain the problem, your solution, and who benefits.">{val('summary')}</textarea></label><label>Builder notes / pitch<textarea required name="details" rows="8" placeholder="Keep unfinished work here: milestones, pitch, application answers, budget, links, mentor feedback...">{val('details')}</textarea></label><p class="strong-description-note">Strong project descriptions should explain: problem, target users, your solution, current stage, what makes it different, how funding will be used, and what success looks like.</p><div class="form-row"><label>Funding goal (USD)<input type="number" min="0" step="1" name="goal_amount" value="{val('goal_amount','0') or '0'}"></label><label>Sale price / licence fee (USD)<input type="number" min="0" step="1" name="price" value="{val('price','0') or '0'}"></label></div><div class="form-row"><label>Demo URL<input name="demo_url" value="{val('demo_url')}" placeholder="https://..."></label><label>Code / project URL<input name="repo_url" value="{val('repo_url')}" placeholder="https://github.com/..."></label></div><div class="payout-section"><h3>Direct Mobile Money funding details</h3><p class="muted">Supporters will send money directly to the project creator. 70Scholar does not send project money to the platform owner's account.</p><div class="form-row"><label>Mobile Money account name<input name="mobile_money_name" value="{val('mobile_money_name')}" placeholder="Account holder name"></label><label>Mobile Money number<input name="mobile_money_number" value="{val('mobile_money_number')}" placeholder="+250..."></label></div><div class="form-row"><label>Network<select name="mobile_money_network"><option value="" {'selected' if not project or not project['mobile_money_network'] else ''}>Choose network</option><option value="MTN Mobile Money" {'selected' if project and project['mobile_money_network']=='MTN Mobile Money' else ''}>MTN Mobile Money</option><option value="Airtel Money" {'selected' if project and project['mobile_money_network']=='Airtel Money' else ''}>Airtel Money</option><option value="Other" {'selected' if project and project['mobile_money_network']=='Other' else ''}>Other</option></select></label><label>Funding instructions<input name="payout_notes" value="{val('payout_notes')}" placeholder="Example: Include project title in payment note"></label></div></div><label>Visibility<select name="status"><option value="draft" {selected('draft')}>Private draft</option><option value="public" {selected('public') or selected('pending_review')}>Submit for marketplace review</option></select></label><p class="muted">New public projects go to admin moderation first. After approval, sponsors and students can see them in the marketplace.</p><div class="form-actions"><button class="cta-primary" type="submit">Save project</button><a class="cta-secondary dark" href="/marketplace">View marketplace</a></div></form>{asset_box}</div></section>"""
    return page_shell("Workspace", body, user, "workspace")

def public_projects(conn):
    return conn.execute("SELECT p.*, u.name maker_name, COALESCE(SUM(pl.amount),0) pledged FROM projects p JOIN users u ON u.id=p.user_id LEFT JOIN pledges pl ON pl.project_id=p.id WHERE p.status='public' GROUP BY p.id ORDER BY p.updated_at DESC").fetchall()

def render_messages(user):
    with db() as conn:
        owned = conn.execute("""SELECT m.*, p.title, p.user_id AS owner_id
            FROM project_messages m JOIN projects p ON p.id=m.project_id
            WHERE p.user_id=? ORDER BY m.created_at DESC""", (user["id"],)).fetchall()
        sent = conn.execute("""SELECT m.*, p.title, p.user_id AS owner_id
            FROM project_messages m JOIN projects p ON p.id=m.project_id
            WHERE lower(m.email)=lower(?) AND p.user_id<>? ORDER BY m.created_at DESC""", (user["email"], user["id"])).fetchall()
    owned_items = ''.join([f"<li><strong>{e(m['name'])}</strong> asked about <a href='/project?id={m['project_id']}'>{e(m['title'])}</a><span>{e(m['email'])} · {e(m['created_at'][:10])}</span><p>{e(m['message'])}</p></li>" for m in owned])
    sent_items = ''.join([f"<li>You asked about <a href='/project?id={m['project_id']}'>{e(m['title'])}</a><span>{e(m['created_at'][:10])}</span><p>{e(m['message'])}</p></li>" for m in sent])
    body=f"""
    <section class='page-hero compact messages-hero'><p class='eyebrow'>Sponsor-builder chat</p><h1>Your project messages.</h1><p>See questions from sponsors about your projects, and track messages you sent to other builders.</p></section>
    <section class='messages-grid'>
      <div class='dash-panel'><h2>Inbox: sponsor questions for your projects</h2><ul class='clean-list message-list'>{owned_items if owned_items else '<li>No sponsor questions yet. Share your project page to start conversations.</li>'}</ul></div>
      <div class='dash-panel'><h2>Messages you sent</h2><ul class='clean-list message-list'>{sent_items if sent_items else '<li>You have not messaged a builder yet.</li>'}</ul></div>
    </section>"""
    return page_shell("Messages", body, user, "messages")

def render_marketplace(user):
    with db() as conn: projects = public_projects(conn)
    cards=[]
    for p in projects:
        goal=float(p["goal_amount"] or 0); pledged=float(p["pledged"] or 0); percent=min(100,int((pledged/goal)*100)) if goal else 0
        sale = f"<span class='sale-pill'>For sale: {money(p['price'])}</span>" if float(p["price"] or 0)>0 else ""
        cards.append(f"<article class='market-card'><div class='listing-top'><span class='tag'>{e(p['category'])}</span>{sale}</div><h3><a href='/project?id={p['id']}'>{e(p['title'])}</a></h3><p class='provider'>by {e(p['maker_name'])}</p><p>{e(p['summary'])}</p><div class='progress'><span style='width:{percent}%'></span></div><p class='progress-copy'>{money(pledged)} pledged of {money(goal)} goal</p><a class='cta-primary slim' href='/project?id={p['id']}'>Fund, buy, or view →</a><a class='ghost-button slim' href='/project?id={p['id']}#project-chat'>Chat with builder</a></article>")
    body=f"""<section class="page-hero compact marketplace-hero"><p class="eyebrow">Project marketplace</p><h1>Small projects deserve real backers.</h1><p>Students can publish apps, programs, prototypes, and research projects. Funders can pledge support; buyers can contact makers; mentors can discover what needs help.</p><a href="/workspace" class="cta-primary">Upload your project →</a></section><section class="panel-section"><div class="listing-grid market-grid">{''.join(cards) if cards else '<p class="empty">No public projects yet.</p>'}</div></section>"""
    return page_shell("Marketplace", body, user, "marketplace")

def render_project_detail(user, project_id):
    if not project_id.isdigit(): return page_shell("Project not found", "<section class='panel-section'><p>Project not found.</p></section>", user)
    with db() as conn:
        p = conn.execute("SELECT p.*, u.name maker_name, u.email maker_email, COALESCE(SUM(pl.amount),0) pledged FROM projects p JOIN users u ON u.id=p.user_id LEFT JOIN pledges pl ON pl.project_id=p.id WHERE p.id=? AND p.status='public' GROUP BY p.id", (int(project_id),)).fetchone()
        if not p: return page_shell("Project not found", "<section class='panel-section'><p>Project not found or not public.</p></section>", user)
        assets = conn.execute("SELECT * FROM assets WHERE project_id=? ORDER BY created_at DESC", (p["id"],)).fetchall()
        pledges = conn.execute("SELECT * FROM pledges WHERE project_id=? ORDER BY created_at DESC LIMIT 10", (p["id"],)).fetchall()
        messages = conn.execute("SELECT * FROM project_messages WHERE project_id=? ORDER BY created_at DESC LIMIT 20", (p["id"],)).fetchall()
    goal=float(p["goal_amount"] or 0); pledged=float(p["pledged"] or 0); percent=min(100,int((pledged/goal)*100)) if goal else 0
    asset_links = [f"<li><a href='/download?id={a['id']}'>{e(a['filename'])}</a><span>{a['size']//1024+1} KB</span></li>" for a in assets]
    media_cards = []
    for a in assets:
        src = f"/download?id={a['id']}&inline=1"
        if str(a['mime']).startswith('image/'):
            media_cards.append(f"<figure class='media-card'><img src='{src}' alt='{e(a['filename'])}'><figcaption>{e(a['filename'])}</figcaption></figure>")
        elif str(a['mime']).startswith('video/'):
            media_cards.append(f"<figure class='media-card'><video controls preload='metadata' src='{src}'></video><figcaption>{e(a['filename'])}</figcaption></figure>")
    media_gallery = f"<h2>Project showcase</h2><div class='media-gallery'>{''.join(media_cards)}</div>" if media_cards else "<h2>Project showcase</h2><p class='empty'>No photos or videos uploaded yet.</p>"
    message_items = [f"<li><strong>{e(m['name'])}</strong><span>{e(m['created_at'][:10])}</span><p>{e(m['message'])}</p></li>" for m in messages]
    message_form = f"""<section class='project-chat' id='project-chat'><h2>Talk to the builder</h2><p class='muted'>Ask about configuration, pricing, pilot testing, sponsorship details, or how the project works before funding it.</p><form method='post' action='/project/message' class='builder-form'><input type='hidden' name='project_id' value='{p['id']}'><label>Your name<input required name='name' value='{e(user['name']) if user else ''}'></label><label>Your email<input required type='email' name='email' value='{e(user['email']) if user else ''}'></label><label>Message<textarea required name='message' rows='4' placeholder='Example: Can you explain how this prototype will be configured for my school or organization?'></textarea></label><button class='cta-primary' type='submit'>Send message</button></form><ul class='clean-list message-list'>{''.join(message_items) if message_items else '<li>No sponsor questions yet. Start the conversation.</li>'}</ul></section>"""
    pledge_items = [f"<li><strong>{money(pl['amount'])}</strong> from {e(pl['name'])}<br><span>{e(pl['message'])}</span></li>" for pl in pledges]
    csrf = f"<input type='hidden' name='csrf' value='{e(user['csrf'])}'>" if user else ""
    login_note = "" if user else "<p class='muted'>You can pledge as a guest, or <a href='/login'>log in</a> to attach the pledge to your account.</p>"
    link_row = (f"<a class='ghost-button' target='_blank' rel='noopener' href='{e(p['demo_url'])}'>Open demo ↗</a>" if p['demo_url'] else '') + (f"<a class='ghost-button' target='_blank' rel='noopener' href='{e(p['repo_url'])}'>Code / project link ↗</a>" if p['repo_url'] else '') + (f"<a class='ghost-button' href='mailto:{e(p['maker_email'])}?subject=70Scholar project: {quote(p['title'])}'>Contact maker</a>" if float(p['price'] or 0)>0 else '')
    sale = f"<p class='sale-pill block'>Available for sale / licence: {money(p['price'])}</p>" if float(p['price'] or 0)>0 else ""
    payout_details = ""
    if p["mobile_money_number"]:
        payout_details = f"<div class='momo-box'><h3>Creator Mobile Money</h3><p>Send support directly to the creator. A {PLATFORM_FEE_PERCENT:.0f}% platform contribution is recorded to sponsor other student projects.</p><dl><div><dt>Account name</dt><dd>{e(p['mobile_money_name'])}</dd></div><div><dt>Network</dt><dd>{e(p['mobile_money_network'])}</dd></div><div><dt>Number</dt><dd>{e(p['mobile_money_number'])}</dd></div></dl><p class='muted'>{e(p['payout_notes']) if p['payout_notes'] else 'Use the project title as your payment reference.'}</p></div>"
    else:
        payout_details = "<div class='momo-box'><h3>Funding not activated</h3><p class='muted'>The creator has not added Mobile Money details yet.</p></div>"
    body=f"""<section class="project-detail"><div class="project-main"><span class="tag">{e(p['category'])}</span><h1>{e(p['title'])}</h1><p class="provider">by {e(p['maker_name'])}</p><p class="lead">{e(p['summary'])}</p><div class="rich-text">{e(p['details']).replace(chr(10),'<br>')}</div>{media_gallery}<div class="link-row">{link_row}</div><h2>Project files</h2><ul class="clean-list asset-list">{''.join(asset_links) if asset_links else '<li>No public release file uploaded yet.</li>'}</ul>{message_form}</div><aside class="fund-card"><h2>Fund this project</h2><div class="progress big"><span style="width:{percent}%"></span></div><p class="progress-copy"><strong>{money(pledged)}</strong> pledged of {money(goal)} goal</p>{sale}<form method="post" action="/pledge" class="pledge-form">{csrf}<input type="hidden" name="project_id" value="{p['id']}"><label>Name<input required name="name" value="{e(user['name']) if user else ''}"></label><label>Email<input required type="email" name="email" value="{e(user['email']) if user else ''}"></label><label>Pledge amount (USD)<input required type="number" min="1" step="1" name="amount" value="25"></label><label>Message<textarea name="message" rows="3" placeholder="I want to support testing, mentorship, buying, or rollout..."></textarea></label><label>Funding option<select name="provider"><option value="momo">Show creator Mobile Money details</option><option value="pledge_only">Record pledge only</option></select></label>{payout_details}<button class="cta-primary full" type="submit">Record support</button>{login_note}<p class="muted">70Scholar does not collect this money. Sponsors send funds directly to the project creator's Mobile Money account and can use the pledge as proof/record.</p></form><h3>Recent support</h3><ul class="clean-list pledge-list">{''.join(pledge_items) if pledge_items else '<li>No pledges yet. Be the first.</li>'}</ul></aside></section>"""
    return page_shell(p["title"], body, user, "marketplace")


def is_admin(user):
    """Only the single allowlisted owner email may ever use admin features."""
    return bool(user and user["role"] == "admin"
                and user["email"].strip().lower() in ADMIN_EMAIL_ALLOWLIST
                and user["email"].strip().lower() == OWNER_ADMIN_EMAIL)

def infer_type(title: str) -> str:
    t = title.lower()
    if "scholar" in t or "fellowship" in t: return "Scholarship"
    if "intern" in t or "trainee" in t: return "Internship"
    if "grant" in t or "fund" in t: return "Grant"
    if "hackathon" in t: return "Hackathon"
    if "competition" in t or "challenge" in t or "contest" in t: return "Competition"
    return "Opportunity"

def infer_deadline(text: str) -> str:
    clean = re.sub(r"(\d+)(st|nd|rd|th|md)\b", r"\1", text, flags=re.I)
    patterns = [
        r"(?:Application\s+)?Deadline:?\s*([A-Z][a-z]+\s+\d{1,2},\s*20\d{2})",
        r"(?:Application\s+)?Deadline:?\s*(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})",
        r"closes?\s+on\s+([A-Z][a-z]+\s+\d{1,2},\s*20\d{2})",
        r"by\s+([A-Z][a-z]+\s+\d{1,2},\s*20\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, clean, re.I)
        if m:
            raw = m.group(1).strip()
            for fmt in ("%B %d, %Y", "%d %B %Y"):
                try: return datetime.strptime(raw, fmt).date().isoformat()
                except ValueError: pass
    return "2026-12-31"

def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:700]

def sync_opportunities_from_feeds() -> tuple[int, str]:
    imported = 0; messages = []
    with db() as conn:
        for source in RSS_SOURCES:
            try:
                req = urllib.request.Request(source, headers={"User-Agent":"70ScholarBot/1.0"})
                data = urllib.request.urlopen(req, timeout=8).read()
                root = ET.fromstring(data)
                items = root.findall(".//item")[:12]
                source_count = 0
                for item in items:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or source).strip()
                    desc = strip_tags(item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or "")
                    if not title: continue
                    typ = infer_type(title)
                    deadline = infer_deadline(title + " " + desc)
                    provider = urlparse(link).netloc.replace("www.", "") or "Auto source"
                    cur = conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (typ,title,provider,"Global / verify","Students, youth, builders, or young professionals",deadline,link,desc or "Auto-imported opportunity. Verify eligibility and deadline on the source page.",typ.lower()+",auto-import",f"Auto RSS import from {source}",now_iso()))
                    if cur.rowcount: source_count += 1; imported += 1
                conn.execute("INSERT INTO sync_logs(source,imported,message,created_at) VALUES(?,?,?,?)", (source, source_count, "OK", now_iso()))
                messages.append(f"{source_count} from {source}")
            except Exception as ex:
                conn.execute("INSERT INTO sync_logs(source,imported,message,created_at) VALUES(?,?,?,?)", (source, 0, str(ex)[:300], now_iso()))
                messages.append(f"failed {source}: {ex}")
    return imported, "; ".join(messages)

def render_admin(user, msg=""):
    with db() as conn:
        stats = {
            "users": conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "unverified": conn.execute("SELECT COUNT(*) c FROM users WHERE email_verified=0").fetchone()["c"],
            "projects": conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"],
            "pending": conn.execute("SELECT COUNT(*) c FROM projects WHERE status='pending_review'").fetchone()["c"],
            "pledges": conn.execute("SELECT COALESCE(SUM(amount),0) c FROM pledges").fetchone()["c"],
        }
        users = conn.execute("SELECT id,name,email,role,email_verified,created_at FROM users ORDER BY id DESC LIMIT 12").fetchall()
        pending_projects = conn.execute("SELECT p.*, u.name maker_name, u.email maker_email FROM projects p JOIN users u ON u.id=p.user_id WHERE p.status='pending_review' ORDER BY p.updated_at DESC").fetchall()
        all_projects = conn.execute("SELECT p.id,p.title,p.status,p.updated_at,u.name maker_name FROM projects p JOIN users u ON u.id=p.user_id ORDER BY p.updated_at DESC LIMIT 12").fetchall()
        opps = conn.execute("SELECT * FROM opportunities ORDER BY created_at DESC LIMIT 8").fetchall()
        logs = conn.execute("SELECT * FROM sync_logs ORDER BY id DESC LIMIT 5").fetchall()
        pledges = conn.execute("SELECT pl.*, p.title FROM pledges pl JOIN projects p ON p.id=pl.project_id ORDER BY pl.id DESC LIMIT 8").fetchall()
        submissions = conn.execute("SELECT s.*, u.name submitter, u.email submitter_email FROM opportunity_submissions s JOIN users u ON u.id=s.user_id WHERE s.status='pending' ORDER BY s.id DESC LIMIT 20").fetchall()
        sources = conn.execute("SELECT * FROM feed_sources ORDER BY id").fetchall()
        fund = conn.execute("SELECT COALESCE(SUM(platform_fee),0) c FROM pledges WHERE status LIKE 'paid%'").fetchone()["c"]
        stats["platform_fund"] = fund
    cards = ''.join([f"<div class='stat-card'><span>{k.replace('_',' ').title()}</span><strong>{money(v) if k=='pledges' else e(v)}</strong></div>" for k,v in stats.items()])
    user_rows = ''
    for u in users:
        role_options = ''.join([f"<option value='{r}' {'selected' if u['role']==r else ''}>{r}</option>" for r in ['student','maker','moderator']])
        protected = 'disabled' if u['email'].lower() == OWNER_ADMIN_EMAIL else ''
        action_forms = f"<form method='post' action='/admin/user/action' class='table-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='user_id' value='{u['id']}'><button class='ghost-button' name='action' value='verify' type='submit'>Verify</button><button class='ghost-button' name='action' value='reset' type='submit'>Reset password</button><button class='ghost-button danger' name='action' value='delete' {protected} type='submit'>Delete</button></form>"
        user_rows += f"<tr><td>{u['id']}</td><td>{e(u['name'])}</td><td>{e(u['email'])}</td><td>{'Verified' if u['email_verified'] else 'Unverified'}</td><td><form method='post' action='/admin/user/role' class='table-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='user_id' value='{u['id']}'><select name='role' {protected}>{role_options}</select><button class='ghost-button' {protected} type='submit'>Save</button></form></td><td>{action_forms}</td></tr>"
    pending_rows = ''
    for p in pending_projects:
        pending_rows += f"<article class='mini-card moderation-card'><span class='tag'>Pending Review</span><h3>{e(p['title'])}</h3><p>{e(p['summary'])}</p><p class='provider'>by {e(p['maker_name'])} · {e(p['maker_email'])}</p><form method='post' action='/admin/project/action' class='card-actions'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='project_id' value='{p['id']}'><button name='action' value='approve' class='cta-primary slim'>Approve</button><button name='action' value='reject' class='ghost-button'>Reject</button></form></article>"
    project_rows = ''.join([f"<tr><td>{p['id']}</td><td>{e(p['title'])}</td><td>{e(p['maker_name'])}</td><td><span class='tag'>{e(p['status'].replace('_',' ').title())}</span></td><td>{e(p['updated_at'][:10])}</td><td><form method='post' action='/admin/project/action' class='table-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='project_id' value='{p['id']}'><button name='action' value='approve' class='ghost-button'>Public</button><button name='action' value='draft' class='ghost-button'>Draft</button><button name='action' value='reject' class='ghost-button'>Reject</button><button name='action' value='delete' class='ghost-button danger'>Delete</button></form></td></tr>" for p in all_projects])
    opp_rows = ''.join([f"<tr><td>{e(o['type'])}</td><td>{e(o['title'])}</td><td>{e(o['deadline'])}</td><td><a href='{e(o['url'])}' target='_blank'>source ↗</a></td><td><form method='post' action='/admin/opportunity/delete'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='opportunity_id' value='{o['id']}'><button class='ghost-button' type='submit'>Delete</button></form></td></tr>" for o in opps])
    log_rows = ''.join([f"<li><strong>{e(l['imported'])}</strong> imported from {e(l['source'])}<br><span>{e(l['message'])}</span></li>" for l in logs])
    pledge_rows = ''.join([f"<li><strong>{money(p['amount'])}</strong> for {e(p['title'])}<br><span>{e(p['name'])} · {e(p['status'])}</span></li>" for p in pledges])
    auto_on = get_setting("auto_sync", "0") == "1"
    toggle_html = f"""<form method='post' action='/admin/auto-sync' class='toggle-form'>
      <input type='hidden' name='csrf' value='{e(user['csrf'])}'>
      <input type='hidden' name='enabled' value='{'0' if auto_on else '1'}'>
      <button class='toggle-switch {'is-on' if auto_on else ''}' type='submit' aria-pressed='{'true' if auto_on else 'false'}'>
        <span class='toggle-knob'></span></button>
      <span class='toggle-label'>Auto-import is <strong>{'ON' if auto_on else 'OFF'}</strong></span></form>"""
    source_rows = ''.join([f"<li><span>{e(r['url'])}</span><form method='post' action='/admin/source/fetch' class='table-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='url' value='{e(r['url'])}'><button class='ghost-button' type='submit'>Fetch now</button></form><form method='post' action='/admin/source/delete' class='table-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='source_id' value='{r['id']}'><button class='ghost-button danger' type='submit'>Remove</button></form></li>" for r in sources])
    sub_rows = ''.join([f"<article class='mini-card moderation-card'><span class='tag'>{e(r['type'])}</span><h3>{e(r['title'])}</h3><p>{e(r['summary'])}</p><p class='provider'>by {e(r['submitter'])} · {e(r['submitter_email'])} · deadline {e(r['deadline'])}</p><p><a href='{e(r['url'])}' target='_blank' rel='noopener'>source ↗</a></p><form method='post' action='/admin/submission/action' class='card-actions'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='submission_id' value='{r['id']}'><button name='action' value='approve' class='cta-primary slim' type='submit'>Approve</button><button name='action' value='reject' class='ghost-button' type='submit'>Reject</button></form></article>" for r in submissions])
    body=f"""
    <section class='page-hero compact admin-hero'><p class='eyebrow'>Admin command center</p><h1>Manage users, opportunities, moderation, and growth.</h1><p>Review marketplace submissions, manage roles, import opportunities, and keep 70Scholar safe. Admin access is restricted to <strong>{OWNER_ADMIN_EMAIL}</strong>.</p></section>
    <section class='admin-grid'>
      <div class='stats-row'>{cards}</div>
      {flash(msg,'success') if msg else ''}
      <div class='dash-panel'><h2>Project moderation queue</h2><p class='muted'>Projects submitted for marketplace publication appear here first.</p><div class='mini-grid'>{pending_rows if pending_rows else '<p class="empty">No projects waiting for review.</p>'}</div></div>
      <div class='dash-panel admin-form'><h2>Add an opportunity manually</h2><form method='post' action='/admin/opportunity/add' class='builder-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><div class='form-row'><label>Type<select name='type'><option>Scholarship</option><option>Internship</option><option>Competition</option><option>Grant</option><option>Hackathon</option><option>Opportunity</option></select></label><label>Deadline<input required type='date' name='deadline'></label></div><label>Title<input required name='title'></label><div class='form-row'><label>Provider<input required name='provider'></label><label>Country / region<input required name='country' value='Global'></label></div><label>Level<input required name='level' value='Students / young builders'></label><label>Application URL<input required type='url' name='url'></label><label>Summary<textarea required name='summary' rows='4'></textarea></label><label>Tags<input name='tags' placeholder='ai,rwanda,climate'></label><button class='cta-primary' type='submit'>Post opportunity</button></form></div>
      <div class='dash-panel'><h2>Automatic opportunity posting</h2><p class='muted'>Imports latest RSS posts from configured opportunity sources. Admin should verify important deadlines.</p><form method='post' action='/admin/sync'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><button class='cta-primary' type='submit'>Sync opportunities now</button></form><ul class='clean-list'>{log_rows if log_rows else '<li>No syncs yet.</li>'}</ul></div>
      <div class='dash-panel'><h2>Community submissions</h2><p class='muted'>User-submitted opportunities stay private until you approve them.</p><div class='mini-grid'>{sub_rows if sub_rows else '<p class="empty">No submissions waiting for review.</p>'}</div></div>
      <div class='dash-panel'><h2>Auto-import &amp; source links</h2><p class='muted'>Turn on auto-import to refresh saved links every 30 minutes, or fetch any link immediately.</p>{toggle_html}
        <form method='post' action='/admin/source/add' class='builder-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><label>Add a feed or webpage link<input name='url' type='url' placeholder='https://example.com/feed' required></label><button class='cta-primary slim' type='submit'>Save link</button></form>
        <form method='post' action='/admin/source/fetch' class='builder-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><label>Fetch a one-off link<input name='url' type='url' placeholder='https://example.com/opportunities' required></label><button class='ghost-button' type='submit'>Fetch now</button></form>
        <ul class='clean-list admin-source-list'>{source_rows if source_rows else '<li>No saved sources.</li>'}</ul></div>
      <div class='dash-panel'><h2>User controls</h2><div class='table-wrap'><table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Email</th><th>Role</th><th>Actions</th></tr></thead><tbody>{user_rows}</tbody></table></div></div>
      <div class='dash-panel'><h2>Recent projects</h2><div class='table-wrap'><table><thead><tr><th>ID</th><th>Title</th><th>Maker</th><th>Status</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{project_rows}</tbody></table></div></div>
      <div class='dash-panel'><h2>Newest opportunities</h2><div class='table-wrap'><table><thead><tr><th>Type</th><th>Title</th><th>Deadline</th><th>Link</th><th>Action</th></tr></thead><tbody>{opp_rows}</tbody></table></div></div>
      <div class='dash-panel'><h2>Recent funding</h2><ul class='clean-list'>{pledge_rows if pledge_rows else '<li>No pledges yet.</li>'}</ul></div>
    </section>"""
    return page_shell("Admin", body, user, "admin")

def render_payment_setup(user, pledge, provider, checkout_url=""):
    ref = f"EDB-{pledge['id']}-{secrets.token_hex(3).upper()}"
    if checkout_url:
        joiner = '&' if '?' in checkout_url else '?'
        return checkout_url + joiner + urlencode({"amount": str(pledge["amount"]), "email": pledge["email"], "reference": ref})
    fee = round(float(pledge["amount"]) * PLATFORM_FEE_PERCENT / 100.0, 2)
    if provider == 'momo':
        instructions = f"Send {money(pledge['amount'])} to {pledge['mobile_money_name']} on {pledge['mobile_money_network']} using number {pledge['mobile_money_number']}. Reference: {ref}. {pledge['payout_notes'] or 'Use the project title in the payment note.'} A {PLATFORM_FEE_PERCENT:.0f}% platform contribution ({money(fee)}) is recorded for the 70Scholar Future Fund; the creator receives {money(float(pledge['amount']) - fee)}."
    else:
        instructions = "This provider is disabled for now. 70Scholar is configured for direct creator Mobile Money funding so money does not go to the platform owner."
    body = f"""<section class='auth-wrap'><div class='auth-card payment-card'><p class='eyebrow eyebrow-dark'>Direct creator payment</p><h1>{e(provider.title())} support</h1><p>You recorded a pledge of <strong>{money(pledge['amount'])}</strong> for <strong>{e(pledge['title'])}</strong>.</p><p class='muted'>Reference: <strong>{e(ref)}</strong></p><div class='rich-text'>{e(instructions)}</div><a class='cta-primary full' href='/payment/success?pledge_id={pledge['id']}'>I have sent it / mark paid in demo</a><a class='ghost-button full' href='/project?id={pledge['project_id']}'>Back to project</a></div></section>"""
    return page_shell("Payment setup", body, user)

class ScholarHandler(BaseHTTPRequestHandler):
    server_version = "70ScholarMVP/1.0"
    def log_message(self, fmt, *args): sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))
    def parse_cookies(self):
        c = cookies.SimpleCookie(); raw = self.headers.get("Cookie")
        if raw: c.load(raw)
        return c
    def current_user(self):
        morsel = self.parse_cookies().get(SESSION_COOKIE)
        if not morsel: return None
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
            return conn.execute("SELECT u.*, s.csrf, s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at > ?", (token_hash(morsel.value), now_iso())).fetchone()
    def send_html(self, text, status=200, headers=None):
        data=text.encode(); self.send_response(status); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("X-Content-Type-Options","nosniff")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)
    def send_json(self, payload, status=200):
        data=json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def send_plain(self, text, content_type="text/plain"):
        data=text.encode(); self.send_response(200); self.send_header("Content-Type", content_type + "; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def build_sitemap(self):
        host = self.headers.get("Host", "localhost:8080")
        base = "https://" + host if "localhost" not in host and "127.0.0.1" not in host else "http://" + host
        urls = ["/", "/opportunities", "/marketplace", "/signup", "/login"]
        items = "".join([f"<url><loc>{base}{u}</loc></url>" for u in urls])
        return "<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + items + "</urlset>"
    def redirect(self, loc, headers=None):
        self.send_response(303); self.send_header("Location", loc)
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers()
    def read_body(self):
        return self.rfile.read(int(self.headers.get("Content-Length","0") or 0))
    def read_form(self):
        return {k:v[0] for k,v in parse_qs(self.read_body().decode(errors="replace"), keep_blank_values=True).items()}
    def require_user(self):
        user = self.current_user()
        if not user:
            dest = self.path if self.path.startswith("/") else "/"
            self.redirect("/login?next=" + quote(dest, safe="/?=&"))
            return None
        return user

    def gate(self, user) -> bool:
        """Return True when the request may proceed; otherwise send a login redirect."""
        if user: return True
        dest = self.path if self.path.startswith("/") else "/"
        self.redirect("/login?next=" + quote(dest, safe="/?=&"))
        return False
    def verify_csrf(self, user, form=None):
        if not user: return False
        sent = form.get("csrf", "") if form is not None else self.headers.get("X-CSRF-Token", "")
        return secrets.compare_digest(sent, user["csrf"])
    def do_HEAD(self):
        # Render and other hosts use HEAD requests for health checks.
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path; query=parse_qs(parsed.query); user=self.current_user()
        if path == "/robots.txt": return self.send_plain("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", "text/plain")
        if path == "/sitemap.xml": return self.send_plain(self.build_sitemap(), "application/xml")
        if path == "/version": return self.send_plain(f"70Scholar {APP_VERSION} - bigger brand, single-owner admin, NESA photo gallery", "text/plain")
        if path.startswith("/uploads/profiles/"): return self.serve_profile_upload(path)
        if path.startswith("/static/"): return self.serve_static(path)
        if path.startswith("/uploads/profiles/"): return self.serve_profile_upload(path)
        if path not in PUBLIC_GET_PATHS and not self.gate(user): return None
        if path == "/download": return self.serve_download(query, user)
        if path == "/": return self.send_html(render_home(user))
        if path == "/signup": return self.send_html(render_auth("signup"))
        if path == "/login": return self.send_html(render_auth("login", next_url=query.get("next", [""])[0]))
        if path == "/verify-email": return self.handle_verify_email(query)
        if path == "/forgot-password": return self.send_html(render_forgot_password())
        if path == "/reset-password": return self.send_html(render_reset_password(query.get("token", [""])[0]))
        if path == "/opportunities": return self.send_html(render_opportunities(user, query))
        if path == "/courses": return self.send_html(render_courses(user))
        if path == "/exams": return self.send_html(render_exams(user))
        if path == "/submit": return self.send_html(render_submit(user))
        if path == "/dashboard":
            user=self.require_user(); return None if not user else self.send_html(render_dashboard(user))
        if path == "/account":
            user=self.require_user(); return None if not user else self.send_html(render_account(user))
        if path == "/messages":
            user=self.require_user(); return None if not user else self.send_html(render_messages(user))
        if path == "/workspace":
            user=self.require_user(); return None if not user else self.send_html(render_workspace(user, query))
        if path == "/admin":
            user=self.require_user();
            if not user: return None
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'><h1>Admin only</h1></section>", user), 403)
            return self.send_html(render_admin(user))
        if path == "/payment/start": return self.handle_payment_start(user, query)
        if path == "/payment/success": return self.handle_payment_success(user, query)
        if path == "/marketplace": return self.send_html(render_marketplace(user))
        if path == "/project": return self.send_html(render_project_detail(user, query.get("id", [""])[0]))
        return self.send_html(page_shell("Not found", "<section class='panel-section'><h1>Page not found</h1></section>", user), 404)
    def serve_static(self, path):
        target=(STATIC_DIR / path.removeprefix("/static/")).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists(): self.send_response(404); self.end_headers(); return
        data=target.read_bytes(); self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def serve_profile_upload(self, path):
        rel = path.removeprefix("/uploads/profiles/")
        target = (UPLOAD_DIR / "profiles" / rel).resolve()
        base = (UPLOAD_DIR / "profiles").resolve()
        if not str(target).startswith(str(base)) or not target.exists():
            self.send_response(404); self.end_headers(); return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def serve_download(self, query, user):
        asset_id=query.get("id", [""])[0]
        if not asset_id.isdigit(): self.send_response(404); self.end_headers(); return
        with db() as conn:
            asset=conn.execute("SELECT a.*, p.status, p.user_id owner_id FROM assets a JOIN projects p ON p.id=a.project_id WHERE a.id=?", (int(asset_id),)).fetchone()
        if not asset or (asset["status"] != "public" and (not user or user["id"] != asset["owner_id"])): self.send_response(403 if asset else 404); self.end_headers(); return
        path=Path(asset["stored_path"])
        if not path.exists(): self.send_response(404); self.end_headers(); return
        data=path.read_bytes(); self.send_response(200); self.send_header("Content-Type", asset["mime"] or "application/octet-stream"); self.send_header("Content-Length", str(len(data))); disposition = "inline" if query.get("inline") else "attachment"; self.send_header("Content-Disposition", f"{disposition}; filename=\"{asset['filename']}\""); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        path=urlparse(self.path).path; user=self.current_user()
        if path not in PUBLIC_POST_PATHS and not self.gate(user): return None
        if path == "/signup": return self.handle_signup(self.read_form())
        if path == "/login": return self.handle_login(self.read_form())
        if path == "/forgot-password": return self.handle_forgot_password(self.read_form())
        if path == "/reset-password": return self.handle_reset_password(self.read_form())
        if path == "/account/name":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_account_name(user, form)
        if path == "/account/password":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_account_password(user, form)
        if path == "/api/profile-photo": return self.handle_profile_photo(user)
        if path == "/logout":
            form=self.read_form()
            if user and self.verify_csrf(user, form):
                morsel=self.parse_cookies().get(SESSION_COOKIE)
                if morsel:
                    with db() as conn: conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(morsel.value),))
            return self.redirect("/", {"Set-Cookie":f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"})
        if path == "/bookmark":
            form=self.read_form()
            if not user: return self.redirect("/login")
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            oid=form.get("opportunity_id", "")
            if oid.isdigit():
                with db() as conn:
                    if conn.execute("SELECT 1 FROM bookmarks WHERE user_id=? AND opportunity_id=?", (user["id"], int(oid))).fetchone(): conn.execute("DELETE FROM bookmarks WHERE user_id=? AND opportunity_id=?", (user["id"], int(oid)))
                    else: conn.execute("INSERT OR IGNORE INTO bookmarks(user_id,opportunity_id,created_at) VALUES(?,?,?)", (user["id"], int(oid), now_iso()))
            return self.redirect("/opportunities")
        if path == "/project/save":
            form=self.read_form()
            if not user: return self.redirect("/login")
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_project_save(user, form)
        if path == "/admin/opportunity/add":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_admin_add_opportunity(user, form)
        if path == "/admin/sync":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            imported, message = sync_opportunities_from_feeds(); return self.send_html(render_admin(user, f"Imported {imported} opportunities. {message}"))
        if path == "/admin/project/action":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_admin_project_action(user, form)
        if path == "/admin/user/role":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Owner admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_admin_user_role(user, form)
        if path == "/admin/user/action":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Owner admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_admin_user_action(user, form)
        if path == "/opportunity/submit":
            form=self.read_form()
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_opportunity_submission(user, form)
        if path == "/course/enrol":
            form=self.read_form()
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_course_enrol(user, form)
        if path == "/admin/submission/action":
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "Owner admin only.", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            return self.handle_submission_action(user, form)
        if path == "/admin/auto-sync":
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "Owner admin only.", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            on = "1" if form.get("enabled") == "1" else "0"
            set_setting("auto_sync", on)
            if on == "1": set_setting("auto_sync_last", "0")
            return self.send_html(render_admin(user, f"Auto-import {'enabled' if on == '1' else 'disabled'}."))
        if path == "/admin/source/add":
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "Owner admin only.", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            url=(form.get("url") or "").strip()
            if urlparse(url).scheme not in ("http","https"):
                return self.send_html(render_admin(user, "Enter a valid http or https link."), 400)
            with db() as conn:
                conn.execute("INSERT OR IGNORE INTO feed_sources(url,added_at) VALUES(?,?)", (url, now_iso()))
            return self.send_html(render_admin(user, "Source link saved. Use 'Fetch now' to import its listings."))
        if path == "/admin/source/fetch":
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "Owner admin only.", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            url=(form.get("url") or form.get("source") or "").strip()
            if urlparse(url).scheme not in ("http","https"):
                return self.send_html(render_admin(user, "Enter a valid http or https link."), 400)
            try:
                items=fetch_feed_items(url)
                added=import_feed_items(items, url)
                return self.send_html(render_admin(user, f"Fetched {len(items)} items; imported {added} new listings from your link."))
            except Exception as ex:
                return self.send_html(render_admin(user, f"Could not fetch that link: {str(ex)[:160]}"), 400)
        if path == "/admin/source/delete":
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "Owner admin only.", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            if form.get("source_id","").isdigit():
                with db() as conn: conn.execute("DELETE FROM feed_sources WHERE id=?", (int(form["source_id"]),))
            return self.send_html(render_admin(user, "Source removed."))
        if path == "/admin/opportunity/delete":
            form=self.read_form();
            if not user: return self.redirect("/login")
            if not is_admin(user): return self.send_html(page_shell("Forbidden", "<section class='panel-section'>Admin only.</section>", user), 403)
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
            return self.handle_admin_delete_opportunity(user, form)
        if path == "/project/message": return self.handle_project_message(user, self.read_form())
        if path == "/pledge": return self.handle_pledge(user, self.read_form())
        if path == "/api/upload": return self.handle_upload(user)
        return self.send_html(page_shell("Not found", "<section class='panel-section'><h1>Page not found</h1></section>", user), 404)
    def consume_email_token(self, token, purpose):
        if not token: return None
        th = token_hash(token)
        with db() as conn:
            row = conn.execute("SELECT * FROM email_tokens WHERE token_hash=? AND purpose=? AND used_at='' AND expires_at > ?", (th, purpose, now_iso())).fetchone()
            if not row: return None
            conn.execute("UPDATE email_tokens SET used_at=? WHERE id=?", (now_iso(), row["id"]))
            return row
    def handle_verify_email(self, query):
        row = self.consume_email_token(query.get("token", [""])[0], "verify_email")
        if not row:
            return self.send_html(render_notice("Verification failed", "That verification link is invalid or expired."), 400)
        with db() as conn:
            conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (row["user_id"],))
        return self.send_html(render_notice("Email verified", "Your email has been verified. You can now log in."))
    def handle_forgot_password(self, form):
        email=form.get("email","").strip().lower()
        with db() as conn:
            user=conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user:
            send_password_reset_email(user["id"], user["email"], user["name"])
        return self.send_html(render_forgot_password("If that account exists, a reset link has been sent."))
    def handle_reset_password(self, form):
        token=form.get("token",""); password=form.get("password","")
        if len(password)<8: return self.send_html(render_reset_password(token, "Password must be at least 8 characters."), 400)
        row=self.consume_email_token(token, "password_reset")
        if not row: return self.send_html(render_notice("Reset failed", "That password reset link is invalid or expired."), 400)
        salt, hashed=hash_password(password)
        with db() as conn:
            conn.execute("UPDATE users SET salt=?, password_hash=? WHERE id=?", (salt, hashed, row["user_id"]))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
        return self.send_html(render_notice("Password reset", "Your password has been updated. Please log in with the new password."))
    def create_session_and_redirect(self, email, location):
        token=secrets.token_urlsafe(36); csrf=secrets.token_urlsafe(24); expires=datetime.now(timezone.utc)+timedelta(days=14)
        with db() as conn:
            uid=conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
            conn.execute("INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES(?,?,?,?,?)", (token_hash(token),uid,csrf,now_iso(),expires.isoformat(timespec="seconds")))
        self.redirect(location, {"Set-Cookie":f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={14*24*60*60}"})
    def handle_signup(self, form):
        name=form.get("name","").strip(); email=form.get("email","").strip().lower(); password=form.get("password","")
        if len(name)<2 or "@" not in email or len(password)<8: return self.send_html(render_auth("signup", "Use a real name, valid email, and password of at least 8 characters."), 400)
        salt, hashed=hash_password(password)
        try:
            with db() as conn:
                cur=conn.execute("INSERT INTO users(name,email,password_hash,salt,role,email_verified,created_at) VALUES(?,?,?,?,?,?,?)", (name,email,hashed,salt,"student",0,now_iso()))
                user_id=cur.lastrowid
            send_verification_email(user_id, email, name)
        except sqlite3.IntegrityError: return self.send_html(render_auth("signup", "That email already has an account."), 409)
        return self.send_html(render_notice("Check your email", "We created your account. Please verify your email address before logging in."))
    def handle_login(self, form):
        email=form.get("email","").strip().lower(); password=form.get("password","")
        with db() as conn: user=conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not verify_password(password, user["salt"], user["password_hash"]): return self.send_html(render_auth("login", "Incorrect email or password."), 401)
        if not user["email_verified"]:
            try: send_verification_email(user["id"], user["email"], user["name"])
            except Exception: pass
            return self.send_html(render_auth("login", "Please verify your email first. We sent a new verification link."), 403)
        nxt = (form.get("next") or "").strip()
        if not (nxt.startswith("/") and not nxt.startswith("//")): nxt = "/dashboard"
        return self.create_session_and_redirect(email, nxt)
    def handle_account_name(self, user, form):
        name=form.get("name","").strip()[:120]
        if len(name) < 2:
            return self.send_html(render_account(user, "Name is too short."), 400)
        with db() as conn:
            conn.execute("UPDATE users SET name=? WHERE id=?", (name, user["id"]))
        fresh=self.current_user()
        return self.send_html(render_account(fresh, "Account name updated."))
    def handle_account_password(self, user, form):
        current=form.get("current_password",""); new=form.get("new_password","")
        if len(new) < 8:
            return self.send_html(render_account(user, "New password must be at least 8 characters."), 400)
        with db() as conn:
            row=conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
            if not row or not verify_password(current, row["salt"], row["password_hash"]):
                return self.send_html(render_account(user, "Current password is incorrect."), 400)
            salt, hashed=hash_password(new)
            conn.execute("UPDATE users SET salt=?, password_hash=? WHERE id=?", (salt, hashed, user["id"]))
            # Keep current session, remove other sessions for safety.
            morsel=self.parse_cookies().get(SESSION_COOKIE)
            current_hash=token_hash(morsel.value) if morsel else ""
            conn.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user["id"], current_hash))
        return self.send_html(render_account(user, "Password updated."))
    def handle_profile_photo(self, user):
        if not user: return self.send_json({"ok":False,"error":"Login required"}, 401)
        if not self.verify_csrf(user): return self.send_json({"ok":False,"error":"CSRF check failed"}, 403)
        try:
            payload=json.loads(self.read_body().decode())
            filename=slugify_filename(payload.get("filename","profile.jpg"))
            mime=str(payload.get("mime") or mimetypes.guess_type(filename)[0] or "image/jpeg")[:120]
            data=payload.get("data","")
            data=data.split(",",1)[1] if "," in data else data
            content=base64.b64decode(data, validate=True)
        except Exception:
            return self.send_json({"ok":False,"error":"Invalid image"}, 400)
        if not mime.startswith("image/"):
            return self.send_json({"ok":False,"error":"Profile photo must be an image"}, 400)
        if len(content) > 10 * 1024 * 1024:
            return self.send_json({"ok":False,"error":"Profile photo max is 10 MB"}, 400)
        profile_dir=UPLOAD_DIR / "profiles"; profile_dir.mkdir(parents=True, exist_ok=True)
        ext=Path(filename).suffix.lower() or ".jpg"
        stored=profile_dir / f"user-{user['id']}-{secrets.token_hex(8)}{ext}"
        stored.write_bytes(content)
        url=f"/uploads/profiles/{stored.name}"
        with db() as conn:
            conn.execute("UPDATE users SET profile_photo_url=? WHERE id=?", (url, user["id"]))
        return self.send_json({"ok":True,"url":url})
    def handle_project_save(self, user, form):
        title=form.get("title","").strip()[:160]; category=form.get("category","").strip()[:80]; summary=form.get("summary","").strip()[:600]; details=form.get("details","").strip()[:10000]
        if not title or not category or not summary or not details: return self.redirect("/workspace")
        requested_public = form.get("status") == "public"
        status = "public" if (requested_public and is_admin(user)) else ("pending_review" if requested_public else "draft")
        try: goal=max(0,float(form.get("goal_amount") or 0)); price=max(0,float(form.get("price") or 0))
        except Exception: goal=price=0
        demo=form.get("demo_url","").strip()[:500]; repo=form.get("repo_url","").strip()[:500]; momo_name=form.get("mobile_money_name","").strip()[:120]; momo_number=form.get("mobile_money_number","").strip()[:60]; momo_network=form.get("mobile_money_network","").strip()[:80]; payout_notes=form.get("payout_notes","").strip()[:300]; pid=form.get("project_id","")
        if requested_public and (len(summary) < 40 or len(details) < 120):
            return self.send_html(page_shell("Stronger description needed", "<section class='panel-section'><h1>Make your project description stronger</h1><p>Before submitting for marketplace review, add at least 40 characters in the summary and 120 characters in the full builder notes. Explain the problem, solution, users, current stage, and what support you need.</p><p><a class='cta-primary' href='/workspace'>Back to workspace</a></p></section>", user), 400)
        if requested_public and (not momo_name or not momo_number or not momo_network):
            return self.send_html(page_shell("Payout details needed", "<section class='panel-section'><h1>Add Mobile Money details first</h1><p>To publish a project for funding, enter the creator's Mobile Money name, number, and network so sponsors can pay the creator directly.</p><p><a class='cta-primary' href='/workspace'>Back to workspace</a></p></section>", user), 400)
        with db() as conn:
            if pid.isdigit() and conn.execute("SELECT id FROM projects WHERE id=? AND user_id=?", (int(pid),user["id"])).fetchone():
                conn.execute("UPDATE projects SET title=?,category=?,summary=?,details=?,goal_amount=?,price=?,demo_url=?,repo_url=?,mobile_money_name=?,mobile_money_number=?,mobile_money_network=?,payout_notes=?,status=?,updated_at=? WHERE id=? AND user_id=?", (title,category,summary,details,goal,price,demo,repo,momo_name,momo_number,momo_network,payout_notes,status,now_iso(),int(pid),user["id"]))
                return self.redirect(f"/workspace?edit={pid}")
            cur=conn.execute("INSERT INTO projects(user_id,title,category,summary,details,goal_amount,price,demo_url,repo_url,mobile_money_name,mobile_money_number,mobile_money_network,payout_notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (user["id"],title,category,summary,details,goal,price,demo,repo,momo_name,momo_number,momo_network,payout_notes,status,now_iso(),now_iso()))
            return self.redirect(f"/workspace?edit={cur.lastrowid}")
    def handle_project_message(self, user, form):
        pid=form.get("project_id",""); name=form.get("name","").strip()[:120]; email=form.get("email","").strip()[:180]; message=form.get("message","").strip()[:1200]
        if not pid.isdigit() or not name or "@" not in email or len(message) < 10:
            return self.redirect(f"/project?id={pid}")
        with db() as conn:
            project=conn.execute("SELECT id FROM projects WHERE id=? AND status='public'", (int(pid),)).fetchone()
            if not project: return self.redirect("/marketplace")
            conn.execute("INSERT INTO project_messages(project_id,user_id,name,email,message,created_at) VALUES(?,?,?,?,?,?)", (int(pid), user["id"] if user else None, name, email, message, now_iso()))
        return self.redirect(f"/project?id={pid}")
    def handle_pledge(self, user, form):
        if user and not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "<section class='panel-section'>CSRF check failed.</section>", user), 403)
        pid=form.get("project_id",""); name=form.get("name","").strip()[:120]; email=form.get("email","").strip()[:180]; msg=form.get("message","").strip()[:600]
        try: amount=max(1,float(form.get("amount") or 0))
        except Exception: amount=0
        if not pid.isdigit() or not name or "@" not in email or amount<=0: return self.redirect(f"/project?id={pid}")
        provider = form.get("provider", "pledge_only")
        status = "pledged" if provider == "pledge_only" else "payment_pending"
        with db() as conn:
            project = conn.execute("SELECT id,mobile_money_number FROM projects WHERE id=? AND status='public'", (int(pid),)).fetchone()
            if not project: return self.redirect("/marketplace")
            if provider == "momo" and not project["mobile_money_number"]:
                provider = "pledge_only"; status = "pledged"
            fee = round(amount * PLATFORM_FEE_PERCENT / 100.0, 2)
            cur = conn.execute("INSERT INTO pledges(project_id,user_id,name,email,amount,message,status,created_at,platform_fee,creator_amount) VALUES(?,?,?,?,?,?,?,?,?,?)", (int(pid), user["id"] if user else None, name, email, amount, msg, status, now_iso(), fee, round(amount - fee, 2)))
            pledge_id = cur.lastrowid
        if provider != "pledge_only": return self.redirect(f"/payment/start?pledge_id={pledge_id}&provider={provider}")
        return self.redirect(f"/project?id={pid}")

    def handle_admin_add_opportunity(self, user, form):
        fields = {k: form.get(k, "").strip() for k in ["type","title","provider","country","level","deadline","url","summary","tags"]}
        if not all(fields[k] for k in ["type","title","provider","country","level","deadline","url","summary"]):
            return self.send_html(render_admin(user, "Please complete all required opportunity fields."), 400)
        try:
            with db() as conn:
                conn.execute("""INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (fields["type"],fields["title"],fields["provider"],fields["country"],fields["level"],fields["deadline"],fields["url"],fields["summary"],fields["tags"],"Admin posted",now_iso()))
        except sqlite3.IntegrityError:
            return self.send_html(render_admin(user, "That opportunity title already exists."), 409)
        return self.send_html(render_admin(user, "Opportunity posted successfully."))
    def handle_admin_project_action(self, user, form):
        pid=form.get("project_id",""); action=form.get("action","")
        if not pid.isdigit() or action not in ("approve","reject","draft","delete"):
            return self.send_html(render_admin(user, "Invalid moderation action."), 400)
        with db() as conn:
            if action == "delete":
                conn.execute("DELETE FROM projects WHERE id=?", (int(pid),))
            else:
                status = {"approve":"public", "reject":"rejected", "draft":"draft"}[action]
                conn.execute("UPDATE projects SET status=?, updated_at=? WHERE id=?", (status, now_iso(), int(pid)))
                conn.execute("INSERT INTO moderation_logs(project_id,admin_id,action,note,created_at) VALUES(?,?,?,?,?)", (int(pid), user["id"], action, form.get("note","")[:300], now_iso()))
        return self.send_html(render_admin(user, f"Project {action} action completed."))
    def handle_admin_user_role(self, user, form):
        uid=form.get("user_id",""); role=form.get("role","")
        if not uid.isdigit() or role not in ("student","maker","moderator") or role == "admin":
            return self.send_html(render_admin(user, "Invalid role update. Admin role is reserved for the owner account only."), 400)
        with db() as conn:
            target=conn.execute("SELECT email FROM users WHERE id=?", (int(uid),)).fetchone()
            if not target or target["email"].lower() == OWNER_ADMIN_EMAIL:
                return self.send_html(render_admin(user, "Owner admin role cannot be changed."), 400)
            conn.execute("UPDATE users SET role=? WHERE id=?", (role, int(uid)))
        return self.send_html(render_admin(user, "User role updated."))
    def handle_admin_user_action(self, user, form):
        uid=form.get("user_id",""); action=form.get("action","")
        if not uid.isdigit() or action not in ("verify","reset","delete"):
            return self.send_html(render_admin(user, "Invalid user action."), 400)
        with db() as conn:
            target=conn.execute("SELECT * FROM users WHERE id=?", (int(uid),)).fetchone()
            if not target:
                return self.send_html(render_admin(user, "User not found."), 404)
            if target["email"].lower() == OWNER_ADMIN_EMAIL and action == "delete":
                return self.send_html(render_admin(user, "Owner admin account cannot be deleted."), 400)
            if action == "verify":
                conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (int(uid),))
                return self.send_html(render_admin(user, "User email marked as verified."))
            if action == "reset":
                temp = "Temp" + secrets.token_urlsafe(8).replace("-", "A").replace("_", "B")[:10] + "!"
                salt, hashed = hash_password(temp)
                conn.execute("UPDATE users SET salt=?, password_hash=? WHERE id=?", (salt, hashed, int(uid)))
                conn.execute("DELETE FROM sessions WHERE user_id=?", (int(uid),))
                return self.send_html(render_admin(user, f"Temporary password for {target['email']}: {temp}"))
            if action == "delete":
                conn.execute("DELETE FROM users WHERE id=?", (int(uid),))
                return self.send_html(render_admin(user, "User deleted."))
        return self.send_html(render_admin(user, "Action complete."))
    def handle_opportunity_submission(self, user, form):
        title=(form.get("title") or "").strip()[:200]
        url=(form.get("url") or "").strip()[:500]
        summary=(form.get("summary") or "").strip()[:1200]
        if not title or not summary or urlparse(url).scheme not in ("http","https"):
            return self.send_html(render_submit(user, "Please provide a title, summary and a valid https link.", "error"), 400)
        with db() as conn:
            conn.execute("""INSERT INTO opportunity_submissions(user_id,type,title,provider,country,level,deadline,url,summary,tags,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user["id"], (form.get("type") or "Opportunity")[:80], title,
                 (form.get("provider") or "Community")[:160], (form.get("country") or "Global / verify")[:100],
                 (form.get("level") or "Students")[:160], (form.get("deadline") or "See official page")[:80],
                 url, summary, (form.get("tags") or "")[:200], "pending", now_iso()))
        return self.send_html(render_submit(user, "Submitted! The admin will review it before it goes public."))

    def handle_course_enrol(self, user, form):
        key=(form.get("course_key") or "").strip()[:160]
        kind=(form.get("kind") or "course").strip()[:20]
        if kind not in ("course","exam"): kind="course"
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO course_enrolments(user_id,course_key,kind,created_at) VALUES(?,?,?,?)",
                         (user["id"], key, kind, now_iso()))
        msg="You're enrolled. Watch your dashboard for study materials."
        return self.send_html(render_courses(user, msg) if kind=="course" else render_exams(user, msg))

    def handle_submission_action(self, user, form):
        sid=form.get("submission_id",""); action=form.get("action","")
        if not sid.isdigit() or action not in ("approve","reject"):
            return self.send_html(render_admin(user, "Invalid submission action."), 400)
        with db() as conn:
            row=conn.execute("SELECT * FROM opportunity_submissions WHERE id=?", (int(sid),)).fetchone()
            if not row: return self.send_html(render_admin(user, "Submission not found."), 404)
            if action == "approve":
                cur=conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (row["type"], row["title"], row["provider"], row["country"], row["level"], row["deadline"],
                     row["url"], row["summary"], row["tags"], "community", now_iso()))
                if cur.rowcount:
                    conn.execute("UPDATE opportunities SET auto_description=? WHERE id=?",
                        (make_auto_description({"type":row["type"],"title":row["title"],"provider":row["provider"],
                          "country":row["country"],"level":row["level"],"deadline":row["deadline"],"summary":row["summary"]}), cur.lastrowid))
                conn.execute("UPDATE opportunity_submissions SET status='approved', reviewed_at=? WHERE id=?", (now_iso(), int(sid)))
                return self.send_html(render_admin(user, f"Approved and published: {row['title']}"))
            conn.execute("UPDATE opportunity_submissions SET status='rejected', reviewed_at=? WHERE id=?", (now_iso(), int(sid)))
        return self.send_html(render_admin(user, "Submission rejected."))

    def handle_admin_delete_opportunity(self, user, form):
        oid=form.get("opportunity_id","")
        if oid.isdigit():
            with db() as conn:
                conn.execute("DELETE FROM opportunities WHERE id=?", (int(oid),))
        return self.send_html(render_admin(user, "Opportunity deleted."))
    def handle_payment_start(self, user, query):
        pledge_id = query.get("pledge_id", [""])[0]; provider = query.get("provider", ["pledge_only"])[0]
        if provider not in PAYMENT_LINKS and provider != "momo": provider = "pledge_only"
        if not pledge_id.isdigit(): return self.redirect("/marketplace")
        with db() as conn:
            pledge = conn.execute("SELECT pl.*, p.title, p.mobile_money_name, p.mobile_money_number, p.mobile_money_network, p.payout_notes FROM pledges pl JOIN projects p ON p.id=pl.project_id WHERE pl.id=?", (int(pledge_id),)).fetchone()
            if not pledge: return self.redirect("/marketplace")
            ref = f"EDB-{pledge['id']}-{secrets.token_hex(3).upper()}"
            conn.execute("INSERT INTO payments(pledge_id,provider,reference,status,checkout_url,created_at) VALUES(?,?,?,?,?,?)", (pledge["id"], provider, ref, "pending", PAYMENT_LINKS.get(provider, ""), now_iso()))
        checkout = "" if provider == "momo" else PAYMENT_LINKS.get(provider, "")
        if checkout:
            joiner = '&' if '?' in checkout else '?'
            return self.redirect(checkout + joiner + urlencode({"amount": str(pledge["amount"]), "email": pledge["email"], "reference": ref, "project": pledge["title"]}))
        return self.send_html(render_payment_setup(user, pledge, provider, ""))
    def handle_payment_success(self, user, query):
        pledge_id = query.get("pledge_id", [""])[0]
        if pledge_id.isdigit():
            with db() as conn:
                conn.execute("UPDATE pledges SET status='paid_demo' WHERE id=?", (int(pledge_id),))
                conn.execute("UPDATE payments SET status='paid_demo' WHERE pledge_id=?", (int(pledge_id),))
                pid = conn.execute("SELECT project_id FROM pledges WHERE id=?", (int(pledge_id),)).fetchone()
            if pid: return self.redirect(f"/project?id={pid['project_id']}")
        return self.redirect("/marketplace")
    def handle_upload(self, user):
        if not user: return self.send_json({"ok":False,"error":"Login required"}, 401)
        if not self.verify_csrf(user): return self.send_json({"ok":False,"error":"CSRF check failed"}, 403)
        try:
            payload=json.loads(self.read_body().decode()); pid=int(payload.get("project_id")); filename=slugify_filename(payload.get("filename","upload.bin")); mime=str(payload.get("mime") or mimetypes.guess_type(filename)[0] or "application/octet-stream")[:120]; data=payload.get("data",""); data=data.split(",",1)[1] if "," in data else data; content=base64.b64decode(data, validate=True)
        except Exception: return self.send_json({"ok":False,"error":"Invalid upload"}, 400)
        if MAX_UPLOAD_BYTES and len(content)>MAX_UPLOAD_BYTES: return self.send_json({"ok":False,"error":f"File too large. Max is {MAX_UPLOAD_BYTES//1024//1024} MB."}, 400)
        with db() as conn:
            if not conn.execute("SELECT id FROM projects WHERE id=? AND user_id=?", (pid,user["id"])).fetchone(): return self.send_json({"ok":False,"error":"Project not found"}, 404)
            stored=UPLOAD_DIR / f"{pid}-{secrets.token_hex(8)}-{filename}"; stored.write_bytes(content)
            external_url = ""
            try:
                external_url = cloudinary_upload(filename, mime, content)
            except Exception as ex:
                print("Cloud upload skipped/failed:", ex, file=sys.stderr)
            cur=conn.execute("INSERT INTO assets(user_id,project_id,filename,stored_path,external_url,mime,size,created_at) VALUES(?,?,?,?,?,?,?,?)", (user["id"],pid,filename,str(stored),external_url,mime,len(content),now_iso()))
            conn.execute("UPDATE projects SET asset_url=?, updated_at=? WHERE id=?", (f"/download?id={cur.lastrowid}", now_iso(), pid))
        return self.send_json({"ok":True,"download_url":f"/download?id={cur.lastrowid}","filename":filename})

def main():
    init_db()
    threading.Thread(target=auto_sync_worker, daemon=True).start()
    httpd=ThreadingHTTPServer((HOST, PORT), ScholarHandler); print(f"70Scholar running at http://{HOST}:{PORT}", flush=True); httpd.serve_forever()
if __name__ == "__main__": main()
