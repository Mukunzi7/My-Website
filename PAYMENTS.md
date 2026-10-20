# EduBridge Direct Mobile Money Funding

EduBridge has been changed so money does **not** go to the platform owner's Mobile Money account.

Each project creator must add their own Mobile Money details before publishing a project for funding:

- Mobile Money account name
- Mobile Money number
- Network, for example MTN Mobile Money or Airtel Money
- Optional payment instructions

When a sponsor funds a project, EduBridge records the pledge and shows the creator's payment details. The sponsor sends money directly to the project creator.

## Why this is better

- EduBridge does not hold student money.
- Sponsors support the project owner directly.
- Each student/founder receives support into their own account.
- The platform can still keep a record of pledges and support activity.

## Current MVP flow

1. Creator creates a project in `/workspace`.
2. Creator adds their Mobile Money details.
3. Creator publishes the project.
4. Sponsor opens the project page.
5. Sponsor enters pledge amount and chooses Mobile Money support.
6. EduBridge shows the creator's Mobile Money details and a reference.
7. Sponsor sends money directly to the creator.

## Future production upgrade

Later, you can add a more advanced escrow or verified payment system:

- Flutterwave Mobile Money collection per creator
- Stripe Connect where supported
- PayPal Commerce Platform
- Automatic payment verification webhooks
- Receipts for sponsors
- Payout dashboards for project creators

For now, the safest simple system is direct creator Mobile Money details plus pledge records.
