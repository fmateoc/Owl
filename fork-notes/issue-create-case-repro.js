// Repro for fork-notes/issue-create-case.md (Node + Playwright, Chromium).
// Start Owl (`streamlit run ui/main.py`), then:
//   OWL_URL=http://localhost:8501 node issue-create-case-repro.js examples/HFP_jack+jill.xlsx
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

async function mouseClick(page, locator) {
  const box = await locator.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

// Create Case: type the case name and the first name, click "Create case"
// with the mouse right after typing (the click blurs the field), then upload the workbook.
const h = { open, nav, idle, alerts, mouseClick };
(async () => {
  const { browser, page } = await h.open();
  await h.nav(page, 'Case Setup', 'Create Case');
  await page.getByRole('tab', { name: 'Create a New Case' }).click();
  await h.idle(page);
  const cname = page.getByLabel('Case name', { exact: true });
  await cname.click();
  await cname.pressSequentially('probe', { delay: 20 });
  await cname.press('Enter');
  await h.idle(page, 1200);
  const first = page.getByLabel('Your first name', { exact: true });
  await first.click();
  await first.pressSequentially('Jack', { delay: 20 });
  const btn = page.getByRole('button', { name: /Create case/ });
  console.log('Create case disabled at the click:', await btn.isDisabled());
  await h.mouseClick(page, btn);
  await h.idle(page, 2000);
  const created = (await h.alerts(page)).filter(t => t.includes('Created new case'));
  console.log('after one click:', created.length ? created[0] : 'no case created',
              '| alerts:', JSON.stringify((await h.alerts(page)).filter(t => !t.includes('Created new case'))));
  if (!created.length) {
    await h.mouseClick(page, btn);
    await h.idle(page, 2000);
    console.log('after a second click:', JSON.stringify((await h.alerts(page)).filter(t => t.includes('Created'))));
  }
  const up = page.locator('[data-testid="stFileUploader"] input[type="file"]').last();
  await up.setInputFiles(process.argv[2]);
  await h.idle(page, 3000);
  console.log('upload heading still shown:', await page.getByText('Upload Financial Profile', { exact: false }).count());
  const caps = await page.locator('[data-testid="stCaptionContainer"]').allInnerTexts();
  console.log('captions mentioning the workbook:', JSON.stringify(caps.filter(c => c.includes('HFP') || c.includes('loaded'))));
  await browser.close();
})();
