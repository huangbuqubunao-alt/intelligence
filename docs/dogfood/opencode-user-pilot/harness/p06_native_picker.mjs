import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
await page.waitForTimeout(400);
await page.getByRole("button", { name: "导入本地文件", exact: true }).click();
await page.waitForTimeout(1200);

console.log("=== LOCAL IMPORT DIALOG ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1800));
await shot(page, "11-local-import-dialog");

console.log("\n=== clicking 'Choose local files' (spawns a REAL macOS NSOpenPanel) ===");
await page.locator('button[aria-label]').filter({ hasText: /选择本地文件|Choose local files/ }).first()
  .or(page.getByRole("button", { name: /选择本地文件|Choose local files/ })).first().click();
await page.waitForTimeout(2500);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1200));
await shot(page, "12-native-picker-open");

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
// Leave the browser open context closed; the panel may remain on screen.
await context.close();