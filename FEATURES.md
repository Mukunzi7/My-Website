# 70Scholar v17 — feature guide

## v17 — programs, link previews, profiles and a cleaner admin

### A. Featured programs
`/programs` is a **public** page with 16 official programme links, including YYAS,
YYGS, RSI, MITES Summer, SSP, Simons, QuestBridge, Mastercard Foundation, ALA,
Chevening, Rhodes, Fulbright, Gates Cambridge, Erasmus Mundus and DAAD EPOS.
The same records are seeded into `opportunities` with `source='featured_program'`,
so they also appear in the main opportunity list. Dates marked **Verify deadline**
must be confirmed on the official page because deadlines vary by country/course.

Source list: `FEATURED_PROGRAMS` in `server.py`.

### B. Add opportunity by link
`/submit` now offers two options:

1. **Option 1 — fill in the details** (manual form, unchanged).
2. **Option 2 — just paste a link**: the server fetches the page's Open Graph /
   meta title, description, site name and image, infers a type and deadline, and
   saves a `pending` submission. The admin sees the fetched preview and an optional
   user note, can edit the title/provider/deadline/summary, must tick **“I checked
   the official page”**, then approves or rejects. Nothing is public before approval.

Security: `is_safe_public_url()` blocks private, loopback, link-local and reserved
addresses; redirects are rechecked; response size and time are capped. Relative
preview images are resolved against the submitted URL and limited to http/https.

### C. Profile picture, signup and helpline
- Signed-in users now see a real profile image in the top-right navigation. An upload
  from **Account** replaces the default `static/images/default-avatar.svg`.
- `/signup` asks for name, email and password (compulsory) plus optional
  “I am a…”, career/field and education level. If no email provider is configured —
  or the provider fails — the account is auto-verified so signup never traps a user.
- Every HTML page footer includes helpline `0726495648` and
  `honoremukunzi6@gmail.com`.

### D. Classic long-scroll homepage
The storytelling sections remain, but the order is now: hero → typewriter →
Discover/Build/Launch → opportunity types → featured programs → the problem →
real photos → workspace → story/impact → extra features/FAQ → final call to action.

### E. Organized admin
`/admin` has a sticky sidebar and four numbered groups: **Review queue**,
**Content & catalogue**, **Automation & imports**, and **People & records**.
The community-submission queue is at the top and includes link previews.

### F. Tests
Run `python3 -m unittest discover -s tests -v` from the repository root.
The suite covers seeded programs, the public programs page, helpline footer,
signup fields, SSRF protection, metadata extraction, and the full
link-submission → admin-approval → public-listing flow.


## 1. Logo
`static/images/logo.svg` (header/footer) and `static/favicon.svg` (browser tab).
See **[LOGO.md](LOGO.md)** for how to replace or recolour it.

## 2. Sign-in required for everything
Anonymous visitors can only reach the homepage, `/login`, `/signup`, password reset,
email verification, `/version`, `/robots.txt`, `/sitemap.xml`, and `/static/*`.
Every other GET **and** POST redirects to `/login?next=<original path>`; after login the
user is returned to the page they wanted.

Controlled by `PUBLIC_GET_PATHS` / `PUBLIC_POST_PATHS` in `server.py`. Admin remains
locked to `honoremukunzi6@gmail.com` (see `ADMIN_EMAIL_ALLOWLIST`).

## 3. Auto-import toggle + custom source links
Admin → **Auto-import & source links**:

- **Toggle switch** turns automatic importing ON/OFF. When ON, a background thread
  (`auto_sync_worker`) refreshes every saved link every 30 minutes
  (`AUTO_SYNC_INTERVAL_SECONDS`).
- **Save link** adds any RSS/Atom feed or ordinary webpage to `feed_sources`.
- **Fetch now** imports listings from that link immediately.

The importer understands RSS/Atom `<item>`/`<entry>` and, for plain HTML pages, links
whose text mentions scholarship/grant/internship/competition/fellowship/application etc.
It infers the type and deadline, deduplicates by title, and writes an
`auto_description` for each listing. Only the owner admin can use these controls.

## 4. Pre-university courses & exam prep
- `/courses` — six pre-university courses (academic English, foundation maths, Python,
  research methods, science bridge, university applications).
- `/exams` — six exam-prep tracks (SAT, ACT, IELTS/TOEFL, AP/IB/A-Levels, aptitude
  tests, scholarship tests).
- Signed-in users can **join/start** a track; enrolments are stored in
  `course_enrolments`. Content is defined in `PREUNI_COURSES` / `EXAM_PREP` in
  `server.py` — edit those lists to add your own material or videos.

## 5. Auto-descriptions on hover
Every opportunity, course, exam and feature tile has a `data-tooltip` containing an
auto-generated description (type, provider, level, deadline, summary, verification
advice). `static/app.js` shows a floating tooltip that **follows the cursor**.
`make_auto_description()` in `server.py` builds the text from whatever fields exist.

## 6. Photo slideshow
`render_slideshow()` renders 12 real NESA photos (`static/images/slides/`) that
auto-advance every 5 seconds, with previous/next arrows, clickable dots and a counter.
It pauses on hover and when the tab is hidden. The separate 7-photo gallery grid
remains below it. The line that mentioned AI has been removed, as has the
version banner at the top of every page.

## 7. Typewriter words
`render_typewriter()` adds a line of large blue words that types and erases through
`TYPEWRITER_WORDS` — scholarships, internships, competitions, courses, exam prep,
funding and more.

## 8. Extra homepage sections
`render_extra_features()` adds: a six-tile feature grid linking to every part of the
site, animated count-up trust stats, an FAQ accordion, and a final call-to-action band.

## 9. Community submissions (user upload → admin approval)
Signed-in users see **Add opportunity** (`/submit`) and can submit a scholarship,
competition, application, etc. Submissions go to `opportunity_submissions` with
status `pending` and are **never public** until the owner admin clicks **Approve** in
Admin → **Community submissions**. Approval inserts the row into `opportunities`.

## 10. 5% platform contribution
`PLATFORM_FEE_PERCENT` (default **5**, override with an env var) is recorded on every
pledge: `pledges.platform_fee` and `pledges.creator_amount` store the split. The
project page, payment instructions and admin **Platform Fund** stat all show it.

> ⚠️ **Important:** with direct Mobile Money, the sponsor sends money straight to the
> creator. The app **records** the 5% contribution but cannot automatically collect it.
> To actually receive it you must set up a payment provider (Flutterwave, Stripe,
> PayPal or a MoMo merchant account) and route the fee portion to your account. Set
> the corresponding `*_PAYMENT_LINK` env var in Render. This is a real-money step that
> needs your own merchant credentials and verification.

## 11. Removed / changed UI
- The version banner at the top of every page is gone. `/version` still works for
  deploy checks.
- The "non-AI photographs" credit line under the gallery is gone. Photo sources remain
  documented in `PHOTOS.md`.

## Deploy
Push to `main` — Render auto-deploys. Verify with `/version` → `v17-programs`.
