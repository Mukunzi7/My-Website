# EduBridge Domain, Google Deployment, Google Search, and GitHub Guide

## 1. Recommended domain names

The old EduBridge name is already used by many websites. The recommended new platform name is:

```text
EduBridge
```

Check these domains:

- `edubridge.com`
- `edubridge.co`
- `edubridge.africa`
- `edubridge.app`
- `edubridge.org`
- `edubridge.rw`

You can use the free Render URL first, then buy a domain later.

## 2. Deploying to Google Cloud Run

From inside the project folder:

```bash
gcloud run deploy edubridge \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars HOST=0.0.0.0,ADMIN_EMAIL=you@example.com,ADMIN_PASSWORD=YourStrongPassword123
```

Google will give you a public URL.

## 3. Connecting a custom domain

After deployment:

1. Go to Google Cloud Console.
2. Open Cloud Run.
3. Click your `edubridge` service.
4. Go to **Manage Custom Domains**.
5. Add your domain, for example:

```text
www.edubridge.app
```

6. Verify ownership.
7. Add the DNS records Google gives you at your domain registrar.
8. Wait for DNS propagation.

## 4. Making the site appear on Google Search

1. Deploy your site publicly.
2. Connect a domain.
3. Go to Google Search Console.
4. Add your domain property.
5. Verify ownership using DNS.
6. Submit your sitemap:

```text
https://www.yourdomain.com/sitemap.xml
```

EduBridge includes:

```text
/robots.txt
/sitemap.xml
```

## 5. Connecting to GitHub

From inside the project folder:

```bash
git init
git add .
git commit -m "Initial EduBridge platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/edubridge.git
git push -u origin main
```

If you keep using your existing repository, push to the existing remote:

```bash
git push origin main
```

## 6. Production warning

For a serious public launch, migrate from local SQLite/local uploads to:

- PostgreSQL: Supabase, Neon, Render PostgreSQL, Railway PostgreSQL, or Google Cloud SQL
- Cloud files: Cloudinary, Google Cloud Storage, S3, or Cloudflare R2
