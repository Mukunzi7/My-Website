# EduBridge Email Verification and Password Reset

EduBridge now includes production-style account security flows:

- Email verification after signup
- Login blocked until email is verified
- Password reset request page
- Password reset tokens that expire
- Session invalidation after password reset

## Local development

If SMTP is not configured, EduBridge writes emails to:

```text
mail_outbox.log
```

After signup, open that file and copy the verification link.

## Production SMTP environment variables

Set these in your hosting provider:

```bash
APP_BASE_URL=https://www.yourdomain.com
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=noreply@yourdomain.com
SMTP_TLS=1
```

Recommended email providers:

- SendGrid
- Mailgun
- Amazon SES
- Brevo
- Google Workspace SMTP

## Pages added

```text
/verify-email?token=...
/forgot-password
/reset-password?token=...
```

## Security notes

- Tokens are stored hashed in the database.
- Verification tokens expire after 48 hours.
- Password reset tokens expire after 2 hours.
- Password reset deletes existing login sessions for that user.

## Bird / MessageBird email option

EduBridge now supports Bird email as the first email provider. If `BIRD_API_KEY` is set, EduBridge sends verification and password-reset emails through Bird. If it is not set, EduBridge falls back to SMTP, then to `mail_outbox.log` in local development.

Set these environment variables:

```bash
BIRD_API_KEY=bk_xxxxxxxxx
BIRD_FROM=onboarding@messagebird.dev
BIRD_REGION=us1
```

Replace `bk_xxxxxxxxx` with your real Bird API key in your local `.env` file or hosting dashboard. Do **not** commit the real API key to GitHub. If you pasted a real key in chat or committed it anywhere, rotate/delete it in the Bird dashboard and create a new one.

A TypeScript example is included at:

```text
examples/bird-email-example.ts
```
