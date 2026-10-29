# 70Scholar v20 feature guide

## Discovery and homepage

- The opening hero uses the owner-supplied group photo as its background, with a dark
  overlay for readability. The owner's Seven Scholars emblem replaces the large homepage
  wordmark and appears in the header, footer and favicon; the platform name remains
  70Scholar. The owner can add or remove any slideshow photo under **Admin → Slideshow photos**.
  New images appear first; the empty slideshow is hidden. The old cursor-following
  descriptions are removed.
- The long-scroll homepage retains the rotating slideshow but removes the seven-photo static
  gallery and the old headline. Program details and official links are accessible only after
  an authorized sign-in. The public teaser does not expose them.
- Featured programmes, searchable opportunities, pre-university courses, exam tracks,
  bookmarks, helpline and profile/avatar remain. Deadlines must be checked on official sites.
- Community members can submit an opportunity manually or by link; the owner reviews it.
  Link previews reject non-public addresses and pin each outbound connection to a checked IP,
  including redirects. A host firewall is still recommended.

## Project submissions and review

`/workspace` offers a guided four-step flow and a full-form alternative. Without JavaScript
all fields are available. Drafts remain private. The owner must explicitly review the entire
project and all uploaded files before approving publication. Every edit and every upload to
an approved project sends it back to review. Approval includes a version check so edits made
after a review screen was opened cannot accidentally be approved.

The marketplace uses generic project and community labels. Public text has conservative
redaction for contact patterns and known registered full names. Legacy messages are hidden
until reviewed. **Text scanning cannot reliably identify every name, every obfuscation, or
private details in files.** Admins must inspect the full text and every attachment, and
reject unsafe material.

## Accounts and moderation

Registration collects private name, email, phone and password; the account-type, career and
education fields are optional. The owner sees private records in `/admin`; other users see
pseudonymous project and message views. Email verification is real token-based; unconfigured
or broken delivery never silently verifies a user. The owner may grant access separately.
Existing accounts lacking evidence of genuine verification must verify or be granted access.

The admin dashboard reports total users, users active in the last seven days, unverified
emails, pending access, blocked accounts, project reviews and message flags. The owner can
manage users, block/unblock accounts, review suppressed messages and add blocked phrases.
Privacy/contact rules and harassment/threat checks remain enabled. Offending messages are
suppressed and the account is blocked with sessions revoked. These checks can miss details
or produce false positives, so review and an appeal through the helpline are important.

## Owner-directed project funding

The admin enters an HTTPS payment link belonging to the owner. Without it, funding is
unavailable. Support starts as pending; a browser return cannot mark it paid. The owner can
manually confirm a payment after inspecting their provider account and can record a separate
transfer already made outside the website. There is no automated collection, proof of
settlement, escrow, fee split, or disbursement. See `PAYMENTS.md`.

## Upgrade and persistence

The v19 slideshow migration seeds the former bundled photos once and retains owner removals
across normal restarts as long as the SQLite database persists. Uploaded photos are stored
in that database and are resized and stripped of metadata.

On first v18 startup, v17 public projects return to review, legacy messages are withheld,
legacy `paid_demo` entries become unverified, and unproven email verification is cleared.
The migration is one-time and preserves the underlying records. On an ephemeral Render
filesystem, a deployment can erase the database and files altogether; back up first and use
persistent storage. Verify `/version` after deployment.
