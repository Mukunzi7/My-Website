# Render deployment and safe upgrade

The GitHub repository is `Mukunzi7/My-Website`, branch `main`. The Render service name is
`70scholar`; its currently observed public URL is
<https://seven0scholar-7cjc.onrender.com>. The URL shown in the Render dashboard is the
source of truth. The app listens on `0.0.0.0:$PORT` and the health endpoint is `/version`.

## Before deploying: protect user data

The free-plan service declared in `render.yaml` has an ephemeral filesystem. Deploys,
restarts or instance replacement can erase the live SQLite database and uploads. The copy
in a developer's workspace is not a backup of Render's live data. Do not deploy over
important live records until you have exported/backed up the database and files and verified
that backup. Provision a paid Render service with a persistent disk or migrate to a
supported persistent database/storage solution; this code currently implements SQLite, not
PostgreSQL.

For a Render disk mounted at `/var/data`, set:

```text
DB_PATH=/var/data/70scholar.sqlite3
UPLOAD_DIR=/var/data/uploads
```

A disk is not a backup. Back up both the SQLite file and uploads independently, with a
consistent SQLite backup procedure (e.g. stop writes or use SQLite's backup API), test
restores, and secure the backup. Migrating existing Render files to a new disk requires
access to the running instance and an explicit transfer; merely adding `DB_PATH` does not
copy the old database. Copy the contents of the old `uploads` folder into the new
`UPLOAD_DIR`, preserving the generated filenames; the server can locate legacy flat filenames
after the move. Verify the migrated downloads as the owner before removing the old files.

## Required configuration

- `ADMIN_EMAIL=honoremukunzi6@gmail.com` — the app hard-locks admin access to this email.
- `ADMIN_PASSWORD` — a strong, unique owner password, stored only as a Render secret. The old
  `Admin123!` default is refused. If the owner account was bootstrapped without a suitable
  password, set this variable and restart; the locked account can then be initialized. Once
  a real password is in use, changing this variable alone does not overwrite that password.
- `APP_BASE_URL=https://seven0scholar-7cjc.onrender.com` or the real custom HTTPS URL.
- Configure either Bird (`BIRD_API_KEY`, verified-domain `BIRD_FROM`, optionally
  `BIRD_REGION`) or SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
  `SMTP_FROM`, `SMTP_TLS`) to deliver verification/reset emails. Bird's onboarding sender is
  sandbox-restricted; see `BIRD_EMAIL_SETUP.md`.
- Set `DB_PATH` and `UPLOAD_DIR` to a persistent disk after arranging a safe data migration.

Payment links are not deployment secrets: the owner configures their own HTTPS checkout
link from **Admin → Funding**. No funding action is available before that.

## Homepage and slideshow update

The homepage hero displays the owner-supplied group photo as a full background and the
owner's Seven Scholars emblem. The platform name remains 70Scholar. Sign in with the owner account
and choose **Admin → Slideshow photos** to add or remove pictures. The first v19 startup
imports the bundled slideshow into the database once; later owner removals are retained if
that database survives. Uploaded images are normalized and stored inside SQLite. Without a
persistent disk, a deploy or restart can erase both the images and the chosen slideshow;
back up the database and use persistent storage. Permission and any required consent must
be obtained before public publication, especially for identifiable minors.

## v18 migration impact

After a safe backup, deploy the updated commit. The first startup with an existing database:

- requires legacy accounts to verify or receive an owner access grant unless a genuinely used
  verification token exists;
- moves formerly public projects into the owner-review queue; hides older messages pending
  review; and treats previous demo-paid records as unverified;
- disables the shared-password legacy demo account and any insecure default owner password.

These changes are intentional and one-time. They are not a substitute for backups. Review
all project text, uploads and older messages before publishing; disabling old Cloudinary
uploads does not revoke old externally hosted copies.

## Verify deployment

1. Check Render deployment status and logs, then open
   <https://seven0scholar-7cjc.onrender.com/version>. Expected:
   `70Scholar v20-logo-hero - privacy, owner review and funding`.
2. In a private browser, `/programs` should redirect to login; the homepage should show the
   slideshow and no seven-image gallery or official program links.
3. Log in as owner, set an owner payment link if ready, and inspect review/user counts. Verify
   signup with an external email inbox or explicitly grant a test account access.
4. Test moderation, approval, and a **test** payment request. Do not mark a real payment
   confirmed until the provider record has been checked. A return from checkout proves nothing.
5. Check the logs for email delivery errors. Protect any personal data in admin screenshots,
   backups, and the provider dashboard.

## Troubleshooting

- Login fails for old users: check email-verification evidence, access grant and block status.
- No verification email: check actual provider credentials, verified sender, region,
  `APP_BASE_URL`, spam folder, provider delivery events and sandbox restrictions.
- Admin cannot log in: verify the owner email and strong `ADMIN_PASSWORD`; for an existing
  changed password use the configured recovery process rather than assuming env overwrites it.
- Data disappeared: restore the independent backup. Git and the code workspace do not contain
  a copy of live private records.
- Funding unavailable: enter a valid owner HTTPS checkout link in Admin. Its ownership and
  transactions require independent verification.
