import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});
const consoleErrors = [];
const externalRequests = [];
const baseUrl = process.env.YIA_E2E_BASE_URL ?? "http://127.0.0.1:5174/";
const screenshotRoot = new URL("../.var/task-026a-audit/final/", import.meta.url).pathname;
const frozenNav = ["Dashboard", "Intelligence", "Topics", "Sources", "Investigations", "Settings"];
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
const readyReadiness = {
  overall: { code: "READY", label: "Ready to check a Source", message: "All required normal Video Distillation prerequisites are available." },
  application: { code: "CONNECTED", label: "Application connected", message: "The local application service is responding." },
  video_distillation: { code: "READY_TO_START", label: "Video Distillation ready to start", message: "The normal production processing route is available." },
  model: { code: "APPROVED", label: "Video analysis model approved", message: "The approved Kimi model is limited to V1 Video Distillation." },
  credential: { code: "AVAILABLE", label: "NVIDIA credential available", message: "The server detected credential presence. Provider success is not guaranteed." },
  budget: { code: "WITHIN_LIMIT", label: "Within current usage limit", message: "The configured call limit has remaining capacity.", limit: 5, used: 0 },
  source: { code: "READY_FOR_MANUAL_CHECK", label: "Source ready for manual check", message: "This Source is enabled and configured for Video Distillation.", source_id: "source-ai" },
  deep_analysis: { code: "BLOCKED", label: "Deep Analysis unavailable", message: "This release supports normal Video Distillation only." },
};
const withReadiness = (changes) => ({ ...structuredClone(readyReadiness), ...changes });

mkdirSync(screenshotRoot, { recursive: true });

for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 768, height: 900 }]) {
  const page = await browser.newPage({ viewport });
  const viewportName = `${viewport.width}x${viewport.height}`;
  let readinessOverride = null;
  let sourceRunsOverride = null;
  await page.route(/\/api\/v1\/(?:sources\/[^/]+\/)?readiness$/, async (route) => {
    if (!readinessOverride) return route.continue();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ readiness: readinessOverride }) });
  });
  await page.route(/\/api\/v1\/sources\/[^/]+$/, async (route) => {
    if (!sourceRunsOverride || route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const body = await response.json();
    body.source_runs = sourceRunsOverride;
    await route.fulfill({ response, json: body });
  });
  page.setDefaultTimeout(7000);
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(`${viewportName}: ${message.text()}`);
  });
  page.on("request", (request) => {
    const url = request.url();
    if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url);
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
  await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
  for (const name of frozenNav) await page.getByRole("button", { name, exact: true }).waitFor();
  for (const legacy of ["Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs", "Models", "Queue", "Evidence"]) {
    if (await page.getByRole("button", { name: legacy, exact: true }).count()) throw new Error(`${legacy} returned as first-level IA`);
  }
  await page.getByText("What matters now", { exact: true }).waitFor();
  await page.getByRole("heading", { name: "Neural networks learn through layers that transform inputs into useful representations.", exact: true }).waitFor();
  const intelligenceY = await page.getByText("What matters now", { exact: true }).evaluate((node) => node.getBoundingClientRect().top);
  const attentionY = await page.getByText("Needs Attention", { exact: true }).evaluate((node) => node.getBoundingClientRect().top);
  if (attentionY <= intelligenceY) throw new Error("Needs Attention dominates Dashboard hierarchy");
  await assertPrimaryLanguage("Dashboard");
  await capture("dashboard");

  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  await page.getByText("Supported statement", { exact: true }).first().waitFor();
  await page.getByText("Attributed opinion", { exact: true }).waitFor();
  await page.getByText("Why this matters", { exact: true }).first().waitFor();
  await page.getByText("What is new", { exact: true }).first().waitFor();
  await page.getByText("Important details", { exact: true }).first().waitFor();
  await page.getByRole("heading", { name: "Evidence", exact: true }).first().waitFor();
  await page.getByText("3Blue1Brown", { exact: true }).first().waitFor();
  await page.getByText("Marques Brownlee", { exact: true }).first().waitFor();
  await page.getByText("But what is a neural network? | Deep learning chapter 1", { exact: true }).waitFor();
  await page.getByText("0:18–0:42", { exact: true }).first().waitFor();
  await page.getByRole("link", { name: "Open video at 0:18", exact: true }).first().waitFor();
  await assertPrimaryLanguage("Intelligence");
  await capture("intelligence-evidence");

  await page.getByRole("button", { name: "Saved", exact: true }).click();
  await page.getByText(/no longer available as current Intelligence/).waitFor();
  if (await page.getByText("Neural networks learn through layers", { exact: false }).count()) throw new Error("Unavailable Saved target leaked stale content");
  await assertPrimaryLanguage("Saved");
  await capture("saved");

  await page.getByRole("button", { name: "Weekly", exact: true }).click();
  await page.getByText(/What mattered ·/).waitFor();
  await page.getByText("Evidence references", { exact: true }).waitFor();
  await assertPrimaryLanguage("Weekly");
  await capture("weekly");

  await page.getByRole("button", { name: "Topics", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "Decision-system practice" }).click();
  await page.getByText("Current understanding", { exact: true }).waitFor();
  await page.getByText("Sources still disagree", { exact: false }).waitFor();
  await page.getByText("Some supporting information is no longer available.", { exact: true }).waitFor();
  await assertPrimaryLanguage("Topics");
  await capture("topics");

  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByText("3Blue1Brown", { exact: true }).waitFor();
  if (await page.getByText("https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw", { exact: true }).count()) throw new Error("Canonical URL rendered as primary Source name");
  await page.getByRole("link", { name: "Open Source", exact: true }).first().waitFor();
  await assertPrimaryLanguage("Sources");
  await capture("sources");

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
  const checkNow = page.getByRole("button", { name: "Check Now", exact: true });
  if (!(await checkNow.isDisabled())) throw new Error("Unconfigured demo exposed Check Now");
  await page.getByText("Setup required", { exact: true }).waitFor();
  await assertPrimaryLanguage("Source detail");
  await capture("source-detail");

  const editTrigger = page.getByRole("button", { name: "Edit configuration", exact: true });
  await editTrigger.click();
  const editDialog = page.getByRole("dialog", { name: "Edit Source configuration", exact: true });
  await editDialog.waitFor();
  if (await page.getByRole("dialog").count() !== 1) throw new Error("Nested Source dialog exposed more than one active modal");
  const editHeading = editDialog.getByRole("heading", { name: "Edit Source configuration", exact: true });
  if (!(await editHeading.evaluate((node) => node === document.activeElement))) throw new Error("Initial focus did not enter Source edit dialog");
  for (let index = 0; index < 18; index += 1) {
    await page.keyboard.press("Tab");
    if (!(await editDialog.evaluate((node) => node.contains(document.activeElement)))) throw new Error("Tab escaped Source edit dialog");
  }
  for (let index = 0; index < 18; index += 1) {
    await page.keyboard.press("Shift+Tab");
    if (!(await editDialog.evaluate((node) => node.contains(document.activeElement)))) throw new Error("Shift+Tab escaped Source edit dialog");
  }
  const backgroundAction = page.locator("button", { hasText: "Stop future monitoring" });
  await backgroundAction.evaluate((node) => node.focus());
  if (await backgroundAction.evaluate((node) => node === document.activeElement)) throw new Error("Background action accepted focus while modal was active");
  await capture("source-configuration-dialog");
  await page.keyboard.press("Escape");
  const editTriggerHandle = await editTrigger.elementHandle();
  await page.waitForFunction((node) => node === document.activeElement, editTriggerHandle);

  await editTrigger.focus();
  await page.keyboard.press("Enter");
  await editDialog.waitFor();
  const focusField = editDialog.getByLabel("Focus", { exact: true });
  await focusField.focus();
  await focusField.fill("neural networks, AI");
  const saveChanges = editDialog.getByRole("button", { name: "Save changes", exact: true });
  await saveChanges.focus();
  await page.keyboard.press("Enter");
  await editDialog.waitFor({ state: "detached" });

  readinessOverride = readyReadiness;
  sourceRunsOverride = [
    { run_id: "browser-active", source_id: "source-ai", state: "RUNNING", attention_reason: null, trigger: "MANUAL_CHECK_NOW", updated_at: "2026-09-14T08:00:00Z", progress: { code: "CREATING_INTELLIGENCE", label: "Creating Intelligence" }, result: { kind: "IN_PROGRESS", label: "Creating Intelligence" } },
    { run_id: "browser-complete", source_id: "source-ai", state: "COMPLETED", attention_reason: null, trigger: "MANUAL_CHECK_NOW", updated_at: "2026-09-14T08:01:00Z", progress: { code: "COMPLETED", label: "Completed" }, result: { kind: "COMPLETED_WITH_INTELLIGENCE", label: "Completed with Intelligence", intelligence_count: 2 } },
    { run_id: "browser-no-result", source_id: "source-ai", state: "COMPLETED", attention_reason: null, trigger: "MANUAL_CHECK_NOW", updated_at: "2026-09-14T08:02:00Z", progress: { code: "COMPLETED", label: "Completed" }, result: { kind: "COMPLETED_NO_IMPORTANT_RESULT", label: "Completed — no important new result", intelligence_count: 0 } },
    { run_id: "browser-ambiguous", source_id: "source-ai", state: "AMBIGUOUS", attention_reason: "AMBIGUOUS_EXTERNAL_OUTCOME", trigger: "MANUAL_CHECK_NOW", updated_at: "2026-09-14T08:03:00Z", progress: { code: "EXTERNAL_RESULT_UNCONFIRMED", label: "External result unconfirmed" }, result: { kind: "EXTERNAL_RESULT_UNCONFIRMED", label: "External result could not be confirmed" }, recovery: { kind: "AMBIGUOUS", what_happened: "The external result could not be confirmed.", why_it_matters: "Repeating the protected execution could duplicate an external action.", safe_action: { kind: "VIEW_RUN_DETAILS", label: "View run details", target: "browser-ambiguous" }, will_not: "The system will not retry, resume, continue, or repeat this execution automatically." } },
  ];
  await page.locator("button.source-select").filter({ hasText: "3Blue1Brown" }).click();
  await page.getByText("Ready to check a Source", { exact: true }).waitFor();
  await page.getByText("Creating Intelligence", { exact: true }).waitFor();
  await page.getByText("Completed with Intelligence", { exact: true }).waitFor();
  await page.getByText("Completed — no important new result", { exact: true }).waitFor();
  await page.getByText("The external result could not be confirmed.", { exact: true }).waitFor();
  if (await page.getByRole("button", { name: /Retry|Try again|Continue|Resume/i }).count()) throw new Error("AMBIGUOUS exposed a redispatch action");
  const sourceDialogText = await page.getByRole("dialog", { name: "3Blue1Brown", exact: true }).innerText();
  if (sourceDialogText.includes("%")) throw new Error("Source Run projection invented percent progress");
  await capture("source-run-orientation");
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText("Video Distillation", { exact: true }).waitFor();
  await page.getByText("Ready to check a Source", { exact: true }).waitFor();
  await page.getByText("The normal production processing route is available.", { exact: true }).first().waitFor();
  await page.getByText("Deep Analysis is unavailable.", { exact: true }).waitFor();
  await page.getByText(/Kimi is not authorized for this capability/).waitFor();
  const providerDetails = page.getByText("Provider and model details", { exact: true });
  await providerDetails.waitFor();
  if (await providerDetails.locator("xpath=..").evaluate((node) => node.hasAttribute("open"))) throw new Error("Provider details should be collapsed by default");
  await providerDetails.click();
  await page.getByText("NVIDIA NIM · moonshotai/kimi-k3", { exact: true }).waitFor();
  await page.getByText("Scope: Video Distillation only.", { exact: true }).waitFor();
  await page.getByText(/Token usage: Unavailable/).first().waitFor();
  await page.getByText(/Cost: Unavailable/).first().waitFor();
  await assertPrimaryLanguage("Settings");
  await capture("readiness-ready");

  readinessOverride = withReadiness({
    overall: { code: "SETUP_REQUIRED", label: "Setup required", message: "Review the prerequisite details before checking this Source." },
    credential: { code: "SETUP_REQUIRED", label: "NVIDIA credential setup required", message: "On your Mac, make NVIDIA_API_KEY available to the Terminal session that starts the local service, then restart it. Use your approved password manager or environment setup; never add the key to project files or enter it in this browser.", recovery: { action: "VIEW_SETUP_INSTRUCTIONS", will_not: "The product will not store the key or call the model just to check presence." } },
  });
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText("NVIDIA credential setup required", { exact: true }).waitFor();
  if (await page.getByRole("textbox", { name: /NVIDIA|API key|credential/i }).count()) throw new Error("Credential input leaked into browser UI");
  await capture("readiness-credential-missing");

  readinessOverride = withReadiness({
    overall: { code: "BUDGET_BLOCKED", label: "Review usage limit", message: "The current usage limit is blocking a Source Run." },
    budget: { code: "LIMIT_REACHED", label: "Usage limit reached", message: "Execution is blocked until you explicitly review the usage limit.", limit: 1, used: 1, recovery: { action: "VIEW_USAGE", will_not: "The product will not increase the limit or authorize spending automatically." } },
  });
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText("Review usage limit", { exact: true }).waitFor();
  await page.getByRole("button", { name: "View usage", exact: true }).waitFor();
  await capture("readiness-budget-blocked");

  readinessOverride = withReadiness({
    overall: { code: "TEMPORARILY_UNAVAILABLE", label: "Temporarily unavailable", message: "Video Distillation cannot run with the configured provider right now." },
    video_distillation: { code: "TEMPORARILY_UNAVAILABLE", label: "Video Distillation temporarily unavailable", message: "The configured production provider is not currently available.", recovery: { action: "CHECK_READINESS", will_not: "The product will not switch provider or model, enable Deep Analysis, or retry a protected execution." } },
    model: { code: "TEMPORARILY_UNAVAILABLE", label: "Video analysis model temporarily unavailable", message: "The approved Kimi model is not currently available through the configured production provider." },
  });
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText("Video Distillation temporarily unavailable", { exact: true }).waitFor();
  if (await page.getByRole("button", { name: /switch|fallback|retry/i }).count()) throw new Error("Provider unavailable exposed fallback or retry");
  await capture("readiness-provider-unavailable");

  readinessOverride = null;
  sourceRunsOverride = null;
  await page.getByRole("button", { name: "Investigations", exact: true }).click();
  await page.getByText("Investigations are not active in V1", { exact: true }).waitFor();
  await page.getByText(/Deep Analysis are not available/).waitFor();
  await assertPrimaryLanguage("Investigations");
  await capture("investigations");
  await page.close();
}

await browser.close();
if (externalRequests.length) throw new Error(`External browser network requests: ${externalRequests.join(" | ")}`);
if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
console.log("Browser E2E passed at 1440×900, 1280×800, and 768×900: RC4 readiness states, persistent Source Run orientation, accessible keyboard-only Source configuration, AMBIGUOUS no-retry, frozen trust IA, no external requests, and no console errors.");
