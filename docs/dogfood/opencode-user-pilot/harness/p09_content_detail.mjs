import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Content/aircAruvnKk", { waitUntil: "networkidle" });
await page.waitForTimeout(6000);
console.log("=== CONTENT DETAIL ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 5000));
await shot(page, "16-content-detail");

console.log("\n=== BUTTONS ===");
console.log(JSON.stringify(await page.evaluate(() =>
  [...document.querySelectorAll("button")].map((b) => `${b.innerText.trim()}${b.disabled ? "(disabled)" : ""}`).filter(Boolean)), null, 1));

console.log("\n=== sections/tabs ===");
console.log(JSON.stringify(await page.evaluate(() =>
  [...document.querySelectorAll("h2,h3,summary,details")].map((e) => e.tagName + ": " + (e.innerText||"").slice(0,80))), null, 1));

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();