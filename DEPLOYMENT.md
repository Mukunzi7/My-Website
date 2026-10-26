# 70Scholar deployment overview

**For Render (recommended), read `RENDER_DEPLOY.md` first.** It has a one-click Blueprint link,
the exact environment variables, persistent storage, and a custom-domain checklist.

Files in this repo that make deployment possible:

| File | Host |
| --- | --- |
| `render.yaml` | Render Blueprint (recommended) |
| `Procfile` | Railway / Heroku-style platforms |
| `Dockerfile` | Any container host, Fly.io, Cloud Run |
| `fly.toml` | Fly.io |
| `cloudbuild.yaml` | Google Cloud Build → Cloud Run |
| `.env.example` | Template for all environment variables |

The app is pure Python standard library, so the build command is just
`pip install -r requirements.txt` (that file is intentionally empty apart from comments).

---

## Universal requirements

```text
HOST=0.0.0.0
PORT=<the port your host injects>
APP_BASE_URL=https://your-public-domain
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=a-long-unique-password
BIRD_API_KEY=bk_...        # or SMTP_* — needed for email verification
```

- The server binds to `HOST:PORT` from the environment; it never hardcodes localhost.
- `do_HEAD` is implemented because many hosts probe with `HEAD /`.
- `/version` is a lightweight health check that returns the running `APP_VERSION`.
- SQLite and `uploads/` live on the container filesystem by default. On any host that rebuilds
  the container, set `DB_PATH` and `UPLOAD_DIR` to a mounted volume or use external storage.

---

## Render

See `RENDER_DEPLOY.md`. Summary:

```text
Build:    pip install -r requirements.txt
Start:    python3 server.py
Health:   /version
Plan:     free (no disk) → upgrade + Render Disk for real data
```

One-click: <https://render.com/deploy?repo=https://github.com/Mukunzi7/My-Website>

---

## Google Cloud Run

```bash
gcloud run deploy 70scholar \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars HOST=0.0.0.0,PORT=8080,APP_BASE_URL=https://YOUR-PUBLIC-URL,ADMIN_EMAIL=you@example.com,ADMIN_PASSWORD=YourStrongPassword123,BIRD_API_KEY=bk_xxx
```

`cloudbuild.yaml` automates this with Cloud Build. Cloud Run is stateless, so use Cloud SQL
(PostgreSQL) plus Cloud Storage/Cloudinary for uploads before a public launch.

---

## Docker (local or any host)

```bash
docker build -t 70scholar .
docker run -p 8080:10000 \
  -e HOST=0.0.0.0 \
  -e PORT=10000 \
  -e APP_BASE_URL=http://localhost:8080 \
  -e ADMIN_EMAIL=you@example.com \
  -e ADMIN_PASSWORD='ChangeThisStrongPassword123!' \
  -v "$PWD/data:/var/data" \
  -e DB_PATH=/var/data/70scholar.sqlite3 \
  -e UPLOAD_DIR=/var/data/uploads \
  70scholar
```

The Dockerfile exposes `10000` by default; override `PORT` if your host expects `8080`.

---

## Fly.io

`fly.toml` sets `PORT=8080` and mounts nothing by default. Before a real launch:

```bash
fly volumes create 70scholar_data --size 1 --region jnb
# add a [mounts] section, then set DB_PATH=/data/70scholar.sqlite3 and UPLOAD_DIR=/data/uploads
fly secrets set ADMIN_PASSWORD=... BIRD_API_KEY=... APP_BASE_URL=https://your-app.fly.dev
fly deploy
```

---

## Production checklist

1. Confirm the current v13 code is on `main` (older commits had a truncated `server.py`).
2. Set `ADMIN_PASSWORD`, `APP_BASE_URL`, and an email provider before the first boot.
3. Verify `/version`, `/static/styles.css`, `/static/app.js`, `/robots.txt`, `/sitemap.xml`.
4. Add persistent storage for SQLite and uploads, or migrate to PostgreSQL + cloud files.
5. Force HTTPS, add a custom domain, submit the sitemap to Google Search Console.
6. Back up the database; a disk alone is not a backup.
7. Add file scanning, audit logs, and rate limiting before a large public launch.

---

## Direct Mobile Money funding

70Scholar uses direct creator Mobile Money funding. Each project creator enters their own
Mobile Money details before publishing; sponsors send money to the creator, not to the platform
owner. See `PAYMENTS.md`.
