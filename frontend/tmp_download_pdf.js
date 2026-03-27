import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  
  await page.goto('http://localhost:5173/');
  
  // Wait for React to load the rows
  await page.waitForTimeout(5000);
  
  // Try to find the chevron button by class or just find "Draft Broszury" directly if it's visible
  try {
    const draftButton = page.locator('text=Draft Broszury').first();
    const isVisible = await draftButton.isVisible();
    
    if (!isVisible) {
      // Need to expand a row. Find the first button containing the chevron svg or just guess the row
      const rows = page.locator('[role="row"]');
      if (await rows.count() > 0) {
        await rows.nth(1).click(); // Click somewhere on the row to expand it? Or the button.
      }
      // Wait for expansion animation
      await page.waitForTimeout(2000);
    }
  } catch(e) {}

  // Force click "Draft Broszury"
  try {
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const draftBtn = btns.find(b => b.textContent && b.textContent.includes('Draft Broszury'));
      if(draftBtn) draftBtn.click();
    });
  } catch(e) {}

  await page.waitForTimeout(2000);
  
  // Now click "Pobierz PDF"
  try {
    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const downloadBtn = btns.find(b => b.textContent && b.textContent.includes('Pobierz PDF'));
      if(downloadBtn) downloadBtn.click();
    });
    
    const download = await downloadPromise;
    const path = 'd:\\kalk_v3\\GOTOWA_BROSZURA_DO_TESTU.pdf';
    await download.saveAs(path);
    console.log('SUCCESS');
  } catch(e) {
    console.log('FAIL:', e.message);
  }

  await browser.close();
  process.exit(0);
})();
