# Deploy Learnwella to Render

This is the shortest path from the v12 code in this repo to a live public URL. Render reads the
`render.yaml` Blueprint in the repo root, so most settings are already filled in.

> **Order matters:** push the v12 changes to GitHub **first**, then deploy. The deploy button
> always builds whatever is on `main` at that moment.

---

## 0. Push the v12 changes to GitHub

The commits currently on GitHub still contain the truncated 57-line `server.py`. Get the fixed
version onto `main` using whichever route you prefer:

**Option A — from your own computer (no token shared with anyone):**

Three files are provided in the workspace — use any one of them:

**A. Bundle (most robust — includes the exact commit):**

```bash
git clone https://github.com/Mukunzi7/My-Website.git
cd My-Website
git pull /path/to/My-Website-v12.bundle main
git push origin main
```

**B. Plain diff (verified to apply cleanly to `main`):**

```bash
git clone https://github.com/Mukunzi7/My-Website.git
cd My-Website
git apply --binary /path/to/v12-full.diff
git add -A
git commit -m "v12: restore app, add styling, align brand"
git push origin main
```

**C. ZIP via the GitHub web UI:** download `My-Website-v12.zip`, unzip it, and upload the
files into the repo (replace `server.py`, add the whole `static/` folder, add
`RENDER_DEPLOY.md`) with the commit message `v12: restore app, add styling, align brand`.
Also delete the tracked `edubridge.sqlite3` and `mail_outbox.log` files.

If `git commit` complains about an unknown identity, set it once:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

---

## 1. One-click deploy (recommended)

1. Create a free account at <https://render.com> (sign in with GitHub).
2. Click this button:

   **[🚀 Deploy to Render](https://render.com/deploy?repo=https://github.com/Mukunzi7/My-Website)**

   Or paste this URL into your browser:

   ```text
   https://render.com/deploy?repo=https://github.com/Mukunzi7/My-Website
   ```

3. Render detects `render.yaml` and shows a **Blueprint** preview with one service named
   `learnwella`. Give the Blueprint a name (e.g. `learnwella`) and click **Apply**.
4. When prompted, fill in the secret environment variables listed in step 3 below.
5. Wait for the build (usually 1–3 minutes). Your site will be at:

   ```text
   https://learnwella.onrender.com
   ```

   (Render appends a suffix if that name is taken — use the URL it shows in the dashboard.)

---

## 2. Manual deploy (same result)

1. Render dashboard → **New +** → **Web Service**.
2. **Connect a repository:** choose `Mukunzi7/My-Website` (public). If you don't see it,
   click *Configure account* and grant Render access to that repo.
3. Configure:

   | Setting | Value |
   | --- | --- |
   | Name | `learnwella` |
   | Region | Singapore or Frankfurt (closest to Rwanda) |
   | Branch | `main` |
   | Runtime | **Python 3** |
   | Build command | `pip install -r requirements.txt` |
   | Start command | `python3 server.py` |
   | Instance type | Free (or Starter if you need a persistent disk — see step 5) |
   | Health check path | `/version` |

4. Add the environment variables below, then click **Create Web Service**.

---

## 3. Environment variables (set these before the first deploy)

In Render: your service → **Environment** → **Add Environment Variable**.

| Key | Value | Why |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Required; otherwise Render reports "No open ports detected" |
| `PORT` | `10000` | Render injects this automatically; set it explicitly if your plan doesn't |
| `APP_BASE_URL` | `https://<your-service>.onrender.com` | Base URL used in verification emails and `sitemap.xml` (no trailing slash) |
| `ADMIN_EMAIL` | your real email | Owner admin created on first boot |
| `ADMIN_PASSWORD` | a long unique password | **Critical.** The built-in default is public in the code |
| `BIRD_API_KEY` | `bk_…` | Sends verification / password-reset emails |
| `BIRD_FROM` | `onboarding@messagebird.dev` | Verified Bird sender |
| `BIRD_REGION` | `us1` or `eu1` | Usually auto-detected from the key prefix |

Optional: `BIRD_REGION`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`,
`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_UPLOAD_PRESET`, `MOMO_PAYMENT_INSTRUCTIONS`,
`FLUTTERWAVE_PAYMENT_LINK`, `STRIPE_PAYMENT_LINK`, `PAYPAL_PAYMENT_LINK`, `MOMO_PAYMENT_LINK`,
`MAX_UPLOAD_BYTES`, `DB_PATH`, `UPLOAD_DIR`.

> ⚠️ **Email is mandatory for real users.** Signup requires email verification and login is
> blocked until it succeeds. With no Bird/SMTP key, links are written to `mail_outbox.log`
> inside the container — your users will never see them. Set `BIRD_API_KEY` before inviting
> anyone. Details: `BIRD_EMAIL_SETUP.md`.

> ⚠️ **Never put secrets in `render.yaml` or `.env.example`.** Those files are public. The
> Blueprint marks secrets `sync: false` so Render asks you for them at deploy time.

---

## 4. Persistent storage (do this before real users sign up)

Render's container filesystem is **ephemeral**: every deploy or restart wipes
`edubridge.sqlite3` and `uploads/`. That means accounts, projects, pledges, and uploaded files
disappear.

**Best quick fix — a Render Disk** (requires a paid Starter plan, ~$7/month):

1. Upgrade the service to **Starter** or higher.
2. Service → **Disks** → **Add Disk**:
   - Name: `data`
   - Mount path: `/var/data`
   - Size: `1 GB` (increase later)
3. Add two environment variables:

   ```text
   DB_PATH=/var/data/learnwella.sqlite3
   UPLOAD_DIR=/var/data/uploads
   ```

   `server.py` now reads both, so the database and uploaded files survive deploys.
4. **Manual Deploy** once to apply, then confirm `/version` still responds.

If you want to add the disk directly to the Blueprint instead, change `plan: free` to
`plan: starter` in `render.yaml` and add:

```yaml
    disk:
      name: data
      mountPath: /var/data
      sizeGB: 1
```

and add `DB_PATH` / `UPLOAD_DIR` to `envVars`.

**Better long-term fix:** migrate to Render PostgreSQL (schema in `database_postgresql.sql`)
and Cloudinary/S3 for files (`CLOUD_UPLOADS.md`, `POSTGRESQL_SETUP.md`). Take regular backups
either way — a disk is not a backup.

---

## 5. Verify the deployment

| Check | Expected |
| --- | --- |
| `https://<service>.onrender.com/` | Styled Learnwella landing page (dark hero, gold buttons) |
| `…/version` | `Learnwella v12-learnwella-brand-static-render - full app restored, static assets included, Render-ready` |
| `…/static/styles.css` | 200, CSS text (if 404, the `static/` folder wasn't pushed) |
| `…/static/app.js` | 200, JS text |
| `…/opportunities` | Directory with seeded listings |
| `…/signup` | Signup form; verification email arrives via Bird |
| `…/robots.txt`, `…/sitemap.xml` | Valid files using your `APP_BASE_URL` |

If `/version` still shows `v11…` or the pages are unstyled, Render is building old code:
confirm the push landed on `main`, then use **Manual Deploy → Clear build cache & deploy**.

**Free-tier note:** free web services spin down after 15 minutes of inactivity, so the first
request after a pause can take 30–50 seconds. A paid plan removes the cold start.

---

## 6. Custom domain and Google

1. Render → your service → **Settings** → **Custom Domains** → **Add Custom Domain**
   (e.g. `learnwella.rw` or `www.learnwella.com`).
2. At your registrar, add the **CNAME / A records** Render shows. Render provisions a free
   Let's Encrypt HTTPS certificate automatically (allow up to ~24h for DNS).
3. Update `APP_BASE_URL` to `https://yourdomain.com` and redeploy — verification links and
   `sitemap.xml` will then use the real domain.
4. Google Search Console → add the domain property → verify via DNS → submit
   `https://yourdomain.com/sitemap.xml`.

More detail: `DOMAIN_AND_GOOGLE_DEPLOYMENT.md`.

---

## 7. Day-to-day workflow

```text
edit code → git commit → git push origin main → Render auto-deploys (Auto-Deploy is ON by default)
```

Watch **Logs** in the Render dashboard during a deploy. Every page links `/version`, so you can
always confirm which build is live.

---

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `No open ports detected on 0.0.0.0` | Set `HOST=0.0.0.0`; confirm `PORT` matches Render's value |
| `Unsupported method ('HEAD')` | Fixed — `server.py` implements `do_HEAD` for health checks |
| Blank/unstyled pages | `static/` folder missing from GitHub; push `styles.css` and `app.js` |
| Nothing served at all / import error | You deployed the truncated 57-line `server.py`; push the v12 fix and redeploy |
| Users can't log in after signup | No email provider configured — set `BIRD_API_KEY` and `BIRD_FROM` |
| Verification link points to `127.0.0.1` | Set `APP_BASE_URL` to your public HTTPS URL |
| Accounts/projects vanish after deploy | Add a Render Disk + `DB_PATH` / `UPLOAD_DIR` (step 4) |
| Uploads fail on large files | Host/browser limits; offload to Cloudinary (`CLOUD_UPLOADS.md`) |
| Old version still live | Check the GitHub commit, clear build cache, redeploy |
