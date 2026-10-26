# GitHub guide for Learnwella

Repository: **<https://github.com/Mukunzi7/My-Website>** (public, branch `main`).

## Clone and work

```bash
git clone https://github.com/Mukunzi7/My-Website.git
cd My-Website
python3 server.py          # http://127.0.0.1:8080
```

## Push changes

```bash
git add .
git status                  # check what you are about to commit
git commit -m "Describe the change"
git push origin main
```

Render has **Auto-Deploy** enabled by default, so a push to `main` triggers a new deployment.
Confirm the new build at `https://<your-service>.onrender.com/version`.

## Applying the v12 changes supplied by an agent

```bash
# Option 1 — bundle (exact commit, most robust)
git pull /path/to/My-Website-v12.bundle main

# Option 2 — plain diff
git apply --binary /path/to/v12-full.diff
git add -A
git commit -m "v12: restore app, add styling, align brand"

git push origin main
```

## Keep secrets private

Never commit:

- `.env` or any real Bird / SMTP / Cloudinary keys
- `edubridge.sqlite3` (contains user accounts and email tokens)
- `mail_outbox.log` (contains verification and password-reset links)
- anything inside `uploads/` (user files)

`.gitignore` already excludes these. Both `edubridge.sqlite3` and `mail_outbox.log` were
removed from version control in v12 because they had been committed with real user data —
if a secret was ever pushed, rotate it.

## Before you deploy

1. `python3 -m py_compile server.py`
2. `python3 server.py` and open `/version`, `/static/styles.css`, `/static/app.js`
3. Commit and push
4. Follow `RENDER_DEPLOY.md`
