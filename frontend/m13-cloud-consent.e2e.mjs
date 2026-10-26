import assert from "node:assert/strict";
import { chromium } from "playwright-core";

// All cloud endpoints are intercepted before they reach the isolated fixture API.
const baseUrl = process.env.YIA_M13_FIXTURE_URL;
assert.equal(baseUrl, "http://127.0.0.1:5193/");
let reviews = 0;
let confirms = 0;
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
        verified_input_hash: "fixture-input-hash",
        review_hash: "fixture-preview-ticket",
        source_id: "source-ai",
        provider: "moonshot",
        model: "kimi-k2.6",
        evidence_ids: ["demo-evidence-aircAruvnKk"],
        cost_status: "UNKNOWN",
      },
    }) });
  });
  await page.route("**/api/v1/videos/aircAruvnKk/cloud-intelligence/confirm", async (route) => {
    confirms += 1;
    const body = route.request().postDataJSON();
    assert.equal(body.authorize, true);
    assert.equal(body.execution_id, "isolated-review-1");
    assert.equal(body.review_hash, "fixture-preview-ticket");
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  await page.route("**/api/v1/videos/aircAruvnKk", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const data = await response.json();
    data.note.v2 = {
      status: "AVAILABLE", language: "zh-CN", summary: "隔离测试摘要。",
      core_points: [], timestamped_key_points: [], evidence_references: [],
    };
    data.intelligence_result = {
      status: "WAITING_MODEL", execution_id: null, has_new_intelligence: null,
      intelligence_id: null, revision_id: null, updated_at: null,
    };
    data.cloud_intelligence_available = true;
    await route.fulfill({ response, json: data });
  });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "内容", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "But what is a neural network?" }).click();
  await page.getByText("隔离测试摘要。").waitFor();
  await page.getByRole("button", { name: "查看云端洞察选项" }).click();
  await page.getByText(/服务商：Moonshot；模型：kimi-k2.6/).waitFor();
  await page.getByText(/只有本次判断所需、经过验证且范围受限的证据片段/).waitFor();
  await page.getByText(/Moonshot API 单独计费/).waitFor();
  assert.equal(reviews, 0);
  assert.equal(confirms, 0);
  await page.getByRole("button", { name: "查看云端洞察选项" }).click();
  assert.equal(confirms, 0, "closing the disclosure does not dispatch");
  await page.getByRole("button", { name: "查看云端洞察选项" }).click();
  await page.getByRole("button", { name: "准备审核本次请求" }).click();
  await page.getByRole("button", { name: "授权本次云端执行" }).waitFor();
  assert.equal(reviews, 1);
  assert.equal(confirms, 0, "review is a read-only preview");
  await page.reload({ waitUntil: "networkidle" });
  assert.equal(confirms, 0, "reload must not dispatch a reviewed request");
  await page.getByRole("button", { name: "内容", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: "But what is a neural network?" }).click();
  await page.getByRole("button", { name: "查看云端洞察选项" }).click();
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
