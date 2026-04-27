import { test, expect } from '@playwright/test';

test.describe('CRUD Panels & Configuration', () => {
  test('should load Control Center page', async ({ page }) => {
    await page.goto('/control-center');
    
    // Ensure the header is visible
    await expect(page.locator('header')).toBeVisible();

    // Ensure URL is correct
    await expect(page).toHaveURL(/.*\/control-center/);

    // Check if the tab is active
    const tabEl = page.getByRole('tab', { name: 'Control Center (Admin)' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });

  test('should load Wyszukiwarka pojazdów page', async ({ page }) => {
    await page.goto('/search');
    
    // Ensure URL is correct
    await expect(page).toHaveURL(/.*\/search/);
    
    // Check if the tab is active
    const tabEl = page.getByRole('tab', { name: 'Wyszukiwarka / Scoring' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });
});
