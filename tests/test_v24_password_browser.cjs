/* Real-browser checks for masked-by-default, keyboard-operable password controls.
   The companion runner starts a disposable local database; never run this on production. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const root = process.env.SCHOLAR_BROWSER_TEST_URL;
if (!root || !['127.0.0.1', 'localhost', '[::1]'].includes(new URL(root).hostname)) {
  throw new Error('This browser test only permits a disposable local server.');
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const ctx = await browser.newContext({ viewport: { width: 320, height: 760 } });
    await ctx.route('**/*', route => route.request().url().startsWith(root + '/') ? route.continue() : route.abort());
    const page = await ctx.newPage();
    const errors = [];
    const posts = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('request', req => { if (req.method() === 'POST') posts.push(req.url()); });

    async function toggle(id, label, autocomplete) {
      const input = page.locator('#' + id);
      const button = page.locator('button[aria-controls="' + id + '"]');
      assert.equal(await input.getAttribute('type'), 'password');
      assert.equal(await input.getAttribute('autocomplete'), autocomplete);
      assert.equal(await button.getAttribute('type'), 'button');
      assert.equal(await button.getAttribute('aria-label'), 'Show ' + label);
      assert.equal(await button.isVisible(), true);
      await input.fill('BrowserTest123!');
      await input.focus();
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.getAttribute('aria-controls')), id);
      await page.keyboard.press('Space');
      assert.equal(await input.getAttribute('type'), 'text');
      assert.equal(await button.innerText(), 'Hide');
      assert.equal(await button.getAttribute('aria-label'), 'Hide ' + label);
      assert.equal(await page.evaluate(() => document.activeElement.id), id);
      await input.press('End');
      await page.keyboard.type('-more');
      assert.equal(await input.inputValue(), 'BrowserTest123!-more');
      await button.focus();
      await page.keyboard.press('Enter');
      assert.equal(await input.getAttribute('type'), 'password');
      assert.equal(await input.inputValue(), 'BrowserTest123!-more');
      assert.equal(await button.getAttribute('aria-label'), 'Show ' + label);
      const ib = await input.boundingBox(), bb = await button.boundingBox();
      assert.ok(ib && bb && bb.x >= ib.x && bb.x + bb.width <= ib.x + ib.width + 1,
        'toggle should fit inside the input, including on narrow screens');
    }

    await page.goto(root + '/signup');
    await toggle('signup-password', 'password', 'new-password');
    assert.equal(posts.length, 0, 'reveal button must not submit the form');
    const widths = await Promise.all(['input[name=name]', 'input[name=phone]', 'input[name=email]'].map(
      async selector => (await page.locator(selector).boundingBox()).width));
    assert.ok(Math.max(...widths) - Math.min(...widths) < 2, 'signup inputs should be consistently sized');
    if (process.env.SCHOLAR_BROWSER_SCREENSHOT) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: process.env.SCHOLAR_BROWSER_SCREENSHOT, fullPage: true });
    }
    await page.goto(root + '/login');
    await toggle('login-password', 'password', 'current-password');
    assert.equal(posts.length, 0);
    await page.locator('input[name=email]').fill('honoremukunzi6@gmail.com');
    await page.locator('#login-password').fill('TestOwnerPassword123!');
    await page.locator('form[action="/login"] button[type=submit]').click();
    await page.waitForURL('**/dashboard');
    assert.equal(posts.length, 1, 'only the intentional local login should submit');

    await page.goto(root + '/account');
    const current = page.locator('#account-current-password');
    const next = page.locator('#account-new-password');
    await current.fill('current-secret'); await next.fill('new-secret-value');
    await page.locator('button[aria-controls="account-current-password"]').click();
    assert.equal(await current.getAttribute('type'), 'text');
    assert.equal(await next.getAttribute('type'), 'password');
    await page.locator('button[aria-controls="account-new-password"]').click();
    assert.equal(await next.getAttribute('type'), 'text');
    await page.locator('button[aria-controls="account-current-password"]').click();
    assert.equal(await current.getAttribute('type'), 'password');
    assert.equal(await next.getAttribute('type'), 'text');
    assert.equal(await current.inputValue(), 'current-secret');
    assert.equal(await next.inputValue(), 'new-secret-value');
    assert.equal(posts.length, 1, 'toggling account fields must not submit or send');
    assert.equal(await current.getAttribute('autocomplete'), 'current-password');
    assert.equal(await next.getAttribute('autocomplete'), 'new-password');

    await page.goto(root + '/reset-password?token=test-token');
    await toggle('reset-password', 'new password', 'new-password');
    assert.equal(posts.length, 1);
    assert.deepEqual(errors, []);
    await ctx.close();

    const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 800 } });
    await noJs.route('**/*', route => route.request().url().startsWith(root + '/') ? route.continue() : route.abort());
    const p = await noJs.newPage();
    await p.goto(root + '/signup');
    assert.equal(await p.locator('#signup-password').getAttribute('type'), 'password');
    assert.equal(await p.locator('button[aria-controls="signup-password"]').isHidden(), true);
    await noJs.close();
    console.log('PASS: Chromium mobile signup, login, reset, account independence, keyboard, no-JS and no-extra-POST checks');
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err); process.exit(1); });
