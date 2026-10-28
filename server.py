#!/usr/bin/env python3
"""70Scholar MVP: landing + authentication + opportunities + builder workspace + funding marketplace.
Run: python3 server.py  then open http://127.0.0.1:8080
No external Python packages required.
"""
from __future__ import annotations
import base64, hashlib, html, json, ipaddress, math, mimetypes, os, re, secrets, socket, sqlite3, ssl, sys, smtplib, threading, time, urllib.request, http.client, xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from email.message import EmailMessage
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse, urlencode, urljoin

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", str(ROOT / "edubridge.sqlite3")))
STATIC_DIR = ROOT / "static"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(ROOT / "uploads")))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
APP_NAME = "70Scholar"
APP_VERSION = "v18-privacy"
COMPANY_NAME = "Nexus Company Ltd"
APP_TAGLINE = "Find the opportunity. Show the build. Start the conversation."
OWNER_ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "honoremukunzi6@gmail.com").strip().lower()
ADMIN_EMAIL_ALLOWLIST = ("honoremukunzi6@gmail.com",)
if OWNER_ADMIN_EMAIL not in ADMIN_EMAIL_ALLOWLIST:
    OWNER_ADMIN_EMAIL = ADMIN_EMAIL_ALLOWLIST[0]
SESSION_COOKIE = "edubridge_session"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "0"))  # 0 means no 70Scholar app limit for project/media uploads

RSS_SOURCES = [
    "https://www.opportunitiesforafricans.com/feed/",
    "https://www.globalsouthopportunities.com/feed/",
]
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
ACCOUNT_TYPES = ["Student", "Parent / Guardian", "Teacher / Mentor", "Employer / Organisation", "Other"]
FEATURED_PROGRAMS = [
 {"title":"Yale Young African Scholars (YYAS) 2027","type":"Summer program","provider":"Yale University","country":"Africa / online + Rwanda","level":"African secondary students aged 14-18 in grades 10-11","deadline":"2027-01-20","url":"https://africanscholars.yale.edu/admissions","summary":"Tuition-free university prep and leadership programme for African secondary school students. Includes a 6-day online college-prep workshop and a 9-day residential leadership summit in Rwanda.","tags":"YYAS, Yale, Africa, Rwanda, leadership, free"},
 {"title":"Yale Young Global Scholars (YYGS) 2027","type":"Summer program","provider":"Yale University","country":"USA / global","level":"High school sophomores and juniors aged 16-18","deadline":"2027-01-06","url":"https://globalscholars.yale.edu/","summary":"Two-week residential academic programme at Yale for students worldwide, with need-based financial aid up to full tuition.","tags":"YYGS, Yale, global, summer, financial aid"},
 {"title":"Research Science Institute (RSI) 2027","type":"Research program","provider":"Center for Excellence in Education, MIT & Stanford","country":"USA","level":"High school juniors (rising seniors), 16+","deadline":"2026-12-11","url":"https://www.cee.org/programs/research-science-institute","summary":"Six-week, cost-free research programme for top STEM students. In 2027, around 100 scholars attend MIT and 50 attend Stanford. Check official application requirements and fees.","tags":"RSI, MIT, Stanford, research, STEM, free"},
 {"title":"MITES Summer (MIT)","type":"Summer program","provider":"Massachusetts Institute of Technology","country":"USA","level":"US grade 11 students","deadline":"See official page","url":"https://mites.mit.edu/discover-mites/mites-summer/","summary":"Free six-week residential STEM enrichment at MIT for high school juniors from underrepresented and underserved communities.","tags":"MIT, MITES, STEM, free, US"},
 {"title":"Summer Science Program (SSP)","type":"Research program","provider":"SSP International","country":"USA","level":"High school juniors aged 15-19","deadline":"See official page","url":"https://ssp.org/","summary":"Five-week residential research in astrophysics, biochemistry, genomics or synthetic chemistry. Co-sponsored by MIT.","tags":"SSP, research, astrophysics, genomics"},
 {"title":"Simons Summer Research Program","type":"Research program","provider":"Stony Brook University","country":"USA","level":"High school juniors, 16+, school nomination required","deadline":"See official page","url":"https://www.stonybrook.edu/simons/","summary":"Six-week mentored research in science, maths or engineering with Stony Brook faculty, ending in a research poster.","tags":"Simons, Stony Brook, research, STEM"},
 {"title":"QuestBridge National College Match","type":"Scholarship","provider":"QuestBridge","country":"USA","level":"High-achieving low-income high school seniors","deadline":"See official page","url":"https://www.questbridge.org/apply-to-college/programs/national-college-match","summary":"Full four-year scholarships worth over $360,000 to 55 top US colleges for high-achieving students from low-income backgrounds.","tags":"QuestBridge, scholarship, USA, full ride"},
 {"title":"Mastercard Foundation Scholars Program","type":"Scholarship","provider":"Mastercard Foundation","country":"Africa / global","level":"African students, undergraduate and masters","deadline":"See official page","url":"https://mastercardfdn.org/en/what-we-do/our-programs/mastercard-foundation-scholars-program/","summary":"Fully funded scholarships and leadership development for talented, service-oriented young Africans at partner universities worldwide.","tags":"Mastercard, scholarship, Africa, fully funded"},
 {"title":"African Leadership Academy (ALA)","type":"Scholarship","provider":"African Leadership Academy","country":"South Africa / Africa","level":"African students aged 16-19","deadline":"See official page","url":"https://www.africanleadershipacademy.org/","summary":"Two-year pre-university programme in leadership, entrepreneurship and African studies with need-based financial aid.","tags":"ALA, leadership, entrepreneurship, Africa"},
 {"title":"Mastercard Foundation Scholars at Cambridge","type":"Scholarship","provider":"University of Cambridge","country":"UK","level":"African students applying for a master's degree","deadline":"See official page","url":"https://www.mastercardfoundation.fund.cam.ac.uk/","summary":"Fully funded master's scholarships for talented young Africans, covering tuition and a monthly maintenance allowance.","tags":"Cambridge, Mastercard, masters, fully funded"},
 {"title":"Chevening Scholarship","type":"Scholarship","provider":"UK Foreign, Commonwealth & Development Office","country":"UK","level":"Graduates with an undergraduate degree and at least two years of work experience","deadline":"See official page","url":"https://www.chevening.org/scholarships/","summary":"Fully funded one-year master's scholarship at any UK university for future leaders from Chevening-eligible countries. Applicants choose three eligible courses and commit to returning home for two years.","tags":"Chevening, UK, masters, leadership, fully funded"},
 {"title":"Rhodes Scholarship","type":"Scholarship","provider":"Rhodes Trust / University of Oxford","country":"UK","level":"Outstanding graduates applying for full-time postgraduate study at Oxford","deadline":"See official page","url":"https://www.rhodeshouse.ox.ac.uk/scholarships/the-rhodes-scholarship/","summary":"The world's oldest international graduate scholarship: covers Oxford course fees and provides an annual stipend for postgraduate study. Eligibility and deadlines vary by constituency.","tags":"Rhodes, Oxford, postgraduate, leadership"},
 {"title":"Fulbright Foreign Student Program","type":"Scholarship","provider":"U.S. Department of State / IIE","country":"USA","level":"Non-U.S. graduates applying for a U.S. master's or PhD","deadline":"See official page","url":"https://foreign.fulbrightonline.org/about/foreign-student-program","summary":"About 4,000 grants each year for international students to pursue graduate study or research in the United States. Applications are administered by the Fulbright commission or U.S. embassy in each home country.","tags":"Fulbright, USA, masters, PhD, research"},
 {"title":"Gates Cambridge Scholarship","type":"Scholarship","provider":"Gates Cambridge Trust","country":"UK","level":"Non-UK citizens applying for an eligible Cambridge postgraduate course","deadline":"See official page","url":"https://www.gatescambridge.org/apply/","summary":"Full-cost postgraduate scholarships at Cambridge for academically outstanding applicants from outside the UK who show leadership potential and a commitment to improving lives.","tags":"Gates Cambridge, UK, postgraduate, fully funded"},
 {"title":"Erasmus Mundus Joint Masters","type":"Scholarship","provider":"European Union / Erasmus+","country":"Europe / global","level":"Bachelor's graduates or final-year bachelor's students worldwide","deadline":"See official page","url":"https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters","summary":"One- to two-year joint master's degrees taught across several universities, with competitive full scholarships covering participation costs, travel, visa and living allowance. Most applications open October–January.","tags":"Erasmus Mundus, Europe, masters, scholarship"},
 {"title":"DAAD Development-Related Postgraduate Courses (EPOS)","type":"Scholarship","provider":"German Academic Exchange Service (DAAD)","country":"Germany","level":"Graduates from developing countries with at least two years of relevant work experience","deadline":"See official page","url":"https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50076777","summary":"Fully funded master's and doctoral scholarships in development-related fields at German universities. Deadlines vary by course; applications go directly to the chosen programme.","tags":"DAAD, Germany, EPOS, development, masters, PhD"},
]

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
HELPLINE_PHONE = os.environ.get("HELPLINE_PHONE", "0726495648")
HELPLINE_EMAIL = os.environ.get("HELPLINE_EMAIL", "honoremukunzi6@gmail.com")
# Accounts require actual email verification or an explicit owner access grant.
EMAIL_ENABLED = bool(BIRD_API_KEY or SMTP_HOST)
MAIL_OUTBOX = ROOT / "mail_outbox.log"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)

def money(value: Any) -> str:
    try: amount = float(value or 0)
    except Exception: amount = 0
    return f"${amount:,.2f}"

def slugify_filename(name: str) -> str:
    name = unquote(name or "upload.bin").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name[:120] or "upload.bin"

@contextmanager
def db():
    """Open a SQLite connection and always close it when the block ends."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

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
    if region not in ('us1', 'eu1'):
        raise ValueError('BIRD_REGION must be us1 or eu1.')
    return f"https://{region}.platform.bird.com/v1/email/messages"

def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> None:
    """Send email through Bird or SMTP; never treat a local log as delivery."""
    if BIRD_API_KEY:
        payload = {
            "from": BIRD_FROM,
            "to": [to_email],
            "subject": subject,
            "text": body,
            "html": html_body or "<p>" + e(body).replace("\n", "<br>") + "</p>",
            "category": "transactional", "track_opens": False, "track_clicks": False,
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
        raise RuntimeError('Email delivery is not configured.')

def create_email_token(user_id: int, purpose: str, hours: int = 24) -> str:
    token = secrets.token_urlsafe(36)
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    with db() as conn:
        conn.execute("DELETE FROM email_tokens WHERE user_id=? AND purpose=?", (user_id, purpose))
        conn.execute("INSERT INTO email_tokens(user_id,token_hash,purpose,created_at,expires_at) VALUES(?,?,?,?,?)", (user_id, token_hash(token), purpose, now_iso(), expires.isoformat(timespec="seconds")))
    return token

def send_verification_email(user_id: int, email: str, name: str) -> None:
    if not EMAIL_ENABLED:
        raise RuntimeError('Email delivery is not configured.')
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
            "account_type": "ALTER TABLE users ADD COLUMN account_type TEXT NOT NULL DEFAULT ''",
            "career": "ALTER TABLE users ADD COLUMN career TEXT NOT NULL DEFAULT ''",
            "education_level": "ALTER TABLE users ADD COLUMN education_level TEXT NOT NULL DEFAULT ''",
            "source_mode": "ALTER TABLE opportunity_submissions ADD COLUMN source_mode TEXT NOT NULL DEFAULT 'manual'",
            "fetched_summary": "ALTER TABLE opportunity_submissions ADD COLUMN fetched_summary TEXT NOT NULL DEFAULT ''",
            "fetched_image": "ALTER TABLE opportunity_submissions ADD COLUMN fetched_image TEXT NOT NULL DEFAULT ''",
            "phone": "ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''",
            "admin_approved": "ALTER TABLE users ADD COLUMN admin_approved INTEGER NOT NULL DEFAULT 0",
            "banned": "ALTER TABLE users ADD COLUMN banned INTEGER NOT NULL DEFAULT 0",
            "ban_reason": "ALTER TABLE users ADD COLUMN ban_reason TEXT NOT NULL DEFAULT ''",
            "last_active": "ALTER TABLE users ADD COLUMN last_active TEXT NOT NULL DEFAULT ''",
            "message_status": "ALTER TABLE project_messages ADD COLUMN status TEXT NOT NULL DEFAULT 'legacy_review'",
            "review_version": "ALTER TABLE projects ADD COLUMN review_version INTEGER NOT NULL DEFAULT 0",
        }.items():
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS message_incidents(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL, raw_text TEXT NOT NULL,
            reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
            reviewed_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS disbursements(
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id),
            amount REAL NOT NULL, reference TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
            recorded_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
        """)
        for item in OPPORTUNITY_SEEDS:
            conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at) VALUES(:type,:title,:provider,:country,:level,:deadline,:url,:summary,:tags,:source,:created_at)""", {**item, "created_at": now_iso()})
        for prog in FEATURED_PROGRAMS:
            cur = conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (prog["type"], prog["title"], prog["provider"], prog["country"], prog["level"],
                 prog["deadline"], prog["url"], prog["summary"], prog["tags"], "featured_program", now_iso()))
            if cur.rowcount:
                conn.execute("UPDATE opportunities SET auto_description=? WHERE id=?",
                    (make_auto_description({"type":prog["type"],"title":prog["title"],"provider":prog["provider"],
                      "country":prog["country"],"level":prog["level"],"deadline":prog["deadline"],"summary":prog["summary"]}), cur.lastrowid))
        for prog in FEATURED_PROGRAMS:
            conn.execute("UPDATE opportunities SET deadline=? WHERE source='featured_program' AND title=?", (prog['deadline'], prog['title']))
            if prog['title'].startswith('Research Science Institute'):
                conn.execute("UPDATE opportunities SET summary=? WHERE source='featured_program' AND title=?", (prog['summary'],prog['title']))
            updated=conn.execute("SELECT * FROM opportunities WHERE source='featured_program' AND title=?",(prog['title'],)).fetchone()
            if updated:
                conn.execute('UPDATE opportunities SET auto_description=? WHERE id=?',(make_auto_description(updated),updated['id']))
        # Old demo projects are retained for review, but no new shared-password account is created.
        # A one-time migration disables any existing well-known demo login.
        admin_email = OWNER_ADMIN_EMAIL
        configured_password = os.environ.get("ADMIN_PASSWORD", "")
        if len(configured_password) < 8 or configured_password == 'Admin123!':
            configured_password = ''
        existing_admin = conn.execute("SELECT id,salt,password_hash FROM users WHERE email=?", (admin_email,)).fetchone()
        bootstrap_locked = conn.execute("SELECT 1 FROM settings WHERE key='admin_bootstrap_locked'").fetchone()
        if not existing_admin:
            salt, hashed = hash_password(configured_password or secrets.token_urlsafe(32))
            conn.execute("INSERT INTO users(name,email,password_hash,salt,role,email_verified,admin_approved,created_at) VALUES(?,?,?,?,?,?,?,?)", ("70Scholar Owner Admin",admin_email,hashed,salt,"admin",0,1,now_iso()))
            if not configured_password:
                conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('admin_bootstrap_locked','1')")
                print('WARNING: set a unique ADMIN_PASSWORD of at least 8 characters and restart to unlock the new owner account.',file=sys.stderr)
        else:
            vulnerable_default=verify_password('Admin123!',existing_admin['salt'],existing_admin['password_hash'])
            if vulnerable_default or bootstrap_locked:
                salt, hashed=hash_password(configured_password or secrets.token_urlsafe(32))
                conn.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,existing_admin['id']))
                conn.execute('DELETE FROM sessions WHERE user_id=?',(existing_admin['id'],))
                if configured_password:
                    conn.execute("DELETE FROM settings WHERE key='admin_bootstrap_locked'")
                else:
                    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('admin_bootstrap_locked','1')")
                    print('WARNING: the insecure default admin password was disabled. Set a unique ADMIN_PASSWORD and restart.',file=sys.stderr)
            conn.execute("UPDATE users SET role='admin',admin_approved=1,banned=0,ban_reason='' WHERE email=?",(admin_email,))
        # Only the configured owner email may remain admin. Others are downgraded.
        conn.execute("UPDATE users SET role='maker' WHERE role='admin' AND lower(email)<>lower(?)", (admin_email,))
        # Defense in depth: no account outside the allowlist can keep admin role.
        conn.execute("UPDATE users SET role='maker' WHERE role='admin' AND lower(email) NOT IN (%s)" % ",".join("?"*len(ADMIN_EMAIL_ALLOWLIST)), ADMIN_EMAIL_ALLOWLIST)
        # Do this once: v17 marked accounts verified without proof and allowed projects
        # and simulated payments to appear public. Preserve data but require fresh review.
        migrated = conn.execute("SELECT 1 FROM settings WHERE key='v18_privacy_migration'").fetchone()
        if not migrated:
            conn.execute("""UPDATE users SET email_verified=CASE WHEN EXISTS
                (SELECT 1 FROM email_tokens t WHERE t.user_id=users.id AND t.purpose='verify_email' AND t.used_at<>'')
                THEN 1 ELSE 0 END, admin_approved=0 WHERE lower(email)<>lower(?)""", (admin_email,))
            conn.execute("UPDATE users SET admin_approved=1, banned=0 WHERE lower(email)=lower(?)", (admin_email,))
            demo = conn.execute("SELECT id FROM users WHERE email='demo@70scholar.local'").fetchone()
            if demo:
                dsalt, dhash = hash_password(secrets.token_urlsafe(40))
                conn.execute("UPDATE users SET salt=?, password_hash=?, banned=1, ban_reason='Inactive legacy demo account' WHERE id=?", (dsalt, dhash, demo['id']))
            conn.execute("UPDATE projects SET status='pending_review', updated_at=? WHERE status='public'", (now_iso(),))
            conn.execute("UPDATE pledges SET status='legacy_unverified' WHERE status LIKE 'paid%'")
            conn.execute("UPDATE payments SET status='legacy_unverified' WHERE status LIKE 'paid%'")
            conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE banned=1 OR (email_verified=0 AND admin_approved=0))")
            conn.execute("INSERT INTO settings(key,value) VALUES('v18_privacy_migration',?)", (now_iso(),))
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

def _resolve_public(url: str):
    """Resolve once, reject every non-public address, then pin the connection to one of them."""
    parsed = urlparse(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or any(ord(c) < 32 for c in url)):
        raise ValueError('Only ordinary public http/https links are allowed.')
    host = parsed.hostname.lower()
    if host in ('localhost', 'localhost.localdomain') or host.endswith(('.local', '.localhost')):
        raise ValueError('Private addresses are not allowed.')
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    if port != (443 if parsed.scheme == 'https' else 80):
        raise ValueError('Only standard web ports are allowed.')
    results = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = []
    for info in results:
        ip = ipaddress.ip_address(info[4][0].split('%')[0])
        if not ip.is_global or ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
            raise ValueError('A private or reserved address was blocked.')
        if str(ip) not in addresses:
            addresses.append(str(ip))
    if not addresses:
        raise ValueError('No public address found.')
    return parsed, addresses

def is_safe_public_url(url: str) -> bool:
    try:
        _resolve_public(url)
        return True
    except Exception:
        return False

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """TLS checks the original hostname, but the TCP socket connects to a verified IP."""
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port=port, timeout=timeout, context=ssl.create_default_context())
        self.pinned_ip = ip
    def connect(self):
        sock = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise

def safe_http_get_bytes(url: str, timeout: int = 10, max_bytes: int = 1_500_000) -> tuple[bytes, str]:
    # No proxy or second DNS resolution: every redirect is independently resolved,
    # checked and pinned. A surrounding firewall is still recommended in production.
    current = url
    for _ in range(6):
        parsed, addresses = _resolve_public(current)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        last_error = None
        for ip in addresses:
            conn = None
            try:
                conn = (_PinnedHTTPSConnection(host, ip, port, timeout) if parsed.scheme == 'https'
                        else http.client.HTTPConnection(ip, port=port, timeout=timeout))
                path = parsed.path or '/'
                if parsed.query: path += '?' + parsed.query
                host_header = f'[{host}]' if ':' in host else host
                conn.request('GET', path, headers={'Host': host_header,
                    'User-Agent':'70ScholarBot/1.0 (opportunity preview)',
                    'Accept-Encoding':'identity', 'Connection':'close'})
                resp = conn.getresponse()
                if resp.status in (301,302,303,307,308):
                    location = resp.getheader('Location')
                    if not location: raise ValueError('Redirect has no destination.')
                    current = urljoin(current, location)
                    break
                if resp.status < 200 or resp.status >= 300:
                    raise ValueError(f'Source returned HTTP {resp.status}.')
                ctype = (resp.getheader('Content-Type') or '').lower()
                raw = resp.read(max_bytes + 1)
                if len(raw) > max_bytes: raise ValueError('Source is too large to preview.')
                return raw, ctype
            except (OSError, http.client.HTTPException, ssl.SSLError) as ex:
                last_error = ex
            finally:
                if conn: conn.close()
        else:
            raise ValueError('Could not connect to the source.') from last_error
    raise ValueError('Too many redirects.')

def safe_http_get(url: str, timeout: int = 10, max_bytes: int = 1_500_000) -> tuple[str, str]:
    raw, ctype = safe_http_get_bytes(url, timeout, max_bytes)
    return raw.decode('utf-8', errors='replace'), ctype

# Message safety checks are intentionally conservative. They cannot detect every
# obfuscation and can flag harmless wording; the owner can review and unban.
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+\-]+\s*(?:@|\[at\]|\(at\))\s*[A-Z0-9.\-]+\.[A-Z]{2,}\b")
URL_PATTERN = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>]+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|rw|edu|io|me|co|gov|app)(?:/[^\s<>]*)?\b")
HANDLE_PATTERN = re.compile(r"(?<![\w@])@[A-Za-z0-9_.-]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")
CONTACT_WORDS = re.compile(r"(?i)\b(?:whats\s*app|telegram|instagram|facebook|snapchat|tiktok|mobile\s*money|m[ -]?pesa|bank\s+account|my\s+address|home\s+address|national\s+id|phone\s+number|my\s+number|call\s+me|text\s+me|email\s+me|contact\s+me|dm\s+me|pay\s+me|send\s+me\s+money|my\s+name\s+is)\b")
HARASSMENT = re.compile(r"(?i)\b(?:kill yourself|i will kill you|you are worthless)\b")

def _registered_names(conn):
    return [r['name'].strip() for r in conn.execute('SELECT name FROM users')
            if len(r['name'].strip()) >= 4 and len(r['name'].strip().split()) >= 2]

def _name_pattern(names):
    names = sorted({x.strip() for x in names if x and len(x.strip()) >= 4 and len(x.strip().split()) >= 2}, key=len, reverse=True)
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(x) for x in names) + r')(?!\w)', re.I) if names else None

def _phone_match(text):
    return next((m for m in PHONE_PATTERN.finditer(text) if len(re.sub(r'\D', '', m.group())) >= 7), None)

def message_violation(text: str, names=(), blocked_phrases=()) -> str:
    if (EMAIL_PATTERN.search(text) or URL_PATTERN.search(text) or HANDLE_PATTERN.search(text)
            or _phone_match(text) or CONTACT_WORDS.search(text)):
        return 'Personal/contact information or off-platform payment/contact'
    name_re = _name_pattern(names)
    if name_re and name_re.search(text): return 'Personal name in message'
    if HARASSMENT.search(text): return 'Harassment or threats'
    folded = text.casefold()
    if any(p.strip() and p.strip().casefold() in folded for p in blocked_phrases):
        return 'Owner-configured blocked phrase'
    return ''

def redact_public_text(text: str, names=()) -> str:
    text = str(text or '')
    for pattern in (EMAIL_PATTERN, URL_PATTERN, HANDLE_PATTERN, CONTACT_WORDS):
        text = pattern.sub('[removed]', text)
    text = PHONE_PATTERN.sub(lambda m: '[removed]' if len(re.sub(r'\D','',m.group())) >= 7 else m.group(), text)
    name_re = _name_pattern(names)
    if name_re: text = name_re.sub('[name removed]', text)
    return text

def external_http_link(value: str) -> str:
    """Allow safe web URLs in href attributes without doing a network lookup."""
    value = (value or '').strip()
    try:
        p=urlparse(value); host=(p.hostname or '').lower()
        if (p.scheme not in ('http','https') or not host or p.username or p.password or
            len(value)>2000 or '\\' in value or any(ord(c)<32 or c.isspace() for c in value) or
            host in ('localhost','localhost.localdomain') or host.endswith(('.local','.localhost'))):
            return ''
        try:
            if not ipaddress.ip_address(host).is_global: return ''
        except ValueError:
            if host.startswith('0x') or re.fullmatch(r'[0-9.]+',host): return ''
        return value
    except (ValueError,TypeError):
        return ''

def anchor_url(value: str) -> str:
    return external_http_link(value) or '#'

def owner_payment_url() -> str:
    url = get_setting('owner_payment_link', '').strip()
    try:
        parsed = urlparse(url)
        if (parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
                and len(url) <= 1000 and not any(ord(c) < 32 or c.isspace() for c in url)):
            return url
    except Exception:
        pass
    return ''

def parse_amount(raw, minimum=Decimal('0.01'), maximum=Decimal('10000000')):
    try:
        val = Decimal(str(raw))
        if not val.is_finite() or val < minimum or val > maximum or val != val.quantize(Decimal('0.01')):
            return None
        return float(val)
    except (InvalidOperation, ValueError, TypeError):
        return None

def fetch_page_metadata(url: str) -> dict:
    """Extract title, description, image and site name from a public web page."""
    text, ctype = safe_http_get(url)
    if "html" not in ctype and "<" not in text[:500]:
        raise ValueError("That link does not look like a web page.")
    def meta(pattern):
        m = re.search(pattern, text, re.I | re.S)
        return strip_tags(m.group(1)).strip() if m else ""
    title = meta(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)') \
        or meta(r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)') \
        or meta(r"<title[^>]*>(.*?)</title>")
    desc = meta(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)') \
        or meta(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)')
    img = meta(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)')
    site = meta(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)') \
        or urlparse(url).netloc.replace("www.", "")
    heading = meta(r"<h1[^>]*>(.*?)</h1>")
    body_text = strip_tags(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S))[:1200]
    if not title:
        title = heading or urlparse(url).netloc
    if not desc:
        desc = body_text[:400] or "No description was found on this page. Verify the details before publishing."
    return {"title": title[:200], "summary": desc[:900], "image": img[:500],
            "site": site[:160], "url": url[:500], "type": infer_type(title),
            "deadline": infer_deadline(title + " " + desc + " " + body_text[:600])}

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
    text, ctype = safe_http_get(url, timeout=timeout, max_bytes=2_000_000)
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
            avatar = f"<img src='/static/images/default-avatar.svg?v={APP_VERSION}' alt='Profile picture'>"
        profile_link = f"<a class='nav-profile {'is-active' if active=='account' else ''}' href='/account' title='Account settings'>{avatar}</a><span class='nav-username'>{e(user['name'].split()[0])}</span>"
        admin_link = f"<a class='nav-link {'is-active' if active=='admin' else ''}' href='/admin'>Admin</a>" if is_admin(user) else ''
        nav_auth = f"""<a class="nav-link {'is-active' if active=='dashboard' else ''}" href="/dashboard">Dashboard</a><a class="nav-link {'is-active' if active=='workspace' else ''}" href="/workspace">Workspace</a><a class="nav-link {'is-active' if active=='messages' else ''}" href="/messages">Messages</a><a class="nav-link {'is-active' if active=='submit' else ''}" href="/submit">Add opportunity</a><a class="nav-link {'is-active' if active=='account' else ''}" href="/account">Account</a>{admin_link}{profile_link}<form class="logout-form" action="/logout" method="post"><input type="hidden" name="csrf" value="{e(user['csrf'])}"><button>Log out</button></form>"""
    else:
        nav_auth = "<a class='nav-link' href='/login'>Log in</a><a class='pill small' href='/signup'>Create account</a>"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{e(title)} — {APP_NAME}</title><meta name="description" content="{APP_NAME} helps students discover opportunities, showcase projects, connect with sponsors, and build what comes next."><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,500;0,600;1,400;1,500&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet"><link rel="icon" type="image/svg+xml" href="/static/favicon.svg?v={APP_VERSION}"><link rel="stylesheet" href="/static/styles.css?v={APP_VERSION}"></head><body><header class="site-header"><a href="/" class="logo">{logo}</a><nav class="top-nav" aria-label="Primary navigation"><a class="nav-link {'is-active' if active=='opportunities' else ''}" href="/opportunities">Opportunities</a><a class="nav-link {'is-active' if active=='courses' else ''}" href="/courses">Courses</a><a class="nav-link {'is-active' if active=='exams' else ''}" href="/exams">Exam prep</a><a class="nav-link {'is-active' if active=='programs' else ''}" href="/programs">Programs</a><a class="nav-link {'is-active' if active=='marketplace' else ''}" href="/marketplace">Marketplace</a>{nav_auth}</nav></header><main>{body}</main><footer class="footer"><div class="logo">{logo}</div><p>{APP_TAGLINE}</p>
    <div class="helpline"><span class="helpline-label">Need help?</span>
      <a href="tel:{HELPLINE_PHONE}">📞 {HELPLINE_PHONE}</a>
      <a href="mailto:{HELPLINE_EMAIL}">✉️ {HELPLINE_EMAIL}</a></div>
    <p class="copyright">© {datetime.now(timezone.utc).year} {COMPANY_NAME}. All rights reserved.</p></footer><script src="/static/app.js?v={APP_VERSION}"></script></body></html>"""



def render_home(user):
    with db() as conn:
        stats = {
            "opportunities": conn.execute("SELECT COUNT(*) c FROM opportunities").fetchone()["c"],
            "projects": conn.execute("SELECT COUNT(*) c FROM projects WHERE status='public'").fetchone()["c"],
            "pledged": conn.execute("SELECT COALESCE(SUM(amount),0) c FROM pledges WHERE status='paid_confirmed'").fetchone()["c"],
        }
    story_section = f'''<section class="story-section"><div class="story-inner"><p class="eyebrow eyebrow-dark">The story 70Scholar is building</p><h2>A path for the student who almost gave up searching.</h2><p>70Scholar was created for students who keep asking, "Where are the scholarships, internships, competitions, sponsors, and people who will believe in my project?" The goal is to make answers easier to find, applications easier to prepare, and student projects easier to support.</p><p>As more students use 70Scholar, this section will grow into a verified wall of wins: scholarships found, internships applied for, jobs reached, sponsors connected, and projects funded. We will share successes only when students confirm them — because trust matters.</p><div class="impact-stats"><div><strong>{stats['opportunities']}</strong><span>opportunities currently listed</span></div><div><strong>{stats['projects']}</strong><span>student projects published</span></div><div><strong>{money(stats['pledged'])}</strong><span>owner-confirmed support</span></div></div></div></section>'''
    hero_section = '''<section class="hero" id="hero"><div class="hero-bg-beyond" aria-hidden="true"></div><div class="hero-bg-now" aria-hidden="true"></div><div class="hero-content"><p class="brand-display"><span class="brand-num">70</span><span class="brand-word">Scholar</span></p><p class="eyebrow">Matched to your level. Built to launch.</p><h1>There's a version of your future<br>still waiting to be found.</h1><p class="subhead">70Scholar finds scholarships, internships, grants, and competitions built for where you stand — then gives you a secure workspace to build the projects that get you noticed, funded, or sold.</p><div class="hero-actions"><a href="/opportunities" class="cta-primary">See real open opportunities <span class="arrow">→</span></a><a href="/marketplace" class="cta-secondary">Fund or buy student projects</a></div><p class="hero-micro">Real listings, refreshed from trusted opportunity feeds.</p></div><div class="scroll-hint" aria-hidden="true"><span></span></div></section>'''
    gap_section = '''<section class="gap-section"><p class="eyebrow eyebrow-dark">Why most students miss out</p><p class="gap-statement">Most scholarships don't go unclaimed because nobody qualified. They go unclaimed because the right student never found them — or found them too late to build something strong.</p></section>'''
    journey_section = '''<section class="journey-section" id="journey"><div class="journey-header"><p class="eyebrow">The path across</p><h2>Discover. Build. Launch. Fund.</h2></div><div class="journey-path"><div class="journey-step"><span class="step-number">01</span><h3>Discover</h3><p>Browse real openings and save the ones that fit your country, field, deadline, and level.</p></div><div class="journey-step"><span class="step-number">02</span><h3>Build</h3><p>Keep drafts, pitch text, links, files, and project details in your private account so unfinished work stays safe.</p></div><div class="journey-step"><span class="step-number">03</span><h3>Launch</h3><p>Publish a project to the marketplace, attach a demo or release file, and invite buyers, donors, mentors, or funders.</p></div></div></section>'''
    opportunities_section = '''<section class="opportunities-section"><div class="opp-header"><p class="eyebrow eyebrow-dark">What's waiting on the other side</p><h2>Every door, sorted by which one actually opens for you.</h2></div><div class="opportunity-cards feature-cards"><div class="opp-card"><div class="icon-dot">🎓</div><h3>Scholarships</h3><p>Funding matched to your field, level, and country, with deadlines you can track.</p></div><div class="opp-card"><div class="icon-dot">💼</div><h3>Internships</h3><p>Roles sized for where you actually are in school, not five-year-experience traps.</p></div><div class="opp-card"><div class="icon-dot">🏆</div><h3>Competitions & grants</h3><p>Contests and small grants your project can realistically compete for.</p></div></div></section>'''
    workspace_section = '''<section class="workspace-section"><div class="workspace-inner"><div class="workspace-visual" aria-hidden="true"><div class="ws-card c1"></div><div class="ws-card c2"></div><div class="ws-card c3"></div></div><div class="workspace-copy"><p class="eyebrow">Where the work actually happens</p><h2>Not just a plan. A place to build it.</h2><p>Create an account, save unfinished project drafts, upload a release file, and later publish the project for funding or sale. Funders can pledge support, buyers can contact makers, and students can continue from where they stopped.</p></div></div></section>'''
    final_cta_section = '''<section class="final-cta" id="final-cta"><h2>Cross over.</h2><p>Somewhere on the other side, there's a deadline that hasn't found you yet. Better to be early.</p><a href="/signup" class="cta-primary">Create your free workspace <span class="arrow">→</span></a></section>'''
    programs_section = """<section class="programs-section"><div class="programs-inner">
      <p class="eyebrow">Explore programmes</p><h2>Find a programme for your next step.</h2>
      <p>Sign in to browse featured programmes, check their requirements and follow their official application links.</p>
      <a class="cta-primary" href="/programs">Explore featured programs <span class="arrow">→</span></a>
      </div></section>"""
    body = (hero_section + render_typewriter() + journey_section + opportunities_section
            + programs_section + gap_section + render_slideshow()
            + workspace_section + story_section + render_extra_features() + final_cta_section)
    return page_shell("Future waiting to be found", body, user)

SLIDESHOW_PHOTOS = [
    ("ilead-students.jpg", "Students standing together outside their school"),
    ("students-reading.jpg", "Students reading together"),
    ("university-graduation.jpg", "University graduates at a ceremony"),
    ("graduation-speech.jpg", "A graduate speaking at a ceremony"),
    ("ilead-classmates.jpg", "Classmates together on school grounds"),
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
      <div class="slideshow-head"><p class="eyebrow eyebrow-dark">Learning, growing, achieving</p>
      <h2>Moments along the learning journey.</h2></div>
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
        <a class="feature-tile" href="/marketplace" data-tooltip="Submit your project for review and let supporters use the owner-managed payment link when available."><span class="feature-icon">🚀</span><h3>Project marketplace</h3><p>Show your build, find sponsors, and get funded.</p></a>
        <a class="feature-tile" href="/signup" data-tooltip="Create a free account to unlock opportunities, courses, exam prep, submissions and the builder workspace."><span class="feature-icon">🔐</span><h3>Your private workspace</h3><p>Drafts, uploads, saved listings and messages in one place.</p></a>
      </div></div></section>
    <section class="trust-section"><div class="trust-inner">
      <div class="trust-stat"><strong data-count="37">0</strong><span>opportunities listed</span></div>
      <div class="trust-stat"><strong data-count="16">0</strong><span>featured programmes</span></div>
      <div class="trust-stat"><strong data-count="6">0</strong><span>pre-university courses</span></div>
      <div class="trust-stat"><strong data-count="6">0</strong><span>exam prep tracks</span></div>
    </div></section>
    <section class="faq-section"><div class="faq-inner"><p class="eyebrow eyebrow-dark">Good to know</p><h2>Questions students ask us.</h2>
      <details class="faq-item"><summary>Do I need an account to see opportunities?</summary><p>Yes. Create a free account or log in to browse opportunities, courses, exam prep, the marketplace and your workspace. The homepage stays open to everyone.</p></details>
      <details class="faq-item"><summary>Are the courses and exam prep free?</summary><p>Joining a course or exam track is free. It saves your place so study materials and practice plans can be added to your dashboard.</p></details>
      <details class="faq-item"><summary>Can I add an opportunity?</summary><p>Yes. Use “Add opportunity” after signing in. Your submission stays private until the admin approves it.</p></details>
      <details class="faq-item"><summary>How does project funding work?</summary><p>When the owner configures a payment link, supporters can use it to pay the owner. The owner reviews payment records and separately decides whether and how to support project creators. A link visit alone does not confirm a payment.</p></details>
      <details class="faq-item"><summary>Are projects reviewed?</summary><p>Yes. New projects and later changes are reviewed by the owner before they appear in the marketplace.</p></details>
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

def render_programs(user):
    cards = "".join([
        hover_card(
            f"""<article class="course-card program-card"><span class="tag">{e(pr['type'])}</span>
            <h3>{e(pr['title'])}</h3><p class="provider">{e(pr['provider'])} · {e(pr['country'])}</p>
            <p class="deadline">{e(deadline_badge(pr['deadline']))}</p><p>{e(pr['summary'])}</p>
            <p class="provider">{e(pr['level'])}</p>
            <a class="cta-primary slim" href="{e(pr['url'])}" target="_blank" rel="noopener">Official page ↗</a></article>""",
            f"{pr['title']} by {pr['provider']}. {pr['summary']} Eligible: {pr['level']}. Location: {pr['country']}. Deadline: {pr['deadline']}. Always confirm on the official page.",
            "course-wrap") for pr in FEATURED_PROGRAMS
    ])
    body = f"""<section class="page-hero compact"><p class="eyebrow">Featured programmes</p>
      <h1>YYAS, YYGS, RSI and more.</h1><p>{len(FEATURED_PROGRAMS)} real programmes with official links, eligibility and deadlines in one place. Hover any card for the details.</p></section>
      <section class="panel-section"><div class="course-grid">{cards}</div>
      <p class="muted">Deadlines change each year — always confirm dates and eligibility on the official page before applying.</p></section>"""
    return page_shell("Featured programs", body, user, "programs")

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
          <h2>Option 1 — fill in the details</h2>
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
        <div class="builder-panel"><h2>Option 2 — just paste a link</h2>
        <p class="muted">Found an opportunity page? Paste its link. We fetch the title, description and image automatically, then the admin reviews what we found before anything is published.</p>
        <form method="post" action="/opportunity/submit-link" class="builder-form">
          <input type="hidden" name="csrf" value="{e(user['csrf'])}">
          <label>Opportunity link <span class='req'>*</span><input name="url" type="url" required placeholder="https://example.com/scholarship"></label>
          <label>Why should others see it? <span class='optional'>(optional)</span><textarea name="note" maxlength="600" placeholder="A short note for the admin"></textarea></label>
          <button class="cta-primary" type="submit">Fetch &amp; send for review</button>
        </form>
        <h2 style="margin-top:2rem">Your submissions</h2>
        <ul class="clean-list">{rows if rows else '<li>Nothing submitted yet.</li>'}</ul>
        <p class="muted">Pending items are visible only to you and the admin until approved.</p></div>
      </div></section>"""
    return page_shell("Submit an opportunity", body, user, "submit")


def render_auth(mode: str, msg: str = "", next_url: str = ""):
    is_signup = mode == "signup"; title = "Create your account" if is_signup else "Log in"; action = "/signup" if is_signup else "/login"
    safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else ""
    hidden_next = f"<input type='hidden' name='next' value='{e(safe_next)}'>" if safe_next and not is_signup else ""
    if is_signup:
        type_opts = "".join(f"<option value='{t}'>{t}</option>" for t in ACCOUNT_TYPES)
        extra = f"""<label>Full name <span class='req'>*</span><input required name="name" autocomplete="name" placeholder="Your name"></label>
        <label>Phone number <span class='req'>*</span><input required name="phone" type="tel" autocomplete="tel" maxlength="32" placeholder="e.g. +250 7xx xxx xxx"></label>
        <p class='form-hint'>Your name, email and phone are private to you and the owner admin. A password is required. The remaining fields are optional.</p>
        <label>I am a... <span class='optional'>(optional)</span><select name="account_type"><option value=''>Prefer not to say</option>{type_opts}</select></label>
        <label>Career / field of interest <span class='optional'>(optional)</span><input name="career" maxlength="120" placeholder="e.g. Medicine, Engineering, Law, Arts"></label>
        <label>Education level <span class='optional'>(optional)</span><input name="education_level" maxlength="80" placeholder="e.g. Senior 5, A-Level, undergraduate"></label>"""
    else:
        extra = ''
    switch = "Already have an account? <a href='/login'>Log in</a>." if is_signup else "New here? <a href='/signup'>Create an account</a>."
    forgot = "" if is_signup else "<p class='muted'><a href='/forgot-password'>Forgot password?</a></p>"
    body = f"""<section class="auth-wrap"><form class="auth-card" method="post" action="{action}"><p class="eyebrow eyebrow-dark">Secure workspace</p><h1>{title}</h1>{flash(msg,'error') if msg else ''}{hidden_next}{extra}<label>Email <span class='req'>*</span><input required type="email" name="email" autocomplete="email" placeholder="you@example.com"></label><label>Password <span class='req'>*</span><input required type="password" name="password" autocomplete="{'new-password' if is_signup else 'current-password'}" minlength="8" placeholder="At least 8 characters"></label><button class="cta-primary auth-button" type="submit">{title}</button>{forgot}<p class="muted">{switch}</p></form></section>"""
    return page_shell(title, body, None)

def render_notice(title: str, message: str, user=None):
    body = f"""<section class='auth-wrap'><div class='auth-card'><p class='eyebrow eyebrow-dark'>70Scholar</p><h1>{e(title)}</h1><p>{e(message)}</p><div class='form-actions'><a class='cta-primary' href='/login'>Log in</a><a class='ghost-button' href='/'>Home</a></div></div></section>"""
    return page_shell(title, body, user)

def render_forgot_password(msg: str = ""):
    body = f"""<section class='auth-wrap'><form class='auth-card' method='post' action='/forgot-password'><p class='eyebrow eyebrow-dark'>Account recovery</p><h1>Reset your password</h1>{flash(msg,'success') if msg else ''}<p class='muted'>Enter your account email. We will send a reset link.</p><label>Email<input required type='email' name='email' autocomplete='email'></label><button class='cta-primary auth-button' type='submit'>Send reset link</button><p class='muted'><a href='/login'>Back to login</a></p></form></section>"""
    return page_shell("Forgot password", body, None)

def render_reset_password(token: str, msg: str = ""):
    body = f"""<section class='auth-wrap'><form class='auth-card' method='post' action='/reset-password'><p class='eyebrow eyebrow-dark'>Account recovery</p><h1>Choose a new password</h1>{flash(msg,'error') if msg else ''}<input type='hidden' name='token' value='{e(token)}'><label>New password<input required type='password' minlength='8' name='password' autocomplete='new-password'></label><button class='cta-primary auth-button' type='submit'>Reset password</button></form></section>"""
    return page_shell("Reset password", body, None)

def render_account(user, msg=""):
    email_status = ("<p class='muted'>Email verified.</p>" if user['email_verified'] else
        f"<p class='muted'>Your email is not verified. You have access because the owner granted it.</p><form method='post' action='/account/verify-email' class='builder-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><button class='ghost-button' type='submit'>Send a verification link</button></form>")
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
        <h2>{e(user['name'])}</h2><p class='muted'>{e(user['email'])}</p>{email_status}
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
        cards.append(f"""<article class="listing-card" data-tooltip="{e(item['auto_description'] if 'auto_description' in item.keys() and item['auto_description'] else make_auto_description(item))}"><div class="listing-top"><span class="tag">{e(item['type'])}</span><span class="deadline">{e(deadline_badge(item['deadline']))}</span></div><h3>{e(item['title'])}</h3><p class="provider">{e(item['provider'])} · {e(item['country'])}</p><p>{e(item['summary'])}</p><dl class="mini-meta"><div><dt>Level</dt><dd>{e(item['level'])}</dd></div><div><dt>Deadline</dt><dd>{e(item['deadline'])}</dd></div></dl><p class="source">Source: {e(item['source'])}</p><div class="card-actions"><a class="cta-primary slim" target="_blank" rel="noopener" href="{e(anchor_url(item['url']))}">Apply on source ↗</a>{save_button}</div></article>""")
    def sel(x): return "selected" if typ == x else ""
    body = f"""<section class="page-hero compact"><p class="eyebrow">Opportunity finder</p><h1>Real applications, contests, internships, and grants.</h1><p>These seed listings are current starting points for August 2026. Always verify the final deadline and eligibility on the official page before applying.</p></section><section class="panel-section"><form class="filter-bar" method="get" action="/opportunities"><input name="q" value="{e(q)}" placeholder="Search Rwanda, AI, climate, internship..."><select name="type"><option value="">All types</option><option {sel('Scholarship')} value="Scholarship">Scholarships</option><option {sel('Internship')} value="Internship">Internships</option><option {sel('Competition')} value="Competition">Competitions</option><option {sel('Grant')} value="Grant">Grants</option><option {sel('Hackathon')} value="Hackathon">Hackathons</option></select><button class="cta-primary slim" type="submit">Filter</button></form><div class="listing-grid">{''.join(cards) if cards else '<p class="empty">No matches yet. Try a different search.</p>'}</div></section>"""
    return page_shell("Opportunities", body, user, "opportunities")

def render_dashboard(user):
    with db() as conn:
        projects = conn.execute("SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC", (user['id'],)).fetchall()
        saved = conn.execute("SELECT o.* FROM bookmarks b JOIN opportunities o ON o.id=b.opportunity_id WHERE b.user_id=? ORDER BY o.deadline ASC", (user['id'],)).fetchall()
        pledges = conn.execute("SELECT pl.*,p.title FROM pledges pl JOIN projects p ON p.id=pl.project_id WHERE pl.user_id=? ORDER BY pl.id DESC", (user['id'],)).fetchall()
        inbox = conn.execute("SELECT m.*,p.title FROM project_messages m JOIN projects p ON p.id=m.project_id WHERE p.user_id=? AND m.status='visible' ORDER BY m.id DESC LIMIT 8", (user['id'],)).fetchall()
        names = _registered_names(conn)
    project_cards = [f"<article class='mini-card'><span class='tag'>{e(p['status'].replace('_',' ').title())}</span><h3>{e(p['title'])}</h3><p>{e(p['summary'])}</p><a href='/workspace?edit={p['id']}'>Continue work →</a></article>" for p in projects]
    saved_cards = [f"<li><a target='_blank' rel='noopener' href='{e(anchor_url(o['url']))}'>{e(o['title'])}</a><span>{e(deadline_badge(o['deadline']))}</span></li>" for o in saved]
    pledge_cards = [f"<li>{money(pl['amount'])} for <a href='/project?id={pl['project_id']}'>{e(redact_public_text(pl['title'], names))}</a><span>{e(pl['status'].replace('_',' '))}</span></li>" for pl in pledges]
    inbox_cards = [f"<li><a href='/project?id={m['project_id']}'>{e(redact_public_text(m['title'], names))}</a><span>Community member: {e(redact_public_text(m['message'][:100], names))}</span></li>" for m in inbox]
    access_note = "Email verified" if user['email_verified'] else "Access granted by the owner; email not yet verified"
    body = f"""<section class='page-hero compact dashboard-hero'><p class='eyebrow'>Welcome back</p><h1>Continue your unfinished work.</h1><p>Your saved opportunities, drafts, uploads and funding activity live here.</p><a href='/workspace' class='cta-primary'>Open builder workspace →</a></section>
    <section class='dashboard-grid'><div class='flash info'>{e(access_note)}.</div><div class='dash-panel large'><div class='panel-head'><h2>Your projects</h2><a href='/workspace'>New project</a></div><div class='mini-grid'>{''.join(project_cards) if project_cards else '<p class="empty">No drafts yet. Start one in the workspace.</p>'}</div></div>
    <div class='dash-panel'><h2>Saved opportunities</h2><ul class='clean-list'>{''.join(saved_cards) if saved_cards else '<li>No saved opportunities yet.</li>'}</ul></div>
    <div class='dash-panel'><h2>Your funding activity</h2><p class='muted'>Pending means a payment has not yet been confirmed by the owner.</p><ul class='clean-list'>{''.join(pledge_cards) if pledge_cards else '<li>No support records yet.</li>'}</ul></div>
    <div class='dash-panel'><h2>Project messages</h2><ul class='clean-list'>{''.join(inbox_cards) if inbox_cards else '<li>No questions yet.</li>'}</ul><a href='/messages'>Open messages →</a></div>
    <div class='dash-panel'><h2>Builder checklist</h2><ol class='check-list'><li>Save an opportunity.</li><li>Create a project draft.</li><li>Upload a prototype without private details.</li><li>Submit for owner review.</li></ol></div></section>"""
    return page_shell('Dashboard', body, user, 'dashboard')


def render_workspace(user, query):
    edit_id = query.get('edit', [''])[0]
    mode = 'full' if query.get('mode', ['guided'])[0] == 'full' else 'guided'
    with db() as conn:
        projects = conn.execute('SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC', (user['id'],)).fetchall()
        project = conn.execute('SELECT * FROM projects WHERE id=? AND user_id=?', (int(edit_id), user['id'])).fetchone() if edit_id.isdigit() else None
        assets = conn.execute('SELECT * FROM assets WHERE project_id=? ORDER BY id DESC', (project['id'],)).fetchall() if project else []
    side = ''.join(f"<a class='project-link {'active' if project and row['id']==project['id'] else ''}' href='/workspace?edit={row['id']}'><strong>{e(row['title'])}</strong><span>{e(row['status'].replace('_',' ').title())} · {e(row['updated_at'][:10])}</span></a>" for row in projects)
    def val(key, default=''):
        return e(project[key]) if project else default
    status = project['status'] if project else 'draft'
    query_base = f"edit={project['id']}&amp;" if project else ''
    if project:
        asset_items = ''.join(f"<li><a href='/download?id={a['id']}'>{e(a['filename'])}</a><span>{a['size']//1024+1} KB</span></li>" for a in assets)
        asset_box = f"""<div class='upload-box' data-project-id='{project['id']}' data-csrf='{e(user['csrf'])}'><h3>Upload project files</h3><p>Do not include names, contact details or other private information in filenames, images, videos or documents. The owner must manually inspect every file. Uploading to a published project sends it back for review.</p><input type='file' id='assetFile' accept='image/*,video/*,.zip,.pdf,.apk,.py,.js,.html,.css'><button class='ghost-button' type='button' id='uploadAsset'>Upload file</button><p class='upload-status' id='uploadStatus'></p><ul class='clean-list asset-list'>{asset_items or '<li>No uploaded files yet.</li>'}</ul></div>"""
    else:
        asset_box = "<div class='upload-box'><h3>Attach files after saving</h3><p>Save your project first, then reopen it to upload a prototype, image, video or document.</p></div>"
    mode_label = 'Guided steps' if mode == 'guided' else 'Full form'
    body = f"""<section class='page-hero compact'><p class='eyebrow'>Builder workspace</p><h1>Build your project, your way.</h1><p>Choose guided steps or the complete form. Projects and any later changes are reviewed by the owner before publication.</p></section>
    <section class='workspace-grid'><aside class='project-sidebar'><a href='/workspace' class='cta-primary slim full'>+ New project</a><div class='side-list'>{side or '<p class="empty">Your drafts will appear here.</p>'}</div></aside><div class='builder-panel'>
    <div class='form-mode-switch' aria-label='Project form mode'><a class='{'selected' if mode=='guided' else ''}' href='/workspace?{query_base}mode=guided'>Guided steps</a><a class='{'selected' if mode=='full' else ''}' href='/workspace?{query_base}mode=full'>Full form</a></div>
    <p class='muted'>Using {mode_label}. Save or submit your work before switching forms. Your registration contact details are never shown to other users.</p>
    <form method='post' action='/project/save' class='builder-form project-builder' {'data-wizard="true"' if mode=='guided' else ''}>
      <input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='project_id' value='{project['id'] if project else ''}'>
      <fieldset class='wizard-step'><legend><span>01</span> The idea</legend><div class='form-row'><label>Project title<input required name='title' maxlength='160' value='{val('title')}' placeholder='e.g. Revision Cards App'></label><label>Category<input required name='category' maxlength='80' value='{val('category')}' placeholder='Education, climate, technology...'></label></div><label>Short summary<textarea required name='summary' maxlength='600' rows='4' placeholder='What problem does this solve, and who benefits?'>{val('summary')}</textarea></label></fieldset>
      <fieldset class='wizard-step'><legend><span>02</span> The plan</legend><label>Project description / pitch<textarea required name='details' maxlength='10000' rows='9' placeholder='Describe the problem, solution, users, current stage and how funding will help.'>{val('details')}</textarea></label><p class='muted'>For review: at least 40 characters in your summary and 120 in the description. Do not include contact details or names.</p></fieldset>
      <fieldset class='wizard-step'><legend><span>03</span> Funding</legend><div class='form-row'><label>Funding goal (USD)<input type='number' min='0' max='10000000' step='0.01' name='goal_amount' value='{val('goal_amount','0') or '0'}'></label><label>Optional sale price / licence (USD)<input type='number' min='0' max='10000000' step='0.01' name='price' value='{val('price','0') or '0'}'></label></div><p class='muted'>Supporters pay through an owner-configured link when available. The owner separately decides how to support founders. No payment is guaranteed.</p></fieldset>
      <fieldset class='wizard-step'><legend><span>04</span> Save or request review</legend><label>Visibility<select name='status'><option value='draft' {'selected' if status not in ('public','pending_review') else ''}>Private draft</option><option value='public' {'selected' if status in ('public','pending_review') else ''}>Submit for owner review</option></select></label><p class='muted'>The owner checks your project text and all uploads before approval. Editing or adding a file to a published project takes it offline for another review.</p></fieldset>
      <div class='wizard-controls' hidden><button class='ghost-button' type='button' data-wizard-prev>← Back</button><span data-wizard-progress aria-live='polite'></span><button class='ghost-button' type='button' data-wizard-next>Next →</button></div>
      <div class='form-actions'><button class='cta-primary' type='submit' data-wizard-submit>Save project</button><a class='cta-secondary dark' href='/marketplace'>View marketplace</a></div>
    </form>{asset_box}</div></section>"""
    return page_shell('Workspace', body, user, 'workspace')


def public_projects(conn):
    return conn.execute("""SELECT p.*, COALESCE((SELECT SUM(pl.amount) FROM pledges pl
        WHERE pl.project_id=p.id AND pl.status='paid_confirmed'),0) AS pledged
        FROM projects p WHERE p.status='public' ORDER BY p.updated_at DESC""").fetchall()


def render_messages(user):
    with db() as conn:
        owned = conn.execute("SELECT m.*,p.title FROM project_messages m JOIN projects p ON p.id=m.project_id WHERE p.user_id=? AND m.status='visible' ORDER BY m.id DESC", (user['id'],)).fetchall()
        sent = conn.execute("SELECT m.*,p.title FROM project_messages m JOIN projects p ON p.id=m.project_id WHERE m.user_id=? AND p.user_id<>? AND m.status='visible' ORDER BY m.id DESC", (user['id'],user['id'])).fetchall()
        names = _registered_names(conn)
    def items(rows, own):
        return ''.join(f"<li><strong>{'Community member' if own else 'You'}</strong> · <a href='/project?id={m['project_id']}'>{e(redact_public_text(m['title'],names))}</a><span>{e(m['created_at'][:10])}</span><p>{e(redact_public_text(m['message'],names))}</p></li>" for m in rows)
    body=f"""<section class='page-hero compact messages-hero'><p class='eyebrow'>Project conversations</p><h1>Your project messages.</h1><p>Messages use a community alias. Contact details are not shared with builders or supporters.</p></section>
    <section class='messages-grid'><div class='dash-panel'><h2>Questions about your projects</h2><ul class='clean-list message-list'>{items(owned,True) or '<li>No questions yet.</li>'}</ul></div><div class='dash-panel'><h2>Messages you sent</h2><ul class='clean-list message-list'>{items(sent,False) or '<li>No messages sent yet.</li>'}</ul></div></section>"""
    return page_shell('Messages', body, user, 'messages')


def render_marketplace(user):
    with db() as conn:
        projects = public_projects(conn)
        names = _registered_names(conn)
    cards=[]
    for p in projects:
        goal=float(p['goal_amount'] or 0); total=float(p['pledged'] or 0); percent=min(100,int(total/goal*100)) if goal else 0
        sale = f"<span class='sale-pill'>Licence: {money(p['price'])}</span>" if float(p['price'] or 0)>0 else ''
        title=e(redact_public_text(p['title'],names)); summary=e(redact_public_text(p['summary'],names)); category=e(redact_public_text(p['category'],names))
        cards.append(f"<article class='market-card'><div class='listing-top'><span class='tag'>{category}</span>{sale}</div><h3><a href='/project?id={p['id']}'>{title}</a></h3><p class='provider'>Student project</p><p>{summary}</p><div class='progress'><span style='width:{percent}%'></span></div><p class='progress-copy'>{money(total)} owner-confirmed of {money(goal)} goal</p><a class='cta-primary slim' href='/project?id={p['id']}'>View project →</a><a class='ghost-button slim' href='/project?id={p['id']}#project-chat'>Ask a question</a></article>")
    body=f"""<section class='page-hero compact marketplace-hero'><p class='eyebrow'>Project marketplace</p><h1>Small projects deserve support.</h1><p>Explore projects reviewed by the owner. Ask questions without exchanging personal details, or support a project when the owner payment link is available.</p><a href='/workspace' class='cta-primary'>Submit a project →</a></section><section class='panel-section'><div class='listing-grid market-grid'>{''.join(cards) if cards else '<p class="empty">No projects have been approved yet.</p>'}</div></section>"""
    return page_shell('Marketplace', body, user, 'marketplace')


def render_project_detail(user, project_id):
    if not project_id.isdigit(): return page_shell('Project not found', "<section class='panel-section'>Project not found.</section>", user)
    with db() as conn:
        p = conn.execute("""SELECT p.*,COALESCE((SELECT SUM(amount) FROM pledges pl WHERE pl.project_id=p.id AND pl.status='paid_confirmed'),0) pledged FROM projects p WHERE p.id=? AND p.status='public'""", (int(project_id),)).fetchone()
        if not p: return page_shell('Project not found', "<section class='panel-section'>Project not found or not public.</section>", user)
        assets = conn.execute('SELECT * FROM assets WHERE project_id=? ORDER BY id DESC', (p['id'],)).fetchall()
        pledges = conn.execute("SELECT amount,created_at FROM pledges WHERE project_id=? AND status='paid_confirmed' ORDER BY id DESC LIMIT 10", (p['id'],)).fetchall()
        messages = conn.execute("SELECT * FROM project_messages WHERE project_id=? AND status='visible' ORDER BY id DESC LIMIT 20", (p['id'],)).fetchall()
        names = _registered_names(conn)
    safe=lambda text: e(redact_public_text(text,names))
    goal=float(p['goal_amount'] or 0); total=float(p['pledged'] or 0); percent=min(100,int(total/goal*100)) if goal else 0
    asset_links=[f"<li><a href='/download?id={a['id']}'>Project file {i+1}</a><span>{a['size']//1024+1} KB</span></li>" for i,a in enumerate(assets)]
    media=[]
    for i,a in enumerate(assets):
        src=f"/download?id={a['id']}&amp;inline=1"
        if a['mime'] in ('image/jpeg','image/png','image/gif','image/webp'):
            media.append(f"<figure class='media-card'><img src='{src}' alt='Project image {i+1}'><figcaption>Project image {i+1}</figcaption></figure>")
        elif a['mime'] in ('video/mp4','video/webm'):
            media.append(f"<figure class='media-card'><video controls preload='metadata' src='{src}'></video><figcaption>Project video {i+1}</figcaption></figure>")
    gallery=f"<div class='media-gallery'>{''.join(media)}</div>" if media else "<p class='empty'>No photos or videos uploaded yet.</p>"
    message_items=''.join(f"<li><strong>Community member</strong><span>{e(m['created_at'][:10])}</span><p>{safe(m['message'])}</p></li>" for m in messages)
    rule_list="""<ol class='message-rules'><li>Do not share names, phone numbers, email addresses, social handles, links or other identifying details.</li><li>Do not request direct contact or off-platform payments.</li><li>Be respectful: no harassment or threats. Owner-added blocked phrases also apply.</li></ol><p class='muted'>Messages that trigger these checks are removed and the account is automatically blocked for owner review. Detection can miss disguised details or flag harmless text.</p>"""
    chat=f"""<section class='project-chat' id='project-chat'><h2>Ask the builder</h2><p class='muted'>Messages appear under a community alias.</p>{rule_list}<form method='post' action='/project/message' class='builder-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='project_id' value='{p['id']}'><label>Message<textarea required minlength='10' maxlength='1200' name='message' rows='4' placeholder='How will this project help students?'></textarea></label><button class='cta-primary' type='submit'>Send message</button></form><ul class='clean-list message-list'>{message_items or '<li>No questions yet.</li>'}</ul></section>"""
    payment_enabled=bool(owner_payment_url())
    funding=(f"""<form method='post' action='/pledge' class='pledge-form'><input type='hidden' name='csrf' value='{e(user['csrf'])}'><input type='hidden' name='project_id' value='{p['id']}'><label>Support amount (USD)<input required type='number' min='0.01' max='10000000' step='0.01' name='amount' value='25'></label><button class='cta-primary full' type='submit'>Continue to owner payment</button></form>""" if payment_enabled else "<p class='funding-unavailable'>Funding is unavailable until the owner configures a payment link.</p>")
    recent=''.join(f"<li><strong>{money(pl['amount'])}</strong> from a community supporter</li>" for pl in pledges)
    sale=f"<p class='sale-pill block'>Licence / sale price: {money(p['price'])}</p>" if float(p['price'] or 0)>0 else ''
    body=f"""<section class='project-detail'><div class='project-main'><span class='tag'>{safe(p['category'])}</span><h1>{safe(p['title'])}</h1><p class='provider'>Student project</p><p class='lead'>{safe(p['summary'])}</p><div class='rich-text'>{safe(p['details']).replace(chr(10),'<br>')}</div><h2>Project showcase</h2>{gallery}<h2>Project files</h2><ul class='clean-list asset-list'>{''.join(asset_links) if asset_links else '<li>No public release files yet.</li>'}</ul>{chat}</div><aside class='fund-card'><h2>Support this project</h2><div class='progress big'><span style='width:{percent}%'></span></div><p class='progress-copy'><strong>{money(total)}</strong> owner-confirmed of {money(goal)} goal</p>{sale}{funding}<p class='muted'>The payment link goes to the owner, not the creator. The owner separately decides whether and how to support the founder. Visiting the link is not proof of payment.</p><h3>Recent confirmed support</h3><ul class='clean-list pledge-list'>{recent or '<li>No owner-confirmed payments yet.</li>'}</ul></aside></section>"""
    return page_shell(redact_public_text(p['title'],names),body,user,'marketplace')


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
    return "See official page"  # never invent a deadline

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

def render_admin(user, msg='', query=None):
    query = query or {}
    try: requested_user_page=int(query.get('users_page',['1'])[0])
    except (ValueError, TypeError): requested_user_page=1
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat(timespec='seconds')
    with db() as conn:
        def count(sql, params=()): return conn.execute(sql,params).fetchone()['n']
        stats={
          'Total users':count("SELECT COUNT(*) n FROM users WHERE email<>'demo@70scholar.local'"),
          'Active (7 days)':count("SELECT COUNT(*) n FROM users WHERE email<>'demo@70scholar.local' AND banned=0 AND (email_verified=1 OR admin_approved=1) AND last_active>=?",(cutoff,)),
          'Unverified emails':count("SELECT COUNT(*) n FROM users WHERE email<>'demo@70scholar.local' AND email_verified=0"),
          'Awaiting access':count("SELECT COUNT(*) n FROM users WHERE email<>'demo@70scholar.local' AND email_verified=0 AND admin_approved=0 AND banned=0"),
          'Blocked accounts':count("SELECT COUNT(*) n FROM users WHERE email<>'demo@70scholar.local' AND banned=1"),
          'Pending projects':count("SELECT COUNT(*) n FROM projects WHERE status='pending_review'"),
          'Open message flags':count("SELECT COUNT(*) n FROM message_incidents WHERE status='open'"),
        }
        total_user_rows=count('SELECT COUNT(*) n FROM users')
        user_pages=max(1,math.ceil(total_user_rows/50))
        user_page=max(1,min(requested_user_page,user_pages))
        users=conn.execute('SELECT * FROM users ORDER BY id DESC LIMIT 50 OFFSET ?',((user_page-1)*50,)).fetchall()
        pending_projects=conn.execute("SELECT p.*,u.name maker_name,u.email maker_email FROM projects p JOIN users u ON u.id=p.user_id WHERE p.status='pending_review' ORDER BY p.updated_at DESC").fetchall()
        pending_assets={p['id']:conn.execute('SELECT id,filename,mime,size FROM assets WHERE project_id=? ORDER BY id DESC',(p['id'],)).fetchall() for p in pending_projects}
        projects=conn.execute('SELECT p.*,u.name maker_name FROM projects p JOIN users u ON u.id=p.user_id ORDER BY p.updated_at DESC LIMIT 250').fetchall()
        payout_projects=conn.execute("SELECT p.id,p.title FROM projects p WHERE EXISTS (SELECT 1 FROM pledges pl WHERE pl.project_id=p.id AND pl.status='paid_confirmed') ORDER BY p.title,p.id").fetchall()
        opps=conn.execute('SELECT * FROM opportunities ORDER BY created_at DESC LIMIT 12').fetchall()
        logs=conn.execute('SELECT * FROM sync_logs ORDER BY id DESC LIMIT 5').fetchall()
        submissions=conn.execute("SELECT s.*,u.name submitter,u.email submitter_email FROM opportunity_submissions s JOIN users u ON u.id=s.user_id WHERE s.status='pending' ORDER BY s.id DESC LIMIT 30").fetchall()
        sources=conn.execute('SELECT * FROM feed_sources ORDER BY id').fetchall()
        payments=conn.execute("""SELECT pl.*,p.title,py.reference FROM pledges pl JOIN projects p ON p.id=pl.project_id
            JOIN payments py ON py.id=(SELECT MAX(id) FROM payments px WHERE px.pledge_id=pl.id AND px.provider='owner_link') ORDER BY CASE WHEN pl.status='payment_pending' THEN 0 ELSE 1 END, pl.id DESC LIMIT 100""").fetchall()
        disbursements=conn.execute('SELECT d.*,p.title FROM disbursements d JOIN projects p ON p.id=d.project_id ORDER BY d.id DESC LIMIT 30').fetchall()
        incidents=conn.execute("SELECT i.*,u.name,u.email,p.title FROM message_incidents i LEFT JOIN users u ON u.id=i.user_id LEFT JOIN projects p ON p.id=i.project_id WHERE i.status='open' ORDER BY i.id DESC LIMIT 100").fetchall()
        legacy=conn.execute("SELECT m.*,p.title FROM project_messages m JOIN projects p ON p.id=m.project_id WHERE m.status='legacy_review' ORDER BY m.id DESC LIMIT 100").fetchall()
    csrf=e(user['csrf'])
    cards=''.join(f"<div class='stat-card'><span>{e(k)}</span><strong>{v}</strong></div>" for k,v in stats.items())
    user_pagination = (f"<a class='ghost-button slim' href='/admin?users_page={user_page-1}#people'>← Previous</a>" if user_page>1 else '') + f" <span>Page {user_page} of {user_pages}</span> " + (f"<a class='ghost-button slim' href='/admin?users_page={user_page+1}#people'>Next →</a>" if user_page<user_pages else '')
    user_rows=''
    for u in users:
        protected=u['email'].lower()==OWNER_ADMIN_EMAIL
        access=('Blocked' if u['banned'] else 'Manual grant' if u['admin_approved'] else 'Verified email' if u['email_verified'] else 'Awaiting access')
        role_options=''.join(f"<option value='{r}' {'selected' if u['role']==r else ''}>{r}</option>" for r in ('student','maker','moderator'))
        role_form=(f"<form method='post' action='/admin/user/role' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='user_id' value='{u['id']}'><select name='role'>{role_options}</select><button class='ghost-button'>Save role</button></form>" if not protected else 'Owner admin')
        buttons=(f"<button name='action' value='grant' class='ghost-button'>Grant access</button><button name='action' value='revoke' class='ghost-button'>Revoke grant</button><button name='action' value='{'unban' if u['banned'] else 'ban'}' class='ghost-button'>{'Unblock' if u['banned'] else 'Block'}</button><button name='action' value='reset' class='ghost-button'>Reset password</button><button name='action' value='delete' class='ghost-button danger'>Delete</button>" if not protected else '')
        actions=f"<form method='post' action='/admin/user/action' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='user_id' value='{u['id']}'>{buttons}</form>"
        user_rows+=f"<tr><td>{u['id']}</td><td>{e(u['name'])}</td><td>{e(u['email'])}<br>{e(u['phone'] or 'No phone on older account')}</td><td>{'Verified' if u['email_verified'] else 'Unverified'}</td><td>{access}<br><small>{e(u['ban_reason'])}</small></td><td>{e((u['last_active'] or '')[:10] or 'Never')}</td><td>{role_form}</td><td>{actions}</td></tr>"
    pending_rows=''
    for p in pending_projects:
        files=pending_assets[p['id']]
        file_html=''.join(f"<li><a href='/download?id={a['id']}'>Review {e(a['filename'])}</a> · {e(a['mime'])} · {a['size']//1024+1} KB</li>" for a in files)
        pending_rows+=f"""<article class='mini-card moderation-card'><span class='tag'>Pending review</span><h3>{e(p['title'])}</h3><p class='provider'>Private owner record: {e(p['maker_name'])} · {e(p['maker_email'])}</p><p><strong>Category:</strong> {e(p['category'])} · <strong>Goal:</strong> {money(p['goal_amount'])} · <strong>Price:</strong> {money(p['price'])}</p><p><strong>Summary:</strong> {e(p['summary'])}</p><details><summary>Review complete description and all files</summary><p class='admin-project-detail'>{e(p['details']).replace(chr(10),'<br>')}</p><p class='muted'>Older links (not published): {e(p['demo_url'])} {e(p['repo_url'])}</p><ul class='clean-list'>{file_html or '<li>No files uploaded.</li>'}</ul></details><form method='post' action='/admin/project/action' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='project_id' value='{p['id']}'><input type='hidden' name='review_version' value='{p['review_version']}'><label class='admin-review-note'><input type='checkbox' name='confirmed' value='1'> I reviewed the complete text and every file for personal information and safety.</label><div class='card-actions'><button name='action' value='approve' class='cta-primary slim'>Approve &amp; publish</button><button name='action' value='reject' class='ghost-button'>Reject</button></div></form></article>"""
    project_rows=''.join(f"<tr><td>{p['id']}</td><td>{e(p['title'])}</td><td>{e(p['maker_name'])}</td><td>{e(p['status'].replace('_',' ').title())}</td><td>{e(p['updated_at'][:10])}</td><td><form method='post' action='/admin/project/action' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='project_id' value='{p['id']}'><button name='action' value='draft' class='ghost-button'>Make draft</button><button name='action' value='reject' class='ghost-button'>Reject</button><button name='action' value='delete' class='ghost-button danger'>Delete</button></form></td></tr>" for p in projects)
    opp_rows=''.join(f"<tr><td>{e(o['type'])}</td><td>{e(o['title'])}</td><td>{e(o['deadline'])}</td><td><a href='{e(anchor_url(o['url']))}' target='_blank' rel='noopener noreferrer'>Source ↗</a></td><td><form method='post' action='/admin/opportunity/delete'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='opportunity_id' value='{o['id']}'><button class='ghost-button'>Delete</button></form></td></tr>" for o in opps)
    log_rows=''.join(f"<li><strong>{e(l['imported'])}</strong> imported from {e(l['source'])}<br><span>{e(l['message'])}</span></li>" for l in logs)
    source_rows=''.join(f"<li><span>{e(r['url'])}</span><form method='post' action='/admin/source/fetch' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='url' value='{e(r['url'])}'><button class='ghost-button'>Fetch now</button></form><form method='post' action='/admin/source/delete' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='source_id' value='{r['id']}'><button class='ghost-button danger'>Remove</button></form></li>" for r in sources)
    def submission_card(r):
        preview=f"<img class='link-preview-image' src='/admin/submission/preview?id={r['id']}' alt='Preview from submitted link' loading='lazy'>" if r['fetched_image'] else ''
        fetched=f"<div class='fetched-box'><strong>What we found on the page</strong><p>{e(r['fetched_summary'])}</p></div>" if r['fetched_summary'] else ''
        edit=f"""<div class='admin-edit-grid'><label>Title<input name='title' value='{e(r['title'])}' maxlength='200'></label><label>Provider<input name='provider' value='{e(r['provider'])}' maxlength='160'></label><label>Deadline<input name='deadline' value='{e(r['deadline'])}' maxlength='80'></label></div><label class='admin-summary-label'>Published summary<textarea name='summary' rows='3' maxlength='1200'>{e(r['summary'])}</textarea></label>""" if r['source_mode']=='link' else ''
        return f"""<article class='mini-card moderation-card submission-card'>{preview}<span class='tag'>{e(r['type'])} · {'Link preview' if r['source_mode']=='link' else 'Manual entry'}</span><h3>{e(r['title'])}</h3><p>{e(r['summary'])}</p>{fetched}<p class='provider'>{e(r['submitter'])} · {e(r['submitter_email'])} · {e(r['deadline'])}</p><p><a href='{e(anchor_url(r['url']))}' target='_blank' rel='noopener noreferrer'>Open original link ↗</a></p><form method='post' action='/admin/submission/action' class='card-actions'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='submission_id' value='{r['id']}'>{edit}<div class='card-actions'><label class='admin-review-note'><input type='checkbox' name='confirmed' value='1'> I checked the official page</label><button name='action' value='approve' class='cta-primary slim'>Approve &amp; publish</button><button name='action' value='reject' class='ghost-button'>Reject</button></div></form></article>"""
    sub_rows=''.join(submission_card(r) for r in submissions)
    incident_rows=''.join(f"""<article class='mini-card'><span class='tag'>Flagged · {e(i['reason'])}</span><p><strong>{e(i['name'] or 'Deleted account')}</strong> · {e(i['email'] or '')} · {e(i['title'] or 'Project removed')}</p><p class='admin-private-text'>{e(i['raw_text'])}</p><form method='post' action='/admin/message/review'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='kind' value='incident'><input type='hidden' name='record_id' value='{i['id']}'><button name='action' value='reviewed' class='ghost-button'>Mark reviewed</button></form></article>""" for i in incidents)
    legacy_rows=''.join(f"""<article class='mini-card'><span class='tag'>Older message · not published</span><p><strong>{e(m['name'])}</strong> · {e(m['email'])} · {e(m['title'])}</p><p class='admin-private-text'>{e(m['message'])}</p><form method='post' action='/admin/message/review' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='kind' value='legacy'><input type='hidden' name='record_id' value='{m['id']}'><button name='action' value='approve' class='ghost-button'>Publish if safe</button><button name='action' value='delete' class='ghost-button danger'>Delete</button></form></article>""" for m in legacy)
    payment_rows=''
    for pl in payments:
        actions=''
        if pl['status']=='payment_pending':
            actions=f"""<form method='post' action='/admin/payment/action' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='pledge_id' value='{pl['id']}'><label class='admin-review-note'><input type='checkbox' name='confirmed' value='1'> I checked the provider record and verified this payment.</label><div class='card-actions'><button name='action' value='confirm' class='ghost-button'>Mark confirmed</button><button name='action' value='cancel' class='ghost-button danger'>Cancel request</button></div></form>"""
        payment_rows+=f"<li><strong>{money(pl['amount'])}</strong> · {e(pl['title'])}<br><span>{e(pl['reference'])} · {e(pl['status'].replace('_',' '))} · {e(pl['name'])} ({e(pl['email'])})</span>{actions}</li>"
    disbursement_rows=''.join(f"<li><strong>{money(d['amount'])}</strong> · {e(d['title'])} · {e(d['reference'])}<br><span>{e(d['note'])} · {e(d['created_at'][:10])}</span></li>" for d in disbursements)
    project_options=''.join(f"<option value='{p['id']}'>{e(p['title'])} · #{p['id']}</option>" for p in payout_projects)
    auto_on=get_setting('auto_sync','0')=='1'
    owner_link=get_setting('owner_payment_link','')
    blocked_phrases=get_setting('message_blocked_phrases','')
    body=f"""<section class='page-hero compact admin-hero'><p class='eyebrow'>Admin command center</p><h1>Manage reviews, people and funding.</h1><p>Owner-only tools for {e(OWNER_ADMIN_EMAIL)}. Personal records below are private.</p></section>
    <section class='admin-shell'><aside class='admin-sidebar'><p class='eyebrow eyebrow-dark'>Workspace</p><h2>Admin menu</h2><nav class='admin-nav' aria-label='Admin sections'><a href='#review'>① Review queue</a><a href='#content'>② Content</a><a href='#automation'>③ Automation</a><a href='#people'>④ People</a><a href='#safety'>⑤ Message safety</a><a href='#funding'>⑥ Funding</a></nav><p class='admin-sidebar-note'>Review project text, files and opportunity links before publication.</p></aside><div class='admin-main'><div class='stats-row'>{cards}</div>{flash(msg,'success') if msg else ''}
    <h2 class='admin-group-title' id='review'>1 · Review queue</h2><div class='dash-panel wide' id='submissions'><h2>Community submissions</h2><p class='muted'>Submissions stay private until approved. Verify the original page and deadlines.</p><div class='mini-grid'>{sub_rows or '<p class="empty">No submissions waiting for review.</p>'}</div></div>
    <div class='dash-panel wide'><h2>Project moderation queue</h2><p class='muted'>Open every project, read its full text and inspect each attachment for identifying information. Automatic filters cannot inspect file contents. Reject material you cannot approve safely.</p><div class='mini-grid'>{pending_rows or '<p class="empty">No projects waiting for review.</p>'}</div></div>
    <h2 class='admin-group-title' id='content'>2 · Content &amp; catalogue</h2><div class='dash-panel admin-form' id='add-opportunity'><h2>Add an opportunity manually</h2><form method='post' action='/admin/opportunity/add' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><div class='form-row'><label>Type<select name='type'><option>Scholarship</option><option>Internship</option><option>Competition</option><option>Grant</option><option>Hackathon</option><option>Opportunity</option></select></label><label>Deadline<input required name='deadline' placeholder='YYYY-MM-DD or See official page'></label></div><label>Title<input required name='title'></label><div class='form-row'><label>Provider<input required name='provider'></label><label>Country / region<input required name='country' value='Global'></label></div><label>Level<input required name='level' value='Students'></label><label>Application URL<input required type='url' name='url'></label><label>Summary<textarea required name='summary' rows='4'></textarea></label><label>Tags<input name='tags'></label><button class='cta-primary'>Post opportunity</button></form></div>
    <div class='dash-panel'><h2>Newest opportunities</h2><div class='table-wrap'><table><thead><tr><th>Type</th><th>Title</th><th>Deadline</th><th>Link</th><th>Action</th></tr></thead><tbody>{opp_rows}</tbody></table></div></div>
    <h2 class='admin-group-title' id='automation'>3 · Automation &amp; imports</h2><div class='dash-panel'><h2>Automatic opportunity posting</h2><p class='muted'>Imports from saved sources; verify deadlines. Auto-import is {'ON' if auto_on else 'OFF'}.</p><form method='post' action='/admin/auto-sync' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='enabled' value='{'0' if auto_on else '1'}'><button class='ghost-button'>Turn {'off' if auto_on else 'on'} auto-import</button></form><form method='post' action='/admin/sync' class='table-form'><input type='hidden' name='csrf' value='{csrf}'><button class='cta-primary slim'>Sync now</button></form><ul class='clean-list'>{log_rows or '<li>No syncs yet.</li>'}</ul></div>
    <div class='dash-panel'><h2>Auto-import &amp; source links</h2><form method='post' action='/admin/source/add' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><label>Add a feed or webpage link<input name='url' type='url' placeholder='https://example.com/feed' required></label><button class='cta-primary slim'>Save link</button></form><form method='post' action='/admin/source/fetch' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><label>Fetch a one-off link<input name='url' type='url' required></label><button class='ghost-button'>Fetch now</button></form><ul class='clean-list admin-source-list'>{source_rows or '<li>No saved sources.</li>'}</ul></div>
    <h2 class='admin-group-title' id='people'>4 · People &amp; records</h2><div class='dash-panel wide'><h2>User controls</h2><p class='muted'>Active = signed-in activity in the last 7 days. Email verification and a manual access grant are separate.</p><div class='user-pagination'>{user_pagination}</div><div class='table-wrap'><table><thead><tr><th>ID</th><th>Name</th><th>Private email / phone</th><th>Email proof</th><th>Access</th><th>Last active</th><th>Role</th><th>Actions</th></tr></thead><tbody>{user_rows}</tbody></table></div></div>
    <div class='dash-panel wide'><h2>Recent projects</h2><div class='table-wrap'><table><thead><tr><th>ID</th><th>Title</th><th>Owner</th><th>Status</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{project_rows}</tbody></table></div></div>
    <h2 class='admin-group-title' id='safety'>5 · Message safety</h2><div class='dash-panel wide'><h2>Message rules and detection</h2><p>Built-in checks prohibit contact details, names, off-platform payments, threats and harassment. Violations are suppressed and accounts automatically blocked; the owner account is exempt from blocking. Filters may miss disguised information or flag innocent wording. Review before unblocking.</p><form method='post' action='/admin/message/settings' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><label>Extra blocked phrases · one per line<textarea name='blocked_phrases' rows='4' maxlength='8000'>{e(blocked_phrases)}</textarea></label><button class='cta-primary slim'>Save phrases</button></form></div>
    <div class='dash-panel wide'><h2>Flagged messages · owner only</h2><p class='muted'>Raw flagged text is visible only here. Mark reviewed, then use User controls to unblock if appropriate.</p><div class='mini-grid'>{incident_rows or '<p class="empty">No open flags.</p>'}</div></div>
    <div class='dash-panel wide'><h2>Older messages awaiting review</h2><p class='muted'>Older messages were hidden during the privacy update. Publish only if safe; identifying fields are never shown to other users.</p><div class='mini-grid'>{legacy_rows or '<p class="empty">No older messages awaiting review.</p>'}</div></div>
    <h2 class='admin-group-title' id='funding'>6 · Funding &amp; disbursement records</h2><div class='dash-panel wide'><h2>Owner payment link</h2><p class='muted'>Use an HTTPS checkout link belonging to you. Leave blank to disable funding. 70Scholar cannot determine who owns a checkout link.</p><form method='post' action='/admin/payment/settings' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><label>Owner HTTPS payment link<input type='url' name='owner_payment_link' value='{e(owner_link)}' placeholder='https://your-payment-provider.example/checkout'></label><button class='cta-primary slim'>Save owner link</button></form></div>
    <div class='dash-panel wide'><h2>Payment requests</h2><p class='muted'>A visit to checkout is not proof of payment. Confirm only after checking your actual provider account. Amounts appear publicly only after your manual confirmation.</p><ul class='clean-list'>{payment_rows or '<li>No owner-link payment requests yet.</li>'}</ul></div>
    <div class='dash-panel wide'><h2>Record an external disbursement</h2><p class='muted'>This is a record only. Send money separately outside 70Scholar. A record cannot exceed the remaining owner-confirmed support for that project.</p><form method='post' action='/admin/disbursement' class='builder-form'><input type='hidden' name='csrf' value='{csrf}'><label>Project<select name='project_id' required><option value=''>Choose a project</option>{project_options}</select></label><div class='form-row'><label>Amount (USD)<input name='amount' type='number' min='0.01' step='0.01' required></label><label>External transfer reference<input name='reference' required maxlength='160'></label></div><label>Private note<input name='note' maxlength='400'></label><label class='admin-review-note'><input type='checkbox' name='confirmed' value='1' required> The transfer has already been made outside 70Scholar.</label><button class='cta-primary slim'>Record disbursement</button></form><ul class='clean-list'>{disbursement_rows or '<li>No external transfers recorded.</li>'}</ul></div>
    </div></section>"""
    return page_shell('Admin',body,user,'admin')


class ScholarHandler(BaseHTTPRequestHandler):
    server_version = "70ScholarMVP/1.0"
    def log_message(self, fmt, *args):
        message = fmt % args
        message = re.sub(r'(?i)(token=)[^&\s"\']+', r'\1[redacted]', message)
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), message))
    def parse_cookies(self):
        c = cookies.SimpleCookie(); raw = self.headers.get("Cookie")
        if raw: c.load(raw)
        return c
    def current_user(self):
        morsel = self.parse_cookies().get(SESSION_COOKIE)
        if not morsel: return None
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
            user = conn.execute("""SELECT u.*,s.csrf,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>? AND u.banned=0 AND (u.email_verified=1 OR u.admin_approved=1)""",
                (token_hash(morsel.value),now_iso())).fetchone()
            if user:
                cutoff=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat(timespec='seconds')
                if not user['last_active'] or user['last_active'] < cutoff:
                    conn.execute('UPDATE users SET last_active=? WHERE id=?', (now_iso(),user['id']))
            return user
    def send_html(self, text, status=200, headers=None):
        data=text.encode(); self.send_response(status); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Cache-Control","private, no-store"); self.send_header("Referrer-Policy","no-referrer")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)
    def send_json(self, payload, status=200):
        data=json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Cache-Control","private, no-store"); self.end_headers(); self.wfile.write(data)
    def send_plain(self, text, content_type="text/plain"):
        data=text.encode(); self.send_response(200); self.send_header("Content-Type", content_type + "; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def build_sitemap(self):
        host = self.headers.get("Host", "localhost:8080")
        base = "https://" + host if "localhost" not in host and "127.0.0.1" not in host else "http://" + host
        urls = ["/", "/signup", "/login"]
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
        path=urlparse(self.path).path
        user=self.current_user()
        if not path.startswith('/static/') and path not in PUBLIC_GET_PATHS and not self.gate(user): return
        self.send_response(200)
        self.send_header('Content-Type','text/plain; charset=utf-8' if path=='/version' else 'text/html; charset=utf-8')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path; query=parse_qs(parsed.query); user=self.current_user()
        if path == "/robots.txt": return self.send_plain("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", "text/plain")
        if path == "/sitemap.xml": return self.send_plain(self.build_sitemap(), "application/xml")
        if path == "/version": return self.send_plain(f"70Scholar {APP_VERSION} - privacy, owner review and funding", "text/plain")
        if path.startswith("/static/"): return self.serve_static(path)
        if path.startswith("/uploads/profiles/"):
            if not self.gate(user): return None
            return self.serve_profile_upload(path, user)
        if path not in PUBLIC_GET_PATHS and not self.gate(user): return None
        if path == "/download": return self.serve_download(query, user)
        if path == "/admin/submission/preview": return self.serve_submission_preview(query, user)
        if path == "/": return self.send_html(render_home(user))
        if path == "/signup": return self.send_html(render_auth("signup"))
        if path == "/login": return self.send_html(render_auth("login", next_url=query.get("next", [""])[0]))
        if path == "/verify-email": return self.handle_verify_email(query)
        if path == "/forgot-password": return self.send_html(render_forgot_password())
        if path == "/reset-password": return self.send_html(render_reset_password(query.get("token", [""])[0]))
        if path == "/opportunities": return self.send_html(render_opportunities(user, query))
        if path == "/courses": return self.send_html(render_courses(user))
        if path == "/exams": return self.send_html(render_exams(user))
        if path == "/programs": return self.send_html(render_programs(user))
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
            return self.send_html(render_admin(user,query=query))
        if path == "/payment/start": return self.handle_payment_start(user, query)
        if path == "/payment/success": return self.handle_payment_success(user, query)
        if path == "/marketplace": return self.send_html(render_marketplace(user))
        if path == "/project": return self.send_html(render_project_detail(user, query.get("id", [""])[0]))
        return self.send_html(page_shell("Not found", "<section class='panel-section'><h1>Page not found</h1></section>", user), 404)
    def serve_static(self, path):
        target=(STATIC_DIR / path.removeprefix("/static/")).resolve()
        if STATIC_DIR.resolve() not in target.parents or not target.is_file(): self.send_response(404); self.end_headers(); return
        data=target.read_bytes(); self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def serve_profile_upload(self, path, user):
        rel = path.removeprefix('/uploads/profiles/')
        match = re.fullmatch(r'user-(\d+)-[a-f0-9]+\.(?:jpg|jpeg|png|gif|webp)', rel, re.I)
        if not match or (int(match.group(1)) != user['id'] and not is_admin(user)):
            self.send_response(403); self.end_headers(); return
        base = (UPLOAD_DIR / 'profiles').resolve(); target=(base / rel).resolve()
        if not target.is_file() or target.parent != base:
            self.send_response(404); self.end_headers(); return
        data=target.read_bytes(); self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data))); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','private, no-store'); self.end_headers(); self.wfile.write(data)

    def serve_download(self, query, user):
        asset_id=query.get('id',[''])[0]
        if not asset_id.isdigit(): self.send_response(404); self.end_headers(); return
        with db() as conn:
            asset=conn.execute('SELECT a.*,p.status,p.user_id owner_id FROM assets a JOIN projects p ON p.id=a.project_id WHERE a.id=?',(int(asset_id),)).fetchone()
        if not asset or (asset['status'] != 'public' and user['id'] != asset['owner_id'] and not is_admin(user)):
            self.send_response(403 if asset else 404); self.end_headers(); return
        root=UPLOAD_DIR.resolve(); path=Path(asset['stored_path']).resolve()
        if root not in path.parents or not path.is_file():
            # Legacy rows contain an absolute location. If the operator moved the
            # uploads directory to a persistent disk, resolve the generated flat
            # filename inside that new directory without following external paths.
            name=Path(asset['stored_path']).name
            expected=rf"{asset['project_id']}-[a-f0-9]{{16}}-[A-Za-z0-9._-]+"
            path=(root/name).resolve() if re.fullmatch(expected,name) else root
        if root not in path.parents or not path.is_file(): self.send_response(404); self.end_headers(); return
        data=path.read_bytes()
        safe_mimes={'image/jpeg':'.jpg','image/png':'.png','image/gif':'.gif','image/webp':'.webp','video/mp4':'.mp4','video/webm':'.webm'}
        inline = bool(query.get('inline')) and asset['mime'] in safe_mimes
        ctype=asset['mime'] if inline else 'application/octet-stream'
        suffix=safe_mimes.get(asset['mime'], '.bin')
        self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"sandbox; default-src 'none'")
        self.send_header('Cache-Control','private, no-store')
        self.send_header('Content-Disposition',f"{'inline' if inline else 'attachment'}; filename=\"project-file-{asset['id']}{suffix}\"")
        self.end_headers(); self.wfile.write(data)

    def serve_submission_preview(self, query, user):
        if not is_admin(user): self.send_response(403); self.end_headers(); return
        sid=query.get('id',[''])[0]
        if not sid.isdigit(): self.send_response(404); self.end_headers(); return
        with db() as conn:
            row=conn.execute('SELECT fetched_image FROM opportunity_submissions WHERE id=?',(int(sid),)).fetchone()
        if not row or not row['fetched_image']: self.send_response(404); self.end_headers(); return
        try:
            data, ctype=safe_http_get_bytes(row['fetched_image'],max_bytes=2_000_000)
            ctype=ctype.split(';')[0].strip()
            if ctype not in ('image/jpeg','image/png','image/gif','image/webp'): raise ValueError('Unsupported image')
        except Exception:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','private, max-age=300'); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        # Browser form submissions should originate from this host, including the
        # unauthenticated login form. API clients without Origin still use CSRF
        # tokens for authenticated actions.
        origin=self.headers.get('Origin')
        if origin:
            try:
                parsed_origin=urlparse(origin)
                same_origin=(parsed_origin.scheme in ('http','https') and
                    parsed_origin.netloc.lower()==self.headers.get('Host','').lower() and
                    not parsed_origin.path and not parsed_origin.query and not parsed_origin.fragment)
            except Exception:
                same_origin=False
            if not same_origin:
                return self.send_html(render_notice('Security check failed','Please submit this form from the 70Scholar website.'),403)
        path=urlparse(self.path).path; user=self.current_user()
        if path not in PUBLIC_POST_PATHS and not self.gate(user): return None
        if path == "/signup": return self.handle_signup(self.read_form())
        if path == "/login": return self.handle_login(self.read_form())
        if path == "/forgot-password": return self.handle_forgot_password(self.read_form())
        if path == "/reset-password": return self.handle_reset_password(self.read_form())
        if path == "/account/verify-email":
            form=self.read_form()
            if not self.verify_csrf(user,form): return self.send_html(render_notice('Security check failed','Please reload the page and try again.',user),403)
            if user['email_verified']: return self.send_html(render_account(user,'Your email is already verified.'))
            try:
                send_verification_email(user['id'],user['email'],user['name'])
                return self.send_html(render_account(user,'A verification link was sent. Check your inbox.'))
            except Exception as ex:
                print('Verification email failed:',ex,file=sys.stderr)
                return self.send_html(render_account(user,'Email delivery is unavailable. Your email remains unverified; please try again later.'),503)
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
        if path == "/opportunity/submit-link":
            form=self.read_form()
            if not self.verify_csrf(user, form): return self.send_html(page_shell("Security check failed", "CSRF check failed.", user), 403)
            return self.handle_link_submission(user, form)
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
        if path in ("/admin/payment/settings", "/admin/payment/action", "/admin/disbursement", "/admin/message/settings", "/admin/message/review"):
            form=self.read_form()
            if not is_admin(user): return self.send_html(page_shell('Forbidden','Owner admin only.',user),403)
            if not self.verify_csrf(user,form): return self.send_html(page_shell('Security check failed','CSRF check failed.',user),403)
            return {
                '/admin/payment/settings': self.handle_payment_settings,
                '/admin/payment/action': self.handle_admin_payment_action,
                '/admin/disbursement': self.handle_admin_disbursement,
                '/admin/message/settings': self.handle_message_settings,
                '/admin/message/review': self.handle_message_review,
            }[path](user,form)
        if path == "/project/message": return self.handle_project_message(user, self.read_form())
        if path == "/pledge": return self.handle_pledge(user, self.read_form())
        if path == "/api/upload": return self.handle_upload(user)
        return self.send_html(page_shell("Not found", "<section class='panel-section'><h1>Page not found</h1></section>", user), 404)
    def consume_email_token(self, token, purpose):
        if not token: return None
        th = token_hash(token)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
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
        if user and EMAIL_ENABLED:
            try: send_password_reset_email(user['id'],user['email'],user['name'])
            except Exception as ex: print('Password reset email failed:',ex,file=sys.stderr)
        return self.send_html(render_forgot_password("If that account exists and email delivery is available, a reset link has been sent."))
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
            row=conn.execute("SELECT id FROM users WHERE email=? AND banned=0 AND (email_verified=1 OR admin_approved=1)",(email,)).fetchone()
            if not row: return self.send_html(render_auth('login','This account cannot sign in.'),403)
            conn.execute('INSERT INTO sessions(token_hash,user_id,csrf,created_at,expires_at) VALUES(?,?,?,?,?)',(token_hash(token),row['id'],csrf,now_iso(),expires.isoformat(timespec='seconds')))
            conn.execute('UPDATE users SET last_active=? WHERE id=?',(now_iso(),row['id']))
        secure = '; Secure' if self.headers.get('X-Forwarded-Proto','').lower() == 'https' else ''
        self.redirect(location, {'Set-Cookie':f'{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={14*24*60*60}{secure}'})

    def handle_signup(self, form):
        name=form.get('name','').strip()[:120]; email=form.get('email','').strip().lower()[:180]; password=form.get('password','')
        phone=form.get('phone','').strip()[:32]
        account_type=(form.get('account_type') or '').strip()[:40]
        career=(form.get('career') or '').strip()[:120]; education_level=(form.get('education_level') or '').strip()[:80]
        if account_type not in ACCOUNT_TYPES: account_type=''
        phone_digits=re.sub(r'\D','',phone)
        if (len(name)<2 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email)
                or len(password)<8 or len(password)>256 or not re.fullmatch(r'[+\d\s().-]+',phone)
                or not 7 <= len(phone_digits) <= 16):
            return self.send_html(render_auth('signup','Please provide a name, valid email, private phone number and password of at least 8 characters.'),400)
        salt, hashed=hash_password(password)
        try:
            with db() as conn:
                cur=conn.execute("""INSERT INTO users(name,email,password_hash,salt,role,email_verified,admin_approved,phone,created_at,account_type,career,education_level)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(name,email,hashed,salt,'student',0,0,phone,now_iso(),account_type,career,education_level))
                user_id=cur.lastrowid
        except sqlite3.IntegrityError:
            return self.send_html(render_auth('signup','That email already has an account.'),409)
        if EMAIL_ENABLED:
            try:
                send_verification_email(user_id,email,name)
                return self.send_html(render_notice('Check your email','Your account was created. Verify your email to sign in, or ask the owner to grant access.'))
            except Exception as ex:
                print('Verification delivery failed; account remains unverified:',ex,file=sys.stderr)
        return self.send_html(render_notice('Account awaiting access','Your account was created but email verification is unavailable. Ask the owner admin to grant access, or try again when email delivery is configured.'))

    def handle_login(self, form):
        email=form.get('email','').strip().lower(); password=form.get('password','')
        with db() as conn: user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if not user or not verify_password(password,user['salt'],user['password_hash']):
            return self.send_html(render_auth('login','Incorrect email or password.'),401)
        if user['banned']:
            return self.send_html(render_auth('login','This account is blocked. Contact the owner for a review.'),403)
        if not user['email_verified'] and not user['admin_approved']:
            sent=False
            if EMAIL_ENABLED:
                try: send_verification_email(user['id'],user['email'],user['name']); sent=True
                except Exception as ex: print('Verification email failed:',ex,file=sys.stderr)
            msg = ('Please verify your email. A new link was sent, or the owner can grant access.' if sent else
                   'Please verify your email or ask the owner to grant access. Email delivery is currently unavailable.')
            return self.send_html(render_auth('login',msg),403)
        nxt=(form.get('next') or '').strip()
        if not (nxt.startswith('/') and not nxt.startswith('//') and '\\' not in nxt and not any(ord(c)<32 for c in nxt)):
            nxt='/dashboard'
        return self.create_session_and_redirect(email,nxt)
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
        signatures = {'image/jpeg':(b'\xff\xd8\xff','.jpg'), 'image/png':(b'\x89PNG\r\n\x1a\n','.png'),
                      'image/gif':(b'GIF8','.gif'), 'image/webp':(b'RIFF','.webp')}
        if mime not in signatures or not content.startswith(signatures[mime][0]) or (mime=='image/webp' and content[8:12] != b'WEBP'):
            return self.send_json({'ok':False,'error':'Choose a valid JPG, PNG, GIF or WebP image.'},400)
        if len(content) > 10 * 1024 * 1024:
            return self.send_json({"ok":False,"error":"Profile photo max is 10 MB"}, 400)
        profile_dir=UPLOAD_DIR / "profiles"; profile_dir.mkdir(parents=True, exist_ok=True)
        ext=signatures[mime][1]
        stored=profile_dir / f"user-{user['id']}-{secrets.token_hex(8)}{ext}"
        stored.write_bytes(content)
        url=f"/uploads/profiles/{stored.name}"
        with db() as conn:
            conn.execute("UPDATE users SET profile_photo_url=? WHERE id=?", (url, user["id"]))
        return self.send_json({"ok":True,"url":url})
    def handle_project_save(self, user, form):
        title=form.get('title','').strip()[:160]; category=form.get('category','').strip()[:80]
        summary=form.get('summary','').strip()[:600]; details=form.get('details','').strip()[:10000]
        if not all((title,category,summary,details)):
            return self.send_html(render_notice('Project details needed','Please fill in the title, category, summary and description.',user),400)
        requested=form.get('status') == 'public'
        status='pending_review' if requested else 'draft'
        goal=parse_amount(form.get('goal_amount') or '0',minimum=Decimal('0'))
        price=parse_amount(form.get('price') or '0',minimum=Decimal('0'))
        if goal is None or price is None:
            return self.send_html(render_notice('Invalid amount','Enter non-negative amounts with at most two decimal places.',user),400)
        if requested and (len(summary)<40 or len(details)<120):
            return self.send_html(render_notice('More detail needed','Before requesting review, use at least 40 characters in your summary and 120 in your description. Explain the problem, solution and funding plans.',user),400)
        pid=form.get('project_id','').strip()
        with db() as conn:
            if pid:
                if not pid.isdigit() or not conn.execute('SELECT id FROM projects WHERE id=? AND user_id=?',(int(pid),user['id'])).fetchone():
                    return self.send_html(render_notice('Project not found','Only the project owner can edit this project.',user),404)
                conn.execute("UPDATE projects SET title=?,category=?,summary=?,details=?,goal_amount=?,price=?,status=?,updated_at=?,review_version=review_version+1 WHERE id=? AND user_id=?",(title,category,summary,details,goal,price,status,now_iso(),int(pid),user['id']))
                project_id=int(pid)
            else:
                cur=conn.execute("INSERT INTO projects(user_id,title,category,summary,details,goal_amount,price,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(user['id'],title,category,summary,details,goal,price,status,now_iso(),now_iso()))
                project_id=cur.lastrowid
        return self.redirect(f'/workspace?edit={project_id}')

    def _moderate_message(self, conn, user, pid, text):
        names=_registered_names(conn)
        row=conn.execute("SELECT value FROM settings WHERE key='message_blocked_phrases'").fetchone()
        blocked=(row['value'].splitlines() if row else [])
        reason=message_violation(text,names,blocked)
        if not reason: return ''
        conn.execute('INSERT INTO message_incidents(user_id,project_id,raw_text,reason,created_at) VALUES(?,?,?,?,?)',(user['id'],pid,text,reason,now_iso()))
        if not is_admin(user):
            conn.execute('UPDATE users SET banned=1,ban_reason=? WHERE id=?',(reason,user['id']))
            conn.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        return reason

    def handle_project_message(self, user, form):
        if not self.verify_csrf(user,form): return self.send_html(render_notice('Security check failed','Please reload the page and try again.',user),403)
        pid=form.get('project_id',''); message=form.get('message','').strip()[:1200]
        if not pid.isdigit() or len(message)<10:
            return self.send_html(render_notice('Message too short','Write at least 10 characters without sharing personal details.',user),400)
        with db() as conn:
            project=conn.execute("SELECT id FROM projects WHERE id=? AND status='public'",(int(pid),)).fetchone()
            if not project: return self.redirect('/marketplace')
            reason=self._moderate_message(conn,user,int(pid),message)
            if not reason:
                conn.execute("INSERT INTO project_messages(project_id,user_id,name,email,message,created_at,status) VALUES(?,?,?,?,?,?,?)",(int(pid),user['id'],'Community member','',message,now_iso(),'visible'))
        if reason:
            explanation=('Your message was removed. Your account has been blocked for owner review; contact the helpline to appeal.' if not is_admin(user) else 'Your message was removed for owner review. The owner account is not blocked.')
            return self.send_html(render_notice('Message removed',explanation),403)
        return self.redirect(f'/project?id={pid}#project-chat')

    def handle_pledge(self, user, form):
        if not self.verify_csrf(user,form): return self.send_html(render_notice('Security check failed','Please reload and try again.',user),403)
        pid=form.get('project_id',''); amount=parse_amount(form.get('amount',''))
        link=owner_payment_url()
        if not link: return self.send_html(render_notice('Funding unavailable','The owner has not configured a payment link yet.',user),503)
        if not pid.isdigit() or amount is None or form.get('provider','owner_checkout') not in ('','owner_checkout'):
            return self.send_html(render_notice('Invalid support request','Choose a valid project and amount.',user),400)
        raw_message=(form.get('message') or '').strip()[:600]
        with db() as conn:
            project=conn.execute("SELECT id FROM projects WHERE id=? AND status='public'",(int(pid),)).fetchone()
            if not project: return self.redirect('/marketplace')
            reason=self._moderate_message(conn,user,int(pid),raw_message) if raw_message else ''
            if not reason:
                cur=conn.execute("""INSERT INTO pledges(project_id,user_id,name,email,amount,message,status,created_at,platform_fee,creator_amount)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",(int(pid),user['id'],user['name'],user['email'],amount,'','payment_pending',now_iso(),0,0))
                pledge_id=cur.lastrowid
                ref=f"70S-{pledge_id}-{secrets.token_hex(4).upper()}"
                conn.execute("INSERT INTO payments(pledge_id,provider,reference,status,checkout_url,created_at) VALUES(?,?,?,?,?,?)",(pledge_id,'owner_link',ref,'pending',link,now_iso()))
        if reason:
            return self.send_html(render_notice('Message removed', 'The message was removed for owner review.' if is_admin(user) else 'The message was removed and the account is blocked for owner review. Contact the helpline to appeal.'),403)
        return self.redirect(f'/payment/start?pledge_id={pledge_id}')

    def handle_admin_add_opportunity(self, user, form):
        fields = {k: form.get(k, "").strip() for k in ["type","title","provider","country","level","deadline","url","summary","tags"]}
        if not all(fields[k] for k in ["type","title","provider","country","level","deadline","url","summary"]) or not external_http_link(fields['url']):
            return self.send_html(render_admin(user, "Complete all required opportunity fields and use an ordinary public HTTP or HTTPS link."), 400)
        try:
            with db() as conn:
                conn.execute("""INSERT INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (fields["type"],fields["title"],fields["provider"],fields["country"],fields["level"],fields["deadline"],fields["url"],fields["summary"],fields["tags"],"Admin posted",now_iso()))
        except sqlite3.IntegrityError:
            return self.send_html(render_admin(user, "That opportunity title already exists."), 409)
        return self.send_html(render_admin(user, "Opportunity posted successfully."))
    def handle_admin_project_action(self, user, form):
        pid=form.get('project_id',''); action=form.get('action','')
        if not pid.isdigit() or action not in ('approve','reject','draft','delete'):
            return self.send_html(render_admin(user,'Invalid project action.'),400)
        with db() as conn:
            project=conn.execute('SELECT * FROM projects WHERE id=?',(int(pid),)).fetchone()
        if not project: return self.send_html(render_admin(user,'Project not found.'),404)
        if action=='approve' and (project['status']!='pending_review' or form.get('confirmed')!='1' or not form.get('review_version','').isdigit()):
            return self.send_html(render_admin(user,'Approve only a pending project after confirming that you reviewed its text and every uploaded file.'),400)
        try:
            with db() as conn:
                if action=='delete':
                    conn.execute('DELETE FROM projects WHERE id=?',(int(pid),))
                else:
                    status={'approve':'public','reject':'rejected','draft':'draft'}[action]
                    # Check pending status in the same update, to avoid approving an edit made during review.
                    if action=='approve':
                        cur=conn.execute("UPDATE projects SET status='public',updated_at=? WHERE id=? AND status='pending_review' AND review_version=?",(now_iso(),int(pid),int(form['review_version'])))
                        if cur.rowcount!=1: raise ValueError('Project changed during review; please review it again.')
                    else: conn.execute('UPDATE projects SET status=?,updated_at=? WHERE id=?',(status,now_iso(),int(pid)))
                    conn.execute('INSERT INTO moderation_logs(project_id,admin_id,action,note,created_at) VALUES(?,?,?,?,?)',(int(pid),user['id'],action,(form.get('note') or '')[:300],now_iso()))
        except (sqlite3.IntegrityError,ValueError) as ex:
            return self.send_html(render_admin(user,f'Could not complete project action: {str(ex)[:120]}'),400)
        return self.send_html(render_admin(user,f'Project {action} action completed.'))

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
        uid=form.get('user_id',''); action=form.get('action','')
        if not uid.isdigit() or action not in ('grant','revoke','ban','unban','reset','delete'):
            return self.send_html(render_admin(user,'Invalid user action.'),400)
        with db() as conn: target=conn.execute('SELECT * FROM users WHERE id=?',(int(uid),)).fetchone()
        if not target: return self.send_html(render_admin(user,'User not found.'),404)
        if target['email'].lower()==OWNER_ADMIN_EMAIL and action in ('revoke','ban','delete'):
            return self.send_html(render_admin(user,'The owner account cannot be blocked, revoked or deleted.'),400)
        message=''
        try:
            with db() as conn:
                if action=='grant':
                    conn.execute('UPDATE users SET admin_approved=1 WHERE id=?',(int(uid),))
                    message='Access granted; email verification status was not changed.'
                elif action=='revoke':
                    conn.execute('UPDATE users SET admin_approved=0 WHERE id=?',(int(uid),))
                    if not target['email_verified']: conn.execute('DELETE FROM sessions WHERE user_id=?',(int(uid),))
                    message='Manual access grant removed. A verified email still permits access.'
                elif action=='ban':
                    conn.execute("UPDATE users SET banned=1,ban_reason='Blocked by owner' WHERE id=?",(int(uid),))
                    conn.execute('DELETE FROM sessions WHERE user_id=?',(int(uid),)); message='User blocked and sessions ended.'
                elif action=='unban':
                    conn.execute("UPDATE users SET banned=0,ban_reason='' WHERE id=?",(int(uid),)); message='User unblocked. Email verification or a manual grant is still required.'
                elif action=='reset':
                    temp='Temp'+secrets.token_urlsafe(10).replace('-','A').replace('_','B')[:12]+'!'
                    salt,hashed=hash_password(temp)
                    conn.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,int(uid)))
                    conn.execute('DELETE FROM sessions WHERE user_id=?',(int(uid),)); message=f"Temporary password for {target['email']}: {temp}"
                elif action=='delete':
                    conn.execute('DELETE FROM users WHERE id=?',(int(uid),)); message='User deleted.'
        except sqlite3.IntegrityError:
            return self.send_html(render_admin(user,'This user cannot be deleted while protected financial records remain.'),400)
        return self.send_html(render_admin(user,message))

    def handle_opportunity_submission(self, user, form):
        title=(form.get("title") or "").strip()[:200]
        url=(form.get("url") or "").strip()[:500]
        summary=(form.get("summary") or "").strip()[:1200]
        if not title or not summary or not external_http_link(url):
            return self.send_html(render_submit(user, "Please provide a title, summary and an ordinary public HTTP or HTTPS link.", "error"), 400)
        with db() as conn:
            conn.execute("""INSERT INTO opportunity_submissions(user_id,type,title,provider,country,level,deadline,url,summary,tags,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user["id"], (form.get("type") or "Opportunity")[:80], title,
                 (form.get("provider") or "Community")[:160], (form.get("country") or "Global / verify")[:100],
                 (form.get("level") or "Students")[:160], (form.get("deadline") or "See official page")[:80],
                 url, summary, (form.get("tags") or "")[:200], "pending", now_iso()))
        return self.send_html(render_submit(user, "Submitted! The admin will review it before it goes public."))

    def handle_link_submission(self, user, form):
        url = (form.get("url") or "").strip()
        note = (form.get("note") or "").strip()[:600]
        if urlparse(url).scheme not in ("http", "https"):
            return self.send_html(render_submit(user, "Please enter a valid http or https link.", "error"), 400)
        try:
            info = fetch_page_metadata(url)
        except Exception as ex:
            return self.send_html(render_submit(user, f"We couldn't read that link: {str(ex)[:160]}", "error"), 400)
        image_url = info["image"]
        if image_url:
            image_url = urljoin(url, image_url)
            if urlparse(image_url).scheme not in ("http", "https"):
                image_url = ""
        with db() as conn:
            conn.execute("""INSERT INTO opportunity_submissions
                (user_id,type,title,provider,country,level,deadline,url,summary,tags,status,created_at,source_mode,fetched_summary,fetched_image)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user["id"], info["type"], info["title"], info["site"], "Verify on source",
                 "See official page", info["deadline"], url, info["summary"], "link-submission",
                 "pending", now_iso(), "link", (note + " " + info["summary"])[:900], image_url))
        return self.send_html(render_submit(user,
            f"Link received. We found “{info['title']}” and sent the details to the admin for review."))

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
        if action == "approve" and form.get("confirmed") != "1":
            return self.send_html(render_admin(user, "Please confirm that you checked the official page before publishing."), 400)
        with db() as conn:
            row=conn.execute("SELECT * FROM opportunity_submissions WHERE id=?", (int(sid),)).fetchone()
            if not row: return self.send_html(render_admin(user, "Submission not found."), 404)
            if action == "approve":
                title=(form.get("title") or row["title"]).strip()[:200]
                provider=(form.get("provider") or row["provider"]).strip()[:160]
                deadline=(form.get("deadline") or row["deadline"]).strip()[:80]
                summary=(form.get("summary") or row["summary"]).strip()[:1200]
                cur=conn.execute("""INSERT OR IGNORE INTO opportunities(type,title,provider,country,level,deadline,url,summary,tags,source,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (row["type"], title, provider, row["country"], row["level"], deadline,
                     row["url"], summary, row["tags"], "community", now_iso()))
                if cur.rowcount:
                    conn.execute("UPDATE opportunities SET auto_description=? WHERE id=?",
                        (make_auto_description({"type":row["type"],"title":row["title"],"provider":row["provider"],
                          "country":row["country"],"level":row["level"],"deadline":deadline,"summary":summary}), cur.lastrowid))
                conn.execute("UPDATE opportunity_submissions SET status='approved', reviewed_at=? WHERE id=?", (now_iso(), int(sid)))
                return self.send_html(render_admin(user, f"Approved and published: {title}"))
            conn.execute("UPDATE opportunity_submissions SET status='rejected', reviewed_at=? WHERE id=?", (now_iso(), int(sid)))
        return self.send_html(render_admin(user, "Submission rejected."))

    def handle_admin_delete_opportunity(self, user, form):
        oid=form.get("opportunity_id","")
        if oid.isdigit():
            with db() as conn:
                conn.execute("DELETE FROM opportunities WHERE id=?", (int(oid),))
        return self.send_html(render_admin(user, "Opportunity deleted."))
    def handle_payment_settings(self, user, form):
        link=(form.get('owner_payment_link') or '').strip()
        if link:
            try:
                u=urlparse(link)
                valid=(u.scheme=='https' and bool(u.hostname) and not u.username and not u.password and len(link)<=1000 and not any(ord(c)<32 or c.isspace() for c in link))
            except Exception: valid=False
            if not valid: return self.send_html(render_admin(user,'Enter a valid HTTPS payment URL with no embedded credentials, or leave it empty to disable funding.'),400)
        set_setting('owner_payment_link',link)
        return self.send_html(render_admin(user,'Owner payment link saved.' if link else 'Funding link disabled.'))

    def handle_admin_payment_action(self, user, form):
        pledge_id=form.get('pledge_id',''); action=form.get('action','')
        if not pledge_id.isdigit() or action not in ('confirm','cancel'):
            return self.send_html(render_admin(user,'Invalid payment action.'),400)
        if action=='confirm' and form.get('confirmed')!='1':
            return self.send_html(render_admin(user,'Check the payment provider records and confirm your review before marking a payment confirmed.'),400)
        with db() as conn:
            pledge=conn.execute("SELECT * FROM pledges WHERE id=? AND status='payment_pending'",(int(pledge_id),)).fetchone()
            if not pledge: return self.send_html(render_admin(user,'Only pending owner-link payments may be changed.'),400)
            status='paid_confirmed' if action=='confirm' else 'cancelled'
            conn.execute('UPDATE pledges SET status=? WHERE id=?',(status,int(pledge_id)))
            conn.execute("UPDATE payments SET status=? WHERE pledge_id=? AND provider='owner_link'",(status,int(pledge_id)))
        return self.send_html(render_admin(user,'Payment manually confirmed from owner records.' if action=='confirm' else 'Support request cancelled.'))

    def handle_admin_disbursement(self, user, form):
        pid=form.get('project_id',''); amount=parse_amount(form.get('amount',''))
        ref=(form.get('reference') or '').strip()[:160]; note=(form.get('note') or '').strip()[:400]
        if not pid.isdigit() or amount is None or not ref or form.get('confirmed')!='1':
            return self.send_html(render_admin(user,'Enter a project, amount and external transfer reference, and confirm the transfer was already made.'),400)
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            project=conn.execute('SELECT id FROM projects WHERE id=?',(int(pid),)).fetchone()
            confirmed=conn.execute("SELECT COALESCE(SUM(amount),0) AS n FROM pledges WHERE project_id=? AND status='paid_confirmed'",(int(pid),)).fetchone()['n']
            recorded=conn.execute('SELECT COALESCE(SUM(amount),0) AS n FROM disbursements WHERE project_id=?',(int(pid),)).fetchone()['n']
            allowed=bool(project) and Decimal(str(amount)) <= Decimal(str(round(confirmed,2)))-Decimal(str(round(recorded,2)))
            if allowed:
                conn.execute('INSERT INTO disbursements(project_id,amount,reference,note,recorded_by,created_at) VALUES(?,?,?,?,?,?)',(int(pid),amount,ref,note,user['id'],now_iso()))
        if not allowed:
            return self.send_html(render_admin(user,'The project must exist and the recorded amount cannot exceed its remaining owner-confirmed support.'),400)
        return self.send_html(render_admin(user,'External disbursement recorded. 70Scholar did not transfer any money.'))

    def handle_message_settings(self, user, form):
        raw=(form.get('blocked_phrases') or '')[:8000]
        phrases=[]
        for line in raw.splitlines():
            line=' '.join(line.strip().split())[:80]
            if len(line)>=3 and line.casefold() not in [p.casefold() for p in phrases]: phrases.append(line)
            if len(phrases)>=100: break
        set_setting('message_blocked_phrases','\n'.join(phrases))
        return self.send_html(render_admin(user,'Blocked phrases saved. Built-in privacy and harassment checks remain active.'))

    def handle_message_review(self, user, form):
        kind=form.get('kind',''); rid=form.get('record_id',''); action=form.get('action','')
        if not rid.isdigit() or kind not in ('incident','legacy'):
            return self.send_html(render_admin(user,'Invalid moderation record.'),400)
        if kind=='incident':
            if action!='reviewed': return self.send_html(render_admin(user,'Invalid moderation action.'),400)
            with db() as conn:
                cur=conn.execute("UPDATE message_incidents SET status='reviewed',reviewed_at=? WHERE id=? AND status='open'",(now_iso(),int(rid)))
            return self.send_html(render_admin(user,'Incident marked reviewed. Unblock the account separately if appropriate.' if cur.rowcount else 'Incident was not found.'))
        if action not in ('approve','delete'):
            return self.send_html(render_admin(user,'Invalid legacy-message action.'),400)
        error=''
        with db() as conn:
            m=conn.execute("SELECT * FROM project_messages WHERE id=? AND status='legacy_review'",(int(rid),)).fetchone()
            if not m: error='Legacy message not found.'
            elif action=='delete': conn.execute('DELETE FROM project_messages WHERE id=?',(int(rid),))
            else:
                row=conn.execute("SELECT value FROM settings WHERE key='message_blocked_phrases'").fetchone()
                reason=message_violation(m['message'],_registered_names(conn),row['value'].splitlines() if row else [])
                if reason: error='This legacy message still triggers a safety rule. Delete it instead of publishing it.'
                else: conn.execute("UPDATE project_messages SET status='visible',name='Community member',email='' WHERE id=?",(int(rid),))
        if error: return self.send_html(render_admin(user,error),400)
        return self.send_html(render_admin(user,'Legacy message reviewed.'))

    def handle_payment_start(self, user, query):
        pledge_id=query.get('pledge_id',[''])[0]
        if not pledge_id.isdigit(): return self.redirect('/marketplace')
        with db() as conn:
            pledge=conn.execute("""SELECT pl.*,p.title,p.status AS project_status,
                (SELECT reference FROM payments pay WHERE pay.pledge_id=pl.id AND pay.provider='owner_link' ORDER BY id DESC LIMIT 1) AS reference
                FROM pledges pl JOIN projects p ON p.id=pl.project_id WHERE pl.id=? AND pl.user_id=?""",(int(pledge_id),user['id'])).fetchone()
            names=_registered_names(conn)
        if not pledge or not pledge['reference']:
            return self.send_html(render_notice('Support record not found','This support record is not available to this account.',user),404)
        link=owner_payment_url()
        if not link or pledge['project_status'] != 'public':
            return self.send_html(render_notice('Funding unavailable','The payment link or project is unavailable. Contact the owner for help.',user),503)
        title=e(redact_public_text(pledge['title'],names))
        body=f"""<section class='auth-wrap'><div class='auth-card payment-card'><p class='eyebrow eyebrow-dark'>Owner payment</p><h1>Continue to payment.</h1><p>You requested to support <strong>{title}</strong> with <strong>{money(pledge['amount'])}</strong>.</p><p>Your reference: <strong>{e(pledge['reference'])}</strong>. Include it in the provider’s payment note if possible.</p><p class='muted'>The link is configured by the 70Scholar owner. You may need to enter the amount and reference on the provider page. Payment remains pending until the owner checks their records; opening the link does not confirm payment. The owner separately decides any support for the founder.</p><a class='cta-primary full' href='{e(link)}' target='_blank' rel='noopener noreferrer'>Open owner payment link ↗</a><a class='ghost-button full' href='/project?id={pledge['project_id']}'>Back to project</a></div></section>"""
        return self.send_html(page_shell('Owner payment',body,user))

    def handle_payment_success(self, user, query):
        # A browser return or a guessed GET can never verify or change a payment.
        return self.send_html(render_notice('Payment pending','Returning to 70Scholar does not confirm payment. The owner must check the payment provider records.',user))

    def handle_upload(self, user):
        if not self.verify_csrf(user): return self.send_json({'ok':False,'error':'CSRF check failed'},403)
        try:
            payload=json.loads(self.read_body().decode()); pid=int(payload.get('project_id'))
            filename=slugify_filename(payload.get('filename','upload.bin'))
            mime=str(payload.get('mime') or mimetypes.guess_type(filename)[0] or 'application/octet-stream').lower()[:120]
            if not re.fullmatch(r'[a-z0-9.+-]+/[a-z0-9.+-]+',mime): mime='application/octet-stream'
            data=payload.get('data',''); data=data.split(',',1)[1] if ',' in data else data
            content=base64.b64decode(data,validate=True)
        except Exception: return self.send_json({'ok':False,'error':'Invalid upload'},400)
        if MAX_UPLOAD_BYTES and len(content)>MAX_UPLOAD_BYTES: return self.send_json({'ok':False,'error':'File exceeds the configured upload limit.'},400)
        with db() as conn:
            project=conn.execute('SELECT id,status FROM projects WHERE id=? AND user_id=?',(pid,user['id'])).fetchone()
            if not project: return self.send_json({'ok':False,'error':'Project not found'},404)
            stored=UPLOAD_DIR / f"{pid}-{secrets.token_hex(8)}-{filename}"
            stored.write_bytes(content)
            cur=conn.execute('INSERT INTO assets(user_id,project_id,filename,stored_path,external_url,mime,size,created_at) VALUES(?,?,?,?,?,?,?,?)',(user['id'],pid,filename,str(stored),'',mime,len(content),now_iso()))
            status='pending_review' if project['status']=='public' else project['status']
            conn.execute('UPDATE projects SET asset_url=?,status=?,updated_at=?,review_version=review_version+1 WHERE id=?',(f'/download?id={cur.lastrowid}',status,now_iso(),pid))
        return self.send_json({'ok':True,'download_url':f'/download?id={cur.lastrowid}','filename':filename,'review_required':status=='pending_review'})

def main():
    init_db()
    threading.Thread(target=auto_sync_worker, daemon=True).start()
    httpd=ThreadingHTTPServer((HOST, PORT), ScholarHandler); print(f"70Scholar running at http://{HOST}:{PORT}", flush=True); httpd.serve_forever()
if __name__ == "__main__": main()
