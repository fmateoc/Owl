// Repro for fork-notes/issue-slcsp-field.md (Node + Playwright, Chromium).
// Start Owl (`streamlit run ui/main.py`), then:
//   OWL_URL=http://localhost:8501 node issue-slcsp-field-repro.js examples/Case_riley+casey.toml
const { chromium } = require('playwright');
const URL = process.env.OWL_URL || 'http://localhost:8501';

async function idle(page, ms = 400) {
  await page.waitForTimeout(ms);
  for (let i = 0; i < 600; i++) {
    const busy = await page.locator('[data-testid="stStatusWidget"]').count();
    if (!busy) break;
    await page.waitForTimeout(250);
  }
  await page.waitForTimeout(300);
}

async function open(viewport = { width: 1440, height: 1000 }) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  await page.goto(URL);
  await page.waitForSelector('[data-testid="stApp"]');
  await idle(page, 1500);
  const ok = page.getByRole('button', { name: 'OK', exact: true });
  if (await ok.count()) { await ok.click(); await idle(page); }
  return { browser, page };
}

async function nav(page, section, link) {
  const sec = page.locator('[data-testid="stTopNavSection"]', { hasText: section }).first();
  if (await sec.count()) { await sec.click(); await page.waitForTimeout(300); }
  await page.getByRole('link', { name: link, exact: true }).first().click();
  await idle(page, 800);
}

async function alerts(page) {
  return await page.locator('[data-testid="stAlert"], [data-testid="stToast"]').allInnerTexts();
}

// The SLCSP field on Run Options: upload a case, type 20.84, read it back, click +.
const h = { open, nav, idle };
(async () => {
  const { browser, page } = await h.open();
  await h.nav(page, 'Case Setup', 'Create Case');
  await page.getByRole('tab', { name: 'Upload Your Own Case File' }).click();
  await h.idle(page);
  await page.locator('[data-testid="stFileUploader"] input[type="file"]').first().setInputFiles(process.argv[2]);
  await h.idle(page, 3000);
  await h.nav(page, 'Case Setup', 'Run Options');
  const field = page.getByRole('spinbutton', { name: /Benchmark Silver plan premium/ });
  console.log('shown on arrival:', await field.inputValue(), '| step:', await field.getAttribute('step'));
  await field.click();
  await field.fill('20.84');
  await field.press('Enter');
  await h.idle(page, 1500);
  console.log('after typing 20.84:', await field.inputValue());
  const box = page.locator('[data-testid="stNumberInput"]', { hasText: 'Benchmark Silver plan premium' });
  await box.locator('button').last().click();
  await h.idle(page, 1500);
  console.log('after one + click:', await field.inputValue());
  await browser.close();
})();
