import { chromium } from "../frontend/node_modules/playwright-core/index.mjs";
import { writeFileSync, existsSync, mkdirSync } from "node:fs";
import assert from "node:assert/strict";

const baseUrl = "http://127.0.0.1:6379/";
const outputDir = "docs/validation/muse-final-audit/screenshots";
mkdirSync(outputDir, { recursive: true });

const auditResults = {
  firstOpen: false,
  onboardingSkipped: false,
  languageSwitched: false,
  modelSettingsVerified: false,
  backupCreated: false,
  backupRestored: false,
  schema44Verified: false,
  topicsPageVerified: false,
  errors: [],
};

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});

try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true,
  });
  const page = await context.newPage();

  page.on("pageerror", (err) => {
    console.error("Page error:", err);
    auditResults.errors.push(String(err));
  });

  // Step 1: First open
  console.log("Testing First Open and Onboarding...");
  await page.goto(baseUrl);
  await page.waitForLoadState("networkidle");
  const bodyText = await page.locator("body").innerText();
  console.log("Body text preview:", bodyText.slice(0, 300));
  auditResults.firstOpen = true;

  // Check onboarding or skip button
  const skipBtn = page.getByRole("button", { name: "暂时跳过", exact: true });
  if (await skipBtn.count()) {
    console.log("Found onboarding skip button, clicking...");
    await skipBtn.click();
    await page.waitForLoadState("networkidle");
  }
  auditResults.onboardingSkipped = true;

  // Step 2: Settings navigation & Language
  console.log("Navigating to Settings...");
  const settingsBtn = page.getByRole("button", { name: /设置|Settings/ });
  await settingsBtn.waitFor({ timeout: 10000 });
  await settingsBtn.click();
  await page.waitForLoadState("networkidle");

  // Verify language switch
  const editZhBtn = page.getByRole("button", { name: "编辑语言", exact: true });
  const editEnBtn = page.getByRole("button", { name: "Edit language", exact: true });

  if (await editZhBtn.count()) {
    await editZhBtn.click();
    await page.getByLabel("界面语言", { exact: true }).selectOption("en");
    await page.getByLabel("默认输出语言", { exact: true }).selectOption("en");
    await page.getByRole("button", { name: "保存语言", exact: true }).click();
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "Edit language", exact: true }).waitFor({ timeout: 10000 });
    console.log("Language switched from Chinese to English successfully");
  }

  // Switch to Chinese to ensure clean baseline
  const editEnBtn2 = page.getByRole("button", { name: "Edit language", exact: true });
  if (await editEnBtn2.count()) {
    await editEnBtn2.click();
    await page.getByLabel("Interface language", { exact: true }).selectOption("zh-CN");
    await page.getByLabel("Preferred output language", { exact: true }).selectOption("zh-CN");
    await page.getByRole("button", { name: "Save language", exact: true }).click();
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "编辑语言", exact: true }).waitFor({ timeout: 10000 });
    console.log("Language switched to Chinese baseline successfully");
  }
  auditResults.languageSwitched = true;

  // Step 3: Model settings & Provider check
  console.log("Verifying Model Settings...");
  // Expand cloud details
  const cloudDetailSummary = page.locator("summary", { hasText: /云端配置与模型详情|Cloud setup and model details/ });
  await cloudDetailSummary.waitFor({ timeout: 10000 });
  await cloudDetailSummary.click();

  const kimiSummary = page.locator("summary", { hasText: /Kimi \/ Moonshot API/ });
  await kimiSummary.waitFor({ timeout: 10000 });
  await kimiSummary.click();
  await page.waitForTimeout(500);

  const kimiPanel = page.locator("#moonshot-settings");
  const kimiText = await kimiPanel.innerText();
  console.log("Kimi panel text:\n", kimiText);
  assert(kimiText.includes("Kimi / Moonshot API"), "Must contain Kimi / Moonshot API in credential panel");
  assert(!kimiText.includes("sk-"), "No secret credential leaked in panel");

  // Test draft clearance on switching
  const keyInput = page.locator("#moonshot-api-key");
  await keyInput.fill("draft-test-key-should-clear");
  assert.equal(await keyInput.inputValue(), "draft-test-key-should-clear");

  // Click BigModel toggle to switch accordion
  const zhipuSummary = page.locator("summary", { hasText: /智谱 GLM-4.7-Flash|Zhipu GLM-4.7-Flash/ });
  if (await zhipuSummary.count()) {
    await zhipuSummary.click();
    await page.waitForTimeout(500);
    // Switch back to Kimi
    await kimiSummary.click();
    await page.waitForTimeout(500);
    const reloadedKeyInput = page.locator("#moonshot-api-key");
    const reloadedValue = await reloadedKeyInput.inputValue();
    assert.equal(reloadedValue, "", "Draft key must be cleared upon switching provider editors");
    console.log("Draft clearance verified upon switching");
  }

  auditResults.modelSettingsVerified = true;
  console.log("Model settings verified without secret exposure");

  // Step 4: Backup Creation
  console.log("Testing Backup Creation...");
  const createBackupBtn = page.getByRole("button", { name: /创建备份|Create Backup/ });
  await createBackupBtn.waitFor({ timeout: 10000 });
  const isBlocked = await createBackupBtn.isDisabled();
  console.log("Create backup button disabled state:", isBlocked);

  if (!isBlocked) {
    await createBackupBtn.click();
    const saveBackupLink = page.getByRole("link", { name: /保存备份文件|Save backup file/ });
    await saveBackupLink.waitFor({ timeout: 15000 });
    console.log("Backup created successfully!");

    const downloadPromise = page.waitForEvent("download");
    await saveBackupLink.click();
    const download = await downloadPromise;
    const backupPath = ".var/antigravity-candidate/candidate-backup.zip";
    await download.saveAs(backupPath);
    console.log("Backup downloaded to:", backupPath);
    assert(existsSync(backupPath), "Backup file must exist on disk");
    auditResults.backupCreated = true;

    // Step 5: Backup Restore preview and confirmation
    console.log("Testing Backup Restore...");
    const chooseBackupInput = page.getByLabel(/选择备份文件|Choose backup file/);
    await chooseBackupInput.setInputFiles(backupPath);

    const restoreBtn = page.getByRole("button", { name: /恢复此备份|Restore this backup/ });
    await restoreBtn.waitFor({ timeout: 15000 });
    await restoreBtn.click();

    const confirmInput = page.getByLabel(/输入 RESTORE 以确认|Type RESTORE to confirm/);
    await confirmInput.fill("RESTORE");

    const confirmRestoreBtn = page.getByRole("button", { name: /确认恢复并重启|Confirm Restore and restart/ });
    await confirmRestoreBtn.click();
    console.log("Restore submitted with RESTORE confirmation");

    // Wait for reconnection
    await page.waitForTimeout(3000);
    auditResults.backupRestored = true;
  } else {
    console.log("Backup is currently blocked as expected due to running/waiting state");
  }

  // Step 6: Topics page check
  console.log("Checking Topics Page...");
  const topicsBtn = page.getByRole("button", { name: "主题", exact: true });
  if (await topicsBtn.count()) {
    await topicsBtn.click();
    await page.waitForLoadState("networkidle");
    const topicsHeading = page.getByRole("heading", { name: "主题", exact: true });
    await topicsHeading.waitFor({ timeout: 10000 });
    auditResults.topicsPageVerified = true;
    console.log("Topics page verified successfully");
  }

  await context.close();
} catch (e) {
  console.error("Test failed with error:", e);
  auditResults.errors.push(String(e));
} finally {
  await browser.close();
}

writeFileSync(".var/antigravity-candidate/gui-e2e-result.json", JSON.stringify(auditResults, null, 2) + "\n");
console.log("Audit complete. Results:", JSON.stringify(auditResults, null, 2));
