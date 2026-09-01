import { chromium } from "playwright-core";

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"]
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const consoleErrors = [];
page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
for (const pageName of ["Dashboard", "Sources", "Videos", "Weekly", "Automation", "Activity", "Settings"]) {
  await page.getByRole("button", { name: pageName, exact: true }).click();
  await page.getByRole("heading", { name: pageName, exact: true }).waitFor();
}
await page.getByRole("button", { name: "Sources", exact: true }).click();
await page.getByRole("heading", { name: "Sources", exact: true }).waitFor();
await page.getByPlaceholder("Search sources").waitFor();
await page.getByRole("button", { name: "Add source", exact: true }).click();
await page.getByPlaceholder("https://www.youtube.com/...").fill("https://youtu.be/abcdefghijk");
await page.getByLabel("Schedule frequency").selectOption("DAILY");
await page.getByLabel("Schedule time").fill("08:30");
await page.getByRole("button", { name: "Save source", exact: true }).click();
await page.getByRole("button", { name: "Open", exact: true }).click();
await page.getByText("Daily at 08:30 · Asia/Shanghai").waitFor();
await page.getByLabel("Schedule frequency").selectOption("WEEKLY");
await page.getByLabel("Schedule weekday").selectOption("6");
await page.getByLabel("Schedule time").fill("20:00");
await page.getByRole("button", { name: "Save schedule", exact: true }).click();
await page.getByText("Weekly · Sunday at 20:00 · Asia/Shanghai").waitFor();
await page.getByRole("button", { name: "Close", exact: true }).click();
await page.getByRole("button", { name: "Automation", exact: true }).click();
await page.getByText("Weekly · Sunday at 20:00").waitFor();
await page.getByText("Asia/Shanghai").waitFor();
await page.getByRole("button", { name: "Videos", exact: true }).click();
await page.getByText("Verified fixture video", { exact: true }).click();
await page.getByRole("button", { name: "Scoring", exact: true }).click();
await page.getByText("Fixture evidence is verified.").waitFor();
await page.getByText("VERIFIED SCORING").waitFor();
await page.getByRole("button", { name: "Close", exact: true }).click();
await page.getByText("Unverified fixture video", { exact: true }).click();
await page.getByRole("button", { name: "Scoring", exact: true }).click();
await page.getByText("No verified scoring result is available for this video.").waitFor();
if (await page.getByText("VERIFIED SCORING", { exact: true }).isVisible()) throw new Error("Unverified scoring surfaced as verified");
await page.getByRole("button", { name: "Close", exact: true }).click();
await page.getByRole("button", { name: "Settings", exact: true }).click();
await page.getByText("A desired preference never becomes active unless the backend marks it qualified and production eligible.").waitFor();
if (consoleErrors.length) throw new Error(`Browser console errors: ${consoleErrors.join(" | ")}`);
await page.screenshot({ path: "/tmp/yia-e2e.png", fullPage: true });
await browser.close();
console.log("Browser E2E passed: routes, verified scoring, schedule controls, and blocked provider state verified.");
