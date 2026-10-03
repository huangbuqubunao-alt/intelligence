import assert from "node:assert/strict";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright-core";

const baseUrl = process.env.YIA_PHASE2_UI_URL ?? "http://127.0.0.1:5291/";
assert.match(baseUrl, /^http:\/\/127\.0\.0\.1:\d+\/$/);
const root = process.env.YIA_PHASE2_FIXTURE_ROOT;
assert.ok(root?.startsWith("/tmp/v1x-phase2-"), "Use only the disposable fixture server root");
const info = JSON.parse(readFileSync(join(root, "browser-fixture.json"), "utf8"));
const screenshots = join(root, "screenshots");
mkdirSync(screenshots, { recursive: true });
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [];
let scenarios = 0;
try {
  for (const language of ["en", "zh-CN"]) {
    for (const width of [320, 768, 1024, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      page.setDefaultTimeout(10000);
      page.on("pageerror", (error) => errors.push(String(error)));
      page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
      const posts = [];
      page.on("request", (request) => { if (request.method() === "POST") posts.push(request); });
      await page.addInitScript((language) => localStorage.setItem("yia.ui-language", language), language);
      await page.goto(`${baseUrl}#Content`);
      await page.getByRole("button", { name: /Phase 2 disposable fixture/ }).click();
      const publish = page.getByRole("button", { name: language === "en" ? "Publish to Obsidian" : "发布到 Obsidian", exact: true });
      await publish.waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll("button")].some(button => /^(Publish to Obsidian|发布到 Obsidian)$/.test(button.textContent) && !button.disabled));
      assert.equal(await page.getByRole("button", { name: language === "en" ? "Run Deep Analysis" : "开始深度分析", exact: true }).isDisabled(), true);
      assert.equal(posts.length, 0, "Opening Content must not publish");
      // Keyboard activation proves the explicit action is accessible.
      await publish.focus();
      await page.keyboard.press("Enter");
      await page.getByRole("status").filter({ hasText: language === "en" ? /Published to Obsidian|Updated in Obsidian|already up to date/ : /已发布到 Obsidian|已更新 Obsidian|已是最新版本/ }).waitFor();
      assert.equal(posts.length, 1);
      assert.ok(posts[0].url().endsWith(`/videos/${info.content_id}/deep-analysis/obsidian`));
      assert.deepEqual(posts[0].postDataJSON(), { result_identity: info.result_identity });
      assert.equal(await page.locator("nav button").count(), 6);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${language} ${width} overflow`);
      const notes = join(root, "external-vault", "Knowledge", "Deep Analysis");
      assert.equal(readdirSync(notes).filter(name => name.endsWith(".md")).length, 1);
      const note = join(notes, readdirSync(notes).find(name => name.endsWith(".md")));
      const markdown = readFileSync(note, "utf8");
      assert.ok(markdown.includes(info.result_identity));
      assert.ok(markdown.includes('output_language: "en"'), "UI language does not change generated output language");
      assert.ok(!markdown.includes("[["));
      assert.match(markdown, /Evidence: [0-9a-f]{64}/);
      await page.screenshot({ path: join(screenshots, `${language}-${width}.png`), fullPage: true });
      await page.close();
      scenarios += 1;
    }
  }
  // Edited managed output is replaced by SQLite authority on the next explicit publish.
  const notes = join(root, "external-vault", "Knowledge", "Deep Analysis");
  const note = join(notes, readdirSync(notes).find(name => name.endsWith(".md")));
  const canonical = readFileSync(note, "utf8");
  writeFileSync(note, canonical.replace("# Phase 2 disposable fixture", "# Edited external projection"));
  const page = await browser.newPage();
  await page.addInitScript(() => localStorage.setItem("yia.ui-language", "en"));
  await page.goto(`${baseUrl}#Content`);
  await page.getByRole("button", { name: /Phase 2 disposable fixture/ }).click();
  const publish = page.getByRole("button", { name: "Publish to Obsidian", exact: true });
  await publish.click();
  await page.getByRole("status").filter({ hasText: "Updated in Obsidian." }).waitFor();
  assert.equal(readFileSync(note, "utf8"), canonical);
  assert.deepEqual(errors, []);
  console.log(`${scenarios + 1} real HTTP/SQLite/vault browser scenarios passed; zero console errors; no horizontal overflow.`);
} finally {
  await browser.close();
}
