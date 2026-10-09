import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright-core";

const base = "http://127.0.0.1:5598/";
const root = process.env.D2_02_UI_FIXTURE_ROOT ?? new URL("../.var/d2-02/ui-fixture/", import.meta.url).pathname;
const evidence = new URL("../docs/validation/dogfood-day2-d2-02/", import.meta.url).pathname;
mkdirSync(evidence, { recursive: true });
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [], external = [], scenarios = [], failedResponses = [];
try {
  for (const [language, filename] of [["en", "small.mp4"], ["zh-CN", "over64.mp4"], ["en", "two-gib.mp4"], ["en", "notes.md"]]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 950 } });
    page.on("pageerror", error => errors.push(String(error)));
    page.on("console", message => { if (["error", "warning"].includes(message.type())) errors.push(message.text()); });
    page.on("request", request => { if (!request.url().startsWith(base)) external.push(request.url()); });
    page.on("response", response => { if (response.status() >= 400) failedResponses.push({ url: response.url(), status: response.status() }); });
    await page.addInitScript(lang => localStorage.setItem("yia.ui-language", lang), language);
    const text = (en, zh) => language === "en" ? en : zh;
    await page.goto(`${base}#Following`);
    await page.getByRole("button", { name: text("Add Source", "添加关注"), exact: true }).first().click();
    await page.getByRole("button", { name: text("Import local file", "导入本地文件"), exact: true }).click();
    const dialog = page.getByRole("dialog");
    assert.ok((await dialog.innerText()).includes("2 GiB"));
    assert.ok((await dialog.innerText()).includes("2 MiB"));
    const chooser = page.waitForEvent("filechooser");
    await page.getByLabel(text("Choose local files", "选择本地文件")).click();
    await (await chooser).setFiles(join(root, filename));
    // Exercise the focus-triggered D2-01 refresh with the real file retained.
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    assert.ok((await dialog.innerText()).includes(filename));
    const response = page.waitForResponse(r => r.url().includes("/local/imports?") && r.request().method() === "POST", { timeout: 180_000 });
    await dialog.getByRole("button", { name: text("Confirm import", "确认导入"), exact: true }).click();
    if (filename === "two-gib.mp4" || filename === "over64.mp4") {
      await page.getByRole("progressbar").waitFor({ timeout: 30_000 });
      const progress = await page.getByRole("progressbar").evaluate(node => ({ value: node.value, max: node.max }));
      assert.ok(progress.value > 0 && progress.value <= progress.max);
      assert.equal(progress.max, filename === "two-gib.mp4" ? 2 * 1024 ** 3 : 65 * 1024 ** 2);
      await page.screenshot({ path: join(evidence, `upload-${filename}-${language}.png`), fullPage: true });
      await page.getByRole("status").filter({ hasText: text("Verifying imported file…", "正在验证导入文件…") }).waitFor({ timeout: 180_000 });
      await page.screenshot({ path: join(evidence, `verifying-${filename}-${language}.png`), fullPage: true });
    }
    const accepted = await response;
    assert.ok([200, 201].includes(accepted.status()));
    await page.waitForURL(`${base}#Content`, { timeout: 30_000 });
    const listing = await page.request.get(`${base}api/v1/videos`);
    const item = (await listing.json()).videos.find(item => item.title === filename);
    assert.ok(item, "saved Content is present in normal listing");
    const contentId = item.video_id;
    await dialog.waitFor({ state: "hidden" });
    await page.getByRole("heading", { name: filename, exact: true }).waitFor();
    const detail = await page.request.get(`${base}api/v1/videos/${contentId}`);
    assert.equal(detail.status(), 200);
    const status = (await detail.json()).video.processing_status;
    assert.equal(status, filename === "notes.md" ? "READY" : "TRANSCRIPTION_UNAVAILABLE");
    await page.reload();
    // Reload reconstructs the list; reopen the same persisted Content.
    if (await page.getByRole("heading", { name: filename, exact: true }).count() === 0) {
      await page.getByRole("button", { name: new RegExp(filename.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) }).first().click();
    }
    await page.getByRole("heading", { name: filename, exact: true }).waitFor();
    await page.screenshot({ path: join(evidence, `saved-${filename}-${language}.png`), fullPage: true });
    scenarios.push({ filename, language, bytes: filename === "two-gib.mp4" ? 2 * 1024 ** 3 : null, status, nativeChooser: "actual Chromium filechooser event with local path; OS dialog not manually driven", focusRefresh: "preserved", successNavigation: page.url(), reload: "passed" });
    await page.close();
  }
  const rss = JSON.parse(readFileSync(join(root, "rss.json")));
  assert.ok(rss.process_peak_rss_bytes < 256 * 1024 ** 2);
  writeFileSync(join(evidence, "browser-large-import-diagnostic.json"), JSON.stringify({ scenarios, errors, failedResponses, external, serverMemory: rss }, null, 2));
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  writeFileSync(join(evidence, "browser-large-import.json"), JSON.stringify({ scenarios, errors, external, serverMemory: rss }, null, 2));
  console.log("ACTUAL_BROWSER_2_GIB_IMPORT_D2_01_REGRESSIONS_PASSED");
} finally { await browser.close(); }
