# Public Supabase CA

`supabase-root-2021.crt` is Supabase's **public CA certificate**, not a secret or a
private key. It was retrieved from the provider's published certificate URL:
<https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt>.
Compare it with the CA downloaded from the project's Supabase Database Settings.

- Subject: Supabase Root 2021 CA
- SHA-256 DER fingerprint: `80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA`
- Valid until 26 April 2031

The app uses it by default **only** for `*.pooler.supabase.com` hosts with PostgreSQL
`sslmode=verify-full` (chain AND hostname verification). The provider can rotate this
CA. Replace it from the provider and update the fingerprint test when needed, or set
`SUPABASE_DB_CA_PEM` / `PG_SSL_ROOT_CERT` privately. Never disable server verification.
