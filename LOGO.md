# 70Scholar logo and favicon

The owner supplied a Seven Scholars emblem and chose to keep the website name **70Scholar**.
The emblem is shown in the header, footer and opening homepage section; the prominent
homepage text wordmark was replaced by the emblem. The headline remains.

- `static/images/seven-scholars-mark.jpg` — square crop of the supplied image, displayed
  as a circle in the site. It retains the full emblem and its original lettering. The JPEG
  is re-encoded without the original metadata.
- `static/favicon.png` — a 192×192 round version used for the browser icon.
- `static/favicon.ico` — multi-size version also served publicly at `/favicon.ico`.
- `static/images/hero-school-group.jpg` — the supplied group photo shown as the background
  of the opening section. An overlay helps text remain readable; browsers crop it to fit.

`APP_VERSION` is included in the asset URLs to encourage browsers to load new files after
an update. If a browser retains an old favicon, reload the site or clear its cached icon.
The site's other branding and account/email identifiers remain 70Scholar.

To change the emblem later, prepare a square crop, update the JPEG and both favicon files,
update `APP_VERSION`, test the homepage on desktop and mobile, and deploy. Only use logos
and photographs you have permission to publish, including any required consent for children.
