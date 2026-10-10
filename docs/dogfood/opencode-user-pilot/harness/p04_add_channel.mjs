import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(900);

const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/")) {
    let p = "";
    try { p = (await r.text()).slice(0, 500); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "")}\n    ${p}`);
  }
});

await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
await page.waitForTimeout(400);
await page.locator('input[placeholder*="youtube"]').fill("https://www.youtube.com/@veritasium");
await page.getByRole("button", { name: "关注频道", exact: true }).click();
console.log("clicked 关注频道; waiting...");
await page.waitForTimeout(30000);

console.log("\n=== PAGE STATE ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 3000));
await shot(page, "09-after-channel-add");

console.log("\n=== API CALLS ===");
console.log(api.join("\n---\n"));
console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();