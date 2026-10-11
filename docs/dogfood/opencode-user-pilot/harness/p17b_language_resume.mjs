// Precise verification: language switch via select + resume Following.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = "";
    try { p = (await r.text()).slice(0, 120); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "").slice(0, 65)} :: ${p.replace(/\n/g, " ").slice(0, 100)}`);
  }
});

// 1) Resume Veritasium
await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(2000);
const resume = page.getByRole("button", { name: /持续关注/ }).first();
console.log("resume(持续关注) button:", await resume.count());
if (await resume.count()) {
  await resume.click();
  await page.waitForTimeout(2000);
  const t = await body();
  console.log("after resume:", /Veritasium[\s\S]{0,120}/.exec(t)?.[0]?.replace(/\n+/g, " | ") ?? t.slice(0, 300));
  await shot(page, "39-following-resumed");
}

// 2) Language switch: zh -> en
await page.getByRole("button", { name: "设置", exact: true }).click();
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "编辑语言", exact: true }).click();
await page.waitForTimeout(800);
const iface = page.getByLabel("界面语言");
console.log("interface select:", await iface.count());
if (await iface.count()) {
  await iface.selectOption("en");
  const output = page.getByLabel("默认输出语言");
  if (await output.count()) await output.selectOption("en");
  await shot(page, "41-language-english-draft");
  await page.getByRole("button", { name: "保存语言", exact: true }).click();
  await page.waitForTimeout(2500);
  console.log("after save EN:", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 900));
  await shot(page, "42-settings-english");

  // 3) switch back to zh
  const zhBtn = page.getByRole("button", { name: /Edit language/ }).first();
  if (await zhBtn.count()) {
    await zhBtn.click();
    await page.waitForTimeout(800);
    const iface2 = page.getByLabel("Interface language");
    if (await iface2.count()) {
      await iface2.selectOption("zh-CN");
      await page.getByLabel("Preferred output language").selectOption("zh-CN");
      await page.getByRole("button", { name: "Save language", exact: true }).click();
      await page.waitForTimeout(2000);
      console.log("back to zh:", (await body()).replace(/\n{3,}/g, "\n\n").slice(0, 600));
      await shot(page, "43-settings-chinese");
    }
  }
}

console.log("\n=== API ===");
console.log(api.join("\n").slice(0, 4000));
console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
