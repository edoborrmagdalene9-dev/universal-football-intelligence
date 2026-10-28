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
test('live fixture feed connects to the model pipeline without manual ID copying', async ({ page }) => {
  await page.route('https://universal-football-intelligence.onrender.com/api/health', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) })
  );
  await page.route('**/api/fixtures*', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        source: 'Mock Sportmonks',
        data: { data: [{ id: 12345, name: 'Alpha FC vs Beta FC', starting_at: '2026-10-28 19:00:00' }] }
      })
    })
  );
  await page.route('**/api/fixture?id=12345', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true, source: 'Mock Sportmonks',
        data: { data: { id: 12345, name: 'Alpha FC vs Beta FC', participants: [] } }
      })
    })
  );
  await page.route('**/api/pipeline/predict*', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        pipeline_status: 'model_ready_market_wait',
        fixture_source: { provider: 'Mock Sportmonks', fixture_id: '12345', home: 'Alpha FC', away: 'Beta FC' },
        stages: { fixture_ingestion: 'PASS', historical_poisson_dixon_coles: 'model_output', player_and_tactical_feature_join: 'WAIT', exact_score_market_validation: 'WAIT', final_market_decision: 'WAIT' },
        match_context: {},
        historical_model: { status: 'model_output', models: { independent_poisson: { top_scores: [{ home: 1, away: 0, p: 0.2, fair_odds: 5 }] } } },
        market_gate: 'WAIT', gate_reasons: [], warning: 'Experimental model output.'
      })
    })
  );

  await page.goto('/');
  await page.locator('#navigation [data-view="liveengine"]').click();
  await expect(page.locator('#esiApiBase')).toHaveValue('https://universal-football-intelligence.onrender.com');
  await expect(page.locator('#ufiEndToEndPipelinePanel')).toBeVisible();

  await page.locator('#esiConnectFeed').click();
  await expect(page.locator('#esiFeedStatus')).toContainText('Loaded 1 source fixture');
  await page.locator('[data-fixture-id="12345"]').click();
  await expect(page.locator('#esiProviderFixtureId')).toHaveValue('12345');

  await page.locator('#esiLoadFixtureDetails').click();
  await expect(page.locator('#esiFixtureDetailsOutput')).toContainText('Alpha FC vs Beta FC');

  await page.locator('#ufiRunEndToEndPipeline').click();
  await expect(page.locator('#ufiPipelineOutput')).toContainText('model_ready_market_wait');
  await expect(page.locator('#ufiPipelineOutput')).toContainText('1-0');
  await expect(page.locator('#ufiPipelineOutput')).toContainText('WAIT');
  await page.locator('#esiStopFeed').click();
});
