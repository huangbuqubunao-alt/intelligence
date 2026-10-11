// Capture missing canonical screenshots: Home, Topics with real data, Content detail sections.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

// Home
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
console.log("=== HOME ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1400));
await shot(page, "44-home");

// Content list (has data now)
await page.getByRole("button", { name: "内容", exact: true }).click();
await page.waitForTimeout(2500);
console.log("\n=== CONTENT LIST ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1400));
await shot(page, "45-content-list-real");

// Content detail top (title + summary + evidence)
await page.getByText("But what is a neural network?").first().click();
await page.waitForTimeout(3500);
console.log("\n=== CONTENT DETAIL ===");
const t = await body();
console.log(t.replace(/\n{3,}/g, "\n\n").slice(0, 1800));
await shot(page, "46-content-detail-full");

// scroll to transcript evidence region
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.35));
await page.waitForTimeout(800);
await shot(page, "47-content-detail-summary");

console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
