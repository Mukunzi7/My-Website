/* Optional real-browser test. This only connects to a disposable local instance. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const root = process.env.SCHOLAR_BROWSER_TEST_URL;
if (!root || !['127.0.0.1', 'localhost', '[::1]'].includes(new URL(root).hostname)) {
  throw new Error('Competition browser test only permits a disposable local server.');
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [320, 390, 1365]) {
      const ctx = await browser.newContext({ viewport: { width, height: 840 }, reducedMotion: 'reduce' });
      await ctx.route('**/*', r => r.request().url().startsWith(root + '/') ? r.continue() : r.abort());
      const page = await ctx.newPage(); const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(root + '/');
      const nav = page.locator('nav[aria-label="Primary navigation"]');
      assert.equal(await nav.getByRole('link', { name: 'Competitions', exact: true }).count(), 1);
      await nav.getByRole('link', { name: 'Competitions', exact: true }).click();
      await page.waitForURL('**/login?next=**');
      await page.locator('input[name=email]').fill('honoremukunzi6@gmail.com');
      await page.locator('#login-password').fill('TestOwnerPassword123!');
      await page.locator('form[action="/login"] button[type=submit]').click();
      await page.waitForURL('**/competitions');
      let cards = page.locator('.listing-card');
      assert.equal(await cards.filter({ hasText: 'International Physics Olympiad Test' }).count(), 1);
      assert.equal(await cards.filter({ hasText: 'Competition for Youth-Led Projects' }).count(), 1);
      assert.equal(await cards.filter({ hasText: 'GirlCode Pan-African Hackathon' }).count(), 1);
      assert.equal(await cards.filter({ hasText: 'University of Rwanda Mastercard' }).count(), 0);
      assert.equal(await page.locator('h1').innerText(), 'Competitions, olympiads and contests.');
      assert.equal(await nav.getByRole('link', { name: 'Competitions', exact: true }).getAttribute('class'), 'nav-link is-active');
      if (process.env.SCHOLAR_BROWSER_SCREENSHOT_DIR) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: process.env.SCHOLAR_BROWSER_SCREENSHOT_DIR + '/v25-competitions-' + width + '.png', fullPage: true });
      }
      const size = await page.evaluate(() => ({ window: innerWidth, content: document.documentElement.scrollWidth }));
      assert.ok(size.content <= size.window + 1, `horizontal overflow at ${width}: ${JSON.stringify(size)}`);
      await page.locator('form[action="/competitions"] input[name=q]').fill('PHYSICS');
      await page.locator('form[action="/competitions"] button[type=submit]').click();
      assert.equal(await cards.filter({ hasText: 'International Physics Olympiad Test' }).count(), 1);
      assert.equal(await cards.filter({ hasText: 'GirlCode Pan-African Hackathon' }).count(), 0);
      await cards.filter({ hasText: 'International Physics Olympiad Test' }).getByRole('button', { name: 'Save', exact: true }).click();
      await page.waitForURL('**/competitions');
      cards = page.locator('.listing-card');
      assert.equal(await cards.filter({ hasText: 'International Physics Olympiad Test' }).getByRole('button', { name: 'Saved ✓' }).count(), 1);
      await page.goto(root + '/dashboard');
      const competitionBox = page.locator('.dash-panel').filter({ has: page.getByRole('heading', { name: 'Saved competitions' }) });
      assert.equal(await competitionBox.getByText('International Physics Olympiad Test').count(), 1);
      await page.goto(root + '/opportunities');
      cards = page.locator('.listing-card');
      assert.equal(await cards.filter({ hasText: 'University of Rwanda Mastercard' }).count(), 1);
      assert.equal(await cards.filter({ hasText: 'International Physics Olympiad Test' }).count(), 0);
      await page.goto(root + '/opportunities?type=Competition&q=physics');
      assert.ok(page.url().includes('/competitions?'));
      const legacyCard = page.locator('.listing-card').filter({ hasText: 'International Physics Olympiad Test' });
      assert.equal(await legacyCard.count(), 1);
      // Reset this synthetic bookmark before testing the next viewport.
      await legacyCard.getByRole('button', { name: 'Saved ✓' }).click();
      await page.waitForURL('**/competitions');
      assert.deepEqual(errors, []);
      console.log('PASS browser width', width, ': navigation, gating, separation, search, saving and old link');
      await ctx.close();
    }
  } finally { await browser.close(); }
})().catch(err => { console.error(err); process.exit(1); });
