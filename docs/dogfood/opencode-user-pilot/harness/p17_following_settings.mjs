// Verify Following pause/resume and Settings language switching via real UI.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = "";
    try { p = (await r.text()).slice(0, 150); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "").slice(0, 70)}`);
  }
});

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
console.log("=== FOLLOWING ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1800));

// Pause the channel
console.log("\n=== PAUSE ===");
const pause = page.getByRole("button", { name: /暂停关注/ }).first();
console.log("pause button:", await pause.count());
if (await pause.count()) {
  await pause.click();
  await page.waitForTimeout(2000);
  console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
  await shot(page, "38-following-paused");
}

// Resume
console.log("\n=== RESUME ===");
const resume = page.getByRole("button", { name: /恢复关注|继续关注/ }).first();
console.log("resume button:", await resume.count());
if (await resume.count()) {
  await resume.click();
  await page.waitForTimeout(2000);
  console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
  await shot(page, "39-following-resumed");
}

// Language switch
console.log("\n=== SETTINGS / LANGUAGE ===");
await page.getByRole("button", { name: "设置", exact: true }).click();
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "编辑语言", exact: true }).click();
await page.waitForTimeout(1000);
console.log("language dialog:", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1000));
await shot(page, "40-language-dialog");

const enOption = page.getByRole("button", { name: /English/ }).first();
console.log("english option:", await enOption.count());
if (await enOption.count()) {
  await enOption.click();
  await page.waitForTimeout(1500);
  console.log("after EN:", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 800));
  await shot(page, "41-settings-english");
  // switch back to Chinese
  const zhBtn = page.getByRole("button", { name: /中文/ }).first();
  if (await zhBtn.count()) {
    await zhBtn.click();
    await page.waitForTimeout(1200);
    console.log("back to zh:", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 500));
  }
}

console.log("\n=== API ===");
console.log(api.join("\n").slice(0, 3000));
console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
