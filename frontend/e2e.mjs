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

mkdirSync(screenshotRoot, { recursive: true });

for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }]) {
  const page = await browser.newPage({ viewport });
  const viewportName = `${viewport.width}x${viewport.height}`;
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
  await page.getByRole("button", { name: "Check Now", exact: true }).click();
  await page.getByText(/Check Now cannot start in this local demo/).waitFor();
  await assertPrimaryLanguage("Source detail");
  await capture("source-detail");
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByText("Video Distillation", { exact: true }).waitFor();
  await page.getByText("Available for V1 video analysis only.", { exact: true }).waitFor();
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
  await capture("settings");

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
console.log("Browser E2E passed at 1440×900 and 768×900: frozen IA, intelligence-first Dashboard, readable Evidence, Source policy, Saved fail-closed, Weekly, Topic disagreement, scoped Kimi capability, no external requests, and no console errors.");
