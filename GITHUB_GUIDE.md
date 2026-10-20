# GitHub Connection Guide for EduBridge

## Push the current project to GitHub

```bash
cd edubridge_platform
git init
git add .
git commit -m "Initial EduBridge platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/edubridge.git
git push -u origin main
```

If you are using the existing GitHub repository that was already connected, use:

```bash
git push origin main
```

## Keep secrets private

Do not commit:

- `.env`
- real Bird API keys
- database files
- uploaded user files

The `.gitignore` file already excludes these.
