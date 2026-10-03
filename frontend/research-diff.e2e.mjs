import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { chromium } from "playwright-core";

const base = process.env.YIA_DIFF_UI_URL ?? "http://127.0.0.1:5419/";
const root = resolve(process.env.YIA_DIFF_FIXTURE_ROOT ?? "../.var/phase6/browser");
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/$/);
assert.ok((root.includes("/v1x-research-diff/.var/phase6/") || root.includes("/v1x-milestone-closure/.var/phase6/")));
const info = JSON.parse(readFileSync(join(root, "diff-fixture.json")));
const mode = process.env.YIA_DIFF_MODE ?? "acceptance";
const errors = [], external = [], scenarios = [];
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const artifact = join(root, "screenshots"); mkdirSync(artifact, { recursive: true });
try {
  for (const language of ["zh-CN", "en"]) for (const width of [320, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (["error", "warning"].includes(m.type())) errors.push(m.text()); });
    page.on("request", r => { if (!r.url().startsWith(base)) external.push(r.url()); });
    await page.addInitScript(lang => localStorage.setItem("yia.ui-language", lang), language);
    const text = (en, zh) => language === "en" ? en : zh;
    const get = async path => { const r = await page.request.get(`${base}api/v1/${path}`); assert.equal(r.status(), 200); return r.json(); };
    const route = (a, b) => `${base}#Research/${info.research_id}/diff/${a}/${b}`;
    const comparison = page.getByRole("heading", { name: text("Research revision comparison", "研究版本对比"), exact: true });
    const noOverflow = async () => {
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      const overflow = await page.locator(".research-diff").evaluate(el => [...el.querySelectorAll("*")].filter(n => n.scrollWidth > n.clientWidth + 1 && getComputedStyle(n).overflowX === "visible").map(n => n.tagName));
      assert.deepEqual(overflow, []);
    };
    await page.goto(`${base}#Research/${info.single}`);
    await page.getByText(text("No previous versions yet.", "暂无历史版本。"), { exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: text("Compare with previous", "与上一版本对比") }).count(), 0);
    await page.goto(`${base}#Research/${info.research_id}`);
    await page.getByRole("button", { name: text("Compare with previous", "与上一版本对比"), exact: true }).click();
    await comparison.waitFor();
    assert.ok(page.url().endsWith(`/diff/${info.middle}/${info.target}`));
    await page.getByText("Canonical evidence", { exact: false }).first().waitFor();
    assert.ok(await page.locator(".research-diff blockquote").count() > 0);
    await noOverflow();
    await page.screenshot({ path: join(artifact, `${mode}-${language}-${width}-added.png`), fullPage: true });
    await page.getByRole("button", { name: text("Open Content and Evidence", "打开内容与证据"), exact: true }).first().click();
    await page.waitForFunction(() => document.activeElement?.id.startsWith("content-evidence-"));
    await page.getByRole("button", { name: text("Back to Research", "返回研究"), exact: true }).click();
    await comparison.waitFor();
    assert.ok(page.url().endsWith(`/diff/${info.middle}/${info.target}`));
    await page.goto(`${base}#Research/${info.research_id}/history/${info.base}`);
    await page.getByRole("button", { name: text("Compare with current", "与当前版本对比"), exact: true }).click();
    await page.getByText(text("No material changes", "无实质变化"), { exact: true }).waitFor();
    assert.ok(page.url().endsWith(`/diff/${info.base}/${info.target}`));
    await page.reload(); await comparison.waitFor();
    await page.getByText(text("No material changes", "无实质变化"), { exact: true }).waitFor();
    await noOverflow();
    const before = await get(`research/${info.research_id}/diff?base_revision=${info.base}&target_revision=${info.target}`);
    if (mode === "restore") {
      const expected = JSON.parse(readFileSync(join(root, "restore-expected.json")));
      assert.deepEqual(before, expected.nochange);
      assert.deepEqual(await get(`research/${info.research_id}/diff?base_revision=${info.middle}&target_revision=${info.target}`), expected.changes);
    }
    await page.screenshot({ path: join(artifact, `${mode}-${language}-${width}-nochange.png`), fullPage: true });
    await page.goto(route(info.target, info.middle)); await comparison.waitFor();
    await page.locator(".research-diff blockquote").first().waitFor(); await noOverflow();
    const reverse = await get(`research/${info.research_id}/diff?base_revision=${info.target}&target_revision=${info.middle}`);
    assert.ok(reverse.diff.evidence.removed.length); assert.equal(reverse.diff.evidence.added.length, 0);
    assert.equal(reverse.diff.base.revision_id, info.target);
    const historical = await get(`research/${info.research_id}/diff?base_revision=${info.base}&target_revision=${info.middle}`);
    assert.ok(historical.diff.evidence.removed.length);
    const self = await get(`research/${info.research_id}/diff?base_revision=${info.base}&target_revision=${info.base}`);
    assert.equal(self.diff.no_material_changes, true);
    assert.equal(await page.locator(".sidebar-nav button").count(), 6);
    const body = await page.locator(".research-diff").innerText();
    assert.doesNotMatch(body, /INSUFFICIENT_MATERIAL|EVIDENCE_AVAILABLE|SYSTEM_INFERENCE|UNSUPPORTED_MODEL_SYNTHESIS|PRIMARY_ORIGINAL/);
    if (language === "zh-CN") assert.doesNotMatch(body, /Base version|Target version|Material status|Recorded interpretations|Packet fields/);
    else assert.doesNotMatch(body, /基础版本|目标版本|无实质变化|证据包字段/);
    scenarios.push(`${language}/${width}: single/previous/historical/current/three-revision/reverse/self/reload/trace`);
    await page.close();
  }
  // Real missing-authority response, localized without backend diagnostics.
  const page = await browser.newPage();
  await page.addInitScript(() => localStorage.setItem("yia.ui-language", "zh-CN"));
  await page.goto(`${base}#Research/${info.research_id}/diff/${"f".repeat(64)}/${info.target}`);
  await page.getByRole("alert").waitFor();
  assert.ok((await page.locator("body").innerText()).includes("基础版本暂不可用"));
  assert.doesNotMatch(await page.locator("body").innerText(), /RESEARCH_DIFF_|Research could not be read/);
  await page.close();
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  writeFileSync(join(root, `${mode}-report.json`), JSON.stringify({ scenarios, consoleErrors: errors, externalRequests: external, overflow: 0, expectedUnavailableResponses: 1 }, null, 2));
  console.log(`${scenarios.length} real HTTP/SQLite Diff flows passed (${mode}); both languages, four widths, explicit snapshot/source identities, zero unexpected console errors/overflow/external requests.`);
} finally { await browser.close(); }
