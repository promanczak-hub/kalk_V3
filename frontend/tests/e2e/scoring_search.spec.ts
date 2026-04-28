import { test, expect } from '@playwright/test';

test.describe('Scoring Search', () => {
  test('should load Wyszukiwarka pojazdów page', async ({ page }) => {
    await page.goto('/search');

    await expect(page).toHaveURL(/.*\/search/);

    const tabEl = page.getByRole('tab', { name: 'Wyszukiwarka / Scoring' });
    await expect(tabEl).toHaveAttribute('aria-selected', 'true');
  });
});
