# Bird or SMTP setup

70Scholar sends real verification and password-reset links only when a delivery provider is
configured. Failure or an absent provider does not verify accounts; the owner can separately
grant access under Admin → People.

## Bird

1. Create a scoped regional Bird email API key. Store it only in Render environment variables,
   never in Git or chat. If a key was exposed, revoke it and create a new one.
2. Verify a sending domain in Bird, then set `BIRD_FROM` to an address on that domain.
   `onboarding@messagebird.dev` is limited to sandbox recipients and verified members of the
   Bird workspace, so it cannot serve ordinary public registrations.
3. Set `BIRD_API_KEY`, optionally `BIRD_REGION=us1` or `eu1` (must match the key), and
   `APP_BASE_URL=https://seven0scholar-7cjc.onrender.com` (or the actual custom domain).
4. Use an actual outside inbox to sign up and click the verification link. API acceptance
   is asynchronous and is not proof of delivery; check Bird delivery events if necessary.

The app uses `POST https://{region}.platform.bird.com/v1/email/messages`, classifies messages
as transactional, and disables click/open tracking for authentication links. Official guides:
<https://bird.com/docs/guides/email/sending-email> and
<https://bird.com/docs/get-started/send-your-first-email>.

## SMTP alternative

Leave `BIRD_API_KEY` unset; set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM`, `SMTP_TLS`, and `APP_BASE_URL`. Use a verified sender and TLS. Test with a real
mailbox. A provider failure leaves the user unverified rather than granting access.
