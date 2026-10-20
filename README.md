# EduBridge Platform MVP v11

EduBridge is a full-stack platform by **Nexus Company Ltd** for opportunity discovery, student project building, sponsor conversations, project showcases, marketplace funding, direct Mobile Money support, and admin moderation.

## Brand

The platform name is **EduBridge**. Every page is protected with **Nexus Company Ltd** copyright.

## Latest v11 additions

1. Visible v11 update banner added on every page so you can confirm the deployed version.
2. Profile photo now appears in the upper-right navigation when a user is logged in.
3. Project/media upload limit removed inside EduBridge; profile photos allow up to 10 MB.
4. Static CSS/JS cache-busting added so Render/browser updates show correctly.
5. `/version` endpoint added to verify the deployed version.
6. Windows update checking guide added in `WINDOWS_UPDATE_GUIDE.md`.
7. Dedicated `/messages` page added for sponsor-builder conversations.
8. Marketplace cards now include a clear “Chat with builder” button.
9. Name kept as **EduBridge** with a luxury visual refresh.
10. Luxury logo mark added to the header and footer.
11. Every page footer now includes: `© 2026 Nexus Company Ltd. All rights reserved.`
12. Project photo/video showcase added.
13. Builders can upload images, videos, pitch decks, ZIP files, or app/program files without an EduBridge app limit. Hosting/browser limits may still apply.
9. Sponsor-to-builder project conversation area added on each project page.
10. Builder dashboard now shows sponsor messages for their projects.
11. Project descriptions must be stronger before marketplace submission.
12. PostgreSQL schema updated with project messages.
13. Brand decision notes added in `BRAND_RENAME.md`.

## Existing production features

- Bird / MessageBird email support for verification and password reset emails.
- Real email verification flow after signup.
- Login blocked until email is verified.
- Password reset flow with expiring reset tokens.
- Project moderation: public submissions go to `pending_review` first.
- Admin moderation queue for approving/rejecting projects.
- Admin controls: project approval/rejection/deletion, user verification, role management without admin promotion, temporary password reset, user deletion, opportunity deletion, and RSS sync.
- Optional Cloudinary cloud upload hook for project files.
- PostgreSQL production schema and setup documentation.

## Run locally

```bash
cd edubridge_platform
python3 server.py
```

Open:

```text
http://127.0.0.1:8080
```

## Bird / MessageBird email support

Set this in Render or your local environment, replacing the placeholder with your real key:

```bash
BIRD_API_KEY=bk_xxxxxxxxx
BIRD_FROM=onboarding@messagebird.dev
BIRD_REGION=us1
```

Never commit your real Bird API key to GitHub. A TypeScript example is included in `examples/bird-email-example.ts`.

## Local email behavior

If Bird/SMTP is not configured, verification and password reset emails are written to:

```text
mail_outbox.log
```

Open that file and copy the verification/reset links during local testing.

## Admin login

For local testing, the app creates a default admin:

```text
Email: honoremukunzi6@gmail.com
Password: Admin123!
```

For production, set Render environment variables:

```bash
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD='A-Very-Strong-Password'
```

## Main pages

- `/account` — change account name, password, and profile photo

- `/` — landing page with story/impact section
- `/opportunities` — opportunities directory
- `/signup` — create account
- `/verify-email?token=...` — email verification
- `/login` — login
- `/forgot-password` — request password reset
- `/reset-password?token=...` — reset password
- `/dashboard` — user dashboard and sponsor message inbox
- `/messages` — dedicated sponsor-builder messages page
- `/workspace` — private builder workspace with Mobile Money fields and file/media upload
- `/marketplace` — approved public project marketplace
- `/project?id=...` — project showcase, sponsor chat, funding, and files
- `/admin` — admin dashboard and moderation queue
- `/robots.txt` — Google crawler file
- `/sitemap.xml` — Google sitemap

## Direct Mobile Money funding

Each creator adds their own Mobile Money details in the workspace before submitting a project for review.

Sponsors send funds directly to the creator. EduBridge records the pledge/support activity but does not collect the money.

See:

```text
PAYMENTS.md
```

## Cloud uploads

Optional Cloudinary uploads are supported. See:

```text
CLOUD_UPLOADS.md
```

## Email verification/password reset setup

See:

```text
EMAIL_AUTH_SECURITY.md
BIRD_EMAIL_SETUP.md
```

## PostgreSQL production setup

The app still runs SQLite by default for local development. PostgreSQL production schema and migration notes are included:

```text
POSTGRESQL_SETUP.md
database_postgresql.sql
```

## Domain, Google deployment, and GitHub

Read:

```text
BRAND_RENAME.md
DOMAIN_AND_GOOGLE_DEPLOYMENT.md
GITHUB_GUIDE.md
DEPLOYMENT.md
RENDER_FIX.md
```

## Pitch deck

```text
pitch_deck.html
pitch_deck.md
```

## Important production upgrades still recommended

1. Add a full PostgreSQL adapter or migrate to SQLAlchemy.
2. Add verified payment confirmations if you later automate payments.
3. Add file/content scanning for uploads.
4. Add email templates and better deliverability setup.
5. Add private/direct messaging notifications for sponsor-builder conversations.
6. Add audit logs for all admin actions.

## Upload limits

- Project/media/file uploads: no fixed EduBridge app limit by default (`MAX_UPLOAD_BYTES=0`). Your host, browser, memory, or network may still limit very large files.
- Profile photos: max 10 MB.

## If profile photo upload does not work

1. Make sure you are logged in.
2. Go to `/account`.
3. Choose an image file under 10 MB.
4. After uploading, hard refresh the browser.
5. If on Render, open `/version` and confirm it says v11.

If `/version` does not show v11, Render is still running old code.
