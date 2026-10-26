# Bird / MessageBird Email Setup for Learnwella

Learnwella now supports Bird email for:

- Email verification
- Password reset emails

## Important security warning

Do **not** hardcode your real Bird API key in `server.py` or commit it to GitHub.

Use this placeholder in code/docs:

```text
bk_xxxxxxxxx
```

Then replace it only in your local `.env` file or your hosting provider's environment variables.

If you pasted a real key into chat, GitHub, or any public place, rotate/delete it in the Bird dashboard and create a new key.

## Environment variables

Set:

```bash
BIRD_API_KEY=bk_xxxxxxxxx
BIRD_FROM=onboarding@messagebird.dev
BIRD_REGION=us1
APP_BASE_URL=https://www.yourdomain.com
```

Replace `bk_xxxxxxxxx` with your real Bird API key.

If your key starts with `bk_us1_`, use:

```bash
BIRD_REGION=us1
```

If your key starts with `bk_eu1_`, use:

```bash
BIRD_REGION=eu1
```

Learnwella can auto-detect `us1` or `eu1` from the key prefix, so `BIRD_REGION` is optional.

## How it works in the Python app

The existing `send_email()` function now checks providers in this order:

1. Bird API if `BIRD_API_KEY` is set
2. SMTP if `SMTP_HOST` is set
3. Local development outbox: `mail_outbox.log`

So after you set `BIRD_API_KEY`, verification and reset emails automatically use Bird.

## TypeScript example

A TypeScript example was added here:

```text
examples/bird-email-example.ts
```

Install the SDK if you want to run the TypeScript example separately:

```bash
npm install @messagebird/sdk
```

Then run it with your environment variable set:

```bash
BIRD_API_KEY=bk_xxxxxxxxx npx tsx examples/bird-email-example.ts
```

Again, replace `bk_xxxxxxxxx` with your real key locally only.
