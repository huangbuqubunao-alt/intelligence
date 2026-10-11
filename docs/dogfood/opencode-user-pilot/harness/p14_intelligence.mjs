// Doubao: manual Intelligence extraction via real UI on Content detail.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = "";
    try { p = (await r.text()).slice(0, 400); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "")} :: ${p.replace(/\n/g, " ")}`);
  }
});

await page.goto(BASE + "#Content/aircAruvnKk", { waitUntil: "networkidle" });
await page.waitForTimeout(5000);
console.log("=== CONTENT DETAIL ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1500));

console.log("\n=== BUTTONS ===");
console.log(JSON.stringify(await page.evaluate(() =>
  [...document.querySelectorAll("button")].map((b) => `${b.innerText.trim()}${b.disabled ? "(disabled)" : ""}`).filter(Boolean)), null, 1));

const btn = page.getByRole("button", { name: /提炼|Extract/ }).first();
console.log("\nbutton count:", await btn.count());
if (await btn.count()) {
  console.log("clicking:", (await btn.innerText()).trim());
  await btn.click();
  for (const w of [5000, 15000, 30000, 60000]) {
    await page.waitForTimeout(w);
    const t = await body();
    console.log(`\n--- after +${w}ms url=${page.url()} ---`);
    console.log(t.replace(/\n{3,}/g, "\n\n").slice(0, 900));
  }
  await shot(page, "31-intelligence-result");
}

console.log("\n=== INTELLIGENCE VIEW ===");
await page.getByRole("button", { name: "洞察", exact: true }).click();
await page.waitForTimeout(4000);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
await shot(page, "32-intelligence-view-after");

console.log("\n=== API ===");
console.log(api.join("\n---\n").slice(0, 5000));
console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
