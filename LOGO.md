# Your logo — how to change it

The 70Scholar logo is a real image file, not text baked into the code:

```text
static/images/logo.svg     <- the logo shown in the header and footer
static/favicon.svg         <- the small browser-tab icon
```

It is a scalable SVG (vector), so it stays sharp on every screen. The wordmark
**70Scholar** next to it is HTML text styled by `.logo-text` in `static/styles.css`.

## Show me how (three ways)

### Option A — replace the file with your own logo (easiest)

1. Prepare your logo as an SVG or PNG, roughly square, with a transparent background.
2. Save it as `static/images/logo.svg` (overwrite the existing file). If you use PNG,
   save it as `static/images/logo.png` instead and change one line in `server.py`:

   ```python
   # in brand_logo(), change /static/images/logo.svg to /static/images/logo.png
   ```

3. Optionally save a square version as `static/favicon.svg` for the browser tab.
4. Bump `APP_VERSION` in `server.py` (e.g. `v17-programs` → `v18-logo`) so browsers
   reload the new image instead of using the cached one.
5. Commit and push:

   ```bash
   git add static/images/logo.svg static/favicon.svg server.py
   git commit -m "Update logo"
   git push origin main
   ```

   Render auto-deploys from `main`. Check the header after the deploy finishes.

### Option B — just change the colours

Open `static/images/logo.svg` in any text editor. The gradient stops are:

```xml
<stop offset="0" stop-color="#F2A93E"/>   <!-- gold -->
<stop offset="1" stop-color="#E8768A"/>   <!-- rose -->
```

Replace those hex values with your own brand colours. The cap shape uses `#10152B`
(dark ink) — change it there too if you want a different mark colour.

### Option C — change the wordmark text or size

- Text: edit `brand_logo()` in `server.py` — the `<span class='logo-first'>70</span>`
  and `<span class='logo-last'>Scholar</span>` parts.
- Size: edit `static/styles.css`:

  ```css
  .logo      { font-size: clamp(1.9rem, 3.1vw, 2.75rem); }  /* wordmark size */
  .logo-img  { width: clamp(46px, 5vw, 68px); }              /* logo image size */
  .brand-display { font-size: clamp(3rem, 8vw, 7rem); }      /* big hero name */
  ```

## Asking an AI agent to do it

You can simply say: *"Replace the logo with the file I uploaded, make the wordmark blue,
and push it."* Upload your image into the workspace first, then tell the agent the filename.

## Notes

- Keep the file small (under ~100 KB) so the header loads instantly.
- SVG is preferred: it scales to any size and is tiny. If you use PNG, export at
  least 512×512 px so it looks sharp on high-density screens.
- `static/` is served directly by the app, so any file you put there is reachable at
  `/static/<filename>`.
