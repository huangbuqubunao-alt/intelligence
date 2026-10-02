import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

// Disposable Vite UI and synthetic HTTP responses; never attach to M13 or call a model.
const baseUrl = process.env.YIA_PHASE1B_UI_URL ?? "http://127.0.0.1:5287/";
assert.match(baseUrl, /^http:\/\/127\.0\.0\.1:\d+\/$/);
const screenshots = process.env.YIA_PHASE1B_SCREENSHOTS ?? "/tmp/v1x-phase1b-browser";
mkdirSync(screenshots, { recursive: true });
const id = "a".repeat(64);
const video = { video_id: "fixture", channel_name: "Synthetic source", title: "Phase 1B fixture", processing_status: "COMPLETE", source_url: "https://www.youtube.com/watch?v=fixture", published_at: "2026-10-01T00:00:00Z" };
const result = {
  content_id: "fixture", result_identity: "result", content_identity: "content", output_language: "en", generated_at: "2026-10-01T00:00:00Z",
  evidence_citation_status: "DURABLE_EVIDENCE_VERIFIED",
  roles: ["CORE_CONCLUSION", "KEY_EVIDENCE", "UNCERTAINTY", "RELEVANCE_TO_USER", "NEXT_QUESTION"].map((role, index) => ({ role, text: `This is claim ${index + 1} from the verified content.`, confidence: "INSUFFICIENT_EVIDENCE", evidence_ids: [id], language_validation: index === 4 ? "UNCERTAIN" : "VALID" })),
};
const evidence = { evidence_id: id, artifact_id: "artifact", lineage_kind: "EXTRACTION", role: "PRIMARY_ORIGINAL", source_language: "en", original_excerpt: "This original transcript supports the source statement.", translated_excerpt: null, translated_language: null, translation_target_language: "en", start_ms: 1000, end_ms: 2000, source_url: video.source_url };
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const errors = [];
let scenarios = 0;
try {
  for (const language of ["en", "zh-CN"]) {
    for (const width of [320, 768, 1024, 1440]) {
      for (const legacy of [false, true]) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        page.setDefaultTimeout(10000);
        page.on("pageerror", (error) => errors.push(String(error)));
        page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
        await page.addInitScript((language) => localStorage.setItem("yia.ui-language", language), language);
        await page.route("**/api/v1/**", async (route) => {
          const path = new URL(route.request().url()).pathname;
          const body = path.endsWith("/videos") ? { videos: [video] }
            : path.endsWith("/deep-analysis") ? { deep_analysis: { status: { availability: "AVAILABLE", qualified: false }, result: legacy ? { ...result, evidence_citation_status: "PENDING_DURABLE_EVIDENCE_CONVERGENCE" } : result } }
            : path.endsWith("/evidence") ? { evidence: [evidence] }
            : path.endsWith("/videos/fixture") ? { video, transcript: { status: "AVAILABLE", text: "Original transcript evidence." }, note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] }
            : {};
          await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
        });
        await page.goto(`${baseUrl}#Content`);
        await page.getByRole("button", { name: /Phase 1B fixture/ }).click();
        await page.getByText("This is claim 1 from the verified content.").waitFor();
        const links = page.getByRole("link", { name: language === "en" ? "Evidence 1" : "证据 1", exact: true });
        assert.equal(await links.count(), legacy ? 0 : 5);
        if (!legacy) {
          await links.first().click();
          assert.equal(await page.locator(`[id="content-evidence-${id}"]`).count(), 1);
          await page.getByText(language === "en" ? "Output language could not be fully verified." : "输出语言尚未完全核验。").waitFor();
        }
        assert.equal(await page.locator("nav button").count(), 6);
        if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) {
          console.log(await page.evaluate(() => [...document.querySelectorAll("body *")].filter(el => el.getBoundingClientRect().right > innerWidth).slice(-12).map(el => ({tag:el.tagName, cls:el.className, width:el.getBoundingClientRect().width, right:el.getBoundingClientRect().right, text:el.textContent.slice(0,80)}))));
        }
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width} ${language} overflow`);
        await page.screenshot({ path: `${screenshots}/${language}-${width}-${legacy ? "legacy" : "durable"}.png`, fullPage: true });
        await page.close();
        scenarios += 1;
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log(`${scenarios} browser scenarios passed; no console errors; no horizontal overflow.`);
} finally {
  await browser.close();
}
