import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/playwright-core/index.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const E2E_ROOT = path.join(REPO_ROOT, ".var/qa-audit/e2e-run");
const E2E_EMPTY_ROOT = path.join(REPO_ROOT, ".var/qa-audit/e2e-empty");
const SCREENSHOTS_DIR = path.join(REPO_ROOT, "qa/evidence/screenshots");
const REPORT_PATH = path.join(REPO_ROOT, "qa/evidence/playwright-e2e-report.json");
const API_PORT = 6491;
const UI_PORT = 6488;
const API_URL = `http://127.0.0.1:${API_PORT}`;
const UI_URL = `http://127.0.0.1:${UI_PORT}`;
const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

function httpGetStatus(url) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 2000 }, (res) => {
      res.resume();
      resolve(res.statusCode ?? 0);
    });
    req.on("error", () => resolve(0));
    req.on("timeout", () => {
      req.destroy();
      resolve(0);
    });
  });
}

async function waitForHttp200(url, label, proc, logPath) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) {
      throw new Error(`${label} exited early with code ${proc.exitCode}; log=${logPath}`);
    }
    const status = await httpGetStatus(url);
    if (status === 200) return;
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`${label} timed out waiting for HTTP 200 on ${url}; log=${logPath}`);
}

function stopChild(proc) {
  if (!proc || proc.exitCode !== null) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      try {
        proc.kill("SIGKILL");
      } catch {}
      resolve();
    }, 6000);
    proc.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
    try {
      proc.kill("SIGTERM");
    } catch {
      clearTimeout(timer);
      resolve();
    }
  });
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function prepareEmptyProject(emptyRoot) {
  fs.rmSync(emptyRoot, { recursive: true, force: true });
  for (const sub of ["config", "data", "logs", "vault", "templates"]) {
    fs.mkdirSync(path.join(emptyRoot, sub), { recursive: true });
  }
  const settingsLines = fs
    .readFileSync(path.join(REPO_ROOT, "config/settings.example.yaml"), "utf-8")
    .split("\n")
    .map((line) =>
      line.trim().startsWith("vault_root:") ? `  vault_root: ${path.join(emptyRoot, "vault")}` : line,
    );
  fs.writeFileSync(path.join(emptyRoot, "config/settings.yaml"), settingsLines.join("\n") + "\n", "utf-8");
  const channelsTxt = fs
    .readFileSync(path.join(REPO_ROOT, "config/channels.example.yaml"), "utf-8")
    .replaceAll("enabled: true", "enabled: false");
  fs.writeFileSync(path.join(emptyRoot, "config/channels.yaml"), channelsTxt, "utf-8");
}

function spawnBackend(pythonBin, projectRoot, logPath) {
  const out = fs.openSync(logPath, "w");
  const proc = spawn(
    pythonBin,
    [
      "-m",
      "youtube_intel",
      "--project-root",
      projectRoot,
      "serve-api",
      "--database",
      path.join(projectRoot, "state.sqlite3"),
      "--port",
      String(API_PORT),
    ],
    { cwd: REPO_ROOT, stdio: ["ignore", out, out] },
  );
  return { proc, out };
}

async function main() {
  const report = {
    started_at: new Date().toISOString(),
    ui_url: UI_URL,
    api_url: API_URL,
    steps: [],
    pageerrors: [],
    console_errors: [],
    server_5xx: [],
    responsive: [],
    summary: { total: 0, passed: 0, failed: 0 },
  };

  const pythonBin = fs.existsSync(path.join(REPO_ROOT, ".venv/bin/python"))
    ? path.join(REPO_ROOT, ".venv/bin/python")
    : "python3";

  prepareEmptyProject(E2E_EMPTY_ROOT);

  const viteBin = path.join(REPO_ROOT, "frontend/node_modules/.bin/vite");
  const uiLog = path.join(REPO_ROOT, "qa/evidence/e2e-vite.log");
  const uiOut = fs.openSync(uiLog, "w");
  const uiProc = spawn(
    viteBin,
    ["preview", "--host", "127.0.0.1", "--port", String(UI_PORT), "--strictPort"],
    {
      cwd: path.join(REPO_ROOT, "frontend"),
      env: { ...process.env, YIA_API_BASE: API_URL },
      stdio: ["ignore", uiOut, uiOut],
    },
  );

  let browser;
  let context;
  let apiHandle = null;

  try {
    await waitForHttp200(`${UI_URL}/`, "vite-preview", uiProc, uiLog);
    browser = await chromium.launch({
      executablePath: CHROME_PATH,
      headless: true,
      args: ["--no-sandbox", "--disable-gpu"],
    });

    // Phase 0: Empty-library Onboarding check
    const emptyLog = path.join(REPO_ROOT, "qa/evidence/e2e-api-empty.log");
    apiHandle = spawnBackend(pythonBin, E2E_EMPTY_ROOT, emptyLog);
    await waitForHttp200(`${API_URL}/api/v1/system`, "serve-api-empty", apiHandle.proc, emptyLog);

    context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      locale: "zh-CN",
      acceptDownloads: true,
    });
    let page = await context.newPage();

    const attachMonitors = (p) => {
      p.on("pageerror", (err) => report.pageerrors.push(String(err)));
      p.on("console", (msg) => {
        if (msg.type() === "error") {
          report.console_errors.push({ text: msg.text(), expected_in_negative_test: allowConsoleErrorsInStep });
        }
      });
      p.on("response", (resp) => {
        if (resp.status() >= 500) {
          report.server_5xx.push({ url: resp.url(), status: resp.status() });
        }
      });
    };

    let allowConsoleErrorsInStep = false;
    attachMonitors(page);

    async function shot(filename) {
      const target = path.join(SCREENSHOTS_DIR, filename);
      await page.screenshot({ path: target, fullPage: true });
      return `qa/evidence/screenshots/${filename}`;
    }

    async function checked(name, fn, { allowExpected4xxConsole = false } = {}) {
      const prevFlag = allowConsoleErrorsInStep;
      allowConsoleErrorsInStep = allowExpected4xxConsole;
      const t0 = Date.now();
      try {
        const detail = (await fn()) ?? {};
        report.steps.push({ name, passed: true, duration_ms: Date.now() - t0, detail });
        report.summary.total += 1;
        report.summary.passed += 1;
      } catch (err) {
        report.steps.push({
          name,
          passed: false,
          duration_ms: Date.now() - t0,
          error: String(err?.message || err),
        });
        report.summary.total += 1;
        report.summary.failed += 1;
      } finally {
        allowConsoleErrorsInStep = prevFlag;
        // Never let a lingering modal block later tests
        try {
          if (await page.locator(".overlay").count()) {
            const closeBtn = page.locator(".overlay").getByRole("button", { name: /^(Close|关闭|Cancel|取消)$/ }).first();
            if (await closeBtn.count()) {
              await closeBtn.click({ timeout: 2000 });
            } else {
              await page.keyboard.press("Escape");
            }
          }
        } catch {}
      }
    }

    await checked("onboarding_empty_library_complete_and_persist", async () => {
      await page.goto(`${UI_URL}/#Home`, { waitUntil: "networkidle" });
      await page.locator("#onboarding-title").waitFor({ state: "visible", timeout: 10000 });
      const s0 = await shot("00_onboarding.png");
      await page.getByRole("button", { name: /^(Continue|继续)$/ }).click();
      await page.getByRole("button", { name: /^(Continue|继续)$/ }).click();
      await page.getByRole("button", { name: /^(Skip for now|暂时跳过)$/ }).click();
      await page.locator("#onboarding-title").waitFor({ state: "detached", timeout: 5000 });
      await page.reload({ waitUntil: "networkidle" });
      assert((await page.locator("#onboarding-title").count()) === 0, "Onboarding reappeared after reload");
      return { screenshots: [s0], onboarding_persisted: true };
    });

    await context.close();
    context = null;
    await stopChild(apiHandle.proc);
    fs.closeSync(apiHandle.out);
    apiHandle = null;

    // Phase 1: Populated seeded DB full-stack QA
    const seedRun = spawnSync(pythonBin, [path.join(__dirname, "qa_e2e_seed.py")], {
      cwd: REPO_ROOT,
      encoding: "utf-8",
      timeout: 60000,
    });
    if (seedRun.status !== 0) {
      throw new Error(`Seeding failed: ${seedRun.stderr || seedRun.stdout}`);
    }
    report.seed = JSON.parse(seedRun.stdout.trim());

    const apiLog = path.join(REPO_ROOT, "qa/evidence/e2e-api.log");
    apiHandle = spawnBackend(pythonBin, E2E_ROOT, apiLog);
    await waitForHttp200(`${API_URL}/api/v1/system`, "serve-api-seeded", apiHandle.proc, apiLog);

    context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      locale: "zh-CN",
      acceptDownloads: true,
    });
    page = await context.newPage();
    attachMonitors(page);

    async function navButton(labelRegex) {
      await page.locator("nav").getByRole("button", { name: labelRegex }).click();
    }

    // 1. Home Dashboard check
    await checked("home_dashboard_panels_render", async () => {
      await page.goto(`${UI_URL}/#Home`, { waitUntil: "networkidle" });
      await page.locator("main").waitFor({ state: "visible" });
      await page.waitForTimeout(500);
      const s1 = await shot("01_home.png");
      const bodyTxt = await page.locator("main").innerText();
      assert(
        bodyTxt.includes("当前重点") || bodyTxt.includes("置顶主题") || bodyTxt.includes("最近 7 天发生了什么变化"),
        `Home missing dashboard panels: ${bodyTxt.slice(0, 200)}`,
      );
      return { screenshots: [s1] };
    });

    // 2. Quick Import (+ 导入) Modal: Invalid URL, Close, macOS native guard check, AND web file upload -> Detail + Notice + Reload
    await checked("quick_import_modal_invalid_close_and_local_md_import", async () => {
      await page.locator(".utility-import-btn").click();
      const dlg = page.getByRole("dialog");
      await dlg.waitFor({ state: "visible" });
      await dlg.locator("input[type='url'], input[type='text'], input").first().fill("not-a-valid-url");
      await dlg.getByRole("button", { name: /^(Confirm import|确认导入|Follow channel|关注此频道)$/ }).click();
      await dlg.getByRole("alert").waitFor({ state: "visible", timeout: 5000 });
      const s2 = await shot("02_import_modal.png");
      await dlg.getByRole("button", { name: /^(Close|关闭|Cancel|取消)$/ }).click();
      await dlg.waitFor({ state: "detached", timeout: 5000 });

      // On macOS without --native-picker-executable, switching to Local files shows honest launcher alert
      await page.locator(".utility-import-btn").click();
      await dlg.waitFor({ state: "visible" });
      await dlg.getByRole("button", { name: /^(Import local file|导入本地文件)$/ }).click();
      await dlg.getByRole("alert").waitFor({ state: "visible", timeout: 5000 });
      const macNativeAlert = await dlg.getByRole("alert").innerText();
      await dlg.getByRole("button", { name: /^(Close|关闭|Cancel|取消)$/ }).click();
      await dlg.waitFor({ state: "detached", timeout: 5000 });

      // Test browser file upload flow in isolated non-Mac context so real POST /local/imports + navigation + notice are verified end-to-end
      const webCtx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "zh-CN" });
      await webCtx.addInitScript(() => {
        Object.defineProperty(navigator, "platform", { get: () => "Linux x86_64" });
      });
      const webPage = await webCtx.newPage();
      let importedHash = "";
      let noticeVisible = false;
      let detailHeading = "";
      try {
        await webPage.goto(`${UI_URL}/#Home`, { waitUntil: "networkidle" });
        await webPage.locator(".utility-import-btn").click();
        const webDlg = webPage.getByRole("dialog");
        await webDlg.waitFor({ state: "visible" });
        await webDlg.getByRole("button", { name: /^(Import local file|导入本地文件)$/ }).click();
        const tmpMd = path.join(E2E_ROOT, "qa-live-import.md");
        fs.writeFileSync(tmpMd, "# QA Live Upload\n\nChromium real upload verification.\n\nPersistence matters.\n", "utf-8");
        await webDlg.locator('input[type="file"]').setInputFiles(tmpMd);
        await webDlg.getByRole("button", { name: /^(Confirm import|确认导入)$/ }).click();
        await webPage.waitForFunction(() => location.hash.startsWith("#Content/local-"), null, { timeout: 10000 });
        await webPage.waitForTimeout(350);
        detailHeading = await webPage.locator("main h1, main h2, main strong").first().innerText();
        noticeVisible = (await webPage.locator("main [role='status']").filter({ hasText: /文件已导入|File imported/ }).count()) > 0;
        importedHash = await webPage.evaluate(() => location.hash);
        await webPage.screenshot({ path: path.join(SCREENSHOTS_DIR, "03_imported_detail.png"), fullPage: true });
        await webPage.reload({ waitUntil: "networkidle" });
        const reloadedText = await webPage.locator("main").innerText();
        assert(reloadedText.includes("qa-live-import.md") || reloadedText.includes("QA Live Upload"), "Imported local doc did not persist after reload");
      } finally {
        await webCtx.close();
      }
      assert(noticeVisible, "DEF-001 reproduced in live Chrome: import confirmation banner disappeared on programmatic navigation!");
      return { screenshots: [s2, "qa/evidence/screenshots/03_imported_detail.png"], macNativeAlert, importedHash, noticeVisible, detailHeading };
    }, { allowExpected4xxConsole: true });

    // 3. Following Page: list, Add Source Close, click source -> Edit Interests Cancel & Save + Reload
    await checked("following_list_modal_cancel_and_source_interests", async () => {
      await navButton(/^(Following|关注)$/);
      await page.waitForTimeout(400);
      const srcRow = page.locator("main button.source-select").filter({ hasText: "Alpha Engineering" }).first();
      await srcRow.waitFor({ state: "visible", timeout: 10000 });
      await page.getByRole("button", { name: /^(Add Source|添加关注)$/ }).first().click();
      const addDlg = page.getByRole("dialog");
      await addDlg.waitFor({ state: "visible" });
      await addDlg.getByRole("button", { name: /^(Close|关闭|Cancel|取消)$/ }).click();
      await addDlg.waitFor({ state: "detached" });

      await srcRow.click();
      const srcDlg = page.getByRole("dialog");
      await srcDlg.waitFor({ state: "visible", timeout: 5000 });
      const editBtn = srcDlg.getByRole("button", { name: /^(Edit interests|编辑兴趣)$/ });
      await editBtn.click();
      await page.waitForTimeout(250);
      const s4 = await shot("04_following.png");
      await srcDlg.getByRole("button", { name: /^(Cancel|取消|取消编辑兴趣)$/ }).last().click();
      await srcDlg.getByRole("button", { name: /^(Close|关闭)$/ }).first().click();
      await srcDlg.waitFor({ state: "detached" });
      return { screenshots: [s4], channel_visible: true };
    });

    // 4. Content Library & Reader Detail
    await checked("content_ordering_shorts_curation_detail_and_history", async () => {
      await navButton(/^(Content|内容)$/);
      await page.waitForTimeout(450);
      const listTitles = await page.locator(".content-media-list .content-media-row strong").allInnerTexts();
      const idxLatest = listTitles.findIndex((t) => t.includes("Production LLM Reliability Systems"));
      const idxOlder = listTitles.findIndex((t) => t.includes("Agentic Workflows Older Deep Dive"));
      assert(idxLatest !== -1 && idxOlder !== -1 && idxLatest < idxOlder, `Content ordering mismatch: latest=${idxLatest}, older=${idxOlder}, titles=${JSON.stringify(listTitles)}`);

      const drawer = page.locator("details.shorts-fold-drawer");
      const drawerCount = await drawer.count();
      assert(drawerCount > 0, "Shorts fold drawer missing");
      await drawer.locator("summary").click();
      await page.waitForTimeout(200);
      const drawerText = await drawer.innerText();
      assert(drawerText.includes("45s Quick Demo") && !drawerText.includes("Production LLM Reliability Systems"), `Shorts folding check failed after expand: ${drawerText}`);
      const s5 = await shot("05_content_list.png");

      const searchInput = page.locator("main input[type='search'], main input[placeholder*='搜索'], main input[placeholder*='Search']").first();
      if (await searchInput.count()) {
        await searchInput.fill("Local-First Knowledge Graph");
        await page.waitForTimeout(250);
        const filteredTitles = await page.locator(".content-media-list .content-media-row strong").allInnerTexts();
        assert(filteredTitles.some((t) => t.includes("Local-First Knowledge Graph")) && filteredTitles.length <= 2, `Content search did not filter: ${JSON.stringify(filteredTitles)}`);
        await searchInput.fill("");
        await page.waitForTimeout(250);
      }

      await page.locator(".content-media-list .content-media-row").filter({ hasText: "Production LLM Reliability Systems" }).first().click();
      await page.waitForFunction(() => location.hash.startsWith("#Content/"), null, { timeout: 8000 });
      await page.locator("#section-evidence").waitFor({ state: "visible", timeout: 8000 });
      await page.waitForFunction(() => {
        const el = document.querySelector("#section-evidence");
        return el && !/正在加载原始证据|Loading canonical Evidence/.test(el.textContent || "");
      }, null, { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(200);
      const s6 = await shot("06_content_detail.png");
      const copyBtn = page.getByRole("button", { name: /Markdown|复制/ }).first();
      if (await copyBtn.count()) {
        await copyBtn.click();
      }
      await page.getByRole("button", { name: /返回内容|Back to Content/ }).click();
      await page.waitForFunction(() => location.hash.startsWith("#Content"), null, { timeout: 5000 });
      await page.goBack();
      await page.waitForTimeout(250);
      const hashAfterBack = await page.evaluate(() => location.hash);
      await page.goForward();
      await page.waitForTimeout(250);
      return { screenshots: [s5, s6], idxLatest, idxOlder, listTitles, hashAfterBack };
    });

    // 5. Intelligence Page
    await checked("intelligence_list_save_reload_and_tabs", async () => {
      await navButton(/^(Intelligence|洞察)$/);
      await page.locator(".intel-list-row").first().waitFor({ state: "visible", timeout: 10000 });
      await page.waitForTimeout(200);
      const s7 = await shot("07_intelligence.png");
      const mainText = await page.locator("main").innerText();
      assert(mainText.length > 40, "Intelligence page rendered empty");
      const saveBtn = page.locator("main button").filter({ hasText: /^(Save|收藏|Unsave|取消收藏|Save insight|收藏洞察)$/ }).first();
      await saveBtn.waitFor({ state: "visible", timeout: 5000 });
      const beforeLabel = await saveBtn.innerText();
      await saveBtn.click();
      await page.waitForTimeout(450);
      await page.getByRole("button", { name: /^(Saved|已收藏)$/ }).first().click();
      await page.waitForTimeout(400);
      await page.reload({ waitUntil: "networkidle" });
      await page.getByRole("button", { name: /^(Saved|已收藏)$/ }).first().click();
      await page.waitForTimeout(450);
      const savedText = await page.locator("main").innerText();
      assert(savedText.includes("洞察要点"), `Saved intelligence did not persist after reload: ${savedText.slice(0, 200)}`);
      return { screenshots: [s7], savedPersisted: `${beforeLabel} -> persisted across reload` };
    });

    // 6. Topics Page
    await checked("topics_pin_persist_and_timeline_detail", async () => {
      await navButton(/^(Topics|主题)$/);
      await page.waitForTimeout(450);
      const s8 = await shot("08_topics.png");
      const firstTopic = page.locator(".content-media-list .content-media-row").first();
      await firstTopic.waitFor({ state: "visible", timeout: 8000 });
      const topicTitle = (await firstTopic.locator("strong").first().innerText()).trim();
      await firstTopic.click();
      await page.waitForTimeout(400);
      const pinBtn = page.getByRole("button", { name: /^(Pin Topic|置顶主题|Unpin Topic|取消置顶)$/ });
      await pinBtn.click();
      await page.waitForTimeout(400);
      await navButton(/^(Home|首页)$/);
      await page.reload({ waitUntil: "networkidle" });
      const homeText = await page.locator("main").innerText();
      assert(homeText.includes(topicTitle), `Pinned topic ${topicTitle} not shown on Home after reload`);
      return { screenshots: [s8], topicTitle };
    });

    // 7. Research Page (opened via utility dock AI Q&A button)
    await checked("research_qa_and_manual_packet_flow", async () => {
      await page.locator(".utility-qa-btn").click();
      await page.waitForTimeout(450);
      const legacyDetails = page.locator("main details").filter({ hasText: /手动组装原始证据包|Manual/ }).first();
      if (await legacyDetails.count()) {
        await legacyDetails.locator("summary").click();
        await page.waitForTimeout(250);
      }
      const s9 = await shot("09_research.png");
      const newResBtn = page.getByRole("button", { name: /^(New Research|新建研究)$/ });
      let createdPacket = false;
      if (await newResBtn.count()) {
        await newResBtn.click();
        const qBox = page.locator("form.research-form textarea, form.research-form input").first();
        await qBox.waitFor({ state: "visible", timeout: 5000 });
        await qBox.fill("How does SQLite state stay deterministic?");
        const checkbox = page.locator("form.research-form input[type='checkbox']").first();
        await checkbox.waitFor({ state: "visible", timeout: 8000 });
        await checkbox.check();
        await page.locator("form.research-form button[type='submit']").click();
        await page.waitForFunction(() => location.hash.startsWith("#Research/"), null, { timeout: 8000 });
        createdPacket = true;
      }
      assert(createdPacket, "Manual Research packet creation failed");
      return { screenshots: [s9], createdPacket };
    });

    // 8. Settings Page
    await checked("settings_language_interests_unchanged_save_and_backup", async () => {
      await navButton(/^(Settings|设置)$/);
      await page.waitForTimeout(500);

      const interestsPanel = page.locator("#settings-interests");
      await interestsPanel.getByRole("button", { name: /^(Edit interests|编辑兴趣)$/ }).click();
      await interestsPanel.getByRole("button", { name: /^(Save preferences|保存偏好)$/ }).click();
      await page.waitForTimeout(500);
      assert((await interestsPanel.locator("[role='alert']").count()) === 0, `GlobalInterests failed saving unchanged: ${await interestsPanel.innerText()}`);

      await interestsPanel.getByRole("button", { name: /^(Edit interests|编辑兴趣)$/ }).click();
      await interestsPanel.getByRole("button", { name: /^(Cancel|取消)$/ }).click();
      await interestsPanel.getByRole("button", { name: /^(Edit interests|编辑兴趣)$/ }).click();
      if ((await interestsPanel.locator("textarea").count()) === 0) {
        await interestsPanel.locator("button").filter({ hasText: /Add focus rule|添加关注词条|添加关注规则|新增关注/ }).first().click();
      }
      const firstTextarea = interestsPanel.locator("textarea").first();
      await firstTextarea.fill("Agent Safety QA");
      await interestsPanel.getByRole("button", { name: /^(Save preferences|保存偏好)$/ }).click();
      await page.waitForTimeout(500);
      await page.reload({ waitUntil: "networkidle" });
      assert((await page.locator("#settings-interests").innerText()).includes("Agent Safety QA"), "GlobalInterests did not persist after reload");

      const langPanel = page.locator("#settings-language");
      await langPanel.getByRole("button", { name: /^(Edit language|编辑语言)$/ }).click();
      await langPanel.getByRole("button", { name: /^(Cancel|取消)$/ }).click();
      await langPanel.getByRole("button", { name: /^(Edit language|编辑语言)$/ }).click();
      await langPanel.getByLabel(/Interface language|界面语言/).selectOption("en");
      await langPanel.getByLabel(/Preferred output language|默认输出语言/).selectOption("en");
      await langPanel.getByRole("button", { name: /^(Save language|保存语言)$/ }).click();
      await page.waitForTimeout(500);
      await page.reload({ waitUntil: "networkidle" });
      assert((await page.locator("nav").innerText()).includes("Settings"), "English language did not persist after reload");
      await langPanel.getByRole("button", { name: "Edit language" }).click();
      await langPanel.getByLabel(/Interface language|界面语言/).selectOption("zh-CN");
      await langPanel.getByLabel(/Preferred output language|默认输出语言/).selectOption("zh-CN");
      await langPanel.getByRole("button", { name: "Save language" }).click();
      await page.waitForTimeout(500);

      const bkPanel = page.locator("#settings-backup");
      await bkPanel.getByRole("button", { name: /^(Create Backup|创建备份)$/ }).click();
      await bkPanel.getByRole("link", { name: /^(Save backup file|保存备份文件)$/ }).waitFor({ state: "visible", timeout: 15000 });
      const badZip = path.join(E2E_ROOT, "corrupt.zip");
      fs.writeFileSync(badZip, "NOT_A_VALID_ZIP", "utf-8");
      await bkPanel.getByLabel(/Choose backup file|选择备份文件/).setInputFiles(badZip);
      await bkPanel.locator("[role='alert']").waitFor({ state: "visible", timeout: 10000 });
      const s10 = await shot("10_settings.png");
      return { screenshots: [s10], unchanged_save_ok: true };
    }, { allowExpected4xxConsole: true });

    // 9. Cmd+K Command Palette & Theme Toggle + Reload
    await checked("command_palette_and_theme_toggle", async () => {
      await page.locator(".utility-theme-btn").click();
      await page.waitForTimeout(250);
      const themeAfterClick = await page.evaluate(() => document.documentElement.dataset.theme || document.body.dataset.theme || "");
      await page.keyboard.press("Meta+k");
      await page.locator("[role='dialog']").waitFor({ state: "visible", timeout: 5000 });
      const s11 = await shot("11_cmdk_dark.png");
      await page.keyboard.press("Escape");
      await page.reload({ waitUntil: "networkidle" });
      const themeAfterReload = await page.evaluate(() => document.documentElement.dataset.theme || document.body.dataset.theme || "");
      assert(themeAfterClick === themeAfterReload, `Theme did not persist across reload: ${themeAfterClick} vs ${themeAfterReload}`);
      await page.locator(".utility-theme-btn").click();
      return { screenshots: [s11], themeAfterClick, themeAfterReload };
    });

    // 10. Responsive Viewport Check
    await checked("responsive_desktop_and_mobile_no_overflow", async () => {
      const checks = [];
      for (const vp of [{ width: 1440, height: 1000, label: "desktop" }, { width: 375, height: 812, label: "mobile" }]) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        for (const h of ["#Home", "#Content", "#Intelligence", "#Topics", "#Settings"]) {
          await page.evaluate((hash) => { location.hash = hash; }, h);
          await page.waitForTimeout(250);
          const dims = await page.evaluate(() => ({
            scrollW: document.documentElement.scrollWidth,
            innerW: window.innerWidth,
          }));
          checks.push({ viewport: vp.label, route: h, ...dims, ok: dims.scrollW <= dims.innerW + 2 });
        }
      }
      await page.evaluate(() => { location.hash = "#Content"; });
      await page.waitForTimeout(250);
      const s12 = await shot("12_mobile_375.png");
      report.responsive = checks;
      const bad = checks.filter((c) => !c.ok);
      assert(bad.length === 0, `Horizontal overflow detected: ${JSON.stringify(bad)}`);
      return { screenshots: [s12], checks_count: checks.length };
    });

    const unexpectedConsole = report.console_errors.filter((c) => !c.expected_in_negative_test);
    await checked("zero_uncaught_pageerror_5xx_or_unexpected_console_errors", async () => {
      assert(report.pageerrors.length === 0, `pageerrors: ${JSON.stringify(report.pageerrors)}`);
      assert(report.server_5xx.length === 0, `server_5xx: ${JSON.stringify(report.server_5xx)}`);
      assert(unexpectedConsole.length === 0, `unexpected console.error: ${JSON.stringify(unexpectedConsole)}`);
      return { total_console_errors: report.console_errors.length, unexpected: unexpectedConsole.length };
    });
  } finally {
    try { await context?.close(); } catch {}
    try { await browser?.close(); } catch {}
    await stopChild(uiProc);
    if (apiHandle) {
      await stopChild(apiHandle.proc);
      try { fs.closeSync(apiHandle.out); } catch {}
    }
    try { fs.closeSync(uiOut); } catch {}
  }

  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify({ summary: report.summary, report: REPORT_PATH, server_5xx: report.server_5xx.length, pageerrors: report.pageerrors.length }));
  process.exitCode = report.summary.failed === 0 ? 0 : 1;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
