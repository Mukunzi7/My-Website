# 70Scholar Cloud Uploads

70Scholar now supports optional cloud uploads through Cloudinary unsigned uploads.

By default, files are saved locally in:

```text
uploads/
```

If Cloudinary environment variables are set, uploaded project files are also uploaded to Cloudinary and 70Scholar stores the cloud URL. Downloads redirect to the cloud file URL.

## Environment variables

```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_UPLOAD_PRESET=your-unsigned-upload-preset
```

## Cloudinary setup

1. Create a Cloudinary account.
2. Go to Settings → Upload.
3. Create an unsigned upload preset.
4. Add the preset name and cloud name to your hosting environment variables.
5. Restart/redeploy 70Scholar.

## Production recommendation

Cloudinary is easy for an MVP. Later, for more control, migrate to:

- Google Cloud Storage
- Cloudflare R2
- Amazon S3

The current code is structured so the upload step can be replaced with another provider later.
