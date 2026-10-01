import puppeteer from 'puppeteer-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SCREENS_DIR = path.resolve(__dirname, '../tests/evidence/p5/screens');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function captureScreens() {
  console.log('Launching Chrome via puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1600,1050'],
    defaultViewport: { width: 1600, height: 1050 },
  });

  const page = await browser.newPage();

  console.log('Navigating to http://localhost:5173/...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await sleep(1500);

  // Ensure logged in as Fleet Manager
  const demoManagerBtn = await page.$('#btn-demo-manager');
  if (demoManagerBtn) {
    console.log('Logging in as Fleet Manager...');
    await demoManagerBtn.click();
    await sleep(400);
    const submitBtn = await page.$('#btn-login-submit');
    if (submitBtn) await submitBtn.click();
    await sleep(2000);
  }

  // Ensure we are on Fleet Overview
  const overviewNav = await page.$('#nav-overview');
  if (overviewNav) {
    await overviewNav.click();
    await sleep(1000);
  }

  // 1. Screenshot: fleet_overview.png
  console.log('1. Capturing fleet_overview.png...');
  await page.screenshot({
    path: path.join(SCREENS_DIR, 'fleet_overview.png'),
    fullPage: false,
  });

  // 2. Screenshot: live_alert_arriving.png
  console.log('2. Navigating to Live Alerts...');
  const alertsNav = await page.$('#nav-alerts');
  if (alertsNav) {
    await alertsNav.click();
    await sleep(1500);
    console.log('Capturing live_alert_arriving.png...');
    await page.screenshot({
      path: path.join(SCREENS_DIR, 'live_alert_arriving.png'),
      fullPage: false,
    });
  }

  // 3. Screenshot: vehicle_detail_charge_plan.png
  console.log('3. Navigating to Vehicle & Plans...');
  const vehiclesNav = await page.$('#nav-vehicles');
  if (vehiclesNav) {
    await vehiclesNav.click();
    await sleep(1500);

    // Click Propose Charge Plan button
    const proposeBtn = await page.$('#btn-propose-plan');
    if (proposeBtn) {
      console.log('Computing DP optimal charging plan...');
      await proposeBtn.click();
      await sleep(2000);
    }

    // Scroll to plan result container
    await page.evaluate(() => {
      const el = document.getElementById('plan-result-container');
      if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
      else window.scrollTo(0, 600);
    });
    await sleep(800);

    console.log('Capturing vehicle_detail_charge_plan.png...');
    await page.screenshot({
      path: path.join(SCREENS_DIR, 'vehicle_detail_charge_plan.png'),
      fullPage: false,
    });
  }

  // 4. Screenshot: copilot_answer.png
  console.log('4. Navigating to Copilot Chat...');
  const copilotNav = await page.$('#nav-copilot');
  if (copilotNav) {
    await copilotNav.click();
    await sleep(1500);

    // Click a sample prompt chip to get fresh copilot response with LangGraph trace
    const promptChip = await page.$('#btn-prompt-1'); // 'Explain the thermal alert on vehicle 2NMEV02B200000002'
    if (promptChip) {
      console.log('Asking copilot question...');
      await promptChip.click();
      await sleep(2500);
    }

    console.log('Capturing copilot_answer.png...');
    await page.screenshot({
      path: path.join(SCREENS_DIR, 'copilot_answer.png'),
      fullPage: false,
    });
  }

  console.log('All 4 evidence screenshots captured successfully in p5/screens/!');
  await browser.close();
}

captureScreens().catch((err) => {
  console.error('Error during capture:', err);
  process.exit(1);
});
