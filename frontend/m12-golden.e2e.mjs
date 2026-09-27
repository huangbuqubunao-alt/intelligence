import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { chromium } from "playwright-core";

const repoRoot = resolve(new URL("..", import.meta.url).pathname);
const mode = process.env.YIA_M12_MODE ?? "fresh";
const artifactDir = resolve(
  process.env.YIA_M12_ARTIFACT_DIR ?? join(repoRoot, ".var/m12-golden"),
);
const resultPath = join(artifactDir, mode === "restart" ? "restart-run.json" : "golden-run.json");
const baseUrl = process.env.YIA_M12_BASE_URL ?? "http://127.0.0.1:5174/";
const maxRunMs = Number(process.env.YIA_M12_MAX_RUN_MS ?? 360_000);
const sourceUrls = (process.env.YIA_M12_SOURCE_URLS ?? "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const sourceFocusTerms = process.env.YIA_M12_FOCUS_TERMS?.trim() ?? "";
const chromePath = process.env.YIA_M12_CHROME_PATH
  ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

mkdirSync(artifactDir, { recursive: true });
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(baseUrl)) {
  throw new Error("The Golden UI runner accepts only a loopback app URL.");
}
if (mode === "fresh" && !sourceUrls.length) {
  throw new Error("Set YIA_M12_SOURCE_URLS to one or more public YouTube video URLs.");
}

const externalRequests = [];
const apiMutations = [];
const apiRequests = [];
const report = {
  mode,
  base_url: baseUrl,
  started_at: new Date().toISOString(),
  status: "RUNNING",
  onboarding_steps: null,
  sample_network_or_model_writes: null,
  candidates: [],
  browser_external_requests_before_source_open: null,
  source_trace: null,
  backup_preview: null,
};
const browser = await chromium.launch({ executablePath: chromePath, headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
page.setDefaultTimeout(15_000);
context.on("request", (request) => {
  const url = new URL(request.url());
  if (!/^127\.0\.0\.1$|^localhost$/.test(url.hostname)) {
    externalRequests.push(request.url());
  }
  if (url.pathname.startsWith("/api/v1/")) {
    apiRequests.push({ method: request.method(), path: url.pathname });
  }
  if (
    url.pathname.startsWith("/api/v1/")
    && ["POST", "PUT", "PATCH", "DELETE"].includes(request.method())
  ) {
    apiMutations.push({ method: request.method(), path: url.pathname });
  }
});

const capture = async (name) => {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  assert.equal(overflow, false, `${page.viewportSize().width}px has horizontal overflow on ${name}`);
  await page.screenshot({ path: join(artifactDir, `${name}.png`), fullPage: true });
};

const videoIdFromUrl = (value) => {
  const url = new URL(value);
  if (url.hostname === "youtu.be") return url.pathname.split("/").filter(Boolean)[0] ?? "";
  const watched = url.searchParams.get("v");
  if (watched) return watched;
  return url.pathname.match(/^\/(?:shorts|live)\/([^/]+)/)?.[1] ?? "";
};

if (sourceUrls.length > 3) {
  throw new Error("The Golden runner accepts at most three distinct real source candidates.");
}
const selectedVideoIds = sourceUrls.map(videoIdFromUrl);
if (selectedVideoIds.some((videoId) => !videoId) || new Set(selectedVideoIds).size !== selectedVideoIds.length) {
  throw new Error("Golden source candidates must be distinct public YouTube video URLs.");
}

const addSourceThroughUi = async (sourceUrl) => {
  const videoId = videoIdFromUrl(sourceUrl);
  const sourceListResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" && url.pathname === "/api/v1/sources";
  });
  await page.getByRole("button", { name: "Following", exact: true }).click();
  const sourceListResponse = await sourceListResponsePromise;
  assert.equal(sourceListResponse.status(), 200);
  const sourceList = await sourceListResponse.json();
  const existingRecord = sourceList.sources?.find((source) => source.canonical_url === sourceUrl);
  const existingSource = existingRecord !== undefined;
  const sourceLabel = existingRecord?.friendly_name || existingRecord?.display_name || videoId;
  let sourceButton = page.locator("button.source-select").filter({ hasText: sourceLabel }).first();
  if (existingSource) {
    await sourceButton.waitFor();
    const existingRunId = process.env.YIA_M12_EXISTING_SOURCE_RUN_ID;
    if (existingRunId) {
      const detailResponsePromise = page.waitForResponse((response) => {
        const url = new URL(response.url());
        return response.request().method() === "GET"
          && /^\/api\/v1\/sources\/[^/]+$/.test(url.pathname);
      });
      // Re-selecting the source to obtain the current durable state is a normal UI read.
      await sourceButton.click();
      const detailResponse = await detailResponsePromise;
      assert.equal(detailResponse.status(), 200);
      const detail = await detailResponse.json();
      const attachedRun = detail.source_runs?.find((run) => run.run_id === existingRunId);
      assert.ok(attachedRun, "The task-owned Source Run must still appear in the UI source details.");
      report.source_run_submission = {
        run_id: attachedRun.run_id,
        state_at_acceptance: attachedRun.state,
        existing_following_reused: true,
        attached_to_previously_accepted_run: true,
      };
      return { sourceRunId: attachedRun.run_id };
    }
    await sourceButton.click();
    await page.getByRole("heading", { name: sourceLabel, exact: true }).waitFor();
    if (sourceFocusTerms) {
      await page.getByRole("button", { name: "Edit configuration", exact: true }).click();
      await page.getByRole("heading", { name: "Edit Source configuration", exact: true }).waitFor();
      await page.getByLabel("Focus", { exact: true }).fill(sourceFocusTerms);
      await page.getByRole("button", { name: "Save changes", exact: true }).click();
      await page.getByRole("heading", { name: "Edit Source configuration", exact: true })
        .waitFor({ state: "detached" });
      await page.getByRole("heading", { name: sourceLabel, exact: true })
        .waitFor({ state: "detached" });
      await sourceButton.click();
      await page.getByRole("heading", { name: sourceLabel, exact: true }).waitFor();
      const policyPanel = page.locator(".panel").filter({ hasText: "Focus:" }).last();
      assert.ok(
        (await policyPanel.innerText()).includes(`Focus: ${sourceFocusTerms}.`),
        "The Following must display the Focus rule saved through its UI.",
      );
    }
  } else {
    await page.getByRole("button", { name: "Add Source", exact: true }).last().click();
    await page.getByRole("heading", { name: "Add a Source", exact: true }).waitFor();
    await page.getByLabel("Source URL", { exact: true }).fill(sourceUrl);
    await page.getByLabel("Processing level", { exact: true })
      .selectOption("STANDARD_INTELLIGENCE");
    await page.getByLabel("Initial history", { exact: true }).selectOption("1");
    await page.getByLabel("Per-run limit", { exact: true }).selectOption("1");
    await page.getByLabel("Automatic schedule", { exact: true }).selectOption("MANUAL");
    if (sourceFocusTerms) {
      await page.getByLabel("Focus", { exact: true }).fill(sourceFocusTerms);
    }
    const refreshedSourceListPromise = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return response.request().method() === "GET" && url.pathname === "/api/v1/sources";
    });
    await page.getByRole("button", { name: "Add Source", exact: true }).last().click();
    await page.getByRole("heading", { name: "Add a Source", exact: true })
      .waitFor({ state: "detached" });
    const refreshedSourceListResponse = await refreshedSourceListPromise;
    assert.equal(refreshedSourceListResponse.status(), 200);
    const refreshedSourceList = await refreshedSourceListResponse.json();
    const createdSource = refreshedSourceList.sources?.find(
      (source) => source.canonical_url === sourceUrl,
    );
    assert.ok(createdSource, "The Following just added through the UI must appear in its refreshed list.");
    const createdSourceLabel = createdSource.friendly_name
      || createdSource.display_name
      || videoId;
    sourceButton = page.locator("button.source-select")
      .filter({ hasText: createdSourceLabel })
      .first();
    await sourceButton.waitFor();
    await sourceButton.click();
  }

  const submittedRunResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "POST" && url.pathname.endsWith("/check");
  });
  await page.getByRole("button", { name: "Check Now", exact: true }).click();
  await page.getByText(
    "Your durable Source Run was accepted. Progress and any required attention appear below.",
    { exact: true },
  ).waitFor();
  const response = await submittedRunResponse;
  assert.equal(response.status(), 202, "The normal UI action must durably accept a Source Run.");
  const body = await response.json();
  assert.ok(body.source_run?.run_id, "The UI must return the durable Source Run identity.");
  report.source_run_submission = {
    run_id: body.source_run.run_id,
    state_at_acceptance: body.source_run.state,
    existing_following_reused: existingSource,
    source_focus_terms: sourceFocusTerms || null,
  };

  return { sourceRunId: body.source_run.run_id };
};

const waitForVisibleRunOutcome = async () => {
  const statusPanel = page.locator(".panel").filter({ hasText: "Source Run status" }).last();
  const deadline = Date.now() + maxRunMs;
  const progressStates = new Set();
  let text = "";
  while (Date.now() < deadline) {
    text = await statusPanel.innerText().catch(() => "");
    const waitingForDecision = /waiting for a clear decision/i.test(text);
    const ambiguousOutcome = /external result could not be confirmed|ambiguous external outcome/i.test(text);
    const active = !waitingForDecision && /queued|waiting|running|partial|processing/i.test(text);
    const terminal = waitingForDecision
      || ambiguousOutcome
      || /completed|needs attention|paused|failed|succeeded/i.test(text);
    if (active) {
      if (/running/i.test(text)) progressStates.add("running");
      else if (/partial/i.test(text)) progressStates.add("partial");
      else progressStates.add("waiting");
    }
    if (terminal && !active) return { text, progress_states: [...progressStates] };
    await page.waitForTimeout(1000);
  }
  throw new Error(`The Source Run did not reach a visible terminal state within ${maxRunMs}ms: ${text}`);
};

const inspectContentThroughUi = async (videoTitle) => {
  const sourceDetail = page.getByRole("dialog").filter({ hasText: "Recent videos" }).last();
  if (await sourceDetail.count()) {
    await sourceDetail.getByRole("button", { name: "Close", exact: true }).click();
    await sourceDetail.waitFor({ state: "detached" });
  }
  await page.getByRole("button", { name: "Content", exact: true }).click();
  const row = page.locator("button.list-row").filter({ hasText: videoTitle }).last();
  await row.waitFor();
  await row.click();

  const transcript = page.locator(".transcript-copy");
  const transcriptFailure = page.getByText(
    "Transcript processing ended without a canonical transcript.",
    { exact: true },
  );
  const transcriptState = await Promise.any([
    transcript.waitFor({ state: "visible", timeout: 45_000 }).then(() => "AVAILABLE"),
    transcriptFailure.waitFor({ state: "visible", timeout: 45_000 }).then(() => "FAILED"),
  ]).catch(() => null);
  assert.ok(transcriptState, "Content details must show a canonical transcript or an explicit transcript failure.");
  if (transcriptState === "FAILED") {
    assert.equal(
      await transcriptFailure.count(),
      1,
      "Content without a transcript must show an explicit truthful failure state.",
    );
    const resultPanel = page.locator(".panel").filter({ hasText: "Intelligence result" }).last();
    return {
      transcript_status: "FAILED",
      transcript_chars: 0,
      summary_chars: 0,
      evidence_id: null,
      excerpt_chars: 0,
      source_position: "Unavailable",
      intelligence_result_text: await resultPanel.innerText(),
    };
  }
  const transcriptText = (await transcript.innerText()).trim();
  assert.ok(transcriptText.length > 0, "The UI must show the real canonical transcript.");

  const summary = page.locator(".summary-note");
  const summaryUnavailable = page.getByText(
    "Summary / Video Notes are not available for this Content yet. No summary is fabricated from missing output.",
    { exact: true },
  );
  const summaryState = await Promise.any([
    summary.waitFor({ state: "visible", timeout: 45_000 }).then(() => "AVAILABLE"),
    summaryUnavailable.waitFor({ state: "visible", timeout: 45_000 }).then(() => "UNAVAILABLE"),
  ]).catch(() => null);
  assert.ok(summaryState, "Content details must show Summary / Video Notes or an explicit unavailable state.");
  if (summaryState === "UNAVAILABLE") {
    const resultPanel = page.locator(".panel").filter({ hasText: "Intelligence result" }).last();
    return {
      transcript_status: "AVAILABLE",
      transcript_chars: transcriptText.length,
      summary_status: "UNAVAILABLE",
      summary_chars: 0,
      evidence_id: null,
      excerpt_chars: 0,
      source_position: "Unavailable",
      intelligence_result_text: await resultPanel.innerText(),
    };
  }
  const summaryText = (await summary.innerText()).trim();
  assert.ok(summaryText.length > 0, "The UI must show the persisted Summary / Video Notes.");

  const evidencePanel = page.locator(".panel").filter({ hasText: "Evidence · source transcript" }).last();
  const evidenceRows = evidencePanel.locator("article.evidence-trace-item");
  const evidenceUnavailable = evidencePanel.getByText(
    "No available, verified canonical transcript Evidence is recorded for this Content.",
    { exact: true },
  );
  const evidenceState = await Promise.any([
    evidenceRows.first().waitFor({ state: "visible", timeout: 45_000 }).then(() => "AVAILABLE"),
    evidenceUnavailable.waitFor({ state: "visible", timeout: 45_000 }).then(() => "UNAVAILABLE"),
  ]).catch(() => null);
  assert.ok(evidenceState, "Content details must show verified Evidence or explain why none is available.");
  if (evidenceState === "UNAVAILABLE") {
    const resultPanel = page.locator(".panel").filter({ hasText: "Intelligence result" }).last();
    return {
      transcript_status: "AVAILABLE",
      transcript_chars: transcriptText.length,
      summary_status: "AVAILABLE",
      summary_chars: summaryText.length,
      evidence_status: "UNAVAILABLE",
      evidence_id: null,
      excerpt_chars: 0,
      source_position: "Unavailable",
      intelligence_result_text: await resultPanel.innerText(),
    };
  }
  const excerpt = (await evidenceRows.first().locator("blockquote").first().innerText()).trim();
  assert.ok(excerpt.length > 0, "The UI must show an original transcript-backed Evidence excerpt.");
  const evidenceId = await evidenceRows.first().locator(".reading-meta strong").innerText();
  const evidencePosition = await evidenceRows.first().getByText("Source position", { exact: true }).locator("xpath=..")
    .innerText();
  const resultPanel = page.locator(".panel").filter({ hasText: "Intelligence result" }).last();
  const resultText = await resultPanel.innerText();

    return {
      transcript_status: "AVAILABLE",
      transcript_chars: transcriptText.length,
      summary_status: "AVAILABLE",
      summary_chars: summaryText.length,
      evidence_status: "AVAILABLE",
      evidence_id: evidenceId,
    excerpt_chars: excerpt.length,
    source_position: evidencePosition,
    intelligence_result_text: resultText,
  };
};

const generateTranslationThroughUi = async (videoTitle, expectedEvidenceId) => {
  await page.getByRole("button", { name: "Content", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: videoTitle }).last().click();
  const evidence = page.locator(".panel")
    .filter({ hasText: "Evidence · source transcript" }).last()
    .locator("article.evidence-trace-item").first();
  await evidence.waitFor();
  const evidenceId = await evidence.locator(".reading-meta strong").innerText();
  assert.equal(evidenceId, expectedEvidenceId);
  await evidence.getByRole("button", { name: "原文", exact: true }).click();
  const original = (await evidence.locator("blockquote").first().innerText()).trim();
  await evidence.getByRole("button", { name: "译文", exact: true }).click();

  const translatedText = async () => {
    const quotes = await evidence.locator("blockquote").allInnerTexts();
    return quotes.map((value) => value.trim()).find((value) => value && value !== original) ?? null;
  };
  let translation = await translatedText();
  if (!translation && await evidence.getByRole("button", { name: "生成译文", exact: true }).count()) {
    await evidence.getByRole("button", { name: "生成译文", exact: true }).click();
    const deadline = Date.now() + maxRunMs;
    while (Date.now() < deadline) {
      translation = await translatedText();
      if (translation) break;
      if (await evidence.getByRole("alert").count()) break;
      await page.waitForTimeout(500);
    }
  }
  if (translation) {
    await evidence.getByRole("button", { name: "双语", exact: true }).click();
    const bilingual = await evidence.locator("blockquote").allInnerTexts();
    assert.ok(bilingual.some((value) => value.trim() === original));
    assert.ok(bilingual.some((value) => value.trim() === translation));
    await evidence.getByRole("button", { name: "原文", exact: true }).click();
    assert.equal((await evidence.locator("blockquote").first().innerText()).trim(), original);
    return { status: "AVAILABLE", text: translation, original_chars: original.length };
  }

  await evidence.getByRole("button", { name: "原文", exact: true }).click();
  assert.equal((await evidence.locator("blockquote").first().innerText()).trim(), original);
  return { status: "UNAVAILABLE", text: null, original_chars: original.length };
};

const locateIntelligenceCard = async () => {
  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  const card = page.locator("article.intelligence-card").first();
  const empty = page.getByText("No verified Intelligence yet.", { exact: true });
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (await card.count()) return card;
    if (await empty.count()) return null;
    await page.waitForTimeout(250);
  }
  throw new Error("The Intelligence page did not resolve to a visible card or empty state.");
};

const authorizeOneCloudExecutionThroughUi = async (videoTitle) => {
  await page.getByRole("button", { name: "Content", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: videoTitle }).last().click();
  await page.getByRole("button", { name: "Review high-quality Intelligence" }).click();
  await page.getByText("Provider: Moonshot · Model: kimi-k2.6 (thinking disabled).", { exact: true }).waitFor();
  await page.getByText(/Cost for this execution: UNKNOWN before the response/).waitFor();
  const reviewResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname.endsWith("/cloud-intelligence/review"),
  );
  await page.getByRole("button", { name: "Prepare one request for review" }).click();
  const reviewed = await reviewResponse;
  assert.equal(reviewed.status(), 201);
  const review = (await reviewed.json()).review;
  assert.equal(review.provider, "moonshot");
  assert.equal(review.model, "kimi-k2.6");
  assert.ok(review.evidence_ids.length > 0, "The UI review must bind verified Evidence.");
  assert.equal(review.cost_status, "UNKNOWN");
  await page.getByText(`Evidence items: ${review.evidence_ids.length}.`, { exact: false }).waitFor();
  const confirmResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname.endsWith("/cloud-intelligence/confirm"),
    { timeout: 330_000 },
  );
  await page.getByRole("button", { name: "Authorize this one cloud execution" }).click();
  const confirmed = await confirmResponse;
  assert.equal(confirmed.status(), 202);
  const result = await confirmed.json();
  assert.equal(result.execution.execution_id, review.execution_id);
  assert.equal(result.execution.invocation_count, 1);
  report.cloud_execution = {
    execution_id: result.execution.execution_id,
    authorization_id: result.authorization_id,
    provider: review.provider,
    model: review.model,
    evidence_count: review.evidence_ids.length,
    status: result.execution.status,
    invocation_count: result.execution.invocation_count,
  };
  return result.execution.status;
};

const makeFreshWorkspaceRun = async () => {
  const cookiesBefore = await context.cookies();
  assert.equal(cookiesBefore.length, 0, "The Golden browser context must start without YouTube cookies.");

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Home", exact: true }).waitFor();
  if (process.env.YIA_M12_RESUME_EXISTING_WORKSPACE === "1") {
    assert.equal(
      await page.getByText("FIRST RUN · 1 / 3", { exact: true }).count(),
      0,
      "Resume mode is only for the already-onboarded task-owned Fresh workspace.",
    );
    report.onboarding_steps = 3;
    report.onboarding_reused_from_prior_ui_run = true;
    report.product_explainer = "Following sources become traceable knowledge, with original Evidence reachable.";
    report.recommended_model_policy = "Local capability first; paid cloud requires explicit opt-in; unavailable local capability pauses rather than silently falling back.";
    report.sample_network_or_model_writes = {
      local_writes: 0,
      external_requests: 0,
      evidence: "Recorded during the prior three-step Playwright onboarding on this same Fresh workspace.",
    };
  } else {
    await page.getByText("FIRST RUN · 1 / 3", { exact: true }).waitFor();
    await page.getByText("Turn what you follow into traceable knowledge.", { exact: true }).waitFor();
    const productConcepts = page.locator(".onboarding-value-grid");
    for (const concept of ["Following", "Content", "Intelligence"]) {
      await productConcepts.getByText(concept, { exact: true }).waitFor();
    }
    await capture("onboarding-1");

    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByText("FIRST RUN · 2 / 3", { exact: true }).waitFor();
    await page.getByText("Recommended", { exact: true }).waitFor();
    await page.getByText(
      "Use local capability first. Never make a paid cloud call unless you explicitly opt in.",
      { exact: true },
    ).waitFor();
    await page.getByText(/instead of silently falling back/).waitFor();
    const sample = page.getByLabel("Synthetic sample experience");
    await sample.getByText("SYNTHETIC SAMPLE", { exact: true }).waitFor();
    await sample.getByText(
      "UI-only example · not written to your library · no network or model call",
      { exact: true },
    ).waitFor();
    for (const stage of ["Content", "Summary", "Evidence · supporting", "Intelligence", "Topic"]) {
      await sample.getByText(stage, { exact: true }).waitFor();
    }
    const sampleMutations = apiMutations.length;
    const sampleExternal = externalRequests.length;
    const sampleApiRequests = apiRequests.slice();
    assert.equal(sampleMutations, 0, "The synthetic sample must not write library data.");
    assert.equal(sampleExternal, 0, "The synthetic sample must not make a network request.");
    assert.ok(
      sampleApiRequests.every(
        (request) => request.method === "GET" && request.path === "/api/v1/dashboard",
      ),
      "Onboarding may refresh the local dashboard projection, but the sample must not trigger library or model APIs.",
    );
    await capture("onboarding-synthetic-sample");

    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByText("FIRST RUN · 3 / 3", { exact: true }).waitFor();
    await page.getByText("Local-first processing", { exact: true }).waitFor();
    await page.getByText(/public YouTube source is processed locally first/i).waitFor();
    await page.getByText(/can take a little time/i).waitFor();
    await page.getByText(/pauses and explains why/i).waitFor();
    await page.getByText(/will not silently switch to a cloud model/i).waitFor();
    assert.equal(await page.getByText(/Runtime qualification is separate/).count(), 0);
    await capture("onboarding-local-first");
    report.onboarding_steps = 3;
    report.product_explainer = "Following sources become traceable knowledge, with original Evidence reachable.";
    report.recommended_model_policy = "Local capability first; paid cloud requires explicit opt-in; unavailable local capability pauses rather than silently falling back.";
    report.sample_network_or_model_writes = {
      local_writes: sampleMutations,
      external_requests: sampleExternal,
      read_only_local_dashboard_requests: sampleApiRequests.length,
    };
  }

  let winning = null;
  for (const sourceUrl of sourceUrls) {
    const videoId = videoIdFromUrl(sourceUrl);
    assert.ok(videoId, `Golden source must be a public YouTube video URL: ${sourceUrl}`);
    const submission = await addSourceThroughUi(sourceUrl);
    const run = await waitForVisibleRunOutcome();
    await capture(`source-run-${videoId}`);

    const recentPanel = page.locator(".panel").filter({ hasText: "Recent videos" }).last();
    const videoTitle = (await recentPanel.locator(".metadata-row span").first().innerText()).trim();
    assert.ok(videoTitle, `No recognizable Content title appeared for ${videoId}.`);
    const content = await inspectContentThroughUi(videoTitle);
    if (
      content.transcript_status === "FAILED"
      || content.summary_status === "UNAVAILABLE"
      || content.evidence_status === "UNAVAILABLE"
    ) {
      report.candidates.push({
        source_url: sourceUrl,
        video_id: videoId,
        video_title: videoTitle,
        source_run_id: submission.sourceRunId,
        source_run_status: run.text,
        progress_states: run.progress_states,
        admitted_intelligence: false,
        ...content,
      });
      continue;
    }
    let card = await locateIntelligenceCard();
    if (!card && /current local model cannot reliably|local model unavailable|waiting for a local model|local model is unavailable/i.test(
      content.intelligence_result_text,
    )) {
      assert.equal(report.cloud_execution, undefined, "Golden permits only one explicit cloud execution.");
      const cloudStatus = await authorizeOneCloudExecutionThroughUi(videoTitle);
      if (cloudStatus === "SUCCEEDED") {
        card = await locateIntelligenceCard();
        assert.ok(card, "A successful cloud execution must appear as an Intelligence card.");
      } else {
        report.status = "CLOUD_RUNTIME_BLOCKED";
        throw new Error(`The single explicitly authorized cloud execution ended ${cloudStatus}.`);
      }
    }
    const candidate = {
      source_url: sourceUrl,
      video_id: videoId,
      video_title: videoTitle,
      source_run_id: submission.sourceRunId,
      source_run_status: run.text,
      progress_states: run.progress_states,
      ...content,
      admitted_intelligence: Boolean(card),
    };
    report.candidates.push(candidate);
    if (card) {
      candidate.conclusion = (await card.getByRole("heading", { level: 2 }).first().innerText()).trim();
      winning = candidate;
      break;
    }
    if (/confirmation needed|external processing outcome could not be confirmed/i.test(
      content.intelligence_result_text,
    )) {
      candidate.execution_outcome = "AMBIGUOUS_EXTERNAL_OUTCOME";
      continue;
    }
    if (/current local model cannot reliably|local model unavailable|waiting for a local model|local model is unavailable/i.test(
      content.intelligence_result_text,
    )) {
      candidate.execution_outcome = "WAITING_MODEL";
      report.status = "DISTILLATION_RUNTIME_BLOCKED";
      throw new Error(
        "Local model work paused before admission; no alternate provider will be tried.",
      );
    }
    if (!/no new intelligence|completed/i.test(content.intelligence_result_text)) {
      throw new Error(`Real Content ended without an admitted Intelligence or truthful positive-zero result: ${content.intelligence_result_text}`);
    }
  }
  if (!winning) {
    const candidatesWithTranscript = report.candidates.filter(
      (candidate) => candidate.transcript_status === "AVAILABLE",
    );
    const candidatesWithContentEvidence = candidatesWithTranscript.filter(
      (candidate) => candidate.summary_status === "AVAILABLE"
        && candidate.evidence_status === "AVAILABLE",
    );
    const hadAmbiguousExecution = report.candidates.some(
      (candidate) => candidate.execution_outcome === "AMBIGUOUS_EXTERNAL_OUTCOME",
    );
    if (hadAmbiguousExecution) {
      report.status = "DISTILLATION_RUNTIME_BLOCKED";
    } else if (candidatesWithContentEvidence.length > 0) {
      report.status = "NO_ADMITTED_INTELLIGENCE_BLOCKED";
    } else if (candidatesWithTranscript.length === 0) {
      report.status = "TRANSCRIPT_RUNTIME_BLOCKED";
    } else {
      report.status = "REGRESSION_REMAINS";
    }
    let exhaustionMessage = "Every bounded real Content candidate completed without an admitted Intelligence.";
    if (hadAmbiguousExecution) {
      exhaustionMessage = "At least one bounded real local distillation execution remained ambiguous; no execution was automatically retried.";
    } else if (candidatesWithContentEvidence.length === 0) {
      exhaustionMessage = "No bounded real Content candidate reached transcript-backed Summary / Video Notes and Evidence.";
    }
    throw new Error(
      exhaustionMessage,
    );
  }
  report.winner = winning;

  winning.translation = await generateTranslationThroughUi(
    winning.video_title,
    winning.evidence_id,
  );

  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  const topicSourceCard = page.locator("article.intelligence-card")
    .filter({ hasText: winning.conclusion }).first();
  await topicSourceCard.waitFor();
  await topicSourceCard.getByRole("button", { name: "Add to a Topic" }).click();
  await topicSourceCard.getByLabel("Topic name").fill(winning.video_title);
  await topicSourceCard.getByRole("button", { name: "Create Topic and link Intelligence" }).click();
  await topicSourceCard.getByText(`Linked to Topic: ${winning.video_title}`, { exact: true }).waitFor();
  await page.getByRole("button", { name: "Topics", exact: true }).click();
  const topic = page.locator("button.list-row").filter({ hasText: winning.video_title }).first();
  await topic.waitFor();
  const topicName = (await topic.locator("strong").innerText()).trim();
  await topic.click();
  await page.getByText("A current contribution supports this topic.", { exact: true }).waitFor();
  report.topic = topicName;
  await capture("topic-associated");

  await page.getByRole("button", { name: "Home", exact: true }).click();
  const homeCard = page.locator("article.intelligence-card")
    .filter({ hasText: winning.conclusion }).first();
  await homeCard.waitFor();
  const start = performance.now();
  let traceClicks = 1;
  await homeCard.getByText("Evidence and source", { exact: true }).click();
  const evidence = homeCard.locator("article.evidence-trace-item").first();
  const originalButton = evidence.getByRole("button", { name: "原文", exact: true });
  if (await originalButton.getAttribute("aria-pressed") !== "true") {
    await originalButton.click();
    traceClicks += 1;
  }
  await evidence.getByText("Source position", { exact: true }).waitFor();
  const originalExcerpt = (await evidence.locator("blockquote").first().innerText()).trim();
  const position = await evidence.getByText("Source position", { exact: true }).locator("xpath=..")
    .innerText();
  const originalLink = evidence.getByRole("link", { name: /^Open original/ });
  const originalHref = await originalLink.getAttribute("href");
  assert.ok(originalExcerpt.length > 0, "The Intelligence trace must show original Evidence.");
  assert.ok(position.match(/\d+:\d+/), `No timed source position was rendered: ${position}`);
  assert.ok(originalHref?.includes(winning.video_id), "The source link must target the cited video.");
  assert.ok(/[?&]t=\d+/.test(originalHref ?? ""), "The source link must include the Evidence timestamp.");
  const traceMs = Math.round(performance.now() - start);
  assert.ok(traceMs < 10_000, `Claim-to-source trace took ${traceMs}ms.`);
  assert.equal(externalRequests.length, 0, "Rendering Evidence must not automatically open an external source.");
  const evidenceText = await evidence.innerText();
  const stance = evidenceText.match(/\b(supporting|contradicting|conditional)\b/i)?.[1] ?? null;
  assert.ok(stance, "The cited Evidence must expose its semantic stance.");
  const cardText = await homeCard.innerText();
  assert.match(cardText, /Validation posture/i);
  assert.match(cardText, /not a numeric confidence score/i);
  assert.doesNotMatch(cardText, /\b\d+(?:\.\d+)?%\b/);
  report.source_trace = {
    conclusion: winning.conclusion,
    evidence_excerpt_chars: originalExcerpt.length,
    source_position: position,
    stance,
    clicks: traceClicks,
    elapsed_ms: traceMs,
    destination: originalHref,
  };
  report.browser_external_requests_before_source_open = externalRequests.length;
  await capture("claim-source-trace-desktop");

  const [sourcePage] = await Promise.all([
    page.waitForEvent("popup"),
    originalLink.click(),
  ]);
  // YouTube navigation can stall outside the app. The link target above is
  // the source-trace contract; the popup proves the user action opened it.
  const openedUrl = sourcePage.url();
  if (openedUrl !== "about:blank") {
    const opened = new URL(openedUrl);
    assert.equal(opened.searchParams.get("v"), winning.video_id);
    assert.ok(opened.searchParams.has("t"), "The user-initiated source opening must retain its timestamp.");
  }
  await sourcePage.close();
  report.user_initiated_source_open = {
    popup_created: true,
    external_navigation_confirmed: openedUrl !== "about:blank",
  };

  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByRole("button", { name: "Create Backup", exact: true }).waitFor();
  const createBackup = page.getByRole("button", { name: "Create Backup", exact: true });
  assert.equal(await createBackup.isEnabled(), true, "Backup must be available at the completed work boundary.");
  await createBackup.click();
  const backupResult = page.getByRole("article", { name: "Backup result" });
  await backupResult.waitFor();
  const backupText = await backupResult.innerText();
  for (const label of ["Following", "Content", "Current Summaries", "Evidence", "Intelligence", "Topic"]) {
    assert.ok(backupText.includes(label), `Backup preview omitted ${label}.`);
  }
  report.backup_preview = backupText;
  await capture("backup-preview");

  await page.getByRole("button", { name: "Following", exact: true }).click();
  const sourceRow = page.locator(".source-row").filter({
    has: page.locator(`a[href="${winning.source_url}"]`),
  }).first();
  await sourceRow.locator("button.source-select").click();
  await page.getByRole("button", { name: "Stop future monitoring", exact: true }).click();
  const pausedRow = page.locator(".source-row").filter({
    has: page.locator(`a[href="${winning.source_url}"]`),
  }).first();
  await pausedRow.getByText("Monitoring is paused", { exact: true }).waitFor();
  await pausedRow.locator("button.source-select").click();
  const checkNow = page.getByRole("button", { name: "Check Now", exact: true });
  assert.equal(await checkNow.isEnabled(), false, "A disabled Following must not start future processing.");
  await page.getByText("Resume monitoring to start a new check. Historical data remains available.", { exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  report.disabled_following_smoke = "Monitoring paused; Check Now disabled; history retained.";

  await page.getByRole("button", { name: "Home", exact: true }).click();
  await homeCard.waitFor();
  await page.setViewportSize({ width: 768, height: 900 });
  await capture("claim-source-trace-768");
  await page.setViewportSize({ width: 1440, height: 900 });
};

const verifyRestartedLibrary = async () => {
  const previous = JSON.parse(readFileSync(resultPath, "utf8"));
  assert.equal(previous.status, "PASS", "Run the fresh Golden flow before the restart smoke.");
  const winner = previous.winner;
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Home", exact: true }).waitFor();
  assert.equal(await page.getByText("FIRST RUN · 1 / 3", { exact: true }).count(), 0);

  await page.getByRole("button", { name: "Following", exact: true }).click();
  const sourceRow = page.locator(".source-row").filter({
    has: page.locator(`a[href="${winner.source_url}"]`),
  }).first();
  await sourceRow.waitFor();
  await sourceRow.getByText("Monitoring is paused", { exact: true }).waitFor();

  await page.getByRole("button", { name: "Content", exact: true }).click();
  await page.locator("button.list-row").filter({ hasText: winner.video_title }).last().click();
  const transcript = page.locator(".transcript-copy");
  await transcript.waitFor();
  assert.ok((await transcript.innerText()).trim().length >= winner.transcript_chars);
  const summary = page.locator(".summary-note");
  await summary.waitFor();
  const evidence = page.locator(".panel").filter({ hasText: "Evidence · source transcript" }).last()
    .locator("article.evidence-trace-item").first();
  await evidence.waitFor();
  assert.equal(await evidence.locator(".reading-meta strong").innerText(), winner.evidence_id);
  if (winner.translation?.status === "AVAILABLE") {
    await evidence.getByRole("button", { name: "译文", exact: true }).click();
    await evidence.getByText(winner.translation.text, { exact: true }).waitFor();
  }

  await page.getByRole("button", { name: "Intelligence", exact: true }).click();
  const card = page.locator("article.intelligence-card").filter({ hasText: winner.conclusion }).first();
  await card.waitFor();
  await page.getByRole("button", { name: "Topics", exact: true }).click();
  await page.locator("button.list-row").first().click();
  await page.getByText("A current contribution supports this topic.", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const outputLanguage = page.getByLabel("Preferred output language", { exact: true });
  await outputLanguage.waitFor();
  assert.equal(await outputLanguage.inputValue(), "zh-CN");
  const backupStatus = page.getByRole("button", { name: "Create Backup", exact: true });
  await backupStatus.waitFor();
  assert.equal(await backupStatus.isEnabled(), true);
  assert.equal(apiMutations.length, 0, "Restart verification must not submit new work or mutate settings.");
  assert.equal(externalRequests.length, 0, "Restart rendering must not open an external source.");
  await capture("restart-settings-1440");
  await page.setViewportSize({ width: 768, height: 900 });
  await capture("restart-settings-768");
  report.restart = "Following, Content, transcript, Summary, Evidence, Intelligence, Topic, output language, and Backup readiness remain available; no new API mutation was submitted.";
};

try {
  if (mode === "fresh") await makeFreshWorkspaceRun();
  else if (mode === "restart") await verifyRestartedLibrary();
  else throw new Error(`Unsupported YIA_M12_MODE: ${mode}`);
  report.status = "PASS";
} catch (error) {
  if (report.status === "RUNNING") report.status = "REGRESSION_REMAINS";
  report.error = error instanceof Error ? error.message : String(error);
  throw error;
} finally {
  report.finished_at = new Date().toISOString();
  report.external_requests = externalRequests;
  report.api_mutations = apiMutations;
  writeFileSync(resultPath, `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
  process.stdout.write(`${JSON.stringify({ resultPath, report }, null, 2)}\n`);
}
