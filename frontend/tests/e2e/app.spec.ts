import { test, expect } from '@playwright/test';

test.describe('App Routing & Loading', () => {
  test('should load the main page correctly', async ({ page }) => {
    await page.goto('/');
    
    // Check if the sticky header is visible
    await expect(page.locator('header')).toBeVisible();

    // Check if the main navigation tabs are visible
    await expect(page.getByRole('tablist')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Ekstrakcja i Analiza AI' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Historia Kalkulacji' })).toBeVisible();
  });
});
