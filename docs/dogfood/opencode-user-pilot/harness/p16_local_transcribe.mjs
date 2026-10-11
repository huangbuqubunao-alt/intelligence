// Verify local audio/video transcription flow via the real UI detail page.
import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });
const body = () => page.evaluate(() => document.body.innerText);
const api = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/v1/") && !r.url().includes("/native/jobs")) {
    let p = "";
    try { p = (await r.text()).slice(0, 200); } catch {}
    api.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://127.0.0.1:5588", "").slice(0, 80)}`);
  }
});

const AUDIO_ID = "local-44d59eee0a96d41ed0305fc1f01b0b3cef0d75b655ed3ae94d7bc6462cf763f8";
await page.goto(BASE + "#Content/" + AUDIO_ID, { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
console.log("=== AUDIO DETAIL (first view) ===");
console.log((await body()).replace(/\n{3,}/g, "\n\n").slice(0, 1600));
await shot(page, "36-audio-detail");

for (const w of [5000, 15000, 30000]) {
  await page.waitForTimeout(w);
  const t = await body();
  const m = /转写|transcri|字幕|Transcript|状态|已完成|处理中[\s\S]{0,400}/.exec(t);
  console.log(`\n--- after +${w}ms ---`);
  console.log((m ? m[0] : t).replace(/\n{3,}/g, "\n\n").slice(0, 600));
}
await shot(page, "37-audio-transcribed");

console.log("\n=== API CALLS ===");
console.log(api.join("\n"));
console.log("\n--- ERRORS ---");
console.log(errors.filter((e) => !e.includes("native/jobs")).join("\n") || "(none)");
await context.close();
