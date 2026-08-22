/**
 * iTourTT — Production Screenshot Script
 * Logs into https://fulvago.itourtt.cloud and captures all key pages.
 * Run: node website/take-screenshots.mjs
 */
import pkg from '/home/gouda/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js';
const { chromium } = pkg;
// Use an already-installed Chromium to avoid download
const BROWSER_EXEC = '/home/gouda/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, 'screenshots');
const BASE = 'https://fulvago.itourtt.cloud';
const EMAIL = 'admin@itour.local';
const PASS  = 'Admin@123';

const VIEWPORT = { width: 1440, height: 900 };

async function shot(page, name, selector) {
  await page.waitForTimeout(1200);
  if (selector) {
    try {
      const el = page.locator(selector).first();
      await el.waitFor({ state: 'visible', timeout: 5000 });
    } catch (_) {}
  }
  await page.screenshot({ path: `${OUT}/${name}`, fullPage: false });
  console.log(`  ✓ ${name}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: BROWSER_EXEC });
  const ctx = await browser.newContext({ viewport: VIEWPORT });
  const page = await ctx.newPage();

  // ── LOGIN ──────────────────────────────────────────────────
  console.log('\n🔐 Logging in…');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot(page, '01-login.png');

  await page.fill('input[type="text"], input[placeholder*="Email"], input[placeholder*="email"], input[name="identifier"]', EMAIL);
  await page.fill('input[type="password"]', PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 15000 });
  await page.waitForTimeout(2000);

  // ── DASHBOARD ──────────────────────────────────────────────
  console.log('\n📊 Dashboard');
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '02-dashboard.png');

  // ── DISPATCH ──────────────────────────────────────────────
  console.log('\n🗓 Dispatch Console');
  await page.goto(`${BASE}/dashboard/dispatch`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await shot(page, '04-dispatch.png');

  // ── TRAFFIC JOBS ──────────────────────────────────────────
  console.log('\n📋 Traffic Jobs (B2B)');
  await page.goto(`${BASE}/dashboard/traffic-jobs`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '03-traffic-jobs.png');

  // ── ONLINE JOBS ───────────────────────────────────────────
  console.log('\n🌐 Online Jobs');
  await page.goto(`${BASE}/dashboard/traffic-jobs/online`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '03b-online-jobs.png');

  // ── FINANCE ───────────────────────────────────────────────
  console.log('\n💰 Finance');
  await page.goto(`${BASE}/dashboard/finance`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '07-finance.png');

  // ── REPORTS ───────────────────────────────────────────────
  console.log('\n📈 Reports');
  await page.goto(`${BASE}/dashboard/reports`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '09-reports.png');

  // Try to click Driver Score tab
  try {
    await page.getByRole('tab', { name: /driver score/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '13-driver-score.png');
  } catch (_) { console.log('  ⚠ Driver Score tab not found'); }

  // Try to click Rep Score tab
  try {
    await page.getByRole('tab', { name: /rep score/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '14-rep-score.png');
  } catch (_) { console.log('  ⚠ Rep Score tab not found'); }

  // Try Evidence tab
  try {
    await page.getByRole('tab', { name: /evidence/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '09b-reports-evidence.png');
  } catch (_) { console.log('  ⚠ Evidence tab not found'); }

  // Try Departure tab
  try {
    await page.getByRole('tab', { name: /departure/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '09c-reports-departure.png');
  } catch (_) { console.log('  ⚠ Departure tab not found'); }

  // Try Supplier Jobs tab
  try {
    await page.getByRole('tab', { name: /supplier jobs/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '09d-reports-supplier-jobs.png');
  } catch (_) { console.log('  ⚠ Supplier Jobs tab not found'); }

  // Try Car Jobs tab
  try {
    await page.getByRole('tab', { name: /car jobs/i }).click();
    await page.waitForTimeout(1500);
    await shot(page, '09e-reports-car-jobs.png');
  } catch (_) { console.log('  ⚠ Car Jobs tab not found'); }

  // ── AGENTS ────────────────────────────────────────────────
  console.log('\n🏢 Agents');
  await page.goto(`${BASE}/dashboard/agents`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '05-agents.png');

  // ── VEHICLES ──────────────────────────────────────────────
  console.log('\n🚗 Vehicles');
  await page.goto(`${BASE}/dashboard/vehicles`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '06-vehicles.png');

  // ── DRIVERS ───────────────────────────────────────────────
  console.log('\n👤 Drivers');
  await page.goto(`${BASE}/dashboard/drivers`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '08-drivers.png');

  // ── DRIVER TARIFFS ────────────────────────────────────────
  console.log('\n💲 Driver Tariffs');
  await page.goto(`${BASE}/dashboard/driver-tariffs`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '12-driver-tariffs.png');

  // ── REPS ──────────────────────────────────────────────────
  console.log('\n👔 Reps');
  await page.goto(`${BASE}/dashboard/reps`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '08b-reps.png');

  // ── LOCATIONS ─────────────────────────────────────────────
  console.log('\n📍 Locations');
  await page.goto(`${BASE}/dashboard/locations`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '11-locations.png');

  // ── USERS ─────────────────────────────────────────────────
  console.log('\n👥 Users & Permissions');
  await page.goto(`${BASE}/dashboard/users`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '10-users.png');

  // ── STYLING ───────────────────────────────────────────────
  console.log('\n🎨 Styling / Theme Customizer');
  await page.goto(`${BASE}/dashboard/styling`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '15-styling.png');

  // ── GOOGLE DRIVE ──────────────────────────────────────────
  console.log('\n☁️  Google Drive');
  await page.goto(`${BASE}/dashboard/google-drive`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '16-google-drive.png');

  // ── WHATSAPP ──────────────────────────────────────────────
  console.log('\n💬 WhatsApp');
  await page.goto(`${BASE}/dashboard/whatsapp`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '17-whatsapp.png');

  // ── JOB CONTROL ───────────────────────────────────────────
  console.log('\n⚙️  Job Control');
  await page.goto(`${BASE}/dashboard/job-control`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '18-job-control.png');

  // ── ACTIVITY LOG ──────────────────────────────────────────
  console.log('\n📝 Activity Log');
  await page.goto(`${BASE}/dashboard/activity-log`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '19-activity-log.png');

  // ── GUEST BOOKINGS ────────────────────────────────────────
  console.log('\n🌍 Guest Bookings');
  await page.goto(`${BASE}/dashboard/guest-bookings`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '20-guest-bookings.png');

  // ── CAR DISPATCH ──────────────────────────────────────────
  console.log('\n🚙 Car Dispatch');
  await page.goto(`${BASE}/dashboard/car-dispatch`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '21-car-dispatch.png');

  // ── SUPPLIERS ─────────────────────────────────────────────
  console.log('\n🏭 Suppliers');
  await page.goto(`${BASE}/dashboard/suppliers`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '22-suppliers.png');

  // ── PORTALS (logged in as admin, navigate to portal URLs) ──
  console.log('\n📱 Driver Portal');
  await page.goto(`${BASE}/driver`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '23-driver-portal.png');

  console.log('\n📱 Rep Portal');
  await page.goto(`${BASE}/rep`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '24-rep-portal.png');

  console.log('\n📱 Supplier Portal');
  await page.goto(`${BASE}/supplier`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '25-supplier-portal.png');

  // ── B2C WEBSITE ────────────────────────────────────────────
  console.log('\n🌐 B2C Website');
  await page.goto(`${BASE}/w`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await shot(page, '26-b2c-website.png');

  await browser.close();
  console.log('\n✅ All screenshots saved to website/screenshots/');
})().catch(e => { console.error('Error:', e.message); process.exit(1); });
