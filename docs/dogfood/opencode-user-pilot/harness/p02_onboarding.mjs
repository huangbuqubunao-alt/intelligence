import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(1000);

const body = () => page.evaluate(() => document.body.innerText);

// Walk to the end regardless of where we resume.
for (let i = 0; i < 4; i += 1) {
  const t = await body();
  if (!/首次使用/.test(t)) break;
  const step = (t.match(/首次使用 · (\d) \/ 3/) ?? [])[1];
  console.log(`at onboarding step ${step}/3`);
  if (step === "3") {
    await page.getByRole("button", { name: "添加内容", exact: true }).click();
  } else {
    await page.getByRole("button", { name: "继续", exact: true }).click();
  }
  await page.waitForTimeout(800);
}

console.log("\n=== AFTER COMPLETING ONBOARDING ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
await shot(page, "04-after-onboarding");

console.log("\n=== RELOAD PERSISTENCE ===");
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(1200);
const t2 = await body();
console.log("onboarding visible after reload:", /首次使用/.test(t2));
console.log(t2.replace(/\n{3,}/g, "\n\n").slice(0, 1200));
await shot(page, "05-after-reload");

console.log("\n=== NAV: HOME -> FOLLOWING -> BACK ===");
await page.getByRole("button", { name: "关注", exact: true }).click();
await page.waitForTimeout(900);
console.log("[Following]", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1000));
await shot(page, "06-following-empty");

await page.getByRole("button", { name: "首页", exact: true }).click();
await page.waitForTimeout(700);
console.log("[back Home] url:", page.url(), "onboarding shown:", /首次使用/.test(await body()));

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();