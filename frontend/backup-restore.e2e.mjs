import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  readlinkSync,
} from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { chromium } from "playwright-core";

const repoRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const acceptanceRoot = resolve(repoRoot, ".var/m10-real-acceptance");
const baseUrl = process.env.YIA_E2E_BASE_URL ?? "http://127.0.0.1:15174/";
const apiBase = process.env.M10_API_BASE ?? "http://127.0.0.1:18765";
const vaultRoots = [process.env.M10_VAULT_CHECK, process.env.M10_EXTERNAL_VAULT_CHECK]
  .filter(Boolean)
  .map((path) => resolve(path));
const archivePath = resolve(acceptanceRoot, "gui-backup-a.zip");
const corruptPath = resolve(acceptanceRoot, "gui-backup-corrupt.zip");
const screenshotPath = resolve(acceptanceRoot, "settings-backup-restore.png");
const chromePath =
  process.env.CHROME_BIN ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

assert(existsSync(chromePath), `Chrome executable not found: ${chromePath}`);
assert(vaultRoots.length > 0, "Set at least one read-only Vault root to verify during restore.");
assert(vaultRoots.every(existsSync), "Every configured M10 Vault root must exist.");
mkdirSync(acceptanceRoot, { recursive: true });

function hashTree(root) {
  const records = [];
  const visit = (directory, prefix = "") => {
    for (const name of readdirSync(directory).sort()) {
      const path = resolve(directory, name);
      const relative = prefix ? `${prefix}/${name}` : name;
      const info = lstatSync(path);
      if (info.isSymbolicLink()) {
        records.push([relative, "symlink", readlinkSync(path)]);
      } else if (info.isDirectory()) {
        records.push([relative, "directory"]);
        visit(path, relative);
      } else if (info.isFile()) {
        records.push([relative, "file", createHash("sha256").update(readFileSync(path)).digest("hex")]);
      } else {
        records.push([relative, "special"]);
      }
    }
  };
  visit(root);
  return createHash("sha256").update(JSON.stringify(records)).digest("hex");
}

const vaultHashesBefore = vaultRoots.map(hashTree);
const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--no-first-run", "--no-default-browser-check"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
const consoleErrors = [];
const expectedConflictConsoleErrors = [];
const pageErrors = [];
const externalRequests = [];
page.on("console", (message) => {
  if (message.type() !== "error") return;
  if (message.text().includes("409 (Conflict)")) {
    expectedConflictConsoleErrors.push(message.text());
    return;
  }
  consoleErrors.push(message.text());
});
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("request", (request) => {
  const url = new URL(request.url());
  if (!(url.hostname === "127.0.0.1" || url.hostname === "localhost")) {
    externalRequests.push(request.url());
  }
});

async function getJson(path) {
  const response = await page.request.get(new URL(path, baseUrl).toString());
  assert.equal(response.status(), 200, `GET ${path} returned ${response.status()}`);
  return response.json();
}

async function stageFile(path) {
  const stageResponse = page.waitForResponse((response) =>
    response.url().includes("/api/v1/backup-restore/restore/stage") &&
    response.request().method() === "POST",
  ).then((response) => ({
    status: response.status(),
    ok: response.ok(),
  }));
  await page.getByLabel("Choose backup file").setInputFiles(path);
  const response = await stageResponse;
  return response;
}

try {
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const initialRestoreStatus = await getJson("/api/v1/backup-restore/status");
  const previousRestoreId = initialRestoreStatus.status.last_restore?.restore_id ?? null;
  const stateADetail = await getJson("/api/v1/videos/--khbXchTeE");
  const stateASummary = stateADetail.note?.v2;
  assert.equal(stateASummary?.status, "AVAILABLE", "Real current Summary must be readable before backup.");
  assert.equal(stateASummary.language, "zh-CN");
  const summaryIdentity = {
    note_identity: stateASummary.note_identity,
    result_identity: stateASummary.result_identity,
    language: stateASummary.language,
    summary: stateASummary.summary,
    core_points: stateASummary.core_points,
    evidence_references: stateASummary.evidence_references,
  };
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByRole("heading", { name: "Backup and Restore", exact: true }).waitFor();
  await page.getByRole("status").filter({ hasText: "Core data is quiescent" }).waitFor();

  const create = page.getByRole("button", { name: "Create Backup", exact: true });
  await create.waitFor();
  assert.equal(await create.isDisabled(), false, "Create Backup must be enabled at the proven quiescent boundary.");
  await create.click();
  const backupResult = page.getByRole("article", { name: "Backup result" });
  await backupResult.waitFor();
  assert((await backupResult.innerText()).includes("DATA artifacts"), "Backup result must include a scope preview.");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Save backup file", exact: true }).click(),
  ]);
  await download.saveAs(archivePath);
  assert(readFileSync(archivePath).length > 1024, "Production Backup API returned an unexpectedly small archive.");

  const languageSelect = page.getByLabel("Preferred output language");
  const languageSave = page.waitForResponse((response) =>
    response.url().includes("/api/v1/settings/output-language") &&
    response.request().method() === "PUT",
  );
  await languageSelect.selectOption("en");
  assert((await languageSave).ok(), "State B output language change failed.");
  await page.waitForFunction(() =>
    document.querySelector('[aria-label="Preferred output language"]')?.value === "en",
  );

  const corruptScript = [
    "import sys, zipfile",
    "source, target = sys.argv[1:]",
    "with zipfile.ZipFile(source) as archive:",
    "    entries = [(item.filename, archive.read(item)) for item in archive.infolist()]",
    "found = False",
    "with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:",
    "    for name, data in entries:",
    "        if not found and name.startswith('data/') and data:",
    "            data = bytes([data[0] ^ 1]) + data[1:]",
    "            found = True",
    "        archive.writestr(name, data)",
    "if not found: raise SystemExit('backup has no DATA artifact to corrupt')",
  ].join("\n");
  const corrupt = spawnSync("uv", ["run", "python", "-c", corruptScript, archivePath, corruptPath], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  assert.equal(corrupt.status, 0, `Could not prepare the corrupt archive: ${corrupt.stderr}`);
  const corruptResponse = await stageFile(corruptPath);
  assert.equal(corruptResponse.ok, false, "A DATA hash mismatch must be rejected before live mutation.");
  await page.getByRole("alert").waitFor();
  assert.equal(await languageSelect.inputValue(), "en", "Corrupt archive inspection changed live settings.");
  assert.equal((await getJson("/api/v1/settings")).general.output_language, "en");

  const cancelledResponse = await stageFile(archivePath);
  assert.equal(cancelledResponse.status, 200, "Valid real pipeline backup did not stage.");
  const cancelledPreview = page.getByRole("article", { name: "Inspected backup preview" });
  await cancelledPreview.waitFor();
  assert((await cancelledPreview.innerText()).includes("Nothing has changed yet."));
  assert.equal(await languageSelect.inputValue(), "en", "Staging changed live state before confirmation.");
  await cancelledPreview.getByRole("button", { name: "Cancel", exact: true }).click();
  await cancelledPreview.waitFor({ state: "detached" });
  assert.equal((await getJson("/api/v1/settings")).general.output_language, "en", "Cancelling Restore changed live settings.");

  const finalStageResponse = await stageFile(archivePath);
  assert.equal(finalStageResponse.status, 200, "Real pipeline backup failed its second inspection.");
  const preview = page.getByRole("article", { name: "Inspected backup preview" });
  await preview.waitFor();
  const previewText = await preview.innerText();
  for (const expected of ["Following", "Content", "Current Summaries", "Evidence", "Topics", "DATA artifacts"]) {
    assert(previewText.includes(expected), `Restore preview omits ${expected}.`);
  }
  await preview.getByRole("button", { name: /Restore this backup/ }).click();
  const dialog = page.getByRole("dialog", { name: "Replace Intelligence core data?" });
  await dialog.waitFor();
  const confirm = dialog.getByRole("button", { name: "Confirm Restore and restart", exact: true });
  assert.equal(await confirm.isDisabled(), true, "Restore confirmation must remain disabled before the typed phrase.");
  await dialog.getByLabel("Type RESTORE to confirm").fill("RESTORE");
  assert.equal(await confirm.isDisabled(), false, "Typed confirmation did not unlock Restore.");
  await confirm.click();

  const deadline = Date.now() + 30_000;
  let restoredStatus;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiBase}/api/v1/backup-restore/status`);
      if (response.ok) {
        const body = await response.json();
        if (
          body.status?.last_restore?.state === "APPLIED" &&
          body.status.last_restore.restore_id !== previousRestoreId
        ) {
          restoredStatus = body.status;
          break;
        }
      }
    } catch {
      // The loopback app is intentionally restarting at the safe boundary.
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 200));
  }
  assert(restoredStatus, "Restore did not complete at the controlled restart boundary.");
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByRole("heading", { name: "Backup and Restore", exact: true }).waitFor();
  await page.getByText("Restore completed successfully.", { exact: true }).waitFor();
  const restoredLanguage = page.getByLabel("Preferred output language");
  await restoredLanguage.waitFor({ state: "visible" });
  assert.equal(await restoredLanguage.inputValue(), "zh-CN", "Settings GUI did not reload State A's output language.");

  const settings = await getJson("/api/v1/settings");
  assert.equal(settings.general.output_language, "zh-CN");
  assert.equal(settings.general.output_language_source, "USER_PREFERENCE");
  const topics = await getJson("/api/v1/topics");
  assert.equal(topics.topics.length, 1, "State B Topic must not survive restoring State A.");
  assert.equal(restoredStatus.ready, true, "Restored core must pass readiness validation.");
  const restoredDetail = await getJson("/api/v1/videos/--khbXchTeE");
  const restoredSummary = restoredDetail.note?.v2;
  assert.equal(restoredSummary?.status, "AVAILABLE", "Restored current Summary must be readable.");
  assert.deepEqual(
    {
      note_identity: restoredSummary.note_identity,
      result_identity: restoredSummary.result_identity,
      language: restoredSummary.language,
      summary: restoredSummary.summary,
      core_points: restoredSummary.core_points,
      evidence_references: restoredSummary.evidence_references,
    },
    summaryIdentity,
    "Restore must keep the explicit current Summary identity and verified content.",
  );

  const evidenceData = await getJson("/api/v1/videos/--khbXchTeE/evidence");
  const translatedEvidence = evidenceData.evidence.filter((item) =>
    item.translated_excerpt && item.translated_language === item.translation_target_language,
  );
  assert.equal(translatedEvidence.length, 1, "The persisted M8 translation must remain available on its Evidence.");
  const persistedTranslation = translatedEvidence[0];
  await page.getByRole("button", { name: "Content", exact: true }).click();
  await page.getByRole("button", { name: /Introducing GPT-4/ }).click();
  await page.getByText(summaryIdentity.summary, { exact: true }).waitFor();
  await page.getByText(/This is the current verified version for this Content/).waitFor();
  const evidenceCard = page.locator("article.evidence-trace-item")
    .filter({ hasText: persistedTranslation.evidence_id })
    .first();
  await evidenceCard.waitFor();
  const quotes = evidenceCard.locator("blockquote");

  await evidenceCard.getByRole("button", { name: "译文", exact: true }).click();
  assert.equal(await quotes.count(), 1, "译文 mode must show only the translated presentation.");
  assert.equal((await quotes.first().textContent())?.trim(), persistedTranslation.translated_excerpt.trim());

  await evidenceCard.getByRole("button", { name: "双语", exact: true }).click();
  const bilingualQuotes = (await quotes.allTextContents()).map((value) => value.trim());
  assert.equal(bilingualQuotes.length, 2, "双语 mode must show both original and translated Evidence.");
  assert(bilingualQuotes.includes(persistedTranslation.original_excerpt.trim()));
  assert(bilingualQuotes.includes(persistedTranslation.translated_excerpt.trim()));

  await evidenceCard.getByRole("button", { name: "原文", exact: true }).click();
  assert.deepEqual(
    (await quotes.allTextContents()).map((value) => value.trim()),
    [persistedTranslation.original_excerpt.trim()],
    "原文 mode must show the authoritative original Evidence only.",
  );

  await page.screenshot({ path: screenshotPath, fullPage: true });
  assert.deepEqual(externalRequests, [], "Settings UI made an unexpected external request.");
  assert.deepEqual(pageErrors, [], `Browser page errors: ${pageErrors.join("; ")}`);
  assert.deepEqual(consoleErrors, [], `Browser console errors: ${consoleErrors.join("; ")}`);
  assert.equal(expectedConflictConsoleErrors.length, 1, "The corrupt archive should produce one expected HTTP conflict.");
  const vaultHashesAfter = vaultRoots.map(hashTree);
  assert.deepEqual(vaultHashesAfter, vaultHashesBefore, "A configured Vault root changed during core Restore.");

  console.log("M10 real-data Playwright E2E: PASS");
  console.log(JSON.stringify({
    archiveBytes: readFileSync(archivePath).length,
    stateBRejectedCorruptArchive: true,
    stagedRestoreCancelledWithoutMutation: true,
    explicitTypedConfirmation: true,
    restartBoundaryApplied: true,
    outputLanguageRestored: settings.general.output_language,
    topicCountRestored: topics.topics.length,
    translatedEvidenceIdRestored: persistedTranslation.evidence_id,
    translationModesVerified: ["译文", "双语", "原文"],
    vaultHashesUnchanged: true,
    vaultRootsHashed: vaultRoots.length,
    corruptArchiveExpectedHttpConflict: true,
    restoreReplayCoveredByServiceTest: true,
  }));
} finally {
  await browser.close();
}
