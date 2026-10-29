# 70Scholar deployment

The current Render hostname is <https://seven0scholar-7cjc.onrender.com>; see
`RENDER_DEPLOY.md` for the authoritative setup, backup and migration checklist.

## Essential warnings

- Render free-tier files are ephemeral. A redeploy or restart can erase SQLite and uploaded
  files. Back up live records and configure persistent storage before using real user data.
- `ADMIN_PASSWORD` must be a strong secret and `APP_BASE_URL` must match the public HTTPS
  URL. The sole admin is `honoremukunzi6@gmail.com`.
- Configure a real Bird or SMTP sender for email verification. No provider does not mean
  auto-verification: an owner access grant is the explicit fallback.
- The owner-configured HTTPS payment link is entered in the admin UI. The application only
  records pending requests, manual confirmations and externally completed transfers; it does
  not settle or send payments.
- Every project and its uploads require owner review. Filters cannot guarantee removal of
  personal information, and previously uploaded external copies may require separate cleanup.

Start command: `python3 server.py`. Bind `HOST=0.0.0.0`; the hosting platform supplies
`PORT`. Health check: `/version`. The app uses SQLite and Pillow for safe slideshow photo processing; install `requirements.txt`.
For other hosts, provide equivalent durable storage, backups, HTTPS, network filtering and
secret management.
