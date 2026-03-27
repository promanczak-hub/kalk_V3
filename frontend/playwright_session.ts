import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.locator('.p-4').first().click();
  await page.locator('.p-4').first().dblclick();
  await page.getByText('22.03.2026VOLKSWAGEN Passat').click();
  await page.getByRole('combobox').nth(3).selectOption('custom');
  await page.getByRole('textbox', { name: 'Wpisz własny rabat' }).dblclick();
  await page.getByRole('textbox', { name: 'Wpisz własny rabat' }).dblclick();
  await page.getByRole('textbox', { name: 'Wpisz własny rabat' }).fill('24');
  await page.getByRole('textbox', { name: 'Wpisz własny rabat' }).press('Enter');
  await page.getByRole('button', { name: 'Zrób kalkulację' }).click();
});