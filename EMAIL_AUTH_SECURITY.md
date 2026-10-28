# Account verification and access

Name, email, phone and password are required at signup. Phone and other account details are
visible to the account holder and owner admin, not in public project/message views. Configure
Bird or SMTP and `APP_BASE_URL` to send a verification link. Email is marked verified only
after a valid, unexpired token is consumed. If the provider is missing, rejects a message or
fails, the account remains unverified and cannot sign in unless the owner grants access.

Admin → People → **Grant access** sets a separate `admin_approved` flag; it does not mark the
email verified. A granted user can request a verification link later from Account settings. The owner can revoke that grant, block/unblock accounts, or reset passwords.
A blocked account cannot sign in even if it has a verified email or grant; its sessions are
revoked. Security filters can be imperfect and need review. Password reset uses the configured
email provider. Verification/reset tokens are hashed in SQLite, expire, are single-use and
are redacted from server request logs.

The one-time v18 migration distrusts older auto-verified accounts unless a used verification
token provides evidence. Those accounts must verify again or receive an explicit owner grant.
Existing sessions for accounts without access are removed. The demo account is disabled.
The old predictable owner default password is disabled; set `ADMIN_PASSWORD` in Render.

For public launch, additionally deploy behind HTTPS, add rate limiting/abuse protection,
use persistent encrypted storage and backups, review privacy laws/consent, and conduct an
independent security assessment. A Bird/SMTP acceptance response is not proof of delivery.
