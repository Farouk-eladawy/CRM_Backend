/**
 * Take report tab screenshots — scrolls tab list and clicks by text
 */
import pkg from '/home/gouda/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js';
const { chromium } = pkg;
const BROWSER_EXEC = '/home/gouda/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

const OUT = '/home/gouda/iTourTT/website/screenshots';
const BASE = 'https://fulvago.itourtt.cloud';
const EMAIL = 'admin@itour.local';
const PASS  = 'Admin@123';

async function clickTab(page, text, file) {
  try {
    // Scroll tabs list into view and click by text
    const tab = page.locator(`[role="tab"]`).filter({ hasText: text });
    await tab.scrollIntoViewIfNeeded({ timeout: 5000 });
    await tab.click({ timeout: 10000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/${file}`, fullPage: false });
    console.log(`  ✓ ${file} (${text})`);
    return true;
  } catch (e) {
    console.log(`  ⚠ "${text}": ${e.message.split('\n')[0].substring(0,80)}`);
    return false;
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: BROWSER_EXEC });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Login
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="text"], input[name="identifier"]', EMAIL);
  await page.fill('input[type="password"]', PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 15000 });
  console.log('Logged in ✓');

  // Go to reports
  await page.goto(`${BASE}/dashboard/reports`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // List all tabs found
  const allTabs = await page.locator('[role="tab"]').allTextContents();
  console.log('Tabs found:', allTabs);

  await clickTab(page, 'Driver Trips', '09b-reports-drivers.png');
  await clickTab(page, 'Driver Score', '13-driver-score.png');
  await clickTab(page, 'Rep Fees', '09c-reports-rep-fees.png');
  await clickTab(page, 'Rep Score', '14-rep-score.png');
  await clickTab(page, 'Evidence', '09d-reports-evidence.png');
  await clickTab(page, 'Supplier Jobs', '09e-reports-supplier-jobs.png');
  await clickTab(page, 'Car Jobs', '09f-reports-car-jobs.png');
  await clickTab(page, 'Visa', '09g-reports-visa.png');
  await clickTab(page, 'Sales', '09h-reports-sales.png');
  await clickTab(page, 'Departure', '09i-reports-departure.png');
  await clickTab(page, 'Revenue', '09j-reports-revenue.png');
  await clickTab(page, 'Agent', '09k-reports-agent.png');

  await browser.close();
  console.log('\n✅ Done');
})().catch(e => { console.error(e.message); process.exit(1); });
