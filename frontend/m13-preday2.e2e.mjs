import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

// Run only against the disposable M13 self-test runtime, never the Owner workspace.
const baseUrl = process.env.YIA_M13_SELFTEST_URL;
const screenshotRoot = process.env.YIA_M13_SELFTEST_SCREENSHOTS;
assert.ok(baseUrl && screenshotRoot, "Set the isolated self-test URL and screenshot path");
assert.match(baseUrl, /^http:\/\/127\.0\.0\.1:519[24]\/$/);
mkdirSync(screenshotRoot, { recursive: true });

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});
const failures = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(10_000);
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) failures.push(`HTTP ${response.status()}: ${response.url()}`);
  });
  const get = async (path) => {
    const response = await page.request.get(`${baseUrl}api/v1${path}`);
    assert.equal(response.status(), 200, path);
    return response.json();
  };
  const capture = async (name) => {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name} overflow`);
    await page.screenshot({ path: `${screenshotRoot}/${name}.png`, fullPage: true });
  };

  const resume = process.env.YIA_M13_SELFTEST_RESUME === "1";
  if (!resume) {
    assert.equal((await get("/sources")).sources.length, 0, "fresh self-test workspace");
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "把关注的内容整理成可追溯的知识。" }).waitFor();
    await page.getByText("仅界面示例 · 不写入资料库 · 不调用网络或模型").count().then((count) => assert.equal(count, 0));
    await page.getByRole("button", { name: "继续" }).click();
    await page.getByText("合成示例", { exact: true }).waitFor();
    assert.equal((await get("/sources")).sources.length, 0, "synthetic sample remains UI-only");
    await page.getByRole("button", { name: "继续" }).click();
    await page.getByRole("heading", { name: "添加第一个关注。" }).waitFor();
    await capture("onboarding-zh");

    for (const [label, title] of [["关注", "关注"], ["内容", "内容"], ["洞察", "洞察"], ["主题", "主题"], ["设置", "设置"]]) {
      await page.getByRole("button", { name: label, exact: true }).click();
      await page.getByRole("heading", { name: title, exact: true, level: 1 }).waitFor();
      assert.ok((await page.locator("body").innerText()).length > 60, `${label} must not be blank`);
    }
    await page.getByLabel("界面语言").waitFor();
    assert.equal(await page.getByLabel("默认输出语言").inputValue(), "zh-CN");
    assert.equal(await page.getByLabel("来源语言").count(), 0, "source language is factual metadata");
    await capture("settings-zh-before");
    await page.getByLabel("界面语言").selectOption("en");
    await page.getByRole("heading", { name: "Settings", exact: true, level: 1 }).waitFor();
    assert.equal(await page.getByLabel("Preferred output language").inputValue(), "zh-CN", "UI language does not change output language");
    await page.getByLabel("Preferred output language").selectOption("en");
    await page.getByText("Saved locally on this Mac.").waitFor();
    assert.equal((await get("/settings")).general.output_language, "en", "output language persists to backend");
    await page.reload({ waitUntil: "networkidle" });
    await page.getByLabel("Interface language").waitFor();
    assert.equal(await page.getByLabel("Preferred output language").inputValue(), "en");
    assert.equal(await page.evaluate(() => localStorage.getItem("yia.ui-language")), "en");
    await capture("settings-en");
    await page.getByLabel("Interface language").selectOption("zh-CN");
    await page.getByLabel("默认输出语言").waitFor();
    assert.equal(await page.getByLabel("默认输出语言").inputValue(), "en", "preferences stay independent");
    await page.getByLabel("默认输出语言").selectOption("zh-CN");
    await page.getByText("已保存在这台 Mac 上。").waitFor();

    await page.getByRole("button", { name: "关注", exact: true }).click();
    await page.getByRole("button", { name: "添加关注", exact: true }).first().click();
    const form = page.getByRole("dialog", { name: "添加关注" });
    await form.getByLabel("处理方式").waitFor();
    assert.match(await form.innerText(), /从相关视频中提炼洞察/);
    assert.match(await form.innerText(), /不是每个视频都会产生洞察/);
    assert.match(await form.innerText(), /仅发现新视频/);
    await form.getByLabel("来源链接").fill("https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw");
    await form.getByLabel("处理方式").selectOption("STANDARD_INTELLIGENCE");
    await form.getByLabel("重点词").fill("puzzle");
    await form.getByLabel("初次纳入的视频数").selectOption("1");
    await form.getByLabel("每次检查上限").selectOption("1");
    await form.getByLabel("自动检查计划", { exact: true }).selectOption("MANUAL");
    await capture("add-following-zh");
    await form.getByRole("button", { name: "添加关注", exact: true }).click();
    await form.waitFor({ state: "hidden" });
  } else {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
  }
  const sources = (await get("/sources")).sources;
  assert.equal(sources.length, 1);
  assert.equal(sources[0].processing_policy, "STANDARD_INTELLIGENCE");

  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page.getByRole("button", { name: "创建备份" }).waitFor();
  await page.getByRole("button", { name: "创建备份" }).click();
  const backup = page.getByLabel("备份结果");
  await backup.waitFor();
  assert.match(await backup.innerText(), /关注\s*1/);
  const download = await backup.getByRole("link", { name: "保存备份文件" }).getAttribute("href");
  assert.ok(download?.includes("/backup-restore/backups/") && download.endsWith("/download"));
  assert.equal((await page.request.get(new URL(download, baseUrl).href)).status(), 200);
  await capture("backup-zh");

  await page.getByRole("button", { name: "关注", exact: true }).click();
  await page.locator("button.source-select").first().click();
  await page.getByRole("button", { name: "立即检查" }).waitFor();
  await page.getByRole("button", { name: "立即检查" }).click();
  await page.getByText(/检查任务已受理|来源检查未完成|无法提交来源检查/).first().waitFor({ timeout: 30_000 });
  await capture("source-check-zh");
  console.log("Isolated real-source check:", JSON.stringify((await get(`/sources/${sources[0].source_id}`)).source_runs.map(({ state, attention_reason }) => ({ state, attention_reason }))));
  console.log("Isolated videos:", (await get("/videos")).videos.length);
  console.log("Isolated output language:", (await get("/settings")).general.output_language);
  assert.deepEqual(failures, [], "no browser/server errors");
  await page.close();
  console.log("M13 pre-Day2 isolated-workspace browser flow passed; no cloud confirmation was issued.");
} finally {
  await browser.close();
}
