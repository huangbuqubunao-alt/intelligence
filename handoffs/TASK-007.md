# TASK-007 交接报告

## 元数据

- Task: `TASK-007`
- Role: `Implementer`
- Agent/session: `Codex /root`
- Base branch/commit: `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-007`
- Branch: `codex/task-007-local-scoring`
- Head commit: 本报告与实现提交在同一 HEAD；最终 SHA 由主控回传记录。
- Started: `2026-07-19`
- Reported: `2026-07-19`

## 目标与范围

- 任务目标：离线实现本地评分的三段采样、版本感知缓存和阈值策略；以严格 JSON Schema
  解析、一次格式修复及 Fake transport 实现 Ollama Adapter。
- 允许修改：`scoring.py`、`providers/ollama.py`、`prompts/scoring.md`、两份任务测试、
  `tests/fixtures/scoring/**` 与本报告。
- 实际修改：上述允许路径，新增评分服务、Ollama Adapter、版本化 Prompt、5 个固定响应夹具
  和 10 个离线测试。
- 明确未做：未改 `pyproject.toml`、`uv.lock`、Schema/migration、`config.py`、`domain.py`、
  `state.py`、任务状态或 `main`；未实现模型安装、服务生命周期、模型拉取或真实评分冒烟。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1：合法、越界、缺字段、非法 JSON、修复成功和失败 | PASS | `tests/integration/test_ollama_provider.py` 使用 5 个固定夹具；6 项 Fake transport 测试通过。 |
| AC-2：开头/正文/结尾采样、长度限制与重复评分缓存 | PASS | `test_sample_transcript_uses_bounded_head_center_tail_segments` 和缓存命中测试通过；同一规范输入只调用 Fake Provider 一次。 |
| AC-3：阈值最终决策与模型建议冲突诊断 | PASS | `ScoringService` 保留模型建议，以 `score >= threshold` 产生最终值，并记录 `MODEL_POLICY_DISAGREEMENT`。 |
| 严格 Provider 边界 | PASS | Adapter 仅构造 `GET /api/tags` 与 `POST /api/generate`；`stream=false`、`think=false`、有限读取、固定 JSON Schema，且默认 transport 未在测试中调用。 |

## 版本、复用与许可证

- Prompt/schema/sampling：`scoring-prompt-v1`、`score-result-v1`、`sampling-v1`。
- `DIRECT`：Python 3.12 `urllib.request` 与 `json`（标准库）；既有锁定 Pydantic 评分对象和
  Provider-call 哈希契约。未新增依赖。
- `DIRECT-PENDING`：Ollama HTTP API 与 `qwen3:8b` 仅作为配置和 Fake 响应的未来运行时边界；
  未安装、启动、拉取、探测或调用。Ollama MIT / qwen3:8b 上游 Apache-2.0 的登记证据见
  `docs/REUSE_REGISTER.md` §7 与 ADR-007 L-08。
- `REJECT`：未引入 `httpx`、Ollama Python SDK、cloud tag 或自动服务/模型 bootstrap。
- 黄金夹具：固定夹具只验证结构、边界和修复语义，不宣称模型质量或人工标注偏差已经校准；
  经批准的本机模型和人工黄金样例校准留待后续资源门禁。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 34 个锁定包已解析；无锁文件修改。 |
| `uv sync --locked --offline` | PASS | 首次 `uv run` 发现构建后端缓存未就绪后按任务包允许的离线同步；30 个已有锁定包安装成功，未联网下载。 |
| `uv run python -m pytest tests/unit/test_scoring.py` | PASS | `4 passed`。 |
| `uv run python -m pytest tests/integration/test_ollama_provider.py` | PASS | `6 passed`，全部为 Fake transport。 |
| `uv run python -m pytest` | PASS | `261 passed`。 |
| `uv run mypy src` | PASS | `Success: no issues found in 11 source files`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist 与 wheel 均构建成功。 |
| 包内容检查 | PASS | 两个产物均含 `youtube_intel/migrations/001_initial.sql`。 |
| Fake/no-real-Ollama 审查 | PASS | 测试注入 `_FakeTransport`；未运行 Ollama、`qwen3:8b`、`127.0.0.1:11434` 或其他网络服务。 |

## Diff 复核

- 修改文件：仅任务批准的 7 个路径组（2 个源模块、Prompt、2 个测试、夹具目录、本报告）。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：`dist/` 和 `.venv/` 为忽略的本地检查产物，未暂存或提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：首次 `uv run` 因缓存中缺少构建后端而尝试网络并被拦截；随后
  `uv sync --locked --offline` 成功，所有后续命令均离线执行。
- 跳过检查及原因：未运行任何真实 Ollama/模型/网络/媒体/Vault/密钥/ffmpeg/删除路径；它们未获授权。
- 剩余风险：真实 Ollama `0.32.x` 与固定 `qwen3:8b` digest 的运行时兼容性、模型质量和
  人工黄金样例偏差仍待独立资源授权；当前 Adapter 只由 Fake transport 证明。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：见包含本报告的实现提交；主控回传精确 SHA。
- 复现/验证说明：在此 worktree 执行上表命令；Provider 集成测试只使用测试内的
  `_FakeTransport`，不使用默认 `urllib` transport。

---

## Independent Codex Reviewer — 2026-07-19

### Review authority and boundary

- Reviewer: fresh independent Codex Reviewer; this reviewer did not implement TASK-007.
- Dynamic authorization: main commit `ecabaf70774858a90f949e635926a0ef0a83577e`
  (`docs: authorize TASK-007 independent review`) adds the reviewer card for source
  `codex/task-007-local-scoring` at `IN_REVIEW`.
- Reviewed range: `6b4d59c882ccdcbd0e5a6069a6661e0672921a80...`
  `258358fcd5227e144c9294beafdf7ec6e2feea63`.
- Source gate: PASS before review — branch is `codex/task-007-local-scoring`, HEAD is
  `258358fcd5227e144c9294beafdf7ec6e2feea63`, and both short and full porcelain status
  were empty. TASK-006 was neither read, run, modified, cleaned, nor reported.

### Required offline reruns

| Command / inspection | Result |
|---|---|
| `uv lock --check` | PASS — resolved 34 packages. |
| `uv sync --locked --offline` | PASS — 34 resolved, 30 checked; no network authority used. |
| `uv run python -m pytest tests/unit/test_scoring.py tests/integration/test_ollama_provider.py` | PASS — 10 passed. |
| `uv run python -m pytest` | PASS — 261 passed. |
| `uv run mypy src` | PASS — no issues in 11 source files. |
| `uv run ruff check .` | PASS — all checks passed. |
| `uv run python -m youtube_intel --help` | PASS. |
| `uv build --offline` | PASS — sdist and wheel built. |
| sdist/wheel listing | PASS — both contain `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check 6b4d59c...258358f` | PASS — no whitespace errors. |
| `git diff --exit-code 6b4d59c 258358f -- pyproject.toml uv.lock` | PASS — no dependency or lockfile change. |

### Independent probes

#### A — offline HTTP and response safety: FAIL (P1-1)

- PASS: all executed checks used an injected in-process Fake transport; no default
  `urllib` transport or listening `127.0.0.1:11434` service was invoked. Fake checks
  confirmed loopback configuration rejection, exact `GET /api/tags` then
  `POST /api/generate` paths, `read(1_000_001)`, response closing, 300-second timeout,
  `stream=false`, `think=false`, JSON Schema `format`, and the expected 401/403, 429,
  5xx, timeout, malformed API payload, and oversized-body mappings where implemented.
- PASS: normal invalid model JSON/schema fixtures make exactly one repair call.
- FAIL: the error boundary is not safe or complete.
  - `src/youtube_intel/providers/ollama.py:322-342` wraps JSON/Pydantic failures in
    `_InvalidModelResponse`, and `:137-145` raises `OllamaProviderError` *from* that
    exception. An injected invalid repair response containing the sentinel
    `/private/secret-transcript-response` remained reachable as
    `exc.__cause__.__cause__.doc`. Raw model output therefore escapes through the
    exception chain despite the safe top-level message.
  - `:208-212` raises the private `_InvalidModelResponse` for a valid JSON generate
    envelope with a missing or >20,000-character `response`; its caller at `:124-132`
    does not catch it. The caller receives a private exception instead of the required
    `AppError(INVALID_RESPONSE)`.
  - `:259-285` catches `TimeoutError`, `socket.timeout`, and `OSError`, but not
    `http.client.IncompleteRead`. An injected short read propagates unwrapped rather
    than mapping to `TRANSIENT_NETWORK` as required by ADR-007 L-09.
- Required remediation: make every malformed/short/oversized response path produce a
  redacted named `AppError` with exception chaining suppressed, then add Fake-transport
  regression tests that inspect the complete exception chain.

#### B — sampling, request hashes, and policy truth: PASS for the in-memory layer

- An independent Unicode probe verified code-point-limited head/body/tail selection,
  the `n <= M` boundary, and `selected_char_count`.
- Independent changes to title, channel, date, duration, default/final language,
  selected description prefix, full transcript (including an unselected character),
  selected sample content, model, temperature, output limit, prompt version, schema
  version, and operation all changed the primary request hash. A suffix beyond the
  configured description limit correctly did not.
- At `score == threshold`, `final_should_summarize` was `True` even when the Fake model
  returned `should_summarize=False`; the disagreement diagnostic was retained without
  altering the model result. Identical input reused `InMemoryScoringCache`; changing
  title caused a second Fake call.

#### C — real SQLite completion and cache recovery: FAIL (P1-2)

- `uv run python -m pytest tests/integration/test_state_store.py -k
  'scoring_stage_requires_summary_and_commits_it_atomically or
  scoring_summary_failure_rolls_back_every_stage_write'` PASS — 2 passed using
  temporary real SQLite. This proves the pre-existing repository can atomically commit
  a scoring summary/provider call and roll it all back after injected failure.
- TASK-007 does not use that capability. `src/youtube_intel/scoring.py:37-55` defines
  only an in-memory `get`/`put` cache, and `:177-252` accepts only provider/settings/
  cache/clock and never reserves/completes a Provider call or calls
  `SQLiteStateRepository.complete_stage`. Repository completion tests therefore do
  not exercise new code. Static review found no other production reference to
  `ScoringService` or `OllamaScoringProvider`.
- Consequently this implementation cannot atomically store `SCORING_RAW`,
  `SCORING_STRUCTURED`, Provider call completion, `ScoringSummaryWrite`, Pipeline CAS,
  and Job success; it also cannot recover a verified SQLite cache across attempts or
  distinguish primary versus repair persistence.
- Required remediation: compose the existing repository reservation/completion APIs
  around the scoring provider, persist both artifacts and the application decision in
  one transaction, and add real temporary-SQLite tests for success, post-write rollback,
  verified cache hit, and all request-separation misses.

#### D — scope and phase honesty: PASS, with the P1 limitations above

- Range is exactly the permitted 11 files within the seven approved path groups:
  handoff, prompt, two source modules, two test modules, and five scoring fixtures.
- No `httpx`, Ollama SDK, dependency, lockfile, Schema/migration, bootstrap, pull, or
  real-service action was introduced. The source uses standard-library `urllib`/`json`.
- Secret-pattern review found only the benign `max_output_tokens` identifier; manual
  diff review found no credential, token, authorization value, or absolute local path.
- Reuse/license evidence is present in `docs/REUSE_REGISTER.md:109-112`: standard
  library use is `DIRECT`; Ollama/qwen3 are `DIRECT-PENDING`; `httpx` and the Ollama
  Python SDK remain deferred/rejected. Fake coverage does not claim to validate a real
  model.

### Acceptance and ADR-007 matrix

| Item | Result | Independent evidence |
|---|---|---|
| AC-1 fixed valid/out-of-range/missing/invalid/repair fixtures | PARTIAL / FAIL | 10 focused Fake tests pass, but P1-1 leaves malformed envelope, short-read, and repair-error paths without the required safe mapping/redaction. |
| AC-2 bounded sampling and same-input cache | PARTIAL / FAIL | Sampling/hash and process-local reuse pass (Probe B); verified persistent cache/recovery required by Probe C is absent (P1-2). |
| AC-3 threshold-derived final policy and disagreement record | PASS logically / FAIL durably | Probe B proves `>=` and preserved disagreement; P1-2 means it is not written atomically with `SCORED`. |
| L-03 model recommendation vs application decision | PASS | `ScoringService` derives final policy from score; independent equality-boundary probe passed. |
| L-04 atomic scoring summary | FAIL | Repository support exists, but TASK-007 does not call it (P1-2). |
| L-05 three-part sampling | PASS | Probe B verified boundaries, Unicode code points, version, and full-hash binding. |
| L-06 metadata/hash boundary | PASS | Probe B independently varied every required metadata/input/version dimension. |
| L-07 standard-library loopback HTTP | PARTIAL / FAIL | Configuration/path/schema/transport controls pass; P1-1 breaks required response safety. |
| L-08 fixed local model preflight | PASS at Fake-only boundary | Exact model/digest Fake preflight occurs before generate; no install, pull, or real call was performed. |
| L-09 response repair, cache, and errors | FAIL | Raw exception-chain leak, incomplete/malformed mappings, and no persistent provider-call/cache flow (P1-1/P1-2). |

### Findings

- P0: None.
- P1-1 — `src/youtube_intel/providers/ollama.py:124-145, 208-212, 259-285, 322-342`:
  malformed/oversized generate envelopes and `IncompleteRead` escape without a named
  safe error, while invalid repair responses retain raw model output in the exception
  chain. This violates the privacy/redaction and error-mapping boundary.
- P1-2 — `src/youtube_intel/scoring.py:37-55, 177-252`: scoring is not connected to
  repository Provider-call lifecycle or atomic stage completion, so its raw/structured
  result, final decision, cache, Pipeline CAS, and Job completion cannot be durable or
  recoverable as required.
- P2: None.
- P3: None.

### Five-axis review, risks, and resources intentionally not run

- Correctness: REJECT — P1-1 and P1-2 leave mandatory failure and completion behavior
  unimplemented.
- Architecture: REJECT — a reusable in-memory policy helper exists, but no production
  composition reaches the existing state transaction boundary.
- Security/privacy: REJECT — raw untrusted response survives exception chaining.
- Performance/resources: PASS at the implemented boundary — bounded response read and
  bounded sample/cache operations; no new dependency or unbounded loop observed.
- Readability: PASS apart from the materially incomplete error/persistence paths; names
  and the focused Fake tests are otherwise clear.
- Intentionally unrun/unauthorized: default `urllib` transport and any real Ollama
  endpoint (including loopback), Ollama installation/start/stop, `qwen3:8b` pull or
  cloud tags/URLs, ffmpeg/media/YouTube/Cookie/remote components, Vault/credentials,
  and any deletion path. No network access was used by the reviewer.
- Remaining risk: P1-1 can expose model response data to callers/loggers; P1-2 means a
  successful scoring call cannot make the system's persisted stage/state truthful.
- `DECISION NEEDED`: `None`.

### Verdict

`REJECT` — approval requires all offline acceptance criteria and no unresolved P0/P1;
P1-1 and P1-2 remain open. No task status was changed, no merge was performed, and the
implementation source was not amended.

---

## Correction 1 — Codex Implementer — 2026-07-19

### Authorization, base, and scope

- Dynamic gate: main authorization commit `5667e9b40aa364e6f05c764808c32db99d1c5275`
  authorizes the original Codex correction role while `TASK-007` remains `IN_PROGRESS`.
- Source branch/base: `codex/task-007-local-scoring`, correction parent
  `266c488c17fc82cb648053b5e1066211a7bea9a9`. The correction is intentionally one
  child commit of that parent; it does not amend the reviewer evidence commit.
- Modified correction paths only: `src/youtube_intel/scoring.py`,
  `src/youtube_intel/providers/ollama.py`, `tests/unit/test_scoring.py`,
  `tests/integration/test_ollama_provider.py`, and this handoff.
- No task status, main worktree, dependency/lockfile, migration/schema, production
  configuration, credential, network, Vault, media, or deletion authority was used.

### P1 closure matrix

| Finding | Closure | Offline evidence |
|---|---|---|
| P1-1 — unsafe/missing Ollama response failures | CLOSED | Fake-transport tests now exercise invalid primary/repair content, missing and overlong generate envelopes, short reads, and transport failures; every path yields a redacted named `AppError` through `OllamaProviderError`. |
| P1-2 — no durable atomic scoring composition | CLOSED | A repository-backed scoring composition reserves/completes the existing Provider call, writes raw/structured artifacts and `ScoringSummaryWrite` through the existing atomic completion API, and validates a persisted cache with temporary real SQLite. |

#### P1-1: exception, transport, and response boundary

- `OllamaScoringProvider.score()` now exits failures only through a fresh safe error
  after untrusted prompt/model-response references have left library traceback frames.
  It preserves the required scoring stage and `video_id`, suppresses raw exception
  chains, and does not log response bodies.
- The final `POST /api/generate` JSON envelope is retained only on success and exposed
  once by `consume_raw_response(request_hash=...)` for the repository composition;
  failure paths clear it.
- A missing/non-string or overlong `response` field maps to
  `ErrorCode.INVALID_RESPONSE`; `http.client.IncompleteRead`, timeouts, socket and
  read/close failures map to `ErrorCode.TRANSIENT_NETWORK`; bounded-body, decoding and
  JSON failures remain safe named errors. HTTP mappings remain deterministic (429 rate
  limited, 5xx unavailable, 401/403 permission denied).
- Regression sentinels `/private/secret-transcript-response` and
  `/private/temporary-transcript-url` are recursively checked across error attributes,
  causes, contexts, and `youtube_intel` traceback frames. They cannot occur in the
  returned error graph. Tests continue to inject only `_FakeTransport`.

#### P1-2: SQLite state, artifacts, cache, and rollback

- `RepositoryBackedScoringService` keeps the existing pure `ScoringService` intact,
  while composing the existing repository contracts at the application boundary. It
  builds the frozen primary request hash, reserves the Provider call, and completes
  `TRANSCRIPT_READY -> SCORED` with the existing owner/CAS and pipeline version.
- On success it persists `SCORING_RAW` (the final full Ollama generate envelope,
  `RAW_RESPONSE_30D`) and `SCORING_STRUCTURED` (canonical `ScoreResult`, long-lived),
  completes the Provider call with the raw artifact ID, records the threshold-derived
  `ScoringSummaryWrite`, pipeline status, and job success in the existing transaction.
  The model recommendation remains on `ScoreResult`; the application decision is
  `score >= configured threshold`, with `MODEL_POLICY_DISAGREEMENT` retained.
- A non-acquired successful reservation is a cache candidate only after raw and
  structured artifact keys/kinds/provenance, file containment, size, SHA-256,
  structured schema, request hash, provider/model, and Provider-call raw-artifact
  binding all verify. A verified hit re-completes the owned stage without another
  model call and reports `PERSISTED_CACHE_HIT`; invalid/missing records fail closed.
- Every injected failure after artifact preparation, Provider-call handling, summary
  preparation, or pipeline completion leaves the temporary SQLite video at
  `TRANSCRIPT_READY`, no committed artifacts/summary, and no successful Provider call.
  The exact temporary payload files created by this attempt are removed on rollback;
  no broad delete is used.
- The raw persistence regression uses `/private/raw-scoring-response` and applies the
  same recursive error-graph redaction assertion to library traceback frames.

### Hash, reuse, and licence record

- The primary hash is now reused by both the pure and repository-backed services and
  changes with all frozen dimensions: video ID/title/channel/date/duration/default and
  chosen language, bounded description, full transcript content hash and sample,
  model/temperature/output limit, prompt version, schema version, and operation.
- `DIRECT`: Python standard-library `urllib` and `json`, plus existing in-repository
  Pydantic/domain/state contracts. No dependency or lockfile changed.
- `DIRECT-PENDING`: Ollama and `qwen3:8b` remain configuration/Fake-bound runtime
  integrations only. Existing reuse/license evidence remains
  `docs/REUSE_REGISTER.md` §7 and ADR-007 L-08 (Ollama MIT; qwen3 upstream
  Apache-2.0). No model or service was installed, started, pulled, or queried.
- `REJECT`: no Ollama SDK, `httpx`, cloud tag discovery, bootstrap, or real-service
  helper was introduced.

### Final offline verification

| Command / check | Result | Evidence |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 34 packages in 1ms`. |
| `uv sync --locked --offline` | PASS | 34 resolved; 30 checked; no network download. |
| `uv run python -m pytest tests/unit/test_scoring.py tests/integration/test_ollama_provider.py` | PASS | `23 passed in 0.21s`. |
| `uv run python -m pytest` | PASS | `274 passed in 1.81s`. |
| `uv run mypy src` | PASS | No issues in 11 source files. |
| `uv run ruff check .` | PASS | All checks passed. |
| `uv run python -m youtube_intel --help` | PASS | CLI help rendered. |
| `uv build --offline` | PASS | Wheel and sdist built. |
| Wheel/sdist migration listing | PASS | Both include `youtube_intel/migrations/001_initial.sql`. |

### Complete correction diff review

- `src/youtube_intel/providers/ollama.py`: closes response/error redaction and
  short-read/malformed-envelope handling; exposes a one-shot successful raw envelope
  handoff only for durable composition.
- `src/youtube_intel/scoring.py`: adds the minimal repository-backed application
  composition, verified persistent cache, deterministic artifact persistence, safe
  failure boundary, and rollback of only files created by the failed attempt.
- `tests/integration/test_ollama_provider.py`: adds Fake-only envelope, short-read,
  transport and complete error-graph sentinel regressions.
- `tests/unit/test_scoring.py`: covers each hash dimension, real temporary-SQLite
  atomic success, verified cache reuse, four post-write rollback points, and persisted
  raw-response redaction.
- `handoffs/TASK-007.md`: records this correction and its reproducible evidence.
- No generated build artifact is staged; no unrelated file is part of the correction.

### Intentionally unrun resources and remaining risk

- Not run or touched: default `urllib` transport, any real Ollama endpoint or model,
  network/cloud/YouTube URLs, media/ffmpeg, Vault, cookies/credentials, external data
  deletion, and main-worktree task-state operations. These were outside authority.
- Remaining risk: a separately authorized real Ollama/model compatibility and quality
  calibration run is still needed; this correction proves only deterministic
  Fake-transport behavior plus temporary local SQLite/artifact behavior.
- `DECISION NEEDED`: `None`.

---

## Correction 1 — Second Independent Codex Reviewer — 2026-07-19

### Authority, source gate, and scope

- Reviewer: fresh independent Codex Reviewer; this reviewer did not implement TASK-007
  or Correction 1.
- Dynamic authorization: `git -C '/Users/hua/Documents/youtubek agent' log -1 --format=%H --
  agent-prompts/TASK-007-REVIEWER-2-CODEX.md` resolved to
  `1eb3380ea329592a4259b5ead24fde5403f7fa0f`; the main task card lists TASK-007 as
  `IN_REVIEW`.
- Source gate: PASS before review — branch `codex/task-007-local-scoring`, clean source
  worktree, HEAD `f46881bc4a8ca0fda4d5ef7006b372bc566cff97`, sole parent
  `266c488c17fc82cb648053b5e1066211a7bea9a9`, and merge-base/common base
  `6b4d59c882ccdcbd0e5a6069a6661e0672921a80` all matched the review package.
- Complete `base...source` range contains exactly the approved handoff, prompt, two source
  modules, two scoring tests, and five scoring fixtures. Correction 1 changes only its
  five authorized paths: this handoff, `scoring.py`, `providers/ollama.py`, and the two
  scoring test files. `pyproject.toml` and `uv.lock` are byte-identical to the base.

### Required offline reruns

| Command / inspection | Result |
|---|---|
| `uv lock --check` | PASS — resolved 34 locked packages. |
| `uv sync --locked --offline` | PASS — resolved 34; checked 30; no network fallback. |
| `uv run python -m pytest tests/unit/test_scoring.py` | PASS — 11 passed. |
| `uv run python -m pytest tests/integration/test_ollama_provider.py` | PASS — 12 passed. |
| `uv run python -m pytest` | PASS — 274 passed. |
| `uv run mypy src` | PASS — no issues in 11 source files. |
| `uv run ruff check .` | PASS — all checks passed. |
| `uv run python -m youtube_intel --help` | PASS — CLI help rendered. |
| `uv build --offline` | PASS — sdist and wheel built. |
| package listing | PASS — both artifacts contain `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check 6b4d59c...f46881b` | PASS — no whitespace errors. |
| dependency/lock diff against base | PASS — no diff in `pyproject.toml` or `uv.lock`. |

### Independent probes

#### A — Fake transport, complete exception graph, and response safety: PASS

- A new in-process Fake transport (no default `urllib` call) covered invalid primary and
  repair payloads containing distinct raw/prompt/transcript/URL sentinels; missing,
  non-string, and 20,001-character generate envelopes; invalid UTF-8/API JSON/schema;
  `IncompleteRead`; read timeout; 401/403; 429; and 500/599. All 15 error cases returned
  the expected named `AppError` code, retryability, `video_id`, and `SCORING` stage.
- Recursive inspection of `message`, `args`, `__cause__`, `__context__`, attributes, and
  `youtube_intel` traceback locals found no raw response, prompt, transcript, URL, or
  absolute-path sentinel. Every Fake response was closed.
- Invalid structured primary output caused exactly one repair POST; a valid repair
  succeeded. No probe invoked an Ollama endpoint, including loopback.

#### B — real SQLite success, rollback, cache, and integrity: PARTIAL / FAIL

- PASS: a new temporary real SQLite/data-root probe completed one
  `TRANSCRIPT_READY -> SCORED` transition. It atomically indexed `SCORING_RAW` with
  `RAW_RESPONSE_30D`, `SCORING_STRUCTURED` with `LONG_LIVED`, a successful Provider Call
  bound to the raw Artifact, `ScoringSummaryWrite`, Pipeline CAS, and Job success. A
  model recommendation of `True` did not override the threshold-derived final decision
  of `False`.
- PASS: injected failures at `stage.after_artifacts`, `stage.after_provider_call`,
  `stage.after_scoring_summary`, and `stage.after_pipeline` left no indexed or local
  scoring artifacts, no score/decision, `TRANSCRIPT_READY`, a running Job, and a safe
  retryable Provider Call.
- PASS: a reset/retry of a verified request reused the persisted result without a second
  Fake provider call. Changing normalized input, model, prompt version, schema version,
  or operation caused a new Fake call. File-hash, artifact-video provenance, and
  Provider-call/raw-Artifact binding tampering all failed closed without a provider call.
- FAIL (P1-1 below): a primary structured-response failure followed by a failed repair
  does not persist the primary raw envelope. An actual requeued retry therefore performs
  another Fake preflight, primary request, and repair instead of reusing that saved
  primary response, contrary to ADR-007 L-09.

#### C — architecture, resource bounds, and red lines: PASS except P1-1

- `providers/ollama.py` has no SQLite write; `RepositoryBackedScoringService` uses the
  established Protocol/repository boundary with `ProviderCallRequest`, `ArtifactWrite`,
  `ProviderCallCompletion`, `ScoringSummaryWrite`, and `complete_stage` CAS semantics.
- The successful raw envelope is bound to its request hash and one-shot: a wrong hash
  cannot consume it; the right hash consumes it once; a second consume fails. Six unsafe
  base origins (TLS, remote host, userinfo, path, query, fragment) were rejected before
  transport. A 1,000,001-byte response was read with the configured capped size,
  rejected, and closed. A persisted `../` artifact path failed closed before any new
  provider call.
- Static and dynamic review found no Ollama SDK, `httpx`, dependency/lock/schema/domain/
  config change, direct Provider SQLite write, real-resource action, generated artifact,
  or silent weakening of sample/policy tests. Secret-pattern hits were only benign test
  sentinels and `max_output_tokens`; no credential, token, or private key was added.
- Reuse evidence remains consistent with `docs/REUSE_REGISTER.md` §7: standard-library
  `urllib.request`/`json` and existing SQLite/Pydantic contracts are `DIRECT`; Ollama and
  `qwen3:8b` remain `DIRECT-PENDING`; `httpx` and the Ollama SDK remain deferred/rejected.

### Acceptance and ADR-007 matrix

| Item | Result | Evidence |
|---|---|---|
| AC-1 — strict valid/invalid/repair provider behavior | PASS | Probe A plus 12 focused Fake-transport tests cover schema, envelope, transport, redaction, and exactly-one repair behavior. |
| AC-2 — bounded sampling and cache/recovery | PARTIAL / FAIL | Verified-success cache and all frozen request dimensions pass; P1-1 leaves the required failed-repair primary-response recovery absent. |
| AC-3 — threshold-derived durable final decision | PASS | Probe B confirmed `score < threshold` persisted `should_summarize=False` despite a `True` model suggestion, atomically with `SCORED`. |
| L-03 — recommendation vs final decision | PASS | Threshold decision is `score >= threshold`; disagreement is retained without mutating the model result. |
| L-04 — atomic score summary | PASS | Probe B success and all four transaction-boundary rollbacks passed using real SQLite. |
| L-05 — three-part sampling | PASS | Source/test review confirms the frozen head/centre/tail formulas, bounded count, and `sampling-v1`. |
| L-06 — metadata/hash boundary | PASS | Probe B proved cache separation for normalized input, model, prompt, schema, and operation; focused tests cover the constituent metadata/sample fields. |
| L-07 — standard-library loopback HTTP | PASS | Fake-only `urllib` adapter, loopback configuration rejection, capped read, schema format, `stream=false`, and `think=false` were verified. |
| L-08 — fixed model preflight | PASS at Fake-only boundary | Exact model/digest check precedes generation; no model, service, or network action was performed. |
| L-09 — response repair, saved primary reuse, and errors | FAIL | Safe mapping/repair/capped reads pass, but P1-1 violates the required primary-response reuse after repair failure. |

### Findings

- P0: None.
- P1-1 — `src/youtube_intel/providers/ollama.py:140-237` and
  `src/youtube_intel/scoring.py:590-638`: when a primary response is structurally invalid
  and its one allowed repair also fails, the Provider clears the primary raw envelope and
  returns only a safe error. The repository service marks the Provider Call retryable but
  writes neither `SCORING_RAW` nor a recovery record. In an independent real-SQLite
  requeue probe, the first failed attempt left both artifact keys absent; the second
  attempt issued a second Fake preflight/primary/repair sequence (six transport calls in
  total). ADR-007 L-09 requires the next Job attempt to prioritize the already saved
  primary response. Required remediation: persist a capped, request-bound primary raw
  envelope on repair-failure paths and add a safe recovery flow that validates/reuses it
  for the single repair without issuing another primary request.
- P2: None.
- P3: None.

### Five-axis review and intentionally unrun resources

- Correctness: REJECT — P1-1 leaves a mandatory L-09 recovery path unimplemented.
- Architecture: REJECT — successful completion composes the repository correctly, but
  the failed-repair primary response cannot enter the repository/cache lifecycle.
- Security/privacy: PASS for the implemented boundary — response limits, loopback-only
  config, Fake-only probes, closed responses, and complete safe exception graphs held.
- Performance/resources: PASS — response read is capped; artifact verification is
  bounded; no unbounded query, retry loop, or new dependency was introduced.
- Readability: PASS — named Protocols, artifacts, outcomes, and focused tests make the
  success/rollback flow understandable; the missing failed-repair persistence is a
  behavioral, not naming/style, issue.
- Intentionally unrun/unauthorized: default transport and every real Ollama endpoint,
  Ollama install/start/stop, model/cloud-tag pull, media/YouTube/Cookie/remote-component/
  ffmpeg paths, Vault/credentials, and deletion paths. No network access was used.

### Verdict

`REJECT` — all required offline gates pass, but approval requires no unresolved P0/P1.
P1-1 must be corrected and independently reviewed again. No task status was changed, no
merge was performed, and no product source or test was amended.

---

## Correction 2 — Codex Implementer — 2026-07-19

### Authority, parent, and exact scope

- Dynamic gate: main authorization commit
  `1aa3dc22b96a0d0493c656a4ce4f5490bd6f770b` authorizes the original Codex
  Implementer while TASK-007 is `IN_PROGRESS`.
- Source branch/head at start: `codex/task-007-local-scoring` at reviewer evidence
  `d8eaeabdd2454141eeb646d9254f4a0a24626605`, whose sole parent is Correction 1
  `f46881bc4a8ca0fda4d5ef7006b372bc566cff97`. This correction is one child commit
  of `d8eaeab...`; no history was amended.
- Correction paths only: `src/youtube_intel/scoring.py`,
  `src/youtube_intel/providers/ollama.py`, `tests/unit/test_scoring.py`,
  `tests/integration/test_ollama_provider.py`, and this handoff. No fixture was needed.
- No task status/main worktree/dependency/lockfile/schema/migration/domain/config/Prompt
  file changed, and no real resource was accessed.

### P1 closure — ADR-007 L-09 primary-response recovery

- The existing private raw-response handoff now preserves a received primary Ollama
  generate envelope when primary structural validation caused its sole repair to fail.
  It remains bound to the existing primary request hash and can be consumed only once;
  no new public free-form Provider contract was added.
- `RepositoryBackedScoringService` writes that primary envelope as a deterministic,
  request-hash-derived `SCORING_RAW` recovery Artifact with `RAW_RESPONSE_30D`, then
  records the existing Provider Call as `FAILED_RETRYABLE`. It writes no structured
  Artifact, scoring summary, `SCORED` Pipeline state, or successful Job on this path.
- A later owned requeue first validates the recovery Artifact's deterministic key and
  ID, DATA-root-contained relative path, bounded bytes, SHA-256, kind, video, nonempty
  source Job, Provider/model, producer version, retention/expiry, and request-derived
  provenance. Only then it invokes the Adapter's private saved-primary repair method.
- Recovery sends one `POST /api/generate` repair request and no preflight or primary
  score request. A valid repair follows the unchanged atomic `complete_stage` path,
  writing the final raw/structured Artifacts, successful Provider Call, threshold-owned
  summary, Pipeline CAS, and Job success together.
- Missing file, modified bytes, or mismatched indexed model fail closed as safe,
  retryable `INVALID_RESPONSE`; no cache hit, primary request, repair request, score,
  Pipeline advance, or successful Job is fabricated. Public error boundaries continue
  to rebuild a fresh safe exception after untrusted values leave library traceback
  frames.

### RED/GREEN proof and focused state evidence

- RED: before implementation, the new focused suite collected 28 items and failed five
  assertions: no `recovery-primary` Artifact existed, requeue could not reuse it, and
  the Adapter had no saved-primary repair entry point. A focused security RED test then
  demonstrated the saved primary text in the private repair traceback; clearing that
  local before the fresh safe raise made the same test GREEN.
- GREEN: `tests/unit/test_scoring.py` has 16 passing tests and uses real temporary
  SQLite/data paths. First primary+repair failure leaves exactly the recovery raw
  Artifact, `FAILED_RETRYABLE` Provider Call, `TRANSCRIPT_READY` video and no score or
  structured Artifact. The test requeues with existing `fail_job`,
  `activate_retry_jobs`, and `claim_next_job` semantics; it proves one initial primary,
  one initial repair, exactly one saved-primary repair, no second primary, and atomic
  final raw/structured/call/summary/Pipeline/Job success.
- Recovery transaction injection at `stage.after_provider_call` retains only the
  already-indexed recovery Artifact; the new final raw/structured files and rows roll
  back, the Pipeline stays `TRANSCRIPT_READY`, the Job is still running, and the
  Provider Call returns to `FAILED_RETRYABLE`.
- Missing temporary recovery file, tampered temporary file bytes, and mismatched
  indexed model each fail closed without a new primary or repair call. The only unlink
  exercised was the exact temporary test Artifact used to prove the missing-file case;
  no user, project-data, or external deletion path was touched.
- `tests/integration/test_ollama_provider.py` has 14 Fake-only tests. The precise
  transport sequence for the recovery probe is initial `GET /api/tags`, primary POST,
  failed-repair POST, followed by exactly one recovery `POST /api/generate`; the
  recovery step has no GET/preflight or repeated primary request. Sentinels in the saved
  primary response are absent from message, args, causes, contexts, attributes and
  `youtube_intel` traceback frames.

### Reuse, licensing, and privacy boundary

- `DIRECT`: existing SQLite `ProviderCallRequest`, reservation/failure,
  `ArtifactWrite`/Artifact index and `complete_stage` contracts; Python standard-library
  `urllib`/`json`/hashing/path APIs. No dependency or lockfile change.
- `ADAPT`: the existing non-exported Ollama raw-response handoff is extended narrowly
  for request-bound saved-primary repair; no SDK, `httpx`, model, service or cloud helper
  is introduced.
- `DIRECT-PENDING`: Ollama HTTP API (MIT) and `qwen3:8b` upstream Apache-2.0 remain
  Fake/configuration-only boundaries, as recorded in `docs/REUSE_REGISTER.md` §7 and
  ADR-007 L-08. No install/start/stop/pull/probe/call occurred.
- Safe errors contain no primary/repair response, prompt, transcript, URL, absolute
  path, credential or token. Raw content is persisted only under the existing controlled
  Artifact root and is never logged.

### Final offline verification

| Command / check | Result | Evidence |
|---|---|---|
| `uv lock --check` | PASS | Resolved 34 packages. |
| `uv sync --locked --offline` | PASS | Resolved 34; checked 30; no network fallback. |
| `uv run python -m pytest tests/unit/test_scoring.py` | PASS | `16 passed in 0.41s`. |
| `uv run python -m pytest tests/integration/test_ollama_provider.py` | PASS | `14 passed in 0.10s`, injected Fake transport only. |
| `uv run python -m pytest` | PASS | `281 passed in 2.09s`. |
| `uv run mypy src` | PASS | No issues in 11 source files. |
| `uv run ruff check .` | PASS | All checks passed. |
| `uv run python -m youtube_intel --help` | PASS | CLI help rendered. |
| `uv build --offline` | PASS | Wheel and sdist built. |
| Package migration listing | PASS | Both outputs contain `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check d8eaeab...HEAD` | PASS | Re-run after the correction commit; no whitespace errors. |

### Diff review, unrun paths, and remaining risk

- Diff contains only the five Correction 2 paths above; `pyproject.toml` and `uv.lock`
  are byte-identical to `d8eaeab...`. Build output remains ignored and unstaged.
- Five-axis self-review: correctness covers failure/requeue/rollback/tamper paths;
  architecture uses only existing repository transactions and a private Adapter hook;
  security redacts raw values and checks path/hash/provenance; bounded reads cap recovery
  at 1,000,000 bytes; names and focused tests keep the two-attempt recovery flow explicit.
- Not run/touched: default `urllib` transport, loopback or remote Ollama, service/model
  installation/start/stop/pull, cloud tags, media/YouTube/Cookie/ffmpeg, Vault,
  credentials, external deletion or task-status actions. No reviewer was started, merge,
  push, rebase, reset or cleanup performed.
- Remaining risk: real Ollama/model compatibility and model-quality calibration still
  require separate resource authority. This correction proves only deterministic Fake
  transport plus temporary SQLite/filesystem recovery behavior.
- `DECISION NEEDED`: `None`.

---

## Correction 2 — Third Independent Codex Reviewer — 2026-07-19

### Authority, source gate, and scope

- Fresh, independent review of `codex/task-007-local-scoring` only. Dynamic main
  authorization resolved to `57f02d8c1bbbaa3e323aa2fe097a139cda0d464f`
  (`docs: authorize TASK-007 recovery review`); the main task card remains
  `IN_REVIEW`.
- Source gate passed before review: clean worktree, HEAD
  `567b0f63f9cefc6c8bff43bfea0e9e156ac3a02c`, sole parent
  `d8eaeabdd2454141eeb646d9254f4a0a24626605`, and common base
  `6b4d59c882ccdcbd0e5a6069a6661e0672921a80` all matched the packet.
- The complete `base...source` range contains exactly the approved handoff, prompt,
  two source modules, two scoring tests, and five scoring fixtures. Correction 2
  changes only this handoff, `scoring.py`, `providers/ollama.py`, and the two
  existing scoring tests. `pyproject.toml` and `uv.lock` are byte-identical to the
  common base; no file is deleted.

### Required offline reruns

| Command / inspection | Result |
|---|---|
| `uv lock --check` | PASS — resolved 34 packages. |
| `uv sync --locked --offline` | PASS — resolved 34 and checked 30; no download fallback. |
| `uv run python -m pytest tests/unit/test_scoring.py` | PASS — 16 passed. |
| `uv run python -m pytest tests/integration/test_ollama_provider.py` | PASS — 14 passed. |
| `uv run python -m pytest` | PASS — 281 passed. |
| `uv run mypy src` | PASS — no issues in 11 source files. |
| `uv run ruff check .` | PASS. |
| `uv run python -m youtube_intel --help` | PASS — CLI help rendered. |
| `uv build --offline` | PASS — sdist and wheel built. |
| package inspection | PASS — both artifacts contain `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check 6b4d59c...567b0f6` | PASS — no whitespace errors. |

### Independent L-09 probes

1. **Persisted failed repair — PASS.** With a temporary real SQLite/data root and an
   in-process Fake HTTP transport, invalid primary and repair responses produced a
   request-keyed `SCORING_RAW` recovery Artifact with `RAW_RESPONSE_30D`, DATA root,
   deterministic path, SHA-256, provider/model/video bindings, and a retryable failed
   Provider Call. No structured Artifact, summary, `SCORED` transition, or successful
   Job appeared. Recursive inspection of error message/args/cause/context/attributes
   and `youtube_intel` traceback locals found none of the primary response, repair
   response, prompt/subtitle, or temporary absolute-path sentinels.
2. **Requeued recovery and transaction rollback — PASS.** Requeuing that identical Job
   validated the saved response and made exactly one `POST /api/generate` repair; the
   full Fake sequence was `GET /api/tags`, primary POST, initial-repair POST,
   recovery-repair POST. Thus requeue made no tags preflight or primary scoring call.
   A valid repair atomically created raw/structured Artifacts, completed the Provider
   Call, wrote the threshold-owned summary, advanced the Pipeline and completed the
   Job. Independent injections at `stage.after_artifacts`,
   `stage.after_provider_call`, `stage.after_scoring_summary`, and
   `stage.after_pipeline` rolled back the new success rows/files while retaining a
   subsequently usable validated recovery input.
3. **Fail-closed validation — PARTIAL / FAIL.** Hash, path, video, provider, model,
   producer, retention, storage-root, kind, expiry, modified file and missing-file
   variants all failed closed without a new primary call. However, deleting the indexed
   recovery Artifact row (the missing request-keyed recovery record) made
   `_load_verified_recovery_raw_response()` return `None` at
   `scoring.py:815-818`; `_score()` then calls `_call_provider()` at `512-517`.
   The real temporary SQLite/Fake-provider probe observed `primary_calls == 2` and no
   recovery repair. This violates the explicit L-09/missing-recovery requirement: a
   recovery attempt must not fabricate a result or issue a new primary request.

### Acceptance and ADR-007 matrix

| Item | Result | Independent evidence |
|---|---|---|
| AC-1 — strict valid/invalid/repair behavior | PASS | 14 Fake-transport integration tests plus Probe 1 covered valid, invalid, one-repair and redacted-error behavior. |
| AC-2 — bounded sampling and cache/recovery | FAIL | Sampling and verified-success cache pass, but P1-1 makes a missing indexed recovery record fall back to a new primary call. |
| AC-3 — threshold-derived durable final policy | PASS | Probe 2 confirmed the threshold-owned summary, Pipeline CAS and Job completion are atomic. |
| L-03 — recommendation separate from application decision | PASS | Existing threshold decision remains derived from score, not the model suggestion. |
| L-04 — atomic scoring summary | PASS | Success and all four post-artifact rollback probes used real temporary SQLite. |
| L-05 — bounded three-part sampling | PASS | Focused tests and range review retain fixed sampling/version behavior. |
| L-06 — metadata/hash boundary | PASS | Focused tests cover frozen input/model/prompt/schema/operation cache dimensions. |
| L-07 — standard-library local HTTP | PASS at Fake-only boundary | Injected transport only; no default transport or endpoint was invoked. |
| L-08 — fixed model preflight | PASS at Fake-only boundary | Exact model/digest Fake preflight precedes primary generation. |
| L-09 — repair, recovery and errors | FAIL | P1-1 allows a missing indexed recovery Artifact to initiate a new primary request. |

### Findings

- P0: None.
- P1-1 — `src/youtube_intel/scoring.py:499-517, 808-818`: a recovery Artifact that is
  absent from the index is indistinguishable from the first scoring attempt. On a
  requeued retry after a failed primary+repair, `_load_verified_recovery_raw_response`
  returns `None`, so the service sends another primary request. The correction's
  stated fail-closed contract and ADR-007 L-09 require a missing recovery input for
  that retry to fail safely without a new primary or claimed cache hit. Persist and
  verify an explicit recovery-required marker/binding with the retryable Provider Call,
  then reject absence or mismatch before the primary-call branch. Add a regression that
  deletes the recovery index row, not only its payload file.
- P2: None.
- P3: None.

### Five-axis review, scope, and resources

- **Correctness:** REJECT — P1-1 breaks the mandatory missing-recovery behavior.
- **Architecture:** REJECT — the successful recovery composition is narrowly aligned
  with the existing Repository API, but it lacks durable state that distinguishes an
  initial request from a recovery-required retry.
- **Security/privacy:** PASS for redaction and validated present-artifact paths; P1-1
  remains an integrity/fail-closed weakness, not a demonstrated content leak.
- **Performance:** PASS — bounded reads and a single repair ceiling remain intact; no
  unbounded query, loop, or added runtime dependency was introduced.
- **Readability:** PASS — the recovery branch and focused Fake tests are clear; the
  defect is a missing state distinction rather than an unclear implementation.
- Scope/red-line/reuse checks: PASS except P1-1. No dependency, lockfile, schema,
  migration, config, domain, task-status or main-history change; no deleted test or
  weakened assertion; no SDK or `httpx` added. Diff secret scan found no sensitive
  material.
- Intentionally unrun/unauthorized: default `urllib` transport, all real Ollama
  endpoints (including loopback), Ollama installation/start/stop, model or cloud-tag
  pull, media/YouTube/Cookie/remote-component/ffmpeg paths, Vault/credentials and
  deletion paths. All dynamic probes used only temporary SQLite/data roots and
  in-process Fakes; no network action occurred.

### Verdict

`REJECT` — all prescribed offline gates pass, but `APPROVE` requires no unresolved
P0/P1. P1-1 must be corrected and independently re-reviewed. No task status was
changed, and no merge, push, or product-source amendment was performed.
