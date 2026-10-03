import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { chromium } from "playwright-core";

const base = "http://127.0.0.1:5488/";
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [], external = [], scenarios = [];
try {
  for (const language of ["zh-CN", "en"]) for (const width of [320, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (["error", "warning"].includes(m.type())) errors.push(m.text()); });
    page.on("request", r => { if (!r.url().startsWith(base)) external.push(r.url()); });
    await page.addInitScript(lang => localStorage.setItem("yia.ui-language", lang), language);
    const system = await (await page.request.get(`${base}api/v1/system`)).json();
    assert.equal(system.runtime.demo_data, false);
    assert.equal(system.runtime.mode, "STANDARD_LOCAL");
    await page.goto(base);
    await page.locator(".onboarding-panel").waitFor();
    const cont = language === "en" ? "Continue" : "继续";
    await page.getByRole("button", { name: cont, exact: true }).click();
    await page.locator(".sample-chain").waitFor();
    await page.getByRole("button", { name: cont, exact: true }).click();
    await page.getByRole("button", { name: language === "en" ? "Add first Following" : "添加第一个关注", exact: true }).click();
    await page.getByRole("button", { name: language === "en" ? "Add Source" : "添加关注", exact: true }).first().click();
    await page.getByRole("dialog").waitFor();
    await page.getByRole("dialog").getByRole("button", { name: language === "en" ? "Cancel" : "取消", exact: true }).first().click();
    for (const name of language === "en" ? ["Home", "Following", "Content", "Intelligence", "Topics", "Settings"] : ["首页", "关注", "内容", "洞察", "主题", "设置"]) {
      await page.getByRole("navigation").getByRole("button", { name, exact: true }).click();
      await page.locator("main h1").waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    await page.getByLabel(language === "en" ? "Discovered candidate" : "已发现的候选模型").waitFor();
    assert.equal(await page.getByRole("button", { name: language === "en" ? "Save candidate preference" : "保存候选偏好", exact: true }).isDisabled(), true);
    scenarios.push(`${language}/${width}: standard launch/onboarding/all-six-navigation/Settings without model`);
    await page.close();
  }
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  writeFileSync("../.var/closure/owner-browser.json", JSON.stringify({ scenarios, errors, external, overflow: 0 }, null, 2));
  console.log("4 standard-runtime owner launch flows passed; no fixture library/model, console errors, external requests or overflow.");
} finally { await browser.close(); }
