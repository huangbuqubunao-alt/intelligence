import { chromium } from "playwright-core";

const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-first-run", "--no-default-browser-check"] });
const consoleErrors = [];
const externalRequests = [];
for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 800 }]) {
  const page = await browser.newPage({ viewport });
  page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("request", request => { const url = request.url(); if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) externalRequests.push(url); });
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.getByText("PO Review Demo", { exact: true }).waitFor();
  for (const pageName of ["Dashboard", "Sources", "Videos", "Weekly", "Automation", "Activity", "Settings"]) { await page.getByRole("button", { name: pageName, exact: true }).click(); await page.getByRole("heading", { name: pageName, exact: true }).waitFor(); }
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await page.getByText("Practical AI Engineering", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Open", exact: true }).first().click();
  await page.getByText("Daily at 08:30 · Asia/Shanghai", { exact: true }).waitFor();
  await page.getByText("How teams turn AI roadmaps into decision systems", { exact: true }).click();
  await page.getByRole("button", { name: "Transcript", exact: true }).click(); await page.getByText(/decision log/).waitFor();
  await page.getByRole("button", { name: "Scoring", exact: true }).click(); await page.getByText("VERIFIED SCORING", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Note", exact: true }).click(); await page.getByText("NOTE_REF_NOT_PERSISTED", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Deep Analysis", exact: true }).click(); await page.getByText("BLOCKED", { exact: true }).waitFor();
  await page.getByRole("button", { name: "History", exact: true }).click(); await page.getByText(/METADATA processing/).first().waitFor();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Videos", exact: true }).click();
  await page.getByText("A rough scoring draft without a trusted result", { exact: true }).click(); await page.getByRole("button", { name: "Scoring", exact: true }).click();
  await page.getByText("No verified scoring result is available for this video.").waitFor();
  if (await page.getByText("VERIFIED SCORING", { exact: true }).isVisible()) throw new Error("Unverified scoring surfaced as verified");
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByText("Provider result uncertain after an interrupted request", { exact: true }).click(); await page.getByRole("button", { name: "History", exact: true }).click(); await page.getByText(/will not automatically retry/).first().waitFor(); await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Weekly", exact: true }).click(); await page.getByText("2026 W36", { exact: true }).waitFor(); await page.getByText("UNKNOWN", { exact: true }).first().waitFor(); await page.getByText(/unavailable in current authority/).first().waitFor();
  await page.getByRole("button", { name: "Automation", exact: true }).click(); await page.getByText("Daily at 08:30", { exact: true }).waitFor(); await page.getByText("Weekly · Sunday at 20:00", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Activity", exact: true }).click(); await page.getByText("AMBIGUOUS", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Settings", exact: true }).click(); await page.getByText("0/2; credential blocked", { exact: true }).waitFor();
  await page.screenshot({ path: `/tmp/yia-po-demo-${viewport.width}x${viewport.height}.png`, fullPage: true }); await page.close();
}
await browser.close();
if (externalRequests.length) throw new Error(`External browser network requests: ${externalRequests.join(" | ")}`);
if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
console.log("Browser E2E passed: PO demo routes, authority states, viewports, console, and local-only network verified.");
