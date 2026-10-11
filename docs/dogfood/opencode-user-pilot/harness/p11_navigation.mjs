import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const snap = () => page.evaluate(() => ({
  hash: location.hash,
  h1: document.querySelector("h1")?.innerText,
  active: [...document.querySelectorAll("button")].filter((b) => (b.className || "").includes("active")).map((b) => b.innerText.trim()),
}));

await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

console.log("=== A. CLICK SIDEBAR NAV (as a real user) ===");
for (const label of ["关注", "内容", "洞察", "主题", "设置", "首页"]) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.waitForTimeout(1500);
  const s = await snap();
  console.log(`click ${label.padEnd(4)} -> hash=${(s.hash || "(none)").padEnd(14)} h1=${s.h1}  activeNav=${JSON.stringify(s.active)}`);
}

console.log("\n=== B. BROWSER BACK / FORWARD ===");
await page.getByRole("button", { name: "内容", exact: true }).click();
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "设置", exact: true }).click();
await page.waitForTimeout(1200);
console.log("now at:", await snap());
await page.goBack(); await page.waitForTimeout(1500);
console.log("after BACK   :", await snap());
await page.goBack(); await page.waitForTimeout(1500);
console.log("after BACK   :", await snap());
await page.goForward(); await page.waitForTimeout(1500);
console.log("after FORWARD:", await snap());

console.log("\n=== C. DIRECT HASH EDIT (typing in the address bar) ===");
await page.goto(BASE + "#Topics", { waitUntil: "networkidle" });
await page.waitForTimeout(1800);
console.log("goto #Topics :", await snap());
await page.evaluate(() => { location.hash = "#Settings"; });
await page.waitForTimeout(1500);
console.log("hash=#Settings:", await snap());
await page.evaluate(() => { location.hash = "#Topics"; });
await page.waitForTimeout(1500);
console.log("hash=#Topics  :", await snap());
await shot(page, "23-topics-route");

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();