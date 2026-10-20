# Windows Update and Version Check Guide

On Windows, `grep` is usually not available. Use `findstr` or PowerShell.

## Check if your folder has the newest EduBridge code

From your project folder, run:

```bat
findstr /C:"EduBridge v11 is live" server.py
```

You should see a line containing:

```text
EduBridge v11 is live
```

Also check scroll effects:

```bat
findstr /C:"reveal-on-scroll" static\app.js
```

Check profile photo nav CSS:

```bat
findstr /C:"nav-profile" static\styles.css
```

Check the new upload settings:

```bat
findstr /C:"v11" server.py
findstr /C:"10 MB" server.py
findstr /C:"10 MB" static\app.js
```

## PowerShell alternatives

```powershell
Select-String -Path server.py -Pattern "EduBridge v11 is live"
Select-String -Path static\app.js -Pattern "reveal-on-scroll"
Select-String -Path static\styles.css -Pattern "nav-profile"
```

## After pushing and redeploying Render

Open:

```text
https://your-site.onrender.com/version
```

You should see:

```text
EduBridge v11-unlimited-project-uploads-profile-10mb - project uploads unlimited by app - profile photo max 10 MB
```

If you do not see that, Render is still running old code.
