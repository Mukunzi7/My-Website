# EduBridge Deployment Guide

This project includes deployment-ready files:

- `Procfile` for Railway/Heroku-style platforms.
- `render.yaml` for Render.
- `Dockerfile` for Docker/Fly.io/Google Cloud Run.
- `cloudbuild.yaml` for Google Cloud Build.
- `.env.example` for production configuration.

## Best Google deployment option: Cloud Run

EduBridge is a Python web app, so the easiest Google deployment is **Google Cloud Run**.

From inside the project folder:

```bash
gcloud run deploy edubridge \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars HOST=0.0.0.0,ADMIN_EMAIL=you@example.com,ADMIN_PASSWORD=YourStrongPassword123
```

Google will give you a public URL that anyone can access.

For full instructions, read:

```text
DOMAIN_AND_GOOGLE_DEPLOYMENT.md
```

## Render deployment

1. Create a GitHub repository.
2. Upload the entire `edubridge_platform` folder.
3. Go to Render.com and create a new **Web Service**.
4. Connect your GitHub repo.
5. Use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python3 server.py`
6. Add environment variables:
   - `HOST=0.0.0.0`
   - `PORT=10000`
   - `ADMIN_EMAIL=your-email@example.com`
   - `ADMIN_PASSWORD=a-very-strong-password`
7. Deploy.

## Docker deployment

```bash
docker build -t edubridge .
docker run -p 8080:8080 \
  -e HOST=0.0.0.0 \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD='ChangeThisStrongPassword123!' \
  edubridge
```

Open:

```text
http://localhost:8080
```

## Direct Mobile Money funding

EduBridge now uses direct creator Mobile Money funding. Each project creator enters their own Mobile Money details before publishing.

Sponsors send money to the creator, not to your platform account.

## Important production notes

1. Use HTTPS in production.
2. Change the default admin password.
3. Use persistent storage for SQLite or migrate to PostgreSQL.
4. Use Google Cloud Storage/S3/R2 for uploads instead of local disk.
5. Add email verification and password reset before public launch.
6. Add marketplace moderation before allowing public uploads.
