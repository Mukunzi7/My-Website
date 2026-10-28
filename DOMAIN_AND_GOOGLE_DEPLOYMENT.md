> **v18 note:** New private uploads are not offloaded to Cloudinary. See `CLOUD_UPLOADS.md` and `RENDER_DEPLOY.md` for current storage and backup guidance.

# Domains, Google Search, and deployment for 70Scholar

## 1. Choosing a domain

The brand is **70Scholar** (see `BRAND_RENAME.md`). Check availability and trademarks for
names like:

```text
70scholar.com
70scholar.app
70scholar.rw
70scholar.co
70scholar.africa
70scholar.org
```

You do not need a domain to start. Deploy to Render first and use the free URL
`https://seven0scholar-7cjc.onrender.com`, then add a custom domain later.

---

## 2. Deploy first

Follow `RENDER_DEPLOY.md`. Set `APP_BASE_URL` to the URL you will actually use, because
verification emails and `sitemap.xml` are generated from it.

---

## 3. Connecting a custom domain on Render

1. Render dashboard → your `70scholar` service → **Settings** → **Custom Domains**.
2. Click **Add Custom Domain** and enter e.g. `www.70scholar.com`.
3. Render shows the DNS records to add at your registrar:
   - usually a **CNAME** for `www` pointing at `70scholar.onrender.com`
   - and/or an **A record** for the apex domain
4. Add the records, wait for DNS propagation (minutes to a few hours), then click **Verify**.
5. Render provisions a free Let's Encrypt TLS certificate automatically. Always force HTTPS.
6. Update `APP_BASE_URL=https://www.70scholar.com` in Environment and redeploy.
7. Open `https://www.70scholar.com/sitemap.xml` — URLs must now use your real domain.

---

## 4. Google Search Console

1. Go to <https://search.google.com/search-console>.
2. Add a **Domain** property for your domain and verify ownership with the DNS TXT record
   Google provides.
3. Submit the sitemap:

   ```text
   https://www.70scholar.com/sitemap.xml
   ```

4. Use **URL Inspection → Request Indexing** for the homepage.
5. 70Scholar already serves:

   ```text
   /robots.txt
   /sitemap.xml
   ```

   Both are generated from `APP_BASE_URL`, so keep that variable correct.

Tips: add a clear page title/description per route, keep opportunity pages crawlable, and avoid
indexing private routes such as `/dashboard`, `/workspace`, `/admin`, `/account`, `/messages`.

---

## 5. Google Cloud Run alternative

```bash
gcloud run deploy 70scholar \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars HOST=0.0.0.0,PORT=8080,APP_BASE_URL=https://YOUR-PUBLIC-URL,ADMIN_EMAIL=you@example.com,ADMIN_PASSWORD=YourStrongPassword123
```

Cloud Run → **Manage Custom Domains** → add and verify your domain → update DNS → set
`APP_BASE_URL` → redeploy.

---

## 6. Connecting GitHub

```bash
git clone https://github.com/Mukunzi7/My-Website.git
cd My-Website
git add .
git commit -m "Update 70Scholar"
git push origin main
```

Render (or Cloud Build) then deploys automatically from `main`. Never commit `.env`, database
files, `mail_outbox.log`, or API keys — see `GITHUB_GUIDE.md`.

---

## 7. Production warning

For a serious public launch, move off local SQLite and local uploads:

- Database: Render PostgreSQL, Supabase, Neon, or Cloud SQL (`database_postgresql.sql`,
  `POSTGRESQL_SETUP.md`)
- Files: Cloudinary, Google Cloud Storage, S3, or Cloudflare R2 (`CLOUD_UPLOADS.md`)
- Backups: schedule a database backup regardless of which option you choose
