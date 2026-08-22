/**
 * Take report tab screenshots
 */
import pkg from '/home/gouda/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js';
const { chromium } = pkg;
const BROWSER_EXEC = '/home/gouda/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

const OUT = '/home/gouda/iTourTT/website/screenshots';
const BASE = 'https://fulvago.itourtt.cloud';
const EMAIL = 'admin@itour.local';
const PASS  = 'Admin@123';

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: BROWSER_EXEC });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Login
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="text"], input[placeholder*="Email"], input[placeholder*="email"], input[name="identifier"]', EMAIL);
  await page.fill('input[type="password"]', PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 15000 });
  console.log('Logged in ✓');

  // Go to reports
  await page.goto(`${BASE}/dashboard/reports`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const tabs = [
    { value: 'drivers',       file: '09b-reports-drivers.png' },
    { value: 'driver-score',  file: '13-driver-score.png' },
    { value: 'rep-fees',      file: '09c-reports-rep-fees.png' },
    { value: 'rep-score',     file: '14-rep-score.png' },
    { value: 'evidence',      file: '09d-reports-evidence.png' },
    { value: 'supplier-jobs', file: '09e-reports-supplier-jobs.png' },
    { value: 'car-jobs',      file: '09f-reports-car-jobs.png' },
    { value: 'visa',          file: '09g-reports-visa.png' },
    { value: 'sales',         file: '09h-reports-sales.png' },
    { value: 'departure',     file: '09i-reports-departure.png' },
    { value: 'revenue',       file: '09j-reports-revenue.png' },
  ];

  for (const tab of tabs) {
    try {
      // Click tab by value attribute
      await page.locator(`[value="${tab.value}"]`).first().click();
      await page.waitForTimeout(1200);
      await page.screenshot({ path: `${OUT}/${tab.file}`, fullPage: false });
      console.log(`  ✓ ${tab.file}`);
    } catch (e) {
      console.log(`  ⚠ ${tab.value}: ${e.message.split('\n')[0]}`);
    }
  }

  // Driver Portal history
  await page.goto(`${BASE}/driver/history`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/23b-driver-portal-history.png` });
  console.log('  ✓ 23b-driver-portal-history.png');

  // Rep Portal history
  await page.goto(`${BASE}/rep/history`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/24b-rep-portal-history.png` });
  console.log('  ✓ 24b-rep-portal-history.png');

  await browser.close();
  console.log('\n✅ Done');
})().catch(e => { console.error(e.message); process.exit(1); });
