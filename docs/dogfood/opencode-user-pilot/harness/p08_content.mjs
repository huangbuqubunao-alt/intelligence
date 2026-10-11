import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Content", { waitUntil: "networkidle" });
for (const wait of [3000, 10000, 20000, 30000, 30000]) {
  await page.waitForTimeout(wait);
  const t = await body();
  console.log(`\n########## CONTENT after ${wait}ms ##########`);
  console.log(t.replace(/\n{3,}/g, "\n\n").slice(0, 1600));
}

console.log("\n=== videos API ===");
const r = await page.evaluate(async () => {
  const res = await fetch("/api/v1/videos");
  return JSON.stringify(await res.json()).slice(0, 2500);
});
console.log(r);
await shot(page, "15-content-list");
console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();