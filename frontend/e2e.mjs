import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});
const consoleErrors = [];
const externalRequests = [];
const failedResponses = [];
const weeklyApiRequests = [];

const observeResponses = (page, name) => page.on("response", (response) => {
  if (response.status() >= 400) failedResponses.push(`${name} ${response.status()} ${response.url()}`);
});
const baseUrl = process.env.YIA_E2E_BASE_URL ?? "http://127.0.0.1:5174/";
const screenshotRoot = new URL("../.var/task-026a-audit/final/", import.meta.url).pathname;
const frozenNav = ["Home", "Following", "Content", "Intelligence", "Topics", "Settings"];
const forbiddenPrimaryTerms = [
  "TASK-",
  "CURRENT_NOT_ACTIVE",
  "FOCUS_MATCH",
  "IGNORE_RULE_MATCH",
  "UNQUALIFIED",
  "SCHEMA_INVALID",
  "PRODUCTION_ELIGIBLE",
  "AMBIGUOUS",
  "request hash",
  "reservation",
  "runtime side-effect guard",
];

mkdirSync(screenshotRoot, { recursive: true });

for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }]) {
  const page = await browser.newPage({ viewport });
  const viewportName = `${viewport.width}x${viewport.height}`;
  observeResponses(page, viewportName);
  await page.route("**/api/v1/backup-restore/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: {
          ready: false,
          reasons: ["DEMO_UNAVAILABLE"],
          message: "Backup and Restore is not configured for the offline review demo.",
          restore_pending: false,
          last_restore: null,
        },
      }),
    });
  });
  page.setDefaultTimeout(7000);
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(`${viewportName}: ${message.text()}`);
  });
  page.on("request", (request) => {
    const url = request.url();
    if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
    if (url.includes("/api/v1/weekly/v1")) weeklyApiRequests.push(url);
  });

  const capture = async (name) => {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    if (overflow) throw new Error(`${viewportName} has horizontal overflow on ${name}`);
    const headingY = await page.getByRole("heading", { level: 1 }).evaluate((node) => node.getBoundingClientRect().top);
    if (viewport.width === 768 && headingY > 220) throw new Error(`Narrow ${name} content starts too low: ${headingY}`);
    await page.screenshot({ path: `${screenshotRoot}/${viewportName}-${name}.png`, fullPage: true });
  };
  const assertPrimaryLanguage = async (screen) => {
    const visible = await page.locator("body").innerText();
    for (const term of forbiddenPrimaryTerms) {
      if (visible.toLowerCase().includes(term.toLowerCase())) {
        throw new Error(`${viewportName} ${screen} exposes internal term: ${term}`);
      }
    }
  };

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home", exact: true }).waitFor();
  for (const name of frozenNav) await page.getByRole("button", { name, exact: true }).waitFor();
  for (const legacy of ["Dashboard", "Sources", "Investigations", "Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs", "Models", "Queue", "Evidence"]) {
    if (await page.getByRole("button", { name: legacy, exact: true }).count()) throw new Error(`${legacy} returned as first-level IA`);
  }
  await page.getByText("What matters now", { exact: true }).waitFor();
  await page.getByRole("heading", { name: "Neural networks learn through layers that transform inputs into useful representations.", exact: true }).waitFor();
  if (await page.getByText("This week", { exact: true }).count()) throw new Error(`${viewportName} Home exposes the Weekly panel`);
  if (await page.getByRole("button", { name: "Open Weekly", exact: true }).count()) throw new Error(`${viewportName} Home exposes Open Weekly`);
  const intelligenceY = await page.getByText("What matters now", { exact: true }).evaluate((node) => node.getBoundingClientRect().top);
  const attentionY = await page.getByText("Needs Attention", { exact: true }).evaluate((node) => node.getBoundingClientRect().top);
  if (attentionY <= intelligenceY) throw new Error("Needs Attention dominates Dashboard hierarchy");
  await assertPrimaryLanguage("Home");
  await capture("home");

  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  if (await page.getByRole("button", { name: "Weekly", exact: true }).count()) throw new Error(`${viewportName} Intelligence exposes a Weekly segment`);
  await page.getByText("Supported statement", { exact: true }).first().waitFor();
  if (weeklyApiRequests.length) throw new Error(`${viewportName} requested the hidden Weekly API: ${weeklyApiRequests.join(", ")}`);
  await page.getByText("Attributed opinion", { exact: true }).waitFor();
  await page.getByText("Why this matters", { exact: true }).first().waitFor();
  await page.getByText("What is new", { exact: true }).first().waitFor();
  await page.getByText("Important details", { exact: true }).first().waitFor();
  await page.getByText("Evidence and source", { exact: true }).first().click();
  await page.getByRole("button", { name: "译文", exact: true }).first().click();
  await page.getByText("Relation not determined", { exact: true }).waitFor();
  await page.getByText("Translation unavailable. Original Evidence remains authoritative.", { exact: true }).first().waitFor();
  await page.getByText("3Blue1Brown", { exact: true }).first().waitFor();
  await page.getByText("But what is a neural network? | Deep learning chapter 1", { exact: true }).waitFor();
  await page.getByText("0:18–0:42", { exact: true }).first().waitFor();
  const originalLink = page.getByRole("link", { name: "Open original at timestamp", exact: true }).first();
  await originalLink.waitFor();
  if (!((await originalLink.getAttribute("href")) ?? "").includes("t=18")) throw new Error("Evidence timestamp link is not bound to its source position");
  await page.getByText("Original transcript · Primary original", { exact: true }).first().waitFor();
  await page.getByText("demo-transcript-aircAruvnKk", { exact: true }).waitFor();
  await assertPrimaryLanguage("Intelligence");
  await capture("intelligence-evidence");

  await page.getByRole("button", { name: "Saved", exact: true }).click();
  await page.getByText(/no longer available as current Intelligence/).waitFor();
  if (await page.getByText("Neural networks learn through layers", { exact: false }).count()) throw new Error("Unavailable Saved target leaked stale content");
  await assertPrimaryLanguage("Saved");
  await capture("saved");

  await page.getByRole("button", { name: "Topics", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "Decision-system practice" }).click();
  await page.getByText("Current understanding", { exact: true }).waitFor();
  await page.getByText("Sources still disagree", { exact: false }).waitFor();
  await page.getByText("Some supporting information is no longer available.", { exact: true }).waitFor();
  await assertPrimaryLanguage("Topics");
  await capture("topics");

  await page.getByRole("button", { name: "Following", exact: true }).click();
  await page.getByText("3Blue1Brown", { exact: true }).waitFor();
  if (await page.getByText("https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw", { exact: true }).count()) throw new Error("Canonical URL rendered as primary Source name");
  await page.getByRole("link", { name: "Open Source", exact: true }).first().waitFor();
  await assertPrimaryLanguage("Following");
  await capture("following");

  await page.getByRole("button", { name: "Add Source", exact: true }).first().click();
  await page.getByRole("heading", { name: "Add a Source", exact: true }).waitFor();
  for (const label of ["Source URL", "Monitor this Source", "Automatic schedule", "Initial history", "Per-run limit", "Focus", "Ignore", "Distillation style"]) {
    await page.getByLabel(label, { exact: true }).waitFor();
  }
  await capture("source-onboarding");
  await page.getByRole("button", { name: "Cancel", exact: true }).first().click();

  await page.locator("button.source-select").filter({ hasText: "3Blue1Brown" }).click();
  await page.getByText("Processing policy", { exact: true }).waitFor();
  await page.getByText(/Runs daily at 08:30/).waitFor();
  await page.getByText("Skipped", { exact: true }).waitFor();
  await page.getByText("Excluded by your ignore rules.", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Analyze this Video", exact: true }).waitFor();
  if (await page.getByText("Retry", { exact: true }).count()) throw new Error("Retry leaked into Source UI");
  await page.getByRole("button", { name: "Check Now", exact: true }).click();
  await page.getByText(/durable Source Run was accepted/).waitFor();
  await assertPrimaryLanguage("Source detail");
  await capture("source-detail");
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("Preferred output language", { exact: true }).waitFor();
  await page.getByText(/New processing batches use this language for generated output/).waitFor();
  await page.getByText(/historical records stay unchanged/).waitFor();
  await page.getByRole("heading", { name: "Scoring and Summary", exact: true }).waitFor();
  await page.getByText("Runs locally with qwen3:8b. Original Evidence remains on this Mac.", { exact: true }).waitFor();
  await page.getByRole("heading", { name: "Intelligence", exact: true }).waitFor();
  await page.getByText(/No qualified Intelligence model is currently available/).waitFor();
  await page.getByText("Deep Analysis is unavailable.", { exact: true }).waitFor();
  await page.getByText(/Kimi is not authorized for this capability/).waitFor();
  if (await page.getByText("Provider and model details", { exact: true }).count()) throw new Error("An unqualified model must not show production provider details");
  await assertPrimaryLanguage("Settings");
  await capture("settings");

  if (await page.getByRole("button", { name: "Investigations", exact: true }).count()) throw new Error("Investigations returned as first-level IA");
  await page.close();
}

const stancePage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
observeResponses(stancePage, "stance");
stancePage.setDefaultTimeout(7000);
stancePage.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`stance: ${message.text()}`);
});
stancePage.on("request", (request) => {
  const url = request.url();
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
});
await stancePage.route("**/api/v1/intelligence/*/evidence/*/translation", async (route) => {
  const evidenceId = decodeURIComponent(
    new URL(route.request().url()).pathname.split("/").at(-2) ?? "",
  );
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      evidence_id: evidenceId,
      translated_excerpt: "第二条 Evidence 在原文之外拥有单独的本地译文。",
      translated_language: "zh-CN",
      translation_target_language: "zh-CN",
      translation_status: "AVAILABLE",
    }),
  });
});
await stancePage.route("**/api/v1/intelligence", async (route) => {
  const response = await route.fetch();
  const payload = await response.json();
  const available = payload.intelligence.find((item) => item.status === "AVAILABLE");
  if (!available?.card?.evidence_links?.length) throw new Error("PO demo lacks a trusted Evidence link for stance rendering");
  const base = available.card.evidence_links[0];
  available.card.evidence_links = [
    ["supporting", "Trusted fixture source excerpt."],
    ["contradicting", "A separate English source excerpt can be translated on request."],
    ["conditional", null],
    [null, null],
  ].map(([stance, original_excerpt], index) => ({
    ...base,
    evidence_id: `${base.evidence_id}-stance-${index}`,
    artifact_id: `${base.artifact_id}-stance-${index}`,
    stance,
    original_excerpt,
    translated_excerpt: index === 0
      ? "可信的中文译文只展示同一 Evidence。"
      : null,
    translated_language: index === 0 ? "zh-CN" : null,
    translation_target_language: "zh-CN",
  }));
  await route.fulfill({ response, json: payload });
});
await stancePage.goto(baseUrl, { waitUntil: "networkidle" });
await stancePage.getByRole("button", { name: "Intelligence", exact: true }).click();
await stancePage.getByText("Evidence and source", { exact: true }).first().click();
const stanceTrace = stancePage.locator("details.evidence-trace").first();
for (const label of ["Supporting", "Contradicting", "Conditional", "Relation not determined"]) {
  await stanceTrace.getByText(label, { exact: true }).waitFor();
}
await stanceTrace.getByText("可信的中文译文只展示同一 Evidence。", { exact: true }).waitFor();
if (await stanceTrace.getByText("Trusted fixture source excerpt.", { exact: true }).count()) throw new Error("Default translated mode also rendered the original excerpt");
await stanceTrace.getByRole("button", { name: "双语", exact: true }).first().click();
await stanceTrace.getByText("Trusted fixture source excerpt.", { exact: true }).waitFor();
await stanceTrace.getByRole("button", { name: "原文", exact: true }).first().click();
await stanceTrace.getByText("Trusted fixture source excerpt.", { exact: true }).waitFor();
if (await stanceTrace.getByText("可信的中文译文只展示同一 Evidence。", { exact: true }).count()) throw new Error("Original mode rendered translated text");
await stanceTrace.locator(".evidence-trace-item").nth(1).getByRole("button", { name: "译文", exact: true }).click();
await stanceTrace.locator(".evidence-trace-item").nth(1).getByRole("button", { name: "生成译文", exact: true }).click();
await stanceTrace.getByText("第二条 Evidence 在原文之外拥有单独的本地译文。", { exact: true }).waitFor();
if (await stanceTrace.getByText("Source excerpt unavailable for this historical Evidence. It is not reconstructed or guessed.", { exact: true }).count() !== 2) throw new Error("Evidence excerpt unavailable state count is wrong");
if (await stanceTrace.getByText("Translation unavailable. Original Evidence remains authoritative.", { exact: true }).count() !== 2) throw new Error("Evidence translation unavailable state count is wrong");
if (await stanceTrace.getByText("source-ai · aircAruvnKk", { exact: true }).count() !== 1) throw new Error("Evidence source identity is wrong");
if (await stanceTrace.getByText("0:18–0:42", { exact: true }).count() !== 4) throw new Error("Evidence source position count is wrong");
if (await stanceTrace.getByText("Original transcript · Primary original", { exact: true }).count() !== 4) throw new Error("Evidence lineage and role count is wrong");
await stanceTrace.getByText("demo-transcript-aircAruvnKk-stance-0", { exact: true }).waitFor();
const stanceOriginal = stanceTrace.getByRole("link", { name: "Open original at timestamp", exact: true }).first();
if (!((await stanceOriginal.getAttribute("href")) ?? "").includes("t=18")) throw new Error("Stance fixture timestamp link is invalid");
await stanceTrace.getByRole("button", { name: "Open Content", exact: true }).first().click();
await stancePage.getByRole("heading", { name: "Content", exact: true }).waitFor();
await stancePage.getByText("But what is a neural network? | Deep learning chapter 1", { exact: true }).waitFor();
await stancePage.close();

const summaryPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
observeResponses(summaryPage, "summary");
summaryPage.setDefaultTimeout(7000);
summaryPage.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`summary: ${message.text()}`);
});
summaryPage.on("request", (request) => {
  const url = request.url();
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
});
await summaryPage.route("**/api/v1/videos/aircAruvnKk", async (route) => {
  const response = await route.fetch();
  const payload = await response.json();
  payload.note.v2 = {
    status: "AVAILABLE",
    note_identity: "browser-summary-note",
    result_identity: "browser-summary-result",
    language: "zh-CN",
    summary: "这是浏览器验收使用的当前可信摘要。",
    core_points: ["可信摘要只从 current authority 读取。"],
    timestamped_key_points: [{
      text: "可信时间点保持 Evidence 绑定。",
      start_seconds: 18,
      end_seconds: 42,
      evidence_ids: ["browser-evidence"],
    }],
    evidence_references: [{
      evidence_id: "browser-evidence",
      source: "transcript",
      excerpt: "00:18 The explanation builds intuition by following how one layer transforms the previous layer's activations.",
      start_seconds: 18,
      end_seconds: 42,
    }],
  };
  await route.fulfill({ response, json: payload });
});
await summaryPage.goto(baseUrl, { waitUntil: "networkidle" });
await summaryPage.getByRole("button", { name: "Content", exact: true }).click();
await summaryPage.locator("button.list-row").filter({ hasText: "But what is a neural network? | Deep learning chapter 1" }).click();
await summaryPage.getByText("这是浏览器验收使用的当前可信摘要。", { exact: true }).waitFor();
await summaryPage.getByText("可信摘要只从 current authority 读取。", { exact: true }).waitFor();
const summaryTimestamp = summaryPage.getByRole("link", { name: "0:18", exact: true });
if (!((await summaryTimestamp.getAttribute("href")) ?? "").includes("t=18")) throw new Error("Summary timestamp is not Evidence-bound");
await summaryPage.getByText("Evidence references", { exact: true }).click();
await summaryPage.getByText("browser-evidence", { exact: true }).waitFor();
await summaryPage.close();

const resultPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
resultPage.setDefaultTimeout(7000);
resultPage.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`result: ${message.text()}`);
});
resultPage.on("request", (request) => {
  const url = request.url();
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
});
const contentEvidenceOriginal = "OpenAI introduced GPT-4 on March 14, 2023.";
const contentEvidenceTranslation = "OpenAI 于 2023 年 3 月 14 日推出了 GPT-4。";
let contentEvidenceTranslated = false;
await resultPage.route("**/api/v1/videos/product-evidence/evidence", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      evidence: [{
        evidence_id: "browser-content-evidence",
        artifact_id: "browser-content-transcript",
        lineage_kind: "ORIGINAL_TRANSCRIPT",
        role: "PRIMARY_ORIGINAL",
        source_language: "en",
        language: "en",
        original_excerpt: contentEvidenceOriginal,
        translated_excerpt: contentEvidenceTranslated ? contentEvidenceTranslation : null,
        translated_language: contentEvidenceTranslated ? "zh-CN" : null,
        translation_target_language: "zh-CN",
        translation_status: contentEvidenceTranslated ? "AVAILABLE" : "UNAVAILABLE",
        start_ms: 12000,
        end_ms: 18000,
        created_at: "2026-09-21T00:00:00Z",
        source_url: "https://www.youtube.com/watch?v=product-evidence",
      }],
    }),
  });
});
await resultPage.route("**/api/v1/videos/product-evidence/evidence/browser-content-evidence/translation", async (route) => {
  if (route.request().method() !== "POST") throw new Error("Content translation must be explicit POST");
  contentEvidenceTranslated = true;
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      evidence_id: "browser-content-evidence",
      translated_excerpt: contentEvidenceTranslation,
      translated_language: "zh-CN",
      translation_target_language: "zh-CN",
      translation_status: "AVAILABLE",
    }),
  });
});
await resultPage.route("**/api/v1/videos/product-evidence", async (route) => {
  const response = await route.fetch();
  const payload = await response.json();
  if (payload.intelligence_result?.status !== "NOT_PROCESSED") {
    throw new Error("PO demo no longer proves the explicit NOT_PROCESSED state");
  }
  payload.intelligence_result = {
    status: "SUCCEEDED_NO_NEW_INTELLIGENCE",
    execution_id: "browser-zero-result",
    has_new_intelligence: false,
    intelligence_id: null,
    revision_id: null,
    updated_at: "2026-09-21T00:00:00Z",
  };
  await route.fulfill({ response, json: payload });
});
await resultPage.goto(baseUrl, { waitUntil: "networkidle" });
await resultPage.getByRole("button", { name: "Content", exact: true }).click();
await resultPage.locator("button.list-row").filter({ hasText: "Research evidence that changes roadmap conversations" }).click();
await resultPage.getByText("Analysis complete — no new Intelligence.", { exact: false }).waitFor();
await resultPage.getByText("Existing Intelligence is unchanged.", { exact: false }).waitFor();
await resultPage.getByText("not an Intelligence validation posture or numeric confidence score", { exact: false }).waitFor();
await resultPage.getByText(contentEvidenceOriginal, { exact: true }).waitFor();
await resultPage.getByText("Translation unavailable.", { exact: true }).waitFor();
const contentSourceTrace = resultPage.getByRole("link", { name: "Open original at timestamp", exact: true });
if (!((await contentSourceTrace.getAttribute("href")) ?? "").includes("t=12")) throw new Error("Content Evidence timestamp does not preserve source trace");
await resultPage.getByRole("button", { name: "译文", exact: true }).first().click();
await resultPage.getByRole("button", { name: "生成译文", exact: true }).click();
await resultPage.getByText(contentEvidenceTranslation, { exact: true }).waitFor();
if (await resultPage.getByText(contentEvidenceOriginal, { exact: true }).count()) throw new Error("Content translated mode also displayed the original excerpt");
await resultPage.getByRole("button", { name: "双语", exact: true }).click();
await resultPage.getByText(contentEvidenceOriginal, { exact: true }).waitFor();
await resultPage.getByText(contentEvidenceTranslation, { exact: true }).waitFor();
await resultPage.getByRole("button", { name: "原文", exact: true }).click();
await resultPage.getByText(contentEvidenceOriginal, { exact: true }).waitFor();
if (await resultPage.getByText(contentEvidenceTranslation, { exact: true }).count()) throw new Error("Content original mode displayed the translation");
await resultPage.getByRole("button", { name: "译文", exact: true }).click();
await resultPage.getByText(contentEvidenceTranslation, { exact: true }).waitFor();
const resultText = await resultPage.locator("body").innerText();
if (/\b\d+%\b/.test(resultText)) throw new Error("Zero result invented a confidence percentage");
if (/\b(low|medium|high) confidence\b/i.test(resultText)) throw new Error("Zero result invented a confidence label");
await resultPage.close();

const admittedPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
admittedPage.setDefaultTimeout(7000);
admittedPage.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(`admitted: ${message.text()}`);
});
admittedPage.on("request", (request) => {
  const url = request.url();
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
});
await admittedPage.route("**/api/v1/videos/aircAruvnKk", async (route) => {
  const response = await route.fetch();
  const payload = await response.json();
  if (payload.intelligence_result?.status !== "SUCCEEDED") {
    throw new Error("PO demo no longer proves the admitted Intelligence result");
  }
  await route.fulfill({ response, json: payload });
});
await admittedPage.goto(baseUrl, { waitUntil: "networkidle" });
await admittedPage.getByRole("button", { name: "Content", exact: true }).click();
await admittedPage.locator("button.list-row").filter({ hasText: "But what is a neural network? | Deep learning chapter 1" }).click();
await admittedPage.getByText("Analysis completed and admitted new Intelligence.", { exact: true }).waitFor();
if (await admittedPage.getByText("Analysis complete — no new Intelligence.", { exact: false }).count()) {
  throw new Error("Admitted success was rendered as a zero result");
}
await admittedPage.close();

await browser.close();
if (externalRequests.length) throw new Error(`External browser network requests: ${externalRequests.join(" | ")}`);
if (consoleErrors.length) {
  throw new Error(
    `Browser console errors: ${consoleErrors.join(" | ")}; HTTP failures: ${failedResponses.join(" | ")}`,
  );
}
console.log("Browser E2E passed at 1440×900 and 768×900: integrated IA, Content, explicit not-processed/admitted/no-new Intelligence results, Evidence 译文/双语/原文 plus explicit generation, all stance states, source trace, output language, Source policy, scoped Kimi capability, zero external requests, and zero console errors.");
