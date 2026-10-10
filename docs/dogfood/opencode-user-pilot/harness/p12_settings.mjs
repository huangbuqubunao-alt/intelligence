import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Settings", { waitUntil: "networkidle" });
await page.waitForTimeout(3000);
console.log("############ SETTINGS ############");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 6000));
await shot(page, "24-settings");

console.log("\n############ SETTINGS BUTTONS/INPUTS ############");
console.log(JSON.stringify(await page.evaluate(() => ({
  buttons: [...document.querySelectorAll("button")].map((b) => `${b.innerText.trim()}${b.disabled ? "(disabled)" : ""}`).filter(Boolean),
  selects: [...document.querySelectorAll("select")].map((s) => ({ label: s.getAttribute("aria-label") || s.previousElementSibling?.innerText, value: s.value, options: [...s.options].map((o) => o.text) })),
  inputs: [...document.querySelectorAll("input")].map((i) => ({ type: i.type, placeholder: i.placeholder, value: i.type === "password" ? "***" : i.value })),
})), null, 1));

console.log("\n############ NARROW VIEWPORT (390x844) ############");
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(1500);
for (const r of ["Home", "Following", "Content", "Settings"]) {
  await page.goto(BASE + "#" + r, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const overflow = await page.evaluate(() => ({
    docW: document.documentElement.scrollWidth, winW: window.innerWidth,
    overflowing: [...document.querySelectorAll("*")].filter((e) => e.scrollWidth > window.innerWidth + 2).slice(0, 5).map((e) => e.tagName + "." + (e.className || "").toString().slice(0, 40)),
  }));
  console.log(`${r}: doc=${overflow.docW} win=${overflow.winW} overflow=${overflow.docW > overflow.winW + 2} ${JSON.stringify(overflow.overflowing)}`);
  await shot(page, `25-narrow-${r.toLowerCase()}`);
}
await page.setViewportSize({ width: 1440, height: 960 });

console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();