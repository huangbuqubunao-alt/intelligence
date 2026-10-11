import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(900);

await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
await page.waitForTimeout(500);

const input = page.locator('input[placeholder*="youtube"]');
await input.fill("https://www.youtube.com/@veritasium");

for (const wait of [500, 1500, 4000]) {
  await page.waitForTimeout(wait);
  console.log(`\n===== after ${wait}ms cumulative =====`);
  console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 2200));
  console.log("buttons:", JSON.stringify(await page.evaluate(() =>
    [...document.querySelectorAll("button")].map((b) => `${b.innerText.trim()}${b.disabled ? "(disabled)" : ""}`).filter(Boolean))));
}
await shot(page, "08-link-typed");

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();