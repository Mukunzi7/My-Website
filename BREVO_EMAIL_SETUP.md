# Brevo account-email setup for 70Scholar

This optional HTTPS integration can be tried without purchasing a custom domain. It does not
change existing accounts, Bird credentials or the website address. Configuration, sender
verification, possible transactional approval, and real inbox testing are still required.
Brevo's free limits and policies may change; check your own account. A verified individual
Gmail sender may be usable, but Brevo can rewrite the visible From address to its own domain
and delivery to every recipient is not guaranteed. A custom authenticated sending domain is
preferable for long-term deliverability, but is not required to try this option.

## 1. Set up the sender in Brevo

1. Create or sign into a Brevo account: <https://www.brevo.com/>. Complete its onboarding.
2. In Brevo, open **Settings → Senders, Domains, IPs → Senders → Add a sender**.
3. Use name **70Scholar** and the owner's mailbox **honoremukunzi6@gmail.com**, if the owner
   controls that mailbox. Save and enter the six-digit verification code Brevo sends there.
   This verifies an individual sender; it does not authenticate a Gmail domain you do not own.
4. If Brevo says its transactional platform is not activated, request activation through
   Brevo support and wait for approval. Sender verification and transactional activation are
   separate. Do not enter Bird DNS records on the Render-owned website hostname.

## 2. Create an API key privately

In Brevo, open **Settings → SMTP & API → API Keys & MCP** and create a standard **API key**
for 70Scholar, not an MCP key or SMTP key. If offered restricted permissions, choose
**Restricted** and set **Transactional email = All**; leave unrelated resources at None.
Brevo documents that its Transactional email resource offers None, Read or All, and that
Read cannot send; All also permits other transactional-email operations, so keep the key
private. Copy it directly into Render in the next step. Never paste the key, database
password or full connection URL into chat, Git, screenshots, public files, browser code, or
the 70Scholar admin dashboard. If a key is exposed, revoke it in Brevo and create a new one.

## 3. Select Brevo in Render

In Render, open the existing **70scholar** service → **Environment**. Add these variables:

```text
EMAIL_PROVIDER=brevo
BREVO_FROM=honoremukunzi6@gmail.com
BREVO_API_KEY=<paste the new API key privately in Render>
```

`BREVO_FROM` must exactly match the sender you verified in Brevo. Do not type the angle-bracket
placeholder as the API key. If needed, set `APP_BASE_URL` to the actual public HTTPS site root,
for example `https://seven0scholar-7cjc.onrender.com`; otherwise Render's
`RENDER_EXTERNAL_URL` is used. Don't change database, storage, owner-account, or existing Bird
settings. Choose **Save and deploy** (wording can vary) and wait for a successful deployment.
The app reads environment variables at startup. **Save only** does not immediately activate
the change.

An explicitly selected provider is the only one used. If Brevo is missing its key or sender,
or rejects a request, the app does not silently use Bird/SMTP or verify the account. The old
Bird variables can remain in place. To switch back deliberately, set `EMAIL_PROVIDER=bird`
with a working Bird key/sender, or `EMAIL_PROVIDER=smtp` with working SMTP settings, and deploy.
With `EMAIL_PROVIDER` unset the previous Bird-first, then SMTP selection is retained, and
Brevo is not auto-selected.

## 4. Check privacy and test delivery

Brevo sends the email contents and may record opens or clicks; the verification/reset code is
in the message but never in the 70Scholar link, so a rewritten link does not itself contain
that code. The code is single-use and expires. Do not share codes. Anonymous tracking does
**not** disable tracking. For additional privacy, if available enable **Settings → Automations
→ Transactional emails → Tracking → Anonymous email tracking → Yes → Save** in Brevo.
This changes which per-recipient events are visible, and may make delivery troubleshooting
less detailed. Review Brevo's current settings and the site's privacy obligations.

1. Sign into 70Scholar as the owner, open **Admin → People → Account email delivery**, and
   select **Send test email to the owner**. It only sends to the owner mailbox. Check Inbox
   and Spam. An HTTP acceptance response is not proof of delivery.
2. With another inbox you control, create a separate test account. Check its email and Spam,
   open the 70Scholar page linked from the message, and paste the latest verification code.
   Sign in. If a new email was requested, older verification codes will no longer work.
3. Test **Forgot password** using that test account: check the email, open the reset page,
   paste its code and choose a new password. Do not use or share someone else's code.
4. Inspect Brevo's transactional logs for delivered, rejected, blocked or bounced events;
   Gmail sender rewriting, filters, quotas and account approval can affect delivery. If the
   owner test works but another mailbox does not, keep investigating before public launch.

For a person who cannot receive an email, the owner can independently use **Admin → People
→ Grant access**. That permits sign-in but does not claim the email is verified. Email failure
or an unconfigured provider never automatically grants access.

## References

- API: <https://developers.brevo.com/reference/send-transac-email>
- Sender verification: <https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email>
- Restricted API key permissions: <https://help.brevo.com/hc/en-us/articles/40158277171474-About-API-key-permissions>
- Gmail and sender rewriting: <https://help.brevo.com/hc/en-us/articles/14925263522578-Comply-with-Gmail-Yahoo-and-Microsoft-s-requirements-for-email-senders>
- Transactional activation: <https://help.brevo.com/hc/en-us/articles/115000188150-Troubleshooting-Issues-with-Brevo-SMTP>
- Anonymous tracking: <https://help.brevo.com/hc/en-us/articles/11643306229906-Can-I-anonymize-the-tracking-of-opens-and-clicks-for-my-emails>
