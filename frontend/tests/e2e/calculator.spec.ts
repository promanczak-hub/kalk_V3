import { test, expect } from '@playwright/test';

test.describe('Calculator & Pipeline', () => {
  test('should load Manualne Kalkulacje page', async ({ page }) => {
    test.setTimeout(600000); // 10 minutes max just in case
    
    // Go to the manual calculator page directly
    await page.goto('/kalkulacje');
    
    // Ensure the page content has loaded (header or main container)
    // The main container padding top switches from 80px to 112px on error, we just check visibility
    await expect(page.locator('header')).toBeVisible();

    // Typically there's a title or elements related to calculations, we just assert the URL is correct
    await expect(page).toHaveURL(/.*\/kalkulacje/);

    // Let's verify the tab "Kalkulacje Manualne" is selected
    const tabEl = page.getByRole('tab', { name: 'Kalkulacje Manualne' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });
});
