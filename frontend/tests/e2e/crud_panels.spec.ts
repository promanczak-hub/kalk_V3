import { test, expect } from '@playwright/test';

test.describe('CRUD Panels & Configuration', () => {
  test('should load Dane zalezne - kalkulator page', async ({ page }) => {
    await page.goto('/dane-zalezne');
    
    // Ensure the header is visible
    await expect(page.locator('header')).toBeVisible();

    // Ensure URL is correct
    await expect(page).toHaveURL(/.*\/dane-zalezne/);

    // Check if the tab is active
    const tabEl = page.getByRole('tab', { name: 'Dane zależne - kalkulator' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });

  test('should load Wyszukiwarka pojazdów page', async ({ page }) => {
    await page.goto('/search');
    
    // Ensure URL is correct
    await expect(page).toHaveURL(/.*\/search/);
    
    // Check if the tab is active
    const tabEl = page.getByRole('tab', { name: 'Wyszukiwarka pojazdów' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });
});
