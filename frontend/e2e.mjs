import { chromium } from "playwright-core";

const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-first-run", "--no-default-browser-check"] });
const consoleErrors = [];
const externalRequests = [];
const baseUrl = process.env.YIA_E2E_BASE_URL ?? "http://127.0.0.1:5174/";
const frozenNav = ["Home", "Following", "Content", "Intelligence", "Topics", "Settings"];

for (const viewport of [{ width: 1440, height: 900 }, { width: 768, height: 900 }]) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(5000);
  page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("request", request => { const url = request.url(); if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url); });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home", exact: true }).waitFor();
  for (const name of frozenNav) await page.getByRole("button", { name, exact: true }).waitFor();
  for (const legacy of ["Dashboard", "Sources", "Investigations", "Videos", "Activity", "Saved", "Weekly", "Daily", "Ask", "Runs", "Jobs", "Models", "Queue", "Evidence"]) {
    if (await page.getByRole("button", { name: legacy, exact: true }).count()) throw new Error(`${legacy} returned as first-level IA`);
  }
  await page.getByText("Important Intelligence", { exact: true }).waitFor();
  await page.getByText("Analysis is paused because no approved model is currently available.", { exact: true }).waitFor();
  if (await page.getByText("MODEL_UNAVAILABLE", { exact: true }).count()) throw new Error("Internal attention reason leaked into primary UX");
  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  await page.getByText("Evidence-backed statement", { exact: true }).waitFor();
  await page.getByText("Evidence and source", { exact: true }).click();
  await page.getByText("Relation not determined", { exact: true }).waitFor();
  await page.getByText("Source excerpt unavailable for this historical Evidence. It is not reconstructed or guessed.", { exact: true }).waitFor();
  await page.getByText("Translation is not available for this Evidence yet. The original remains authoritative.", { exact: true }).waitFor();
  await page.getByText("source-ai · golden-ai-roadmap", { exact: true }).waitFor();
  await page.getByText("18s–42s", { exact: true }).waitFor();
  await page.getByText("Original transcript · Primary original", { exact: true }).waitFor();
  await page.getByText("demo-transcript-golden-ai-roadmap", { exact: true }).waitFor();
  const originalLink = page.getByRole("link", { name: "Open original at timestamp" });
  if (!((await originalLink.getAttribute("href")) ?? "").includes("t=18")) throw new Error("Evidence timestamp link is not bound to the source position");
  await page.getByText(/source-/).first().waitFor();
  await page.getByRole("button", { name: "Saved", exact: true }).click();
  await page.getByText(/no longer available as current Intelligence/).waitFor();
  if (await page.getByText("Decision logs keep roadmap changes evidence-bound.", { exact: true }).count()) throw new Error("Unavailable Saved target leaked a stale card");
  await page.getByRole("button", { name: "Weekly", exact: true }).click();
  await page.getByText(/Weekly digest/).waitFor();
  await page.getByRole("button", { name: "Topics", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "Decision-system practice" }).click();
  await page.getByText("Timeline", { exact: true }).waitFor();
  await page.getByText("Related Topics", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Content", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "How teams turn AI roadmaps into decision systems" }).click();
  await page.getByText(/decision log/i).waitFor();
  await page.getByText("Summary / Video Notes", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Back to Content", exact: true }).click();
  await page.getByRole("button", { name: "Following", exact: true }).click();
  await page.getByRole("button", { name: "Add Following", exact: true }).first().click();
  await page.getByRole("heading", { name: "Add a Following", exact: true }).waitFor();
  for (const label of ["YouTube URL", "Monitor this Following", "Automatic schedule", "Initial history", "Per-run limit", "Focus", "Ignore", "Distillation style"]) await page.getByLabel(label, { exact: true }).waitFor();
  await page.screenshot({ path: `/tmp/yia-v1-ux-source-${viewport.width}x${viewport.height}.png`, fullPage: true });
  await page.getByRole("button", { name: "Cancel", exact: true }).first().click();
  await page.getByText("Practical AI Engineering", { exact: true }).click();
  await page.getByText("Processing policy", { exact: true }).waitFor();
  await page.getByText("Schedule", { exact: true }).waitFor();
  await page.getByText(/Runs daily at 08:30/).waitFor();
  await page.getByText("Skipped", { exact: true }).waitFor();
  await page.getByText("Excluded by your ignore rules.", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Analyze this Video", exact: true }).waitFor();
  if (await page.getByText("Retry", { exact: true }).count()) throw new Error("Retry leaked into Following UI");
  await page.getByRole("button", { name: "Check Now", exact: true }).click();
  await page.getByText(/Processing is currently unavailable in this local setup/).waitFor();
  if (await page.getByText(/runtime side-effect guard/i).count()) throw new Error("Check Now leaked internal guard language");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("Preferred output language").waitFor();
  await page.getByText(/New processing batches use this language for generated output/i).waitFor();
  await page.getByLabel("Preferred output language").selectOption("en");
  await page.getByText("Saved locally on this Mac.", { exact: true }).waitFor();
  await page.getByText(/This screen cannot enable a provider/).waitFor();
  await page.getByText("Unavailable", { exact: true }).first().waitFor();
  await page.getByText("Explicit", { exact: true }).waitFor();
  await page.getByText("Derived", { exact: true }).waitFor();
  await page.getByText("Temporary", { exact: true }).waitFor();
  await page.getByText("Resource Usage", { exact: true }).waitFor();
  await page.getByText(/Token usage: Unavailable/).waitFor();
  await page.getByText(/Cost: Unavailable/).waitFor();
  await page.screenshot({ path: `/tmp/yia-task026-${viewport.width}x${viewport.height}.png`, fullPage: true });
  await page.close();
}

const stancePage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
stancePage.setDefaultTimeout(5000);
stancePage.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
stancePage.on("request", request => { const url = request.url(); if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url); });
await stancePage.route("**/api/v1/intelligence", async route => {
  const response = await route.fetch();
  const payload = await response.json();
  const available = payload.intelligence.find(item => item.status === "AVAILABLE");
  if (!available?.card?.evidence_links?.length) throw new Error("PO demo lacks a trusted Evidence link for stance rendering");
  const base = available.card.evidence_links[0];
  available.card.evidence_links = [
    ["supporting", "Trusted fixture source excerpt."],
    ["contradicting", null],
    ["conditional", null],
    [null, null],
  ].map(([stance, original_excerpt], index) => ({
    ...base,
    evidence_id: `${base.evidence_id}-stance-${index}`,
    artifact_id: `${base.artifact_id}-stance-${index}`,
    stance,
    original_excerpt,
  }));
  await route.fulfill({ response, json: payload });
});
await stancePage.goto(baseUrl, { waitUntil: "networkidle" });
await stancePage.getByRole("button", { name: "Intelligence", exact: true }).click();
await stancePage.getByText("Evidence and source", { exact: true }).click();
for (const label of ["Supporting", "Contradicting", "Conditional", "Relation not determined"]) {
  await stancePage.getByText(label, { exact: true }).waitFor();
}
await stancePage.getByText("Trusted fixture source excerpt.", { exact: true }).waitFor();
if (await stancePage.getByText("Source excerpt unavailable for this historical Evidence. It is not reconstructed or guessed.", { exact: true }).count() !== 3) throw new Error("Evidence excerpt unavailable state count is wrong");
if (await stancePage.getByText("Translation is not available for this Evidence yet. The original remains authoritative.", { exact: true }).count() !== 4) throw new Error("Evidence translation unavailable state count is wrong");
if (await stancePage.getByText("source-ai · golden-ai-roadmap", { exact: true }).count() !== 4) throw new Error("Evidence source identity count is wrong");
if (await stancePage.getByText("18s–42s", { exact: true }).count() !== 4) throw new Error("Evidence source position count is wrong");
if (await stancePage.getByText("Original transcript · Primary original", { exact: true }).count() !== 4) throw new Error("Evidence lineage and role count is wrong");
await stancePage.getByText("demo-transcript-golden-ai-roadmap-stance-0", { exact: true }).waitFor();
const stanceOriginal = stancePage.getByRole("link", { name: "Open original at timestamp" }).first();
if (!((await stanceOriginal.getAttribute("href")) ?? "").includes("t=18")) throw new Error("Stance fixture timestamp link is invalid");
await stancePage.getByRole("button", { name: "Open Content" }).first().click();
await stancePage.getByRole("heading", { name: "Content", exact: true }).waitFor();
await stancePage.getByText("How teams turn AI roadmaps into decision systems", { exact: true }).waitFor();
await stancePage.close();

await browser.close();
if (externalRequests.length) throw new Error(`External browser network requests: ${externalRequests.join(" | ")}`);
if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
console.log("Browser E2E passed: Intelligence IA, Content transcript read surface, trusted Intelligence, Saved fail-closed, Weekly V1, Topic, Following policy, and finite attention.");
