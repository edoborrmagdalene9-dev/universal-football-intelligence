const { test, expect } = require('@playwright/test');

test('home page and key UFI workspace areas load', async ({ page }) => {
  const response = await page.goto('/');
  expect(response, 'the local app should return an HTTP response').toBeTruthy();
  expect(response.status()).toBe(200);
  await expect(page).toHaveTitle(/Universal Football Intelligence/i);
  await expect(page.getByRole('heading', { name: /Intelligence overview/i })).toBeVisible();

  for (const view of [
    'overview', 'data', 'matchlab', 'players', 'scenarios', 'exactscore',
    'liveengine', 'universalengine', 'bookieedge', 'slips', 'backtest',
    'library', 'settings'
  ]) {
    await expect(page.locator(`#view-${view}`), `expected existing view #view-${view}`).toHaveCount(1);
  }
});

test('every workspace navigation item opens its corresponding view', async ({ page }) => {
  await page.goto('/');
  const navItems = page.locator('#navigation .nav-item[data-view]');
  const count = await navItems.count();
  expect(count).toBeGreaterThanOrEqual(10);

  for (let i = 0; i < count; i++) {
    const item = navItems.nth(i);
    const view = await item.getAttribute('data-view');
    expect(view, 'navigation item must declare its target view').toBeTruthy();
    await item.click();
    await expect(item, `navigation item for ${view} should become active`).toHaveClass(/active/);
    await expect(page.locator(`#view-${view}`), `target view ${view} should become visible`).toBeVisible();
  }
});

test('real-data and exact-score workflows expose their core controls', async ({ page }) => {
  await page.goto('/');
  await page.locator('#navigation [data-view="data"]').click();
  await expect(page.locator('#loadCompetitions')).toBeVisible();
  await expect(page.locator('#competitionSelect')).toBeVisible();
  await expect(page.locator('#matchSelect')).toBeVisible();

  await page.locator('#navigation [data-view="exactscore"]').click();
  await expect(page.locator('#view-exactscore')).toBeVisible();
});
