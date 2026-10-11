import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = ""; try { p = (await r.text()).slice(0, 500); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "")} :: ${p}`);
  }
});

console.log("############ INTELLIGENCE (before) ############");
await page.goto(BASE + "#Intelligence", { waitUntil: "networkidle" });
await page.waitForTimeout(3000);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 2000));
await shot(page, "20-intelligence-empty");

console.log("\n############ TOPICS ############");
await page.goto(BASE + "#Topics", { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1500));
await shot(page, "21-topics-empty");

console.log("\n############ TRIGGER 提炼为洞察 from Content ############");
await page.goto(BASE + "#Content/aircAruvnKk", { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
const btn = page.getByRole("button", { name: /提炼为洞察|Extract Intelligence|提炼洞察/ }).first();
console.log("button found:", await btn.count(), await btn.isDisabled().catch(() => "n/a"));
await btn.click();
for (const w of [4000, 10000, 20000, 30000, 30000]) {
  await page.waitForTimeout(w);
  const t = await body();
  const m = /洞察处理结果[\s\S]{0,600}/.exec(t);
  console.log(`\n--- after ${w}ms --- url=${page.url()}`);
  console.log((m ? m[0] : t).replace(/\n{3,}/g, "\n\n").slice(0, 700));
}
await shot(page, "22-intelligence-result");
console.log("\n=== API ===");
console.log(api.join("\n---\n").slice(0, 6000));
console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();