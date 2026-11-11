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
that backup. Render Free provides no Shell/SSH or persistent disk. Ask Render support
whether it can create a consistent, private export of the still-running instance's SQLite
database AND uploads. Do not restart, upgrade, deploy, or change the active data source
in an attempt to get access. Data already removed from an ephemeral instance cannot be
recovered by a new deployment. A public slideshow download is not a backup of accounts,
projects or private files. Before cutover, make and test a complete database/files backup
and a migration into a separate target; verify both counts and individual records/files.
Writes made after a snapshot are **not** in that snapshot; coordinate a maintenance window
and reconcile any later changes before cutover. Retain the original backup privately even
if an import succeeds.

### Offline migration helper (not a live export)

Once you genuinely have a consistent v21 SQLite snapshot AND its matching complete
`uploads` directory, `migrate_sqlite.py` can first inspect them offline:

```text
python3 migrate_sqlite.py --sqlite /private/path/backup.sqlite3 --uploads /private/path/uploads --verify-only
```

It checks database integrity, foreign keys, expected v21 tables, every referenced profile
and project file, and bundled slide names. It cannot prove the snapshot has the latest live
writes. Importing without `--verify-only` asks for confirmation and a hidden PostgreSQL
session-pooler URL if `DATABASE_URL` is not already in the environment. Run it only from a
trusted private machine against a **new** target database/schema; the helper refuses to
replace an existing `scholar_data` schema. It checks copied row values, counts, and file
checksums, keeps deleted-ID high-water marks, and publishes a temporary private schema
only after verification. Unreferenced files remain solely in the original backup. It does
not switch the Render site or test the actual Supabase project. Check free-plan capacity,
provider connectivity, privacy, and the migration on isolated synthetic data first; make
an independent PostgreSQL backup and test the restored site before any production cutover.

This version supports PostgreSQL in a private `scholar_data` schema when `DATABASE_URL`
is present. On Render it refuses to start without PostgreSQL or a mounted SQLite disk; it
will not silently create an empty ephemeral database. This does not make a risky deploy safe:
a deployment can destroy the old instance's files before this code ever runs. If the owner
explicitly chooses to proceed without the unavailable complete backup, existing live
accounts, private projects and uploads cannot be promised or automatically imported.
The owner accepted that risk, but it does not turn a public slideshow archive into a
private-data backup. Recheck the live slideshow and preserve any accessible data again
immediately before cutover.

Alternatively, for a paid Render disk mounted at `/var/data`, set:

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
- Optionally set `APP_BASE_URL=https://seven0scholar-7cjc.onrender.com` or the real custom
  HTTPS site-root URL. If unset, the app uses Render's `RENDER_EXTERNAL_URL`; it never derives
  account links from a request Host. Clearly local, malformed or non-HTTPS link bases are
  rejected on Render; this does not verify DNS, domain ownership or inbox delivery.
- For the no-custom-domain option, verify an individual sender in Brevo, then privately set
  `EMAIL_PROVIDER=brevo`, `BREVO_FROM` to that exact sender, and `BREVO_API_KEY` to a Brevo
  **API key**. See `BREVO_EMAIL_SETUP.md` for sender rewriting, possible activation,
  tracking/privacy, and testing. This explicitly selects Brevo without deleting Bird settings.
  Alternatively configure Bird (`EMAIL_PROVIDER=bird`, `BIRD_API_KEY`, verified-domain
  `BIRD_FROM`, optionally `BIRD_REGION`) or SMTP; see `BIRD_EMAIL_SETUP.md`. Explicit selection
  fails closed rather than falling back. With no selector, legacy Bird-first then SMTP
  behavior remains. Render Free blocks SMTP ports 25, 465 and 587. In the owner dashboard,
  **People → Account email** reports non-secret setup categories and offers an owner-address
  test. Provider acceptance does not establish delivery.
- For Supabase: use the IPv4-compatible **session pooler** PostgreSQL URL in `DATABASE_URL`,
  privately in Render's environment settings (never in Git, chat or screenshots). Replace
  its password placeholder, URL-encoding special characters as necessary. Do not use the
  public API URL, anon key, service key, or a transaction-pooler URL. Render's **Save only**
  option stages changes without an immediate redeploy, but even then do not cut over until
  live data is backed up and migrated safely.
- TLS uses `sslmode=verify-full`. For `*.pooler.supabase.com`, the app uses the bundled
  public Supabase Root 2021 CA certificate (SHA-256 DER fingerprint
  `80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA`,
  expires 26 April 2031); it is not a credential. For an updated CA, download it
  from Supabase Database Settings and supply its PEM content in the Render variable
  `SUPABASE_DB_CA_PEM`, or set `PG_SSL_ROOT_CERT` to its path. Do not put private keys in
  either. An invalid or expired CA or hostname fails closed; no unverified connection is used.
  If the provider rotates its CA, update and retest before the old one expires.
- Create a **new, private** Supabase Storage bucket (for example `70scholar-private`) with
  no broad anonymous or authenticated access policies. A private bucket alone does not
  neutralize an existing permissive `storage.objects` RLS policy. Before production,
  explicitly test direct object reads with no login, a publishable key, and an unrelated
  Supabase-authenticated user; none may access private project or profile objects. The app
  uses its own authorization checks and proxies allowed files; it does not give browsers
  its privileged key or direct object URLs. The startup check verifies the bucket's private
  flag, not every possible RLS policy.
- Privately set `SUPABASE_URL` (standard `https://<project-ref>.supabase.co` project URL),
  `SUPABASE_STORAGE_BUCKET` (the exact private bucket name), and `SUPABASE_SECRET_KEY`
  (the backend-only `sb_secret_…` key) in Render. Never share the key in chat, Git or a
  browser. It bypasses RLS and has elevated project-wide access; rotate it if exposed.
  Do not use an anon/publishable key here. Render PostgreSQL startup fails closed if the
  bucket is missing, public, incorrectly configured or unreachable. Stage variables with
  **Save only** and perform a real provider/auth/privacy test before deployment.
- On the Supabase Free plan, new files count toward the separate **1 GB Storage** quota;
  accounts, metadata and any legacy imported database blobs count toward the **500 MB
  database** quota. Project files and profile photos are limited to 10 MiB each; slideshow
  source photos to 8 MiB. Uploads are bounded before buffering. Free projects can pause
  for inactivity and don't offer downloadable automatic backups. Keep and test consistent
  backups of both the PostgreSQL `scholar_data` schema and the private bucket; neither
  alone restores everything. Monitor usage and plan for growth.
- Removed remote objects are queued for deletion and retried when Storage is available;
  errors do not make private files public. A previously created backup can still contain
  deleted data. On 2026-11-03 the private bucket passed a synthetic upload, authenticated
  download, anonymous/public denial and deletion test; no Storage object policies were
  present then. Recheck before release. The real Render-to-PostgreSQL session-pooler
  credentials, certificate path and deployed app flow have not yet been tested.
- For a paid disk alternative, set `DB_PATH` and `UPLOAD_DIR` under the actual persistent
  disk mount after arranging a safe data migration. Set `PERSISTENT_DISK_MOUNT` if the
  mount is not `/var/data`.

Payment links are not deployment secrets: the owner configures their own HTTPS checkout
link from **Admin → Funding**. No funding action is available before that.

## Homepage and slideshow update

The homepage hero displays the owner-supplied group photo as a full background and the
owner's Seven Scholars emblem. The platform name remains 70Scholar. Sign in with the owner account
and choose **Admin → Slideshow photos** to add or remove pictures. The first v19 startup
imports the bundled slideshow into the database once; later owner removals are retained if
that database survives. The 2026-11-02 public snapshot had 16 bundled photos and excluded
`slide-07.jpg`. On 2026-11-03 the live site showed 17 defaults again, consistent with an
ephemeral reset. The fresh-database default deliberately restores the earlier 16-photo
owner selection; recheck for later changes immediately before cutover. New images are normalized and stored in the private bucket when
configured; older imported image blobs remain in the database. Use PostgreSQL and the
private bucket, or a persistent disk, together with independent backups; free Render SQLite
alone can lose images and the chosen slideshow at any time. Permission and any required consent must
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
   `70Scholar v26-brevo-account-email - privacy, owner review and funding`.
2. In a private browser, `/programs` should redirect to login; the homepage should show the
   daily Bible verse and slideshow, and no seven-image gallery or official program links.
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
