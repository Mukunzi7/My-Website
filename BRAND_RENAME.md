# Brand decision: Learnwella

**The platform name is Learnwella.** This is the single source of truth for the brand.

## History

- The project started as **EduBridge** (v1–v11).
- Commit `0c111b6` renamed the app title to **Learnwella**, but that commit also accidentally
  deleted most of `server.py`. In v12 the app was restored and the rename completed across
  the entire repository.
- `README.md`, `pitch_deck.html`, `pitch_deck.md`, all setup guides, config files, page copy,
  emails, the update banner and the `/version` response now say **Learnwella**.

## Company and copyright

The product is owned by **Nexus Company Ltd**. Every page footer includes:

```text
© 2026 Nexus Company Ltd. All rights reserved.
```

## Logo

The header/footer logo is an inline SVG gradient mark (gold → rose) plus the wordmark
**Learn** (light) + **wella** (gold). It is generated in `brand_logo()` in `server.py`, so no
image file is needed. The pitch deck uses the same typography.

## Internal identifiers kept for compatibility

These are **not** user-visible and are deliberately unchanged so existing data keeps working:

| Identifier | Reason |
| --- | --- |
| `edubridge.sqlite3` | Default SQLite filename; renaming would orphan existing databases |
| `edubridge_session` | Session cookie name; renaming would log out every user |

Use `DB_PATH` to point at a differently named database file in production.

## Domain note

Check domain and trademark availability before buying a domain or launching publicly —
`learnwella.com`, `learnwella.rw`, `learnwella.app`, and similar names may already be taken.
See `DOMAIN_AND_GOOGLE_DEPLOYMENT.md`.
