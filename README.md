# 70Scholar

70Scholar helps students discover programmes and opportunities, prepare for university,
create projects, and request support. It is a server-rendered Python/SQLite application.
The public homepage and helpline are available to everyone; programmes, opportunities,
the workspace and marketplace require an account with access.

- Live service: <https://seven0scholar-7cjc.onrender.com>
- Owner admin: **honoremukunzi6@gmail.com** (the only permitted admin)
- Helpline: **0726495648** · **honoremukunzi6@gmail.com**
- Deployment check: `/version` → `70Scholar v20-logo-hero - privacy, owner review and funding`

## Manage the homepage slideshow

Sign in as **honoremukunzi6@gmail.com**, open **Admin → Slideshow photos**, choose a JPEG,
PNG or WebP photo (up to 8 MB) and select **Add photo to slideshow**. An optional description
appears on the image and serves as accessible text. New pictures appear first. Remove any
bundled or uploaded image with its **Remove photo** button. An empty slideshow is hidden.
Only publish photos with the necessary permission and consent, especially for children.
Photos are resized and stripped of metadata; they and the slideshow selection are stored in
SQLite. Without persistent storage, uploads and changes can disappear on deploy or restart.

## Critical: protect live data before deployment

The Render free service's filesystem is ephemeral. A deployment or restart can replace the
filesystem and erase the live SQLite database and uploads. The local files in this repository
are **not** a backup of the live service. Before using real accounts, arrange a persistent
Render disk (paid service), set `DB_PATH` and `UPLOAD_DIR` to it, and maintain independent,
tested backups. Back up the live database and files before any deployment. See
`RENDER_DEPLOY.md`. Never put user databases, uploads or secrets into Git.

## Run locally

Python 3.10+ and Pillow (installed from `requirements.txt`) are required.

```bash
python3 -m pip install -r requirements.txt
export ADMIN_PASSWORD='a-long-unique-secret'
export APP_BASE_URL='http://localhost:8080'
python3 server.py
```

Open <http://localhost:8080>. On Windows PowerShell use `$env:ADMIN_PASSWORD='...'` and
`$env:APP_BASE_URL='http://localhost:8080'`. Set a unique `ADMIN_PASSWORD` of at least eight
characters before the first run. The insecure old default `Admin123!` is disabled. If no
acceptable password exists, a newly created owner account is locked until `ADMIN_PASSWORD`
is configured and the app restarts. An existing owner-changed password is not overwritten by
routine restarts.

To test: `python3 -m unittest discover -s tests -v`.

## Accounts and privacy

- Registration requires a name, email, private phone number and password. Account type,
  career and education level are optional. Contact details appear only in the account's own
  views and in the owner-only admin area, not in project listings or conversations.
- Email verification requires a real, unexpired token sent by Bird or SMTP. Sending failure
  or an absent provider **never** verifies an account. Alternatively the owner can use
  **Admin → People → Grant access**; that does not claim the email is verified.
- The 7-day active-user count is based on authenticated activity; admins can review counts,
  verification, access grants, blocks, phone details, roles and sessions.
- The v18 migration re-gates older accounts that have no stored evidence of a used email
  verification token. Their owners can verify or receive a manual access grant. Previously
  public projects return to the review queue and older messages are hidden for review.
  Legacy demo payment markers are not counted as confirmed payments.
- Uploaded project files are stored locally in `UPLOAD_DIR` and served only to the project
  owner or admin until publication. Before approving, the admin must inspect every file,
  image and video for sensitive information. Older Cloudinary copies, if any, may still be
  accessible there and must be reviewed or removed separately.
- Automatic checks can miss disguised personal information and can also block harmless text.
  These are safeguards, not a guarantee; the owner must review flags and uploads.

## Projects, messages and funding

A builder can choose **Guided steps** or **Full form** under `/workspace`. Every requested
publication, including a later edit or upload, requires explicit owner approval. The review
queue includes the full text and attachment links. Public project cards use neutral labels,
not creators' names, email addresses, phone numbers or Mobile Money details.

Messages have three main rules: no personal/contact information, no direct/off-platform
contact or payments, and no harassment/threats. Rule-triggering messages are suppressed and
the account is blocked and signed out; the owner can review flags, add blocked phrases and
unblock accounts. Older messages require review before they can appear.

The owner sets one HTTPS checkout URL under **Admin → Funding → Owner payment link**.
Until then, funding is unavailable. Support requests are pending even after a supporter
opens the link. The owner must independently check the payment provider and manually mark a
payment confirmed. Any transfer to a founder happens separately; the admin may record an
already-completed external transfer. The app does **not** automatically collect, verify,
settle, split, escrow or disburse money. See `PAYMENTS.md`.

## Email configuration

Set `APP_BASE_URL` to the actual public HTTPS URL and configure either Bird or SMTP. For Bird,
set `BIRD_API_KEY`, `BIRD_FROM` to an address on your verified sending domain, and optionally
`BIRD_REGION=us1` or `eu1`. Bird's onboarding address is restricted to sandbox addresses and
verified workspace members; it is not sufficient for general public signup. A provider's
acceptance is not proof of delivery. Test with an actual external mailbox. See
`BIRD_EMAIL_SETUP.md` and `EMAIL_AUTH_SECURITY.md`.

## Routes and files

| Path | Purpose |
| --- | --- |
| `/`, `/signup`, `/login`, `/verify-email`, `/version` | Public entry and account pages |
| `/programs`, `/opportunities`, `/courses`, `/exams`, `/submit` | Account-only discovery and submission |
| `/workspace`, `/marketplace`, `/project`, `/messages`, `/dashboard` | Account-only project tools |
| `/admin` | Owner-only review, access, message safety and funding controls |
| `server.py` | HTTP application, migrations, storage and security rules |
| `static/` | Styles, JavaScript, slideshow images and branding |
| `tests/` | Integration, security and actual v17-schema upgrade regression tests |
| `PHOTOS.md`, `PAYMENTS.md`, `RENDER_DEPLOY.md` | Source notes and operational guidance |

The app is an MVP: SQLite is not a substitute for production-grade auditing, encrypted
storage, rate limiting, a payment-provider integration, or legal/privacy review. Use a
network firewall as defence in depth around the link-preview fetcher.
