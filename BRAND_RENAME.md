# Brand decision: 70Scholar

**The platform name is 70Scholar.** This is the single source of truth for the brand.

## History

| Version | Name |
| --- | --- |
| v1–v11 | EduBridge |
| v12 | Learnwella |
| v13 onward | **70Scholar** |

The v13 rename changed every user-visible string: `APP_NAME`, the SVG wordmark
(**70** light + **Scholar** gold), page titles and meta descriptions, the update banner,
`/version`, all verification and password-reset emails, the notice pages, the pitch deck,
and every document and config file in this repository.

## Company and copyright

The product is owned by **Nexus Company Ltd**. Every page footer includes:

```text
© 2026 Nexus Company Ltd. All rights reserved.
```

## Logo

The owner-supplied Seven Scholars emblem is used in the header, footer, homepage and
favicon; the site's name remains **70Scholar** by the owner's choice. `brand_logo()` in
`server.py` pairs the emblem with the `70` + `Scholar` text. See `LOGO.md` for asset paths.
`pitch_deck.html` remains a historical deck and may use earlier styling.

## Identifiers deliberately NOT renamed

These are invisible infrastructure labels, not branding. Renaming them breaks things.

| Identifier | Why it stays |
| --- | --- |
| `edubridge.sqlite3` | Default SQLite filename; renaming would orphan existing databases |
| `edubridge_session` | Session cookie name; renaming would log out every user |
| `70scholar` in `render.yaml` | Render **service** name, renamed in v13. Your free URL is `https://seven0scholar-7cjc.onrender.com`. Changing it again requires a fresh Blueprint. |
| `Mukunzi7/My-Website` | GitHub repo name; renaming it would break the deploy button and clone URLs |

Use `DB_PATH` to choose a new database filename. The Render service name already
matches the brand; a custom domain is still recommended for a professional URL. See `DOMAIN_AND_GOOGLE_DEPLOYMENT.md`.

## Domain note

Check availability and trademarks before buying — `70scholar.com`, `70scholar.rw`,
`70scholar.app`, `70scholar.africa`, and similar names may already be taken.
