import { chromium } from 'playwright';

(async () => {
  console.log("Launching browser...");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    console.log("Navigating to http://localhost:5173...");
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    
    console.log("Waiting for 'Otwórz dokument' button...");
    await page.waitForSelector('text=Otwórz dokument', { timeout: 15000 });
    
    console.log("Clicking the first 'Otwórz dokument' button...");
    await page.click('text=Otwórz dokument');
    
    console.log("Waiting for iframe to appear...");
    await page.waitForSelector('iframe', { timeout: 10000 });
    
    const iframeSrc = await page.getAttribute('iframe', 'src');
    console.log('Iframe src:', iframeSrc);
    
    if (iframeSrc && iframeSrc.startsWith('blob:')) {
      console.log('✅ SUCCESS: Blob URL generated and injected into iframe');
    } else {
      console.error('❌ FAILURE: Blob URL not found');
      process.exit(1);
    }

    console.log("Taking screenshot...");
    await page.screenshot({ path: 'pdf_viewer_test.png' });
    console.log("Screenshot saved to pdf_viewer_test.png");
    
  } catch (err) {
    console.error("Test failed:", err);
    await page.screenshot({ path: 'pdf_viewer_error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
