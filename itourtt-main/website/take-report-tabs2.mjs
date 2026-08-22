/**
 * Take report tab screenshots — uses JS click + scroll wrapper
 */
import pkg from '/home/gouda/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js';
const { chromium } = pkg;
const BROWSER_EXEC = '/home/gouda/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

const OUT = '/home/gouda/iTourTT/website/screenshots';
const BASE = 'https://fulvago.itourtt.cloud';
const EMAIL = 'admin@itour.local';
const PASS  = 'Admin@123';

async function clickTabByText(page, text, file) {
  try {
    // Use JS evaluate to find and click tab by text
    await page.evaluate((txt) => {
      const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
      const tab = tabs.find(t => t.textContent.trim().includes(txt));
      if (!tab) throw new Error(`Tab "${txt}" not found in DOM`);
      tab.scrollIntoView({ block: 'nearest', inline: 'center' });
      tab.click();
    }, text);
    await page.waitForTimeout(1800);
    await page.screenshot({ path: `${OUT}/${file}`, fullPage: false });
    console.log(`  ✓ ${file}`);
  } catch (e) {
    console.log(`  ⚠ "${text}": ${e.message.split('\n')[0].substring(0,100)}`);
    // Still take a screenshot to see what's on screen
    await page.screenshot({ path: `${OUT}/debug-${file}`, fullPage: false });
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
  await page.goto(`${BASE}/dashboard/reports`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);

  // Take screenshot of default (Daily Dispatch) tab first
  await page.screenshot({ path: `${OUT}/09-reports.png`, fullPage: false });
  console.log('  ✓ 09-reports.png (Daily Dispatch)');

  await clickTabByText(page, 'Driver Trips',   '09b-reports-drivers.png');
  await clickTabByText(page, 'Driver Score',   '13-driver-score.png');
  await clickTabByText(page, 'Agent Statement','09k-reports-agent.png');
  await clickTabByText(page, 'Rep Fees',       '09c-reports-rep-fees.png');
  await clickTabByText(page, 'Rep Score',      '14-rep-score.png');
  await clickTabByText(page, 'Revenue',        '09j-reports-revenue.png');
  await clickTabByText(page, 'Vehicle Compliance', '09l-reports-compliance.png');
  await clickTabByText(page, 'Evidence',       '09d-reports-evidence.png');
  await clickTabByText(page, 'Supplier Jobs',  '09e-reports-supplier-jobs.png');
  await clickTabByText(page, 'Car Jobs',       '09f-reports-car-jobs.png');
  await clickTabByText(page, 'Visa',           '09g-reports-visa.png');
  await clickTabByText(page, 'Sales',          '09h-reports-sales.png');
  await clickTabByText(page, 'Departure',      '09i-reports-departure.png');

  await browser.close();
  console.log('\n✅ Done');
})().catch(e => { console.error(e.message); process.exit(1); });
