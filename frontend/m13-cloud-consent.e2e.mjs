import assert from "node:assert/strict";
import { chromium } from "playwright-core";

// All cloud endpoints are intercepted before they reach the isolated fixture API.
const baseUrl = process.env.YIA_M13_FIXTURE_URL;
assert.equal(baseUrl, "http://127.0.0.1:5193/");
let reviews = 0;
let confirms = 0;
let offlineAdmission = false; // Simulated finite admission only; no real qualification.
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});
try {
  const page = await browser.newPage();
  page.setDefaultTimeout(30_000);
  await page.route("**/api/v1/videos/aircAruvnKk/cloud-intelligence/review", async (route) => {
    reviews += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      review: {
        execution_id: "isolated-review-1",
        verified_input_hash: "a".repeat(64),
        review_hash: "b".repeat(64),
        video_id: "aircAruvnKk",
        expires_at: new Date(Date.now() + 300_000).toISOString(),
        output_language: "zh-CN",
        source_id: "source-ai",
        provider: "offline-preview-provider",
        model: "offline-preview-model",
        evidence_ids: ["demo-evidence-aircAruvnKk"],
        cost_status: "UNKNOWN",
        readiness: { can_confirm: offlineAdmission, blockers: offlineAdmission ? [] : ["CREDENTIAL_REQUIRED", "CLOUD_SPENDING_POLICY_REQUIRED"], budget_state: offlineAdmission ? "OFFLINE_TEST_ONLY" : "CLOUD_SPENDING_POLICY_REQUIRED" },
        outgoing_data: { video_id: "aircAruvnKk", output_language: "zh-CN", evidence: [{ evidence_id: "demo-evidence-aircAruvnKk", excerpt: "仅用于离线界面验收的公开模拟证据。" }], personalization: [], source_focus_rules: [], source_ignore_rules: [], distillation_style: "BALANCED" },
        outgoing_request: { model: "offline-preview-model", max_tokens: 8192 },
      },
    }) });
  });
  await page.route("**/api/v1/videos/aircAruvnKk/cloud-intelligence/confirm", async (route) => {
    confirms += 1;
    const body = route.request().postDataJSON();
    assert.equal(body.authorize, true);
    assert.equal(body.execution_id, "isolated-review-1");
    assert.equal(body.review_hash, "b".repeat(64));
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  await page.route("**/api/v1/videos/aircAruvnKk", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const data = await response.json();
    data.video.provider = "YOUTUBE";
    data.transcript = { status: "AVAILABLE", text: "离线界面模拟原文。" };
    data.note.v2 = {
      status: "AVAILABLE", language: "zh-CN", summary: "隔离测试摘要。",
      core_points: [], timestamped_key_points: [], evidence_references: [],
    };
    data.intelligence_result = {
      status: "WAITING_MODEL", execution_id: null, has_new_intelligence: null,
      intelligence_id: null, revision_id: null, updated_at: null,
    };
    data.cloud_intelligence_available = false;
    await route.fulfill({ response, json: data });
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "内容", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "But what is a neural network?" }).click();
  await page.getByText("隔离测试摘要。").waitFor();
  await page.getByRole("button", { name: "查看云端洞察预览" }).click();
  await page.getByText(/只有本次判断所需、经过验证且范围受限的证据片段/).waitFor();
  assert.equal(reviews, 0);
  assert.equal(confirms, 0);
  await page.getByRole("button", { name: "查看云端洞察预览" }).click();
  assert.equal(confirms, 0, "closing the disclosure does not dispatch");
  await page.getByRole("button", { name: "查看云端洞察预览" }).click();
  await page.getByRole("button", { name: "准备审核本次请求" }).click();
  await page.getByRole("button", { name: "授权本次云端执行" }).waitFor();
  await page.getByText(/offline-preview-provider/).waitFor();
  assert.equal(await page.getByRole("button", { name: "授权本次云端执行" }).isDisabled(), true);
  await page.getByText("请先在设置中配置云端凭据，再确认执行。").waitFor();
  assert.equal(reviews, 1);
  assert.equal(confirms, 0, "review is a read-only preview");
  await page.reload({ waitUntil: "networkidle" });
  offlineAdmission = true;
  assert.equal(confirms, 0, "reload must not dispatch a reviewed request");
  await page.getByRole("button", { name: "内容", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "But what is a neural network?" }).click();
  await page.getByRole("button", { name: "查看云端洞察预览" }).click();
  await page.getByRole("button", { name: "准备审核本次请求" }).click();
  await page.getByRole("button", { name: "授权本次云端执行" }).click();
  assert.equal(reviews, 2);
  assert.equal(confirms, 1, "only explicit per-execution authorization dispatches");
  await page.getByRole("button", { name: "洞察", exact: true }).click();
  await page.getByText("结论", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "加入主题" }).first().click();
  await page.getByLabel("主题名称").first().fill("M13 隔离自测主题");
  await page.getByRole("button", { name: "创建主题并关联洞察" }).first().click();
  await page.getByText("已关联主题: M13 隔离自测主题").waitFor();
  await page.getByRole("button", { name: "主题", exact: true }).click();
  await page.getByRole("button", { name: /M13 隔离自测主题/ }).waitFor();
  console.log("Mocked cloud consent browser flow passed: cancel/reload zero dispatch; one explicit confirm, zero paid calls.");
} finally {
  await browser.close();
}
