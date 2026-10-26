# Windows update and version-check guide

On Windows, `grep` is usually unavailable. Use `findstr` (Command Prompt) or `Select-String`
(PowerShell).

## 1. Confirm you have the v12 code

From the project folder:

```bat
findstr /C:"Learnwella v12 is live" server.py
```

You should see the update-banner line. Then check the supporting files exist:

```bat
dir static
findstr /C:"reveal-on-scroll" static\app.js
findstr /C:"nav-profile" static\styles.css
findstr /C:"APP_VERSION" server.py
findstr /C:"10 MB" static\app.js
```

PowerShell equivalents:

```powershell
Select-String -Path server.py -Pattern "Learnwella v12 is live"
Select-String -Path static\app.js -Pattern "reveal-on-scroll"
Select-String -Path static\styles.css -Pattern "nav-profile"
```

Also confirm `static\` contains both `styles.css` and `app.js`. If the folder is missing, the
site will load without styling.

## 2. Run locally

```bat
py -3 server.py
```

Open <http://127.0.0.1:8080> and then <http://127.0.0.1:8080/version>. You should see:

```text
Learnwella v12-learnwella-brand-static-render - full app restored, static assets included, Render-ready
```

## 3. Push and redeploy

```bat
git add .
git commit -m "Update Learnwella"
git push origin main
```

Render deploys automatically from `main`. If it doesn't, use **Manual Deploy → Clear build
cache & deploy** in the Render dashboard.

## 4. Check the live version

Open:

```text
https://<your-service>.onrender.com/version
```

You must see the same v12 string. Also open `/static/styles.css` — it should return CSS, not a
404 page.

If the live site still shows `v11` or looks unstyled, Render is running old code. See
`RENDER_DEPLOY.md` → Troubleshooting.
