// Doubao handoff: re-verify routing/navigation behavior reported by OpenCode.
// Focus: does each sidebar click actually render the right view? (23/25 suspicious shots)
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const snap = () => page.evaluate(() => ({
  hash: location.hash,
  h1: document.querySelector("h1")?.innerText ?? "(no h1)",
  h2: [...document.querySelectorAll("h2")].map((e) => e.innerText.trim()).slice(0, 4),
}));

await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
console.log("INITIAL:", JSON.stringify(await snap()));

// skip onboarding if shown
if (/首次使用/.test(await body())) {
  for (let i = 0; i < 4; i += 1) {
    const t = await body();
    if (!/首次使用/.test(t)) break;
    const step = (t.match(/首次使用 · (\d) \/ 3/) ?? [])[1];
    if (step === "3") await page.getByRole("button", { name: "添加内容", exact: true }).click();
    else await page.getByRole("button", { name: "继续", exact: true }).click();
    await page.waitForTimeout(600);
  }
  console.log("onboarding skipped; now:", JSON.stringify(await snap()));
}

console.log("=== A. SIDEBAR CLICKS ===");
for (const label of ["关注", "内容", "洞察", "主题", "设置", "首页"]) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.waitForTimeout(1200);
  const s = await snap();
  console.log(`click ${label} -> hash=${s.hash} h1=${s.h1} h2=${JSON.stringify(s.h2)}`);
}

console.log("\n=== B. DIRECT HASH ===");
await page.goto(BASE + "#Topics", { waitUntil: "networkidle" });
await page.waitForTimeout(2000);
console.log("goto #Topics:", JSON.stringify(await snap()));
await shot(page, "30-topics-real");
await page.evaluate(() => { location.hash = "#Settings"; });
await page.waitForTimeout(1500);
console.log("hash=#Settings:", JSON.stringify(await snap()));
await page.evaluate(() => { location.hash = "#Intelligence"; });
await page.waitForTimeout(1500);
console.log("hash=#Intelligence:", JSON.stringify(await snap()));

console.log("\n=== C. BROWSER BACK/FORWARD ===");
await page.goto(BASE + "#Content", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.goto(BASE + "#Settings", { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
console.log("at Settings:", JSON.stringify(await snap()));
await page.goBack(); await page.waitForTimeout(1200);
console.log("after BACK:", JSON.stringify(await snap()));
await page.goForward(); await page.waitForTimeout(1200);
console.log("after FWD:", JSON.stringify(await snap()));

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();
