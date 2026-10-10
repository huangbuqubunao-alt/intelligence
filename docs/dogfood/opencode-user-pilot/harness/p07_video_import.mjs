import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = "";
    try { p = (await r.text()).slice(0, 700); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "")}\n    ${p}`);
  }
});

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
await page.waitForTimeout(400);

const link = process.argv[2] ?? "https://www.youtube.com/watch?v=aircAruvnKk";
await page.locator('input[placeholder*="youtube"]').fill(link);
await page.waitForTimeout(1200);

console.log("=== dialog after recognizing", link, "===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1400));
console.log("buttons:", JSON.stringify(await page.evaluate(() =>
  [...document.querySelectorAll("button")].map((b) => b.innerText.trim()).filter(Boolean))));
await shot(page, "13-video-link-recognized");

const confirm = page.getByRole("button", { name: /导入视频|Import video|确认导入|关注频道|Follow channel/ }).first();
console.log("clicking:", await confirm.innerText());
await confirm.click();
console.log("waiting for import...");
await page.waitForTimeout(45000);

console.log("\n=== PAGE STATE ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 2500));
await shot(page, "14-after-video-import");

console.log("\n=== API CALLS ===");
console.log(api.join("\n---\n"));
console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();