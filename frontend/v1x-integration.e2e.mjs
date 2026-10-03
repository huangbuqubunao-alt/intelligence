import assert from "node:assert/strict";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright-core";

const base = process.env.YIA_INTEGRATION_UI_URL ?? "http://127.0.0.1:5297/";
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/$/);
const root = process.env.YIA_PHASE2_FIXTURE_ROOT;
assert.ok(root?.startsWith("/tmp/v1x-phase2-integration-"));
const info = JSON.parse(readFileSync(join(root, "browser-fixture.json"), "utf8"));
const artifacts = join(root, "integrated-screenshots");
mkdirSync(artifacts, { recursive: true });
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [], external = [];
let scenarios = 0;
try {
  for (const language of ["zh-CN", "en"]) for (const width of [320, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const posts = [];
    page.on("pageerror", error => errors.push(String(error)));
    page.on("console", message => { if (["error", "warning"].includes(message.type())) errors.push(message.text()); });
    page.on("request", request => {
      if (request.method() === "POST") posts.push(request);
      if (!request.url().startsWith(base)) external.push(request.url());
    });
    await page.addInitScript(lang => localStorage.setItem("yia.ui-language", lang), language);
    await page.goto(`${base}#Home`);
    const home = language === "en" ? "Home" : "首页";
    const content = language === "en" ? "Content" : "内容";
    const delta = page.getByRole("region", { name: language === "en" ? "What changed in the last 7 days?" : "最近 7 天发生了什么变化？" });
    await delta.locator(".delta-items li").waitFor();
    const beforeDelta = await delta.innerText();
    assert.equal(await page.locator(".knowledge-delta").count(), 1);
    assert.equal(await page.locator("nav button").count(), 6);
    await page.getByRole("navigation").getByRole("button", { name: content, exact: true }).click();
    await page.getByRole("button", { name: /Integration no result/ }).click();
    const runName = language === "en" ? "Run Deep Analysis" : "开始深度分析";
    // The preserved failed receipt binds pre-integration domain/state source.
    // Their accepted changes correctly invalidate its binding to STALE.
    await page.getByText(language === "en" ? "Qualification needs renewal" : "资格评测需要重新进行", { exact: false }).waitFor();
    assert.equal(await page.getByRole("button", { name: runName, exact: true }).isDisabled(), true);
    assert.equal(await page.locator(".deep-analysis-result").count(), 0);
    if (language === "zh-CN") assert.doesNotMatch(await page.locator("body").innerText(), /No canonical transcript|A readable transcript|The recorded canonical transcript/);
    await page.screenshot({ path: join(artifacts, `${language}-${width}-no-result.png`), fullPage: true });
    await page.getByRole("button", { name: language === "en" ? "Back to Content" : "返回内容", exact: true }).click();
    await page.getByRole("button", { name: /Phase 2 disposable fixture/ }).click();
    await page.locator(".deep-analysis-result").waitFor();
    assert.equal(await page.locator(".deep-analysis-result .intelligence-section").count(), 5);
    const citations = page.locator('.deep-analysis-result a[href^="#content-evidence-"]');
    assert.ok(await citations.count() >= 5);
    const href = await citations.first().getAttribute("href");
    await page.locator(`[id="${decodeURIComponent(href.slice(1))}"]`).waitFor();
    assert.equal(await page.locator(`[id="${decodeURIComponent(href.slice(1))}"]`).count(), 1);
    assert.equal(await page.getByRole("button", { name: runName, exact: true }).isDisabled(), true);
    const publish = page.getByRole("button", { name: language === "en" ? "Publish to Obsidian" : "发布到 Obsidian", exact: true });
    await publish.waitFor();
    await page.waitForFunction(() => [...document.querySelectorAll("button")].some(button => /^(Publish to Obsidian|发布到 Obsidian)$/.test(button.textContent) && !button.disabled));
    assert.equal(posts.length, 0);
    await publish.click();
    await page.getByRole("status").filter({ hasText: language === "en" ? /Published to Obsidian|Updated in Obsidian|already up to date/ : /已发布到 Obsidian|已更新 Obsidian|已是最新版本/ }).waitFor();
    assert.equal(posts.length, 1);
    assert.ok(posts[0].url().endsWith(`/videos/${info.content_id}/deep-analysis/obsidian`));
    assert.doesNotMatch(await page.locator("body").innerText(), /NOT_QUALIFIED|DURABLE_EVIDENCE_VERIFIED|NOT_TESTED|SELECTED_EVIDENCE_ONLY/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: join(artifacts, `${language}-${width}-existing-result.png`), fullPage: true });
    await page.getByRole("navigation").getByRole("button", { name: home, exact: true }).click();
    await delta.locator(".delta-items li").waitFor();
    assert.equal(await delta.innerText(), beforeDelta);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: join(artifacts, `${language}-${width}-home.png`), fullPage: true });
    await page.close(); scenarios++;
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  console.log(`${scenarios} integrated real HTTP/SQLite/vault flows passed; production NONE, no-result/result/evidence/publish/Home, both languages, four widths, zero console errors or external requests.`);
} finally { await browser.close(); }
