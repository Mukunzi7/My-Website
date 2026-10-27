# Render port binding and health-check fix

## The error

```text
No open ports detected on 0.0.0.0
Detected open ports on localhost -- did you mean to bind one of these to 0.0.0.0?
```

This means the server was listening on `127.0.0.1` / `localhost` instead of `0.0.0.0`.
`server.py` now binds from the environment:

```python
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
```

Render can detect the port. Set `HOST=0.0.0.0` and let Render supply `PORT` (usually `10000`).

## HEAD requests

Render may send `HEAD /` health checks. `server.py` implements `do_HEAD`, so this is fixed:

```text
Unsupported method ('HEAD')
```

Use `healthCheckPath: /version` in `render.yaml` for a cheap, explicit health check.

## Render settings

```text
Runtime:        Python 3
Build command:  pip install -r requirements.txt
Start command:  python3 server.py
Health check:   /version
```

Environment variables (see `RENDER_DEPLOY.md` for the full table):

```text
HOST=0.0.0.0
PORT=10000
APP_BASE_URL=https://seven0scholar-7cjc.onrender.com
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=your-strong-password
BIRD_API_KEY=bk_xxxxxxxxx
BIRD_FROM=onboarding@messagebird.dev
BIRD_REGION=us1
```

Usually you do not need to set `PORT` manually because Render provides it. If asked, use `10000`.

## v17 deployment gotchas

1. **Deploy current `main`.** Older commits contained a truncated 57-line `server.py`
   that imports but serves nothing; the current file is complete. Confirm locally with `python3 -m py_compile server.py` and
   by opening `/version`.
2. **Push the `static/` folder.** `/static/styles.css` and `/static/app.js` must return 200;
   otherwise the site loads unstyled.
3. **Check `/version` after deploy.** It must say
   `70Scholar v17-programs ...`.

## After updating GitHub

```bash
git add .
git commit -m "Fix Render deployment"
git push origin main
```

Then let Auto-Deploy run, or use **Manual Deploy → Clear build cache & deploy**.
