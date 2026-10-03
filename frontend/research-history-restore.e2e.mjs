import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "playwright-core";

const base = process.env.YIA_RESEARCH_UI_URL ?? "http://127.0.0.1:5399/";
const root = resolve(process.env.YIA_RESEARCH_FIXTURE_ROOT ?? "../.var/phase5/browser-acceptance");
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/$/);
assert.ok(root.includes("/v1x-research-history/.var/phase5/"));
const restoreOnly = process.env.YIA_RESEARCH_RESTORE_ONLY === "1";
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [], external = [];
try {
  const page = await browser.newPage({ viewport: { width: 320, height: 1000 } });
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => { if (["error", "warning"].includes(m.type())) errors.push(m.text()); });
  page.on("request", r => { if (!r.url().startsWith(base)) external.push(r.url()); });
  await page.addInitScript(() => localStorage.setItem("yia.ui-language", "en"));
  const get = async path => { const response = await page.request.get(`${base}api/v1/${path}`); assert.equal(response.status(), 200); return response.json(); };
  const snapshot = async id => {
    const current = await get(`research/${id}`);
    const pages = [];
    let cursor = null;
    do {
      const data = await get(`research/${id}/history${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`);
      pages.push(data); cursor = data.next_cursor;
    } while (cursor);
    const oldId = pages.at(-1).revisions.at(-1).revision_id;
    const old = await get(`research/${id}/history/${oldId}`);
    return { current, pages, old };
  };
  let expected;
  if (!restoreOnly) {
    const list = await get("research");
    const item = list.research.find(r => r.question === "What can canonical evidence tell me?");
    assert.ok(item);
    expected = await snapshot(item.research_id);
    assert.equal(expected.pages[0].revisions.length, 25);
    assert.equal(expected.pages[0].has_more, true);
    assert.ok(expected.pages.length >= 2);
    await page.goto(`${base}#Research/${item.research_id}`);
    await page.waitForFunction(() => document.querySelectorAll(".research-history-list li").length === 25);
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction(() => document.querySelectorAll(".research-history-list li").length < 25 && document.querySelectorAll(".research-history-list li").length > 0);
    await page.getByRole("button", { name: "Previous", exact: true }).click();
    await page.waitForFunction(() => document.querySelectorAll(".research-history-list li").length === 25);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    writeFileSync(join(root, "restore-expected.json"), JSON.stringify(expected, null, 2));
    const created = await page.request.post(`${base}api/v1/backup-restore/backups`, { data: {}, headers: { "X-YIA-Request": "local-ui" } });
    assert.equal(created.status(), 201);
    const backup = (await created.json()).backup;
    const download = await page.request.get(`${base}api/v1/backup-restore/backups/${backup.backup_id}/download`);
    assert.equal(download.status(), 200);
    const staged = await page.request.post(`${base}api/v1/backup-restore/restore/stage`, { data: await download.body(), headers: { "Content-Type": "application/zip", "X-YIA-Request": "local-ui" } });
    assert.equal(staged.status(), 200);
    const restoreId = (await staged.json()).restore.restore_id;
    const confirm = await page.request.post(`${base}api/v1/backup-restore/restore/confirm`, { data: { restore_id: restoreId }, headers: { "X-YIA-Request": "local-ui" } });
    assert.equal(confirm.status(), 202);
    console.log("Real HTTP archive created, downloaded, staged and confirmed; 25-row browser pagination passed. Restart the isolated backend to apply restore.");
  } else {
    expected = JSON.parse(readFileSync(join(root, "restore-expected.json"), "utf8"));
    const id = expected.current.research.packet.research_id;
    assert.deepEqual(await snapshot(id), expected);
    await page.goto(`${base}#Research/${id}/history/${expected.old.research.result_identity}`);
    await page.getByRole("heading", { name: "Previous Research version", exact: true }).waitFor();
    assert.ok((await page.locator(".research-result").innerText()).includes(expected.old.research.packet.evidence[0].excerpt));
    await page.getByRole("button", { name: "Open Content and Evidence", exact: true }).click();
    await page.waitForFunction(() => document.activeElement?.id.startsWith("content-evidence-"));
    await page.getByRole("button", { name: "Back to Research", exact: true }).click();
    await page.getByRole("heading", { name: "Previous Research version", exact: true }).waitFor();
    await page.getByRole("button", { name: "Open current version", exact: true }).click();
    await page.getByRole("heading", { name: "Current Research version", exact: true }).waitFor();
    writeFileSync(join(root, "restore-report.json"), JSON.stringify({ restored: true, exactPackets: true, exactOrder: true, currentPreserved: true, sourceTracing: true, consoleErrors: errors, externalRequests: external }, null, 2));
    console.log("Real archive restore + server restart preserves every page, exact old packet, current pointer and browser source tracing.");
  }
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
} finally { await browser.close(); }
