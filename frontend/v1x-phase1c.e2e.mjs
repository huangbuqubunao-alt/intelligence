import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const base = process.env.YIA_PHASE1C_UI_URL ?? "http://127.0.0.1:5287/";
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+\/$/);
const screenshots = process.env.YIA_PHASE1C_SCREENSHOTS ?? "/tmp/v1x-phase1c-browser";
mkdirSync(screenshots, { recursive: true });
const video = { video_id: "fixture", channel_name: "Synthetic source", title: "Phase 1C fixture", processing_status: "COMPLETE", source_url: "https://www.youtube.com/watch?v=fixture" };
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
let count = 0;
const errors = [], external = [];
try {
  for (const language of ["en", "zh-CN"]) for (const width of [320, 768, 1024, 1440]) {
    for (const scenario of ["not-tested", "failed", "stale", "credential-missing", "unreachable", "local", "cloud-denied", "cloud-approved", "cloud-ambiguous", "cloud-network-failed"]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      page.setDefaultTimeout(10000);
      page.on("pageerror", error => errors.push(String(error)));
      page.on("console", message => { if (message.type() === "error" && !message.text().includes("409 (Conflict)")) errors.push(message.text()); });
      page.on("request", request => { if (!request.url().startsWith(base)) external.push(request.url()); });
      await page.addInitScript(language => localStorage.setItem("yia.ui-language", language), language);
      const cloud = scenario.startsWith("cloud-") || scenario === "credential-missing";
      const eligible = scenario.startsWith("cloud-") || scenario === "local";
      const qualified = eligible || ["credential-missing", "unreachable"].includes(scenario);
      let dispatched = 0;
      const candidate = { route_id: "one-route", provider_id: cloud ? "openai" : "ollama-local", model_id: "qualified-candidate", configured: scenario !== "credential-missing", credential_configured: scenario !== "credential-missing", reachability: scenario === "credential-missing" ? "NOT_CHECKED" : scenario === "unreachable" ? "UNREACHABLE" : "REACHABLE", contract_capable: true, qualification_status: scenario === "failed" ? "FAILED" : scenario === "stale" ? "STALE" : qualified ? "QUALIFIED" : "NOT_TESTED", production_eligible: eligible };
      await page.route("**/api/v1/**", async route => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith("/deep-analysis") && route.request().method() === "POST") {
          dispatched++;
          const body = route.request().postDataJSON();
          if (cloud) assert.deepEqual(body, { route_id: "one-route", execution_id: "one-execution", authorize_cloud: true, acknowledge_unknown_cost: true, egress_mode: "SELECTED_EVIDENCE_ONLY" });
          if (scenario === "cloud-network-failed") return route.abort("failed");
          if (scenario === "cloud-ambiguous") return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: { code: "DEEP_ANALYSIS_FAILED", message: "Do not render backend prose", details: { reason_code: "DISPATCH_AMBIGUOUS", availability: "FAILED" } } }) });
        }
        const body = path.endsWith("/videos") ? { videos: [video] }
          : path.endsWith("/deep-analysis/preflight") ? { preflight: { execution_id: "one-execution", route_id: "one-route", provider_id: "openai", model_id: "qualified-candidate", credential_configured: true, qualification_status: "QUALIFIED", data_egress_mode: "SELECTED_EVIDENCE_ONLY", cost: { state: "UNKNOWN", hard_monetary_cap: false, input_characters: 1234 } } }
          : path.endsWith("/deep-analysis") ? { deep_analysis: { status: { availability: eligible ? "NOT_REQUESTED" : qualified ? "UNAVAILABLE" : "NOT_QUALIFIED", reason_code: eligible ? "NOT_REQUESTED" : scenario === "credential-missing" ? "CREDENTIAL_MISSING" : scenario === "unreachable" ? "ROUTE_UNREACHABLE" : "NO_QUALIFIED_MODEL", qualified, production_eligible: eligible, consent_required: cloud, route_id: eligible ? "one-route" : null, routes: [candidate] }, result: null } }
          : path.endsWith("/evidence") ? { evidence: [] }
          : path.endsWith("/videos/fixture") ? { video, transcript: { status: "AVAILABLE", text: "Synthetic original transcript." }, note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] }
          : {};
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
      });
      await page.goto(`${base}#Content`);
      await page.getByRole("button", { name: /Phase 1C fixture/ }).click();
      const run = page.getByRole("button", { name: language === "en" ? "Run Deep Analysis" : "开始深度分析", exact: true });
      await run.waitFor();
      assert.equal(dispatched, 0);
      if (!eligible) assert.equal(await run.isDisabled(), true);
      if (cloud && eligible) {
        await run.click();
        const disclosure = language === "en" ? "The monetary cost is unknown. No hard spending cap is enforced." : "金额费用未知；本次执行没有强制金额上限。";
        await page.getByText(disclosure, { exact: true }).waitFor();
        assert.equal(dispatched, 0);
        const authorize = page.getByRole("button", { name: language === "en" ? "Authorize this cloud run" : "授权本次云端执行" });
        assert.equal(await authorize.isDisabled(), true);
        if (scenario === "cloud-denied") {
          await page.getByRole("button", { name: language === "en" ? "Cancel cloud run" : "取消云端执行" }).click();
          assert.equal(dispatched, 0);
        } else {
          if (width === 320 || width === 1440) await page.screenshot({ path: `${screenshots}/${language}-${width}-${scenario}-preflight.png`, fullPage: true });
          await page.getByRole("checkbox", { name: language === "en" ? "I acknowledge the unknown cost for this execution." : "我已知晓本次执行的费用未知。" }).check();
          await authorize.click();
          await authorize.waitFor({ state: "detached" });
          assert.equal(dispatched, 1);
          if (scenario !== "cloud-approved") {
            assert.equal(await run.isDisabled(), true);
            await page.getByText(language === "en" ? /The cloud request may have been processed/ : /云端请求可能已被处理/).waitFor();
          }
        }
      }
      assert.equal(await page.locator("nav button").count(), 6);
      const text = await page.locator("body").innerText();
      for (const code of ["NOT_TESTED", "SELECTED_EVIDENCE_ONLY", "UNKNOWN", "PRODUCTION_ELIGIBLE", "Do not render backend prose"]) assert.equal(text.includes(code), false, code);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${language}/${width}/${scenario} overflow`);
      await page.close(); count++;
    }
  }
  assert.deepEqual(external, []);
  // Aborted synthetic response intentionally generates a browser network diagnostic.
  assert.deepEqual(errors.filter(error => !error.includes("net::ERR_FAILED")), []);
  console.log(`${count} Phase 1C browser scenarios passed; no external requests, unexpected console errors or horizontal overflow.`);
} finally { await browser.close(); }
