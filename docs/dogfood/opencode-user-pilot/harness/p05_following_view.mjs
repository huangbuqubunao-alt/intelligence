import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);

let polls = 0;
let firstPoll = 0;
let lastPoll = 0;
page.on("request", (r) => {
  if (r.url().includes("/local/native/jobs")) {
    polls += 1;
    const now = Date.now();
    if (!firstPoll) firstPoll = now;
    lastPoll = now;
  }
});

await page.goto(BASE + "#Following", { waitUntil: "networkidle" });
await page.waitForTimeout(1000);
polls = 0; firstPoll = 0; lastPoll = 0;
await page.waitForTimeout(12000);
const span = (lastPoll - firstPoll) / 1000;
console.log(`IDLE POLL: ${polls} native/jobs polls in ${span.toFixed(1)}s => ${(polls / span).toFixed(2)} req/s`);

console.log("\n=== FOLLOWING LIST ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 3000));
await shot(page, "10-following-with-channel");

console.log("\n=== FOLLOWING DETAIL (expand?) ===");
const detailButtons = await page.evaluate(() =>
  [...document.querySelectorAll("button")].map((b) => b.innerText.trim()).filter(Boolean));
console.log("buttons:", JSON.stringify(detailButtons));

console.log("\n=== RAW API: following detail ===");
const r = await page.evaluate(async () => {
  const res = await fetch("/api/v1/sources/channels", {
    method: "POST", headers: { "Content-Type": "application/json", "X-YIA-Request": "local-ui" },
    body: JSON.stringify({ canonical_url: "https://www.youtube.com/@veritasium" }),
  });
  return { status: res.status, body: (await res.text()).slice(0, 1200) };
});
console.log(JSON.stringify(r, null, 1));

console.log("\n--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();