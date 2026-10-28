# Project upload storage and privacy

New v18 project uploads are stored in `UPLOAD_DIR` on the server. The old optional unsigned
Cloudinary upload path is disabled so a new private draft is not automatically sent to a
public third-party bucket. Owner/admin access is required until the project is approved;
public downloads have generic filenames. The owner must inspect every attachment for private
information before approval. Automated text filters cannot inspect images, videos, PDFs,
archives or their metadata.

A persistent disk and independent backups are necessary. Render's free filesystem can be
replaced during a deployment, destroying local uploads. Set `UPLOAD_DIR=/var/data/uploads`
only after mounting a persistent disk. See `RENDER_DEPLOY.md`.

**Existing external copies:** A previous version may already have uploaded files to an
unsigned Cloudinary preset. Disabling new uploads does not revoke those old URLs. Review and
remove or secure any existing third-party objects directly with the provider.
