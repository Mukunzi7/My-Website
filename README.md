# 70Scholar — Platform MVP v13

**70Scholar** (previously Learnwella, originally EduBridge) is a full-stack platform by **Nexus Company Ltd** for
opportunity discovery, student project building, sponsor conversations, project showcases,
marketplace funding, direct Mobile Money support, and admin moderation.

Everything runs on the Python standard library — no web framework, no package install needed.
Pages are server-rendered by `server.py`, stored in SQLite, and styled by `static/styles.css`
with a small progressive-enhancement script in `static/app.js`.

## 🚀 Launch it from this repo (about 2 minutes)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Mukunzi7/My-Website)

Direct link: <https://render.com/deploy?repo=https://github.com/Mukunzi7/My-Website>

1. Click the button, sign in to Render with GitHub, and grant it access to this repository.
2. **Blueprint Path:** leave blank — it defaults to `render.yaml` at the repo root.
3. The preview must say **Create web service `70scholar`**. Fill the environment variables
   it asks for (see the table in [RENDER_DEPLOY.md](RENDER_DEPLOY.md)).
4. Click **Apply**. Your site will be at <https://70scholar.onrender.com>.

> If the preview still says `learnwella`, hard-refresh or reopen the deploy link in a new
> tab — Render reads `render.yaml` when the page loads.

Before inviting real users, configure an email provider (Bird or SMTP) so verification emails
are delivered, and add a Render Disk so accounts and uploads survive deploys.

Full guide: **[RENDER_DEPLOY.md](RENDER_DEPLOY.md)** — one-click Blueprint link, manual steps,
required environment variables, persistent storage, and custom-domain setup.

---

## What's in this repo

| File | Purpose |
| --- | --- |
| `server.py` | The entire app: routing, HTML rendering, auth, emails, uploads, admin, SEO routes |
| `static/styles.css` | Full site stylesheet (all page, form, dashboard and admin classes) |
| `static/app.js` | AJAX profile-photo + project-file uploads, filter helpers, scroll reveal |
| `render.yaml` | Render Blueprint (service name, build/start commands, health check) |
| `Dockerfile`, `Procfile`, `fly.toml`, `cloudbuild.yaml` | Alternative Docker / Cloud Run / Fly deployments |
| `.env.example` | Template for every environment variable the app understands |
| `database_postgresql.sql` | Production schema if you migrate off SQLite |
| `pitch_deck.html`, `pitch_deck.md` | Investor/partner pitch deck |

---

## v13 changes

1. **Renamed the platform to 70Scholar** — page titles, SVG wordmark, footer, page copy,
   verification and password-reset emails, `/version`, the pitch deck, and all documentation.
2. **Bumped `APP_VERSION` to `v13-70scholar-brand`** so `/version` proves which build is live
   and browser caches pick up the new CSS/JS.
3. **Renamed the Render service to `70scholar`** in `render.yaml`, so the free URL is
   `https://70scholar.onrender.com`. This requires starting a fresh Blueprint flow; see
   `RENDER_DEPLOY.md`. You can still add a custom domain such as `70scholar.com` later.

### Earlier v12 fixes (already included)

- Restored the full 1,052-line `server.py` after commit `0c111b6` truncated it to 57 lines.
- Added the missing `static/styles.css` and `static/app.js` (previously every page 404'd them).
- Added `DB_PATH` / `UPLOAD_DIR` env vars so SQLite and uploads can live on a Render Disk.
- Removed committed runtime data (`edubridge.sqlite3`, `mail_outbox.log`) from Git and
  replaced the real default admin password in `.env.example` with a placeholder.
- Added `RENDER_DEPLOY.md` and the `render.yaml` Blueprint.

Legacy internal identifiers `edubridge.sqlite3` (default DB filename) and
`edubridge_session` (cookie name) are intentionally kept so existing databases and sessions
are not broken. They are not shown anywhere in the UI.

---

## Run locally

From the **repository root** (there is no `edubridge_platform` subfolder):

```bash
python3 server.py
```

Open <http://127.0.0.1:8080>. The app creates a fresh SQLite database and seeds demo
opportunities and projects on first start.

To use a different port or storage location:

```bash
PORT=8080 DB_PATH=/tmp/70scholar.sqlite3 UPLOAD_DIR=/tmp/70scholar-uploads python3 server.py
```

Verify what is running:

```text
http://127.0.0.1:8080/version
→ 70Scholar v13-70scholar-brand - full app restored, static assets included, Render-ready
```

---

## Environment variables

Copy `.env.example` and set the values in your host's dashboard (never commit real secrets).

| Variable | Required in production | Notes |
| --- | --- | --- |
| `HOST` | yes | Must be `0.0.0.0` on Render/Docker |
| `PORT` | yes | Render supplies this (usually `10000`) |
| `APP_BASE_URL` | yes | `https://70scholar.onrender.com` — used in verification email links |
| `ADMIN_EMAIL` | yes | Owner admin account created at startup |
| `ADMIN_PASSWORD` | yes | **Set a strong unique value.** The code default is for local testing only. |
| `BIRD_API_KEY` | strongly recommended | Without email, new users cannot verify their address or log in |
| `BIRD_FROM`, `BIRD_REGION` | with Bird | Sender address and `us1`/`eu1` |
| `SMTP_*` | alternative | Used if Bird is not configured |
| `DB_PATH` | with a Render Disk | e.g. `/var/data/70scholar.sqlite3` |
| `UPLOAD_DIR` | with a Render Disk | e.g. `/var/data/uploads` |
| `CLOUDINARY_*` | optional | Offloads project uploads to Cloudinary |
| `MAX_UPLOAD_BYTES` | optional | `0` = no app-level limit; profile photos are capped at 10 MB |

---

## Email is not optional in production

Signup requires email verification and login is blocked until verification succeeds. If neither
Bird nor SMTP is configured, verification links are written to `mail_outbox.log` **inside the
container**, which is invisible to your users and wiped on redeploy. Configure `BIRD_API_KEY`
(or SMTP) before launching. See `BIRD_EMAIL_SETUP.md` and `EMAIL_AUTH_SECURITY.md`.

---

## Main pages

| Route | Purpose |
| --- | --- |
| `/` | Landing page with story and impact section |
| `/opportunities` | Searchable opportunities directory with bookmarks |
| `/signup`, `/login` | Account creation and login |
| `/verify-email?token=…` | Email verification |
| `/forgot-password`, `/reset-password?token=…` | Password reset |
| `/dashboard` | User dashboard and sponsor message inbox |
| `/messages` | Sponsor–builder conversations |
| `/workspace` | Private builder workspace, Mobile Money details, file uploads |
| `/marketplace` | Approved public project marketplace |
| `/project?id=…` | Showcase, sponsor chat, funding, files |
| `/pledge`, `/payment/start`, `/payment/success` | Support / pledge flow |
| `/account` | Name, password, profile photo |
| `/admin` | Moderation queue, users, roles, opportunities, RSS sync |
| `/version` | Plain-text deploy verification |
| `/robots.txt`, `/sitemap.xml` | SEO / crawler files |

---

## Admin account

On first start the app creates an owner admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. For local
testing only, the built-in default is printed in `server.py` — **do not use it in production**.
Set both environment variables on your host before the first deploy; changing `ADMIN_PASSWORD`
later does not reset an already-created account, so choose it carefully.

---

## Direct Mobile Money funding

Each creator adds their own Mobile Money details in the workspace before submitting a project
for review. Sponsors send funds directly to the creator; 70Scholar records the pledge/support
activity but never collects the money. See `PAYMENTS.md`.

---

## More documentation

| File | Topic |
| --- | --- |
| `RENDER_DEPLOY.md` | **Render hosting, one-click deploy, env vars, disk, domain** |
| `RENDER_FIX.md` | Port binding and HEAD health-check notes |
| `DEPLOYMENT.md` | Cloud Run, Docker and other hosts |
| `DOMAIN_AND_GOOGLE_DEPLOYMENT.md` | Domains, Google Search Console |
| `GITHUB_GUIDE.md` | Pushing this repo |
| `BIRD_EMAIL_SETUP.md`, `EMAIL_AUTH_SECURITY.md` | Transactional email |
| `CLOUD_UPLOADS.md` | Optional Cloudinary uploads |
| `POSTGRESQL_SETUP.md` | Future PostgreSQL migration |
| `WINDOWS_UPDATE_GUIDE.md` | Checking versions on Windows |
| `BRAND_RENAME.md` | Brand decision record |

---

## Recommended production upgrades

1. Add a persistent Render Disk (or migrate to PostgreSQL) — SQLite on ephemeral disk is lost on redeploy.
2. Move uploaded files to Cloudinary / S3 / R2; a disk alone is not a backup.
3. Add file/content scanning for uploads and audit logs for admin actions.
4. Add email templates, alerts, and deadline reminders.
5. Add verified payment confirmations if payments are automated.

© 2026 Nexus Company Ltd. All rights reserved.
