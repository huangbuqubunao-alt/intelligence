// Fresh-context test: full page load with each hash (user opens URL directly)
import { chromium } from "/Users/hua/Documents/yia-worktrees/opencode-user-pilot/frontend/node_modules/playwright-core/index.mjs";
import { PROFILE, BASE } from "./browser.mjs";

for (const route of ["", "#Following", "#Content", "#Intelligence", "#Topics", "#Settings", "#Home", "#Content/aircAruvnKk"]) {
  const context = await chromium.launchPersistentContext(PROFILE, {
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true, viewport: { width: 1440, height: 960 },
  });
  const page = context.pages()[0] ?? await context.newPage();
  await page.goto(BASE + route, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const snap = await page.evaluate(() => ({
    hash: location.hash,
    h1: document.querySelector("h1")?.innerText ?? "(no h1)",
  }));
  console.log(`direct ${JSON.stringify(route)} -> hash=${snap.hash} h1=${snap.h1}`);
  await context.close();
}
