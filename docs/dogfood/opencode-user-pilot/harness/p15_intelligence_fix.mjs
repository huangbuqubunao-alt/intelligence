// Verify UI shows the completed Intelligence result after the fix.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Content/aircAruvnKk", { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
console.log("=== CONTENT DETAIL (Intelligence area) ===");
const t = await body();
const m = /Intelligence result|洞察结果|提炼为洞察[\s\S]{0,800}/.exec(t);
console.log((m ? m[0] : t).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
await shot(page, "33-intelligence-after-fix");

// Trigger a fresh extraction via UI and watch status
console.log("\n=== TRIGGER 提炼为洞察 via UI ===");
const btn = page.getByRole("button", { name: /提炼为洞察/ }).first();
if (await btn.count()) {
  console.log("clicking:", (await btn.innerText()).trim());
  await btn.click();
  for (const w of [3000, 8000]) {
    await page.waitForTimeout(w);
    const t2 = await body();
    const m2 = /洞察结果|Intelligence result|提炼为洞察|已完成[\s\S]{0,500}/.exec(t2);
    console.log(`after +${w}ms:`, (m2 ? m2[0] : t2).replace(/\n{3,}/g, "\n\n").slice(0, 700));
  }
  await shot(page, "34-intelligence-extracted");
}

console.log("\n=== INTELLIGENCE VIEW ===");
await page.getByRole("button", { name: "洞察", exact: true }).click();
await page.waitForTimeout(3000);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1000));
await shot(page, "35-intelligence-view");

console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
