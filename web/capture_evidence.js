import puppeteer from 'puppeteer-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const EVIDENCE_DIR = path.resolve(__dirname, '../tests/evidence/p5');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function capture() {
  console.log('Launching Chrome via puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1600,1000'],
    defaultViewport: { width: 1600, height: 1000 },
  });

  const page = await browser.newPage();

  console.log('Navigating to http://localhost:5173/...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await sleep(1000);

  // Sign out if logged in to capture login page
  const logoutBtn = await page.$('#btn-logout');
  if (logoutBtn) {
    await logoutBtn.click();
    await sleep(1000);
    console.log('Capturing 00_login.png...');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '00_login.png'), fullPage: true });

    // Click demo manager to log back in
    const demoBtn = await page.$('#btn-demo-manager');
    if (demoBtn) {
      await demoBtn.click();
      await sleep(500);
      const submitBtn = await page.$('#btn-login-submit');
      if (submitBtn) await submitBtn.click();
      await sleep(1500);
    }
  }

  // 1. Fleet Overview Screenshot
  console.log('Capturing 01_fleet_overview.png...');
  await page.screenshot({ path: path.join(EVIDENCE_DIR, '01_fleet_overview.png'), fullPage: true });

  // 2. Click Inspect Telemetry on Vehicle
  console.log('Inspecting vehicle 1VXEV01A100000001...');
  const viewBtn = await page.$('#btn-view-1VXEV01A100000001');
  if (viewBtn) {
    await viewBtn.click();
    await sleep(1500);

    // Click Propose Charge Plan
    const proposeBtn = await page.$('#btn-propose-plan');
    if (proposeBtn) {
      await proposeBtn.click();
      await sleep(1500);
    }

    console.log('Capturing 02_vehicle_detail_and_dp_plan.png...');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '02_vehicle_detail_and_dp_plan.png'), fullPage: true });
  }

  // 3. Navigate to Alerts
  console.log('Navigating to Live Alerts...');
  const alertsNav = await page.$('#nav-alerts');
  if (alertsNav) {
    await alertsNav.click();
    await sleep(1500);
    console.log('Capturing 03_realtime_alerts.png...');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '03_realtime_alerts.png'), fullPage: true });
  }

  // 4. Navigate to Copilot Chat
  console.log('Navigating to Copilot Chat...');
  const copilotNav = await page.$('#nav-copilot');
  if (copilotNav) {
    await copilotNav.click();
    await sleep(1500);
    console.log('Capturing 04_copilot_intelligence.png...');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '04_copilot_intelligence.png'), fullPage: true });
  }

  // 5. Navigate to Admin
  console.log('Navigating to Compliance & Admin...');
  const adminNav = await page.$('#nav-admin');
  if (adminNav) {
    await adminNav.click();
    await sleep(1500);
    console.log('Capturing 05_admin_privacy_dp_benchmark.png...');
    await page.screenshot({ path: path.join(EVIDENCE_DIR, '05_admin_privacy_dp_benchmark.png'), fullPage: true });

    // Switch Role to Viewer (Masked)
    const viewerRoleBtn = await page.$('#btn-role-viewer');
    if (viewerRoleBtn) {
      await viewerRoleBtn.click();
      await sleep(1000);
      console.log('Capturing 06_viewer_role_location_masked.png...');
      await page.screenshot({ path: path.join(EVIDENCE_DIR, '06_viewer_role_location_masked.png'), fullPage: true });
    }
  }

  console.log('Finished capturing all evidence screenshots successfully!');
  await browser.close();
}

capture().catch((err) => {
  console.error('Error during capture:', err);
  process.exit(1);
});
