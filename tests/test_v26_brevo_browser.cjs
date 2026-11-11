/* Browser checks use ONLY a disposable local app with fake captured mail. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');
const root = process.env.SCHOLAR_BROWSER_TEST_URL;
const capture = process.env.SCHOLAR_BROWSER_TEST_MAIL;
if (!root || !['127.0.0.1', 'localhost', '[::1]'].includes(new URL(root).hostname) || !capture) {
  throw new Error('Only a disposable local test server and synthetic mail are permitted.');
}
function readMail(email) {
  const mail = JSON.parse(fs.readFileSync(capture, 'utf8'));
  assert.equal(mail.to, email);
  const code = mail.body.match(/(?:[A-F0-9]{4}-){7}[A-F0-9]{4}/)?.[0];
  assert.ok(code, 'a grouped code must be present in the synthetic message');
  assert.ok(!mail.html.includes('?token='));
  return code;
}
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [320, 390, 1280]) {
      const ctx = await browser.newContext({ viewport: { width, height: 820 }, reducedMotion: 'reduce' });
      await ctx.route('**/*', r => r.request().url().startsWith(root + '/') ? r.continue() : r.abort());
      const page = await ctx.newPage(); const errors = [];
      page.on('pageerror', err => errors.push(err.message));
      const email = `browser-${width}@example.test`;
      async function noOverflow() {
        const size = await page.evaluate(() => ({ window: innerWidth, content: document.documentElement.scrollWidth }));
        assert.ok(size.content <= size.window + 1, `horizontal overflow at ${width}: ${JSON.stringify(size)}`);
      }
      await page.goto(root + '/signup');
      assert.equal(await page.getByText('Brevo delivers account emails and may track email opens and clicks.', { exact: false }).count(), 1);
      await page.locator('input[name=name]').fill('Browser Student');
      await page.locator('input[name=email]').fill(email);
      await page.locator('#signup-password').fill('BrowserInitial123!');
      assert.equal(await page.locator('#signup-password').getAttribute('type'), 'password');
      await page.locator('button[aria-controls="signup-password"]').click();
      assert.equal(await page.locator('#signup-password').getAttribute('type'), 'text');
      await page.locator('button[aria-controls="signup-password"]').click();
      await page.locator('form[action="/signup"] button[type=submit]').click();
      await page.waitForLoadState('load');
      assert.equal(await page.getByRole('heading', { name: 'Check your email' }).count(), 1);
      const verification = readMail(email);
      await page.goto(root + '/verify-email');
      await noOverflow();
      assert.equal(await page.getByLabel('Verification code').getAttribute('autocomplete'), 'one-time-code');
      await page.getByLabel('Verification code').fill(verification.toLowerCase());
      await page.getByRole('button', { name: 'Verify email' }).click();
      await page.waitForLoadState('load');
      assert.equal(await page.getByRole('heading', { name: 'Email verified' }).count(), 1);
      assert.ok(!page.url().includes(verification));
      await page.goto(root + '/login');
      await page.locator('input[name=email]').fill(email);
      await page.locator('#login-password').fill('BrowserInitial123!');
      await page.locator('form[action="/login"] button[type=submit]').click();
      await page.waitForURL('**/dashboard');
      await page.goto(root + '/forgot-password');
      await page.locator('input[name=email]').fill(email);
      await page.getByRole('button', { name: 'Send reset code' }).click();
      await page.waitForLoadState('load');
      const reset = readMail(email);
      await page.goto(root + '/reset-password');
      await noOverflow();
      assert.equal(await page.getByLabel('Reset code').getAttribute('autocomplete'), 'one-time-code');
      await page.getByLabel('Reset code').fill(reset);
      await page.locator('#reset-password').fill('BrowserUpdated123!');
      await page.getByRole('button', { name: 'Reset password', exact: true }).click();
      await page.waitForLoadState('load');
      assert.equal(await page.getByRole('heading', { name: 'Password reset' }).count(), 1);
      assert.ok(!page.url().includes(reset));
      await page.goto(root + '/login');
      await page.locator('input[name=email]').fill(email);
      await page.locator('#login-password').fill('BrowserUpdated123!');
      await page.locator('form[action="/login"] button[type=submit]').click();
      await page.waitForURL('**/dashboard');
      assert.deepEqual(errors, []);
      console.log('PASS width', width, ': synthetic signup, verification code, reset code and login');
      await ctx.close();
    }
  } finally { await browser.close(); }
})().catch(err => { console.error(err); process.exit(1); });
