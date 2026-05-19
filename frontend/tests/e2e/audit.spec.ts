import { test, Page, ConsoleMessage, Request, Response } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

type Finding = {
  route: string;
  phase: string;
  kind: 'console.error' | 'pageerror' | 'unhandledrejection' | 'http_error' | 'http_failed' | 'timeout' | 'visual';
  detail: string;
  url?: string;
  status?: number;
};

const findings: Finding[] = [];
let currentRoute = '/';
let currentPhase = 'init';

function attachListeners(page: Page) {
  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter out known noise: React DevTools, vite HMR
      if (/Download the React DevTools|\[vite\]|HMR/i.test(text)) return;
      findings.push({
        route: currentRoute,
        phase: currentPhase,
        kind: 'console.error',
        detail: text.slice(0, 500),
      });
    }
  });

  page.on('pageerror', (err: Error) => {
    findings.push({
      route: currentRoute,
      phase: currentPhase,
      kind: 'pageerror',
      detail: `${err.name}: ${err.message}`.slice(0, 500),
    });
  });

  page.on('requestfailed', (req: Request) => {
    const url = req.url();
    if (/\.hot-update\.|\/@vite|\/@react-refresh/.test(url)) return;
    findings.push({
      route: currentRoute,
      phase: currentPhase,
      kind: 'http_failed',
      detail: req.failure()?.errorText ?? 'unknown',
      url,
    });
  });

  page.on('response', (res: Response) => {
    const status = res.status();
    if (status >= 400) {
      const url = res.url();
      // Ignore favicon and source map noise
      if (/favicon|\.map$/.test(url)) return;
      findings.push({
        route: currentRoute,
        phase: currentPhase,
        kind: 'http_error',
        detail: res.statusText() || `HTTP ${status}`,
        url,
        status,
      });
    }
  });
}

const ROUTES = [
  { path: '/', name: 'Ekstrakcja i Analiza AI' },
  { path: '/calculations', name: 'Historia Kalkulacji' },
  { path: '/search', name: 'Wyszukiwarka / Scoring' },
  { path: '/control-center', name: 'Control Center (Admin)' },
];

test.describe('Stability Audit', () => {
  test.setTimeout(180_000);

  test('walk every route and probe for errors', async ({ page }) => {
    attachListeners(page);

    // 1. Visit each route, wait for network idle, scroll
    for (const r of ROUTES) {
      currentRoute = r.path;
      currentPhase = 'navigate';
      try {
        await page.goto(r.path, { waitUntil: 'networkidle', timeout: 30_000 });
      } catch (e) {
        findings.push({
          route: r.path,
          phase: 'navigate',
          kind: 'timeout',
          detail: `goto failed: ${(e as Error).message}`.slice(0, 300),
        });
        continue;
      }

      currentPhase = 'idle';
      await page.waitForTimeout(1500);

      // Scroll the page to trigger lazy loading
      currentPhase = 'scroll';
      await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' as ScrollBehavior }));
      await page.waitForTimeout(500);
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }));
    }

    // 2. Stress test: rapid tab switching (12 swaps)
    currentRoute = 'rapid-tab-switch';
    currentPhase = 'stress';
    for (let i = 0; i < 12; i++) {
      const target = ROUTES[i % ROUTES.length];
      await page.goto(target.path, { waitUntil: 'commit', timeout: 10_000 }).catch(() => {});
      await page.waitForTimeout(120);
    }
    await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});

    // 3. Control Center: try to open every visible button/tab inside it
    currentRoute = '/control-center';
    currentPhase = 'control-center-explore';
    await page.goto('/control-center', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Enumerate all buttons / tabs that look navigational and click first 12 (skip destructive)
    const ccButtons = await page.locator('button, [role="tab"]').all();
    let clicked = 0;
    for (const btn of ccButtons) {
      if (clicked >= 12) break;
      try {
        const text = ((await btn.textContent()) ?? '').trim();
        const aria = ((await btn.getAttribute('aria-label')) ?? '').trim();
        const label = (text || aria).slice(0, 60);
        if (!label) continue;
        // Skip destructive / submit / dialog-closing labels
        if (/usuń|delete|wyloguj|logout|zapisz|save|submit|wyślij|publish|prześlij|x$/i.test(label)) continue;
        if (!(await btn.isVisible())) continue;
        currentPhase = `cc-click:${label}`;
        await btn.click({ timeout: 2000, trial: false }).catch(() => {});
        await page.waitForTimeout(400);
        clicked++;
      } catch {
        // ignore individual failures
      }
    }

    // 4. Extraction page: try invalid file upload (empty file)
    currentRoute = '/';
    currentPhase = 'invalid-upload';
    await page.goto('/', { waitUntil: 'networkidle' });
    try {
      const fileChooserPromise = page.waitForEvent('filechooser', { timeout: 5_000 });
      const uploadBtn = page.getByLabel('prześlij dokumenty');
      if (await uploadBtn.isVisible()) {
        await uploadBtn.click();
        const fc = await fileChooserPromise;
        await fc.setFiles({
          name: 'empty.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from(''),
        });
        await page.waitForTimeout(2500);
      }
    } catch {
      // upload control may not be discoverable
    }

    // 5. Calculations history: try interacting with grid (sort/filter)
    currentRoute = '/calculations';
    currentPhase = 'calc-grid-probe';
    await page.goto('/calculations', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    // Click first column header if any
    const headers = page.locator('[role="columnheader"]');
    const hcount = await headers.count();
    if (hcount > 0) {
      await headers.first().click({ timeout: 2000 }).catch(() => {});
      await page.waitForTimeout(500);
    }

    // 6. Search page: type junk into any visible search input
    currentRoute = '/search';
    currentPhase = 'search-junk-input';
    await page.goto('/search', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const inputs = page.locator('input[type="text"], input[type="search"], input:not([type])');
    const icount = await inputs.count();
    if (icount > 0) {
      const first = inputs.first();
      if (await first.isVisible()) {
        await first.fill('!!!@@@<script>alert(1)</script>;DROP TABLE--').catch(() => {});
        await page.waitForTimeout(800);
        await first.fill('').catch(() => {});
      }
    }

    // 7. Bogus route -> should redirect to /
    currentRoute = '/bogus-route-xyz';
    currentPhase = 'bogus-route';
    await page.goto('/this/does/not/exist-' + Date.now(), { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);

    // Final settle
    await page.waitForTimeout(1000);

    // Write report
    const reportDir = path.join(process.cwd(), 'audit-output');
    fs.mkdirSync(reportDir, { recursive: true });
    fs.writeFileSync(
      path.join(reportDir, 'findings.json'),
      JSON.stringify(findings, null, 2),
      'utf-8'
    );

    // Findings are written to disk for the full audit. We still fail the
    // test on the hard-failure kinds (page crashes, server errors, network
    // failures, navigation timeouts) so CI catches real regressions.
    // Soft-noise kinds (console.error from third-party libs) are tolerated.
    const FATAL_KINDS = new Set(['pageerror', 'http_failed', 'timeout']);
    const fatal = findings.filter(f => FATAL_KINDS.has(f.kind));
    const httpServerErrors = findings.filter(
      f => f.kind === 'http_error' && typeof f.status === 'number' && f.status >= 500,
    );
    if (fatal.length || httpServerErrors.length) {
      const summary = [...fatal, ...httpServerErrors]
        .map(f => `[${f.kind}] ${f.route}/${f.phase}: ${f.detail}`)
        .join('\n');
      throw new Error(`Stability audit found ${fatal.length + httpServerErrors.length} fatal issues:\n${summary}`);
    }
  });
});
