# Account verification and access

Name, email and password are required at signup; phone and other profile fields are optional.
Contact details are visible to the account holder and owner admin, not in public project/message
views. Configure Brevo, Bird or SMTP to request verification and password-reset emails. See
`BREVO_EMAIL_SETUP.md` and `BIRD_EMAIL_SETUP.md` for the distinct provider requirements.
On Render, `APP_BASE_URL` takes precedence; if unset, `RENDER_EXTERNAL_URL` supplies the
public site URL. Account pages must use a public HTTPS address on Render. Email is marked
verified only after a valid, unexpired token is consumed. If the provider is missing, rejects
a message or fails, the account remains unverified and cannot sign in unless the owner grants
access. Provider acceptance is not proof of inbox delivery.

When `EMAIL_PROVIDER=brevo`, the email contains a one-time code, and its link to the relevant
70Scholar page does **not** contain the code. This avoids placing the bearer secret in a link
that Brevo may rewrite for click tracking. The code is 128 bits of randomness, is valid for
48 hours for verification or two hours for password reset, and is shown grouped for copying.
Whitespace, dashes and letter case are normalized on input. A new request invalidates the
previous token of that purpose. The provider necessarily receives the recipient address and
message, including the code. Brevo may track opens and clicks, including after anonymization;
anonymous tracking reduces the association with individual recipients but does not turn
tracking off. Review its settings and applicable privacy/consent requirements. Do not share
codes or credentials. Existing Bird/SMTP email links, including previously issued unexpired
links, continue to work; old token query parameters are redacted from app logs.

The owner-only Admin → People → Account email panel shows non-secret setup categories and can
send a test only to the owner's own email address. A successful API response is only acceptance:
check spam and provider delivery events, then test another inbox. Bird's shared onboarding
sender is restricted to sandbox addresses and verified workspace members. Render Free blocks
outbound SMTP ports 25, 465 and 587; an HTTPS email API is usually the practical option.
Explicit `EMAIL_PROVIDER` selection never silently falls back. With the selector unset, the
previous Bird-first, then SMTP behavior remains unchanged; Brevo requires explicit selection.

Admin → People → **Grant access** sets a separate `admin_approved` flag; it does not mark the
email verified. A granted user can request a new verification email from Account settings.
The owner can revoke that grant, block/unblock accounts, or reset passwords. A blocked account
cannot sign in even if it has a verified email or grant; its sessions are revoked. Security
filters can be imperfect and need review. Verification/reset token hashes, rather than raw
tokens or codes, are stored in the configured database; tokens expire and are single-use.
Password resets revoke existing sessions.

The one-time v18 migration distrusts older auto-verified accounts unless a used verification
token provides evidence. Those accounts must verify again or receive an explicit owner grant.
Existing sessions for accounts without access are removed. The demo account is disabled.
The old predictable owner default password is disabled; set `ADMIN_PASSWORD` in Render.

For public launch, additionally deploy behind HTTPS, add rate limiting/abuse protection,
use persistent encrypted storage and backups, review privacy laws/consent, and conduct an
independent security assessment. No provider's acceptance response proves inbox delivery.
