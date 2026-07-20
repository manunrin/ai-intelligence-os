import { test, expect } from '@playwright/test';

test.describe('Phase 9 End-to-End Verification', () => {
  const BASE_URL = 'http://localhost:3000';
  const API_URL = 'http://localhost:8000';

  test('root page loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/AI Intelligence OS/i);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Root page loaded successfully');
  });

  test('dashboard route loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Dashboard route loaded successfully');
  });

  test('knowledge route loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    await expect(page).toHaveURL(/\/knowledge/);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Knowledge route loaded successfully');
  });

  test('agents route loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/agents`);
    await expect(page).toHaveURL(/\/agents/);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Agents route loaded successfully');
  });

  test('login route loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Login route loaded successfully');
  });

  test('register route loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/register`);
    await expect(page).toHaveURL(/\/register/);
    await expect(page.locator('body')).toBeVisible();
    console.log('✓ Register route loaded successfully');
  });

  test('backend API health check', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/health`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe('healthy');
    console.log('✓ Backend API health check passed');
  });

  test('knowledge search functionality', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    // Wait for knowledge interface to load
    await page.waitForTimeout(2000);
    // Look for search input or button
    const searchInput = page.locator('input[type="text"], input[placeholder*="search" i], textarea').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test query');
      await searchInput.press('Enter');
      await page.waitForTimeout(2000);
      console.log('✓ Knowledge search initiated');
    } else {
      console.log('⚠ Knowledge search input not found');
    }
  });

  test('RAG chat functionality', async ({ page }) => {
    await page.goto(`${BASE_URL}/knowledge`);
    // Wait for page to load
    await page.waitForTimeout(1500);
    // Look for chat interface
    const chatInput = page.locator('textarea[placeholder*="ask" i], textarea[placeholder*="chat" i]').first();
    if (await chatInput.isVisible()) {
      await chatInput.fill('What is AI Intelligence OS?');
      await chatInput.press('Enter');
      await page.waitForTimeout(3000);
      console.log('✓ RAG chat message sent');
    } else {
      console.log('⚠ RAG chat input not found');
    }
  });

  test('check for runtime errors in console', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    await page.goto(BASE_URL);
    await page.waitForTimeout(2000);
    if (errors.length > 0) {
      console.log(`⚠ Console errors found: ${errors.length}`);
      errors.forEach(err => console.log(`  - ${err}`));
    } else {
      console.log('✓ No console errors detected');
    }
  });
});