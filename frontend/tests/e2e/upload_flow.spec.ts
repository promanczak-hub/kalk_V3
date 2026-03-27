import { test, expect } from '@playwright/test';

test.describe('Upload Flow & Cancel', () => {
  test('should allow user to upload and immediately cancel', async ({ page }) => {
    test.setTimeout(30000);
    await page.goto('/');

    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.locator('label[for="file-upload"]').click();
    
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: 'dummy_cancel_test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('dummy content')
    });

    // Oczekujemy, że element DocumentCard się pojawi z naszą nazwą pliku
    const cardTitle = page.getByText('dummy_cancel_test.pdf');
    await expect(cardTitle).toBeVisible();

    // Szybko próbujemy kliknąć X, aby anulować (zakładając że backend nie odpowie w 1ms)
    const cancelButton = page.locator('button[title="Zatrzymaj wgrywanie"], button[title="Przerwij analizę"]');
    
    // Upewniamy się, że przycisk się pojawi i go klikamy
    await expect(cancelButton).toBeVisible();
    await cancelButton.click();

    // Po anulowaniu, DocumentCard powinien zniknąć
    await expect(cardTitle).not.toBeVisible();
  });
});
