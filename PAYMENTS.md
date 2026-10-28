# Owner-directed funding

The admin-controlled funding workflow deliberately does not pretend to be a payment gateway.

1. The owner signs in as `honoremukunzi6@gmail.com` and opens **Admin → Funding → Owner
   payment link**.
2. Enter an HTTPS payment/checkout link for an account controlled by the owner, then save.
   70Scholar cannot verify who owns the link. Leave it blank to disable new funding.
3. A signed-in supporter selects an approved project and an amount. 70Scholar creates a
   **pending** request and a `70S-...` reference. The supporter can open the external link,
   enter the amount and reference if the provider supports them, and complete any payment
   with the provider.
4. A link visit, browser return, and `/payment/success` do **not** verify a payment or change
   its status. The owner checks the actual provider records, matches the reference and amount,
   and only then manually confirms the request in Admin. Only manually confirmed amounts
   appear in public funding totals. The admin action is not independent provider verification.
5. The owner separately decides how to support a founder. If money has already been sent
   outside the website, the owner can enter the project, amount and external reference under
   **Record an external disbursement**. This records an action; it does not send money.

Public project pages and messages do not display creators' personal or Mobile Money details.
Previous demo-paid records are treated as unverified after the v18 migration. No automatic
5% fee, split, escrow, settlement or transfer is implemented. If a real automated payment
flow is needed, use a provider's authenticated webhook, signatures, idempotency and audit
records; get legal and financial advice before launch.
