# Render Port Binding Fix

If Render shows this error:

```text
No open ports detected on 0.0.0.0
Detected open ports on localhost -- did you mean to bind one of these to 0.0.0.0?
```

It means the server is listening on `127.0.0.1` / `localhost` instead of `0.0.0.0`.

This has been fixed in `server.py`:

```python
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
```

Render can now detect the web service port.

## Render settings

Use these settings:

```text
Build command: pip install -r requirements.txt
Start command: python server.py
```

Environment variables:

```text
HOST=0.0.0.0
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=your-strong-password
APP_BASE_URL=https://your-render-url.onrender.com
BIRD_API_KEY=bk_xxxxxxxxx
BIRD_FROM=onboarding@messagebird.dev
BIRD_REGION=us1
```

Usually you do not need to set `PORT` manually because Render provides it automatically. If Render asks for it, use:

```text
PORT=10000
```

## HEAD request fix

Render may send `HEAD /` health checks. The app now supports `HEAD` requests, so this error is also fixed:

```text
Unsupported method ('HEAD')
```

## After updating GitHub

Commit and push the fixed version:

```bash
git add .
git commit -m "Fix Render port binding"
git push origin main
```

Then redeploy on Render.
