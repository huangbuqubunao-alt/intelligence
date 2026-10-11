import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(1000);

const body = () => page.evaluate(() => document.body.innerText);

console.log("=== CLICK 添加关注 (header button) ===");
await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
await page.waitForTimeout(700);
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 2000));
await shot(page, "07-add-source-dialog");

console.log("\n=== DIALOG CONTROLS ===");
console.log(JSON.stringify(await page.evaluate(() => ({
  inputs: [...document.querySelectorAll("input,textarea")].map((e) => ({
    tag: e.tagName, type: e.type, name: e.name, id: e.id,
    placeholder: e.placeholder, accept: e.accept,
  })),
  buttons: [...document.querySelectorAll("button")].map((b) => ({
    text: b.innerText.trim(), disabled: b.disabled,
  })).filter((b) => b.text),
  fileInputs: [...document.querySelectorAll("input[type=file]")].map((e) => ({
    accept: e.accept, multiple: e.multiple, visible: e.offsetParent !== null,
  })),
}), null), null, 1));

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();