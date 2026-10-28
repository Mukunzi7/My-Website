# Update 70Scholar on Windows

Before updating the live Render service, read `RENDER_DEPLOY.md`: a deploy on free ephemeral
storage may erase live users, projects and files. A local checkout is not a live backup.

In PowerShell:

```powershell
cd C:\path\to\My-Website
git pull origin main
$env:ADMIN_PASSWORD = 'a-long-unique-password'
$env:APP_BASE_URL = 'http://localhost:8080'
python -m unittest discover -s tests -v
python server.py
```

Open `http://localhost:8080`. Check `/version` for
`70Scholar v18-privacy-r1 - privacy, owner review and funding`. Sign in with the owner account,
configure email and an owner payment link when ready, and inspect the admin queues. Do not
store the password in a committed file. Existing accounts may require email verification or
an owner grant; existing projects must be reapproved after the v18 migration.
