# TASK-014 交接报告

## 元数据

- Task: `TASK-014 Phase A — Release Readiness: 发行资料与风险披露`
- Role: `Implementer`
- Agent/session: `Codex / TASK-014 Phase A`
- Base branch/commit: `main@54b5be8c28554b70b1e3f294d6ed6f9f6fee2c21`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-a`
- Branch: `codex/task-014-release-readiness-phase-a`
- Head commit: `pending implementation commit; reported to orchestrator after commit`
- Started: `2026-07-26`
- Reported: `2026-07-26`

## 目标与范围

- 任务目标：建立 V1 发行资料、第三方/供应链风险披露、No-Go 发布门禁、四阶段真实 smoke
  授权矩阵，并将 `.gitignore` 的运行路径规则锚定到仓库根。
- Reuse decision: `DIRECT` — 仅使用已锁定的项目元数据、已有 ADR/Reuse Register/验收
  记录与 Git/Markdown 文本资料；未复制第三方代码、LICENSE 或 NOTICE 全文，未新增依赖。
- 允许修改：`.gitignore`、`README.md`、`docs/SBOM.md`、`docs/THIRD_PARTY_NOTICES.md`、
  `docs/RELEASE_CHECKLIST.md`、`docs/SMOKE_AUTHORIZATION_MATRIX.md`、`handoffs/TASK-014.md`。
- 实际修改：仅上述七个路径。
- 明确未做：未发布、push、合并、rebase、reset、清理或改变任务状态；未修改依赖、锁、
  源码、测试、配置、ADR、项目 LICENSE/NOTICE、构建或验收报告。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| SBOM/NOTICE 区分已证实事实与证据缺口 | PASS | `docs/SBOM.md`、`docs/THIRD_PARTY_NOTICES.md` 仅依据已提交 `pyproject.toml`、`uv.lock` 和 ADR；不推断未证实许可证。 |
| `mutagen` GPL 与 BPE 文件级门禁 | PASS（披露） / BLOCKED（发行） | 两份发行资料均将 `mutagen==1.48.1` 分发处置和 BPE 文件级许可/NOTICE 列为阻断项。 |
| 用户可见的 at-most-once 边界 | PASS | README 与发布检查表明确 Provider→SQLite、replace→SQLite、cleanup CAS 三个残余崩溃窗口，未称 exactly-once。 |
| 四阶段 smoke 只设计、不执行 | PASS | `docs/SMOKE_AUTHORIZATION_MATRIX.md` 为每阶段列数据范围、PO 批准、成功证据和停止条件；真实 Vault 未获授权。 |
| `.gitignore` 根目录锚定 | PASS（文本） | `data/`、`logs/` 变更为 `/data/`、`/logs/`。 |
| 正式发布、真实 smoke 与最终 Go | BLOCKED | 需要 PO/TL/QA/隐私 Reviewer 的后续书面签署和独立授权。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| 已提交文档/锁文件/ADR 文本复核 | PASS | 核对直接依赖、锁定组件、BPE 哈希/来源、mutagen 门禁、离线验收边界与运维说明。 |
| `git diff --check 54b5be8...HEAD` | PASS | 无空白错误；该基线比较还包含实现前已有的控制面 commit `d0d136a`，本实现 commit 的范围见下方。 |
| `git status --short` | PASS | 最终工作树干净。 |
| pytest / mypy / ruff / build / CLI / smoke | NOT RUN（授权禁止） | Phase A 明确禁止 uv、Python/import、测试、构建、产品 CLI、真实资源和 smoke。 |

## Diff 复核

- 修改文件：本实现 commit 仅包含允许的七个路径。
- 是否存在任务范围外修改：否。`base...HEAD` 还列出实现前已有的 `d0d136a` 控制面任务包/状态快照路径；它们不属于本实现 commit。
- 是否存在生成文件或格式化噪声：预期否。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：原 `.gitignore` 未锚定 `data/`/`logs/` 的发布门禁风险已改为根目录规则。
- 跳过检查及原因：测试、类型检查、lint、构建、安装、hash、CLI 和所有真实 smoke 均被
  Phase A 包明确禁止；仅允许 Git/文本复核。
- 剩余风险：许可证/NOTICE 资料尚未构成法律或发行签署；最终目标平台的实际包含集仍需
  构建后证据（需另行授权）；离线验收不能替代真实资源验证；恢复不是严格 exactly-once。
- `DECISION NEEDED`：PO/TL/QA/隐私 Reviewer 必须书面决定最终发行形态、`mutagen` GPL
  处置、`o200k_base.tiktoken` 文件级许可/归属/NOTICE、条件性模型/ffmpeg/Ollama 的
  包含/排除、真实 smoke 授权，以及 at-most-once 风险接受。未作出这些决定前为 `NO-GO`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`pending implementation commit; supplied in implementer report`
- 复现/验证说明：仅执行任务包允许的 Git/文本检查；无运行时或真实资源验证声明。

## Reviewer 结论

- Reviewer agent/session: `not started by implementer`
- 审查 commit:
- 重新运行的检查:
- Findings:
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1:

## 主控验收

- Orchestrator:
- Verdict：`ACCEPT | REJECT`
- 依据:
- 批准整合的 commit:

## 整合结果

- Integrator:
- 主线 commit:
- 整合后检查:
- 最终状态：`DONE | BLOCKED`

## TASK-014B7 Implementer Evidence — 2026-07-28

### Fixed assignment and scope

- Task: `TASK-014B7 — safe subtitle directory origin and fingerprint`; role:
  `Implementer`.
- Required base and sole parent for the first product commit:
  `5b7dcca2ba9bd9e52e254a8944e584542838e24b`.
- Worktree/branch: `task-014b7-safe-directory-origin-fingerprint` /
  `codex/task-014b7-safe-directory-origin-fingerprint`.
- Reuse decision: `DIRECT` — reused the locked subtitle Adapter, ADR-017 B6
  `directory_diagnostic`, B4 directory-only boundary, B5 safe stdout/JSONL
  outlets, JsonlLogger, and existing offline Fake/fixture integration setup.
  No third-party code, dependency, lockfile, schema, logging, CLI, or
  configuration change was made.
- Actual paths are exactly the six authorized paths: subtitle Adapter, public
  smoke composition, one new sanitized fingerprint fixture, the two specified
  integration tests, and this handoff.

### Implemented contract and TDD evidence

- B6 `directory_diagnostic` remains unchanged and independent. Only a
  directory-stage `INVALID_RESPONSE` with one enumeration and zero body reads
  can append frozen `directory_origin` and `directory_fingerprint` labels to
  the existing stdout summary and JSONL `safe_message`.
- The two B7 vocabularies are exact ADR-018 finite sets. Mapping failures carry
  fixed origin/fingerprint pairs; extractor and decode boundaries carry their
  fixed origins; untrusted or unclassified labels reduce to fixed `*_unknown`.
  A reliably non-structural fingerprint can be omitted. No response acceptance
  rule was changed.
- RED: the first frozen-vocabulary regression failed during test collection
  because `DIRECTORY_FINGERPRINT_CODES` did not exist. After adding only the
  frozen vocabularies, the required integration command passed (`105 passed`).
  The next stdout/JSONL propagation slice failed with three missing-label
  assertions, then passed after the bounded safe-output implementation.
- Offline Fakes cover every frozen origin/fingerprint code, B6 preservation,
  unknown and omission boundaries, default one-body read, directory-only
  `1/1/0`, non-directory body `INVALID_RESPONSE` suppression, exit-code and
  no-retry boundaries, and zero business records.

### Validation and safety review

| Command/check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Completed once from local cache; no lockfile change, download, or network use. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `113 passed`; offline only. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS | `Success: no issues found in 2 source files`. |
| `.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Existing CLI topology is unchanged; no smoke was executed. |
| `git diff --check` | PASS | No whitespace errors. |

- Leakage evidence: stdout and JSONL regressions assert that raw URLs, subtitle
  body, titles, language/track data, field values, paths, original exceptions,
  Cookie, token, payload, and user-data probes are absent; stderr is empty on
  the directory failure path. The new sanitized fixture's values are also
  absent from Adapter error and diagnostic messages. Only prevalidated IDs,
  integer counts, fixed error codes, B6 diagnostics, and ADR-018 labels can
  reach the summaries.
- No real YouTube/network request, smoke, authentication, Cookie, credential,
  media, ffmpeg, Vault, model, Ollama, OpenAI, paid call, push, merge, source
  cleanup, or control-plane edit was performed. TASK-014 remains
  `IN_PROGRESS / No-Go`.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the single fixed-parent commit.
- Commit SHA: recorded in the Implementer report after commit creation; not
  self-recorded here before the commit to preserve the single-commit history.
- Remaining risk: offline Fakes prove only the constrained diagnostic and
  leakage boundary; they do not authorize real-service validation, release
  approval, or final Go.
- `DECISION NEEDED`: `None`.

## Independent Reviewer Evidence — 2026-07-26

### Fixed review object and cleanliness

- Review role: independent Codex Reviewer; source worktree:
  `/Users/hua/Documents/yia-worktrees/task-014-release-readiness-phase-a`.
- Fixed control-plane base: `main@d0d136a4754a97954f64f1ca39b87837e639decc`.
- Reviewed source HEAD: `8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59`; sole parent confirmed as
  `d0d136a4754a97954f64f1ca39b87837e639decc`.
- `git diff --name-status d0d136a...8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59`
  contained exactly the seven authorized paths: `.gitignore`, `README.md`,
  `docs/RELEASE_CHECKLIST.md`, `docs/SBOM.md`,
  `docs/SMOKE_AUTHORIZATION_MATRIX.md`, `docs/THIRD_PARTY_NOTICES.md`, and
  this handoff. `git diff --check` was clean. Before this reviewer append,
  `git status --short` was empty and the handoff had no uncommitted change.

### Independent document and metadata review

- **SBOM / NOTICE / lock consistency:** `pyproject.toml` direct dependencies and
  `uv.lock` agree with the SBOM: Jinja2 `3.1.6`, mlx-whisper `0.4.3`, OpenAI
  `2.46.0`, Pydantic `2.13.4`, PyYAML `6.0.3`, tiktoken `0.13.0`, and
  `yt-dlp[default,deno]` `2026.7.4`; development tools are separately identified.
  The lock has 84 package entries, and SBOM's non-root, non-direct list accounts
  for the remaining resolved packages. `uv.lock` records `mutagen==1.48.1` in
  yt-dlp's `default` extra and Jinja2's MarkupSafe dependency. SBOM and NOTICE
  correctly distinguish existing ADR/Reuse Register license facts from
  `EVIDENCE GAP`; neither treats a lock, offline package evidence, or historical
  checks as a distribution approval or legal conclusion.
- **GPL, BPE, and project-license gates:** the documents preserve
  `mutagen` GPL-2.0-or-later as a blocker for source/binary/bundle/container
  distribution pending TL/release-owner disposition. They preserve the official
  `o200k_base.tiktoken` source, fixed SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`, and
  no-runtime-network-fallback contract while leaving its file-level license,
  attribution, NOTICE, and distribution decision blocked. They do not create or
  imply a project LICENSE; final PO/TL/QA/privacy-reviewer signatures remain
  required.
- **No-Go and real-resource accuracy:** README, release checklist, and the
  TASK-013 acceptance report consistently limit existing evidence to fixtures,
  temporary SQLite/DATA/Vault, and Fakes. They state that real YouTube/subtitles,
  media/ffmpeg/Whisper, Ollama/fixed model, OpenAI/credentials/paid calls,
  launchd, real Vault/user notes, and backup/recovery rehearsal are not
  authorized or not run. No document represents those as verified.
- **At-most-once disclosure:** README and the checklist explicitly retain all
  three residual crash windows—external Provider to SQLite, atomic file replace
  to SQLite, and audio-cleanup final CAS—and label the guarantee
  `at-most-once best effort`, not strict/exactly-once or an accepted release
  risk. This matches ADR-008, ADR-009, ADR-012, System Design, and the existing
  acceptance evidence.
- **Future smoke authorization only:** the matrix is explicitly
  `NOT AUTHORIZED / NOT EXECUTED` and fully specifies the four future phases:
  public YouTube/subtitles; controlled media plus ffmpeg/Whisper; loopback
  Ollama plus fixed model; and OpenAI plus a new temporary Vault. Each phase has
  controlled data scope, required PO approval, success evidence, and stop
  conditions. It explicitly excludes real Vault/user notes from Phase A and
  from the authorization implied by the matrix.
- **Root ignore anchoring:** the only runtime-ignore edit is `data/` -> `/data/`
  and `logs/` -> `/logs/`; no additional ignore semantics were introduced.

### Verification limits and conclusion

- Permitted checks run: Git identity/parent/range/status/diff/diff-check and
  Markdown, `pyproject.toml`, `uv.lock`, ADR, Reuse Register, operations, task,
  and acceptance-report text inspection only.
- Not run or accessed: tests, type checking, lint, build/package/install, uv,
  Python/imports, CLI/doctor, any smoke, network, YouTube, ffmpeg, Whisper,
  Ollama, OpenAI, launchd, credentials, SQLite, logs/cache/media, or any Vault.
- Findings: **no P0–P3 findings**.
- Verdict: **APPROVE** for the Phase A documentation review only. This is not a
  release approval, legal opinion, real-smoke authorization, risk acceptance,
  or final Go decision; the documented No-Go gates remain open.

## TASK-014B5 Implementer Evidence — 2026-07-28

### Fixed assignment and scope

- Task: `TASK-014B5 — safe smoke summary output`; role: `Implementer`.
- Base and sole required parent for the implementation commit:
  `main@b1ea7a66aaf513aa0fa8262780f9c59072cc18b4`.
- Worktree/branch: `task-014b5-safe-smoke-summary` /
  `codex/task-014b5-safe-smoke-summary`.
- Reuse decision: `DIRECT` — reused the existing restricted CLI,
  `PublicSubtitleSmoke`, fixed `ErrorCode` values, ADR-015
  `directory_diagnostic`, `JsonlLogger`, and offline Fake integration setup;
  no third-party code or dependency was added.
- Actual implementation paths: `src/youtube_intel/public_subtitle_smoke.py`,
  `tests/integration/test_public_subtitle_smoke.py`, and this handoff. No
  change was needed to `cli.py` or `test_operations.py`; both remain in the
  allowed scope but are intentionally untouched.

### Implemented contract

- Each processed `smoke-public-subtitles` target emits exactly one compact JSON
  line to stdout in fixed insertion order: `video_id`, `metadata`,
  `enumerate`, `read`, `error_code`, then (only for directory
  `INVALID_RESPONSE`) `directory_diagnostic`.
- `OK` is the explicit fixed safe success code. Failure summaries reuse only
  the existing fixed safe error code and ADR-015 fixed diagnostic; no JSONL
  schema or `logging.py` change was made.
- Default smoke retains one selected-body read; directory-only success and
  directory `INVALID_RESPONSE` retain per-target `1/1/0` counts and existing
  exit-code semantics.

### RED/GREEN and offline checks

| Command/check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Completed once from the locked local cache; no download or lockfile change. |
| Focused pytest before implementation | RED | Three new Fake summary regressions failed because stdout was empty; existing 16 tests passed. |
| `.venv/bin/pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py` | PASS | `19 passed`; covers directory-only success, directory `INVALID_RESPONSE`, default one-body read, global-config early rejection, non-smoke flag rejection, input limits, no retry, and zero business records. |
| `.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py` | PASS | `Success: no issues found in 2 source files`. |
| `.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py tests/integration/test_public_subtitle_smoke.py tests/integration/test_operations.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Existing command structure, including `smoke-public-subtitles`, is unchanged. |

### Security and diff review

- The new Fake assertions decode stdout and require only the frozen keys and
  fixed values. They reject URL, subtitle body, title, language, field value,
  raw exception, temporary path, Cookie, token, payload, and user-data probes;
  stderr remains empty. Existing JSONL assertions continue to reject the same
  sensitive fixture values and prove the schema is unchanged.
- Before commit, the diff contains only the three paths above; it contains no
  dependency, lockfile, Schema/migration, configuration, credential, Vault,
  network, media, authentication, model, push, or merge change. `git diff
  --check` is clean.
- No real smoke, YouTube/network request, media, authentication, Cookie,
  credential, Vault, model, OpenAI/Ollama, paid call, launchd action, push, or
  merge was performed. TASK-014 remains `IN_PROGRESS / No-Go`.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the single implementation commit below.
- Commit SHA: reported externally after this single fixed-parent implementation
  commit (not self-recorded to preserve the one-commit history).
- Remaining risk: offline Fakes validate the bounded output contract only; they
  do not authorize or demonstrate real-service behavior, release approval, or
  final Go.
- `DECISION NEEDED`: `None`.

## TASK-014B5 Independent Reviewer Evidence — 2026-07-28

### Fixed review identity and scope

- Role: `Independent Reviewer`; reviewed branch:
  `codex/task-014b5-safe-smoke-summary`.
- Reviewed implementation: `ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1`; sole
  parent verified as `b1ea7a66aaf513aa0fa8262780f9c59072cc18b4`.
- Reviewer authorization verified: `main@6ceaca1431205880f6acd0aed466b9a5d28f0e17`
  is a descendant of the package's control-plane authorization commit.
- Product review range:
  `b1ea7a66aaf513aa0fa8262780f9c59072cc18b4...ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1`.
  Cleanliness and complete diff were independently verified before review.
- Exact product paths are limited to
  `src/youtube_intel/public_subtitle_smoke.py`,
  `tests/integration/test_public_subtitle_smoke.py`, and this handoff; no
  dependency, lockfile, Schema, configuration, credential, Vault, network,
  authentication, media, model, push, or merge change is present.

### Independent review findings

- Fixed stdout contract: PASS. `_emit_summary` builds compact JSON in the
  stable order `video_id`, `metadata`, `enumerate`, `read`, `error_code`, then
  optional `directory_diagnostic`. The only dynamic identifier is the
  prevalidated 6--32-character video ID; counts are integers. Success uses
  fixed `OK`; failures use only the frozen `ErrorCode` set. The optional
  diagnostic is emitted only for the existing enumerate-stage
  `INVALID_RESPONSE` / zero-read condition and is restricted to ADR-015's
  frozen diagnostic-code set.
- Behavior and boundary preservation: PASS. Default mode still ranks and reads
  exactly one body per successful target. Directory-only success and
  enumerate-stage `INVALID_RESPONSE` are respectively verified as `1/1/0`.
  The unchanged CLI continues to reject smoke global configuration input before
  initialization; non-smoke command parsing, 1--3 unique-ID checks, temporary
  root, 30-second timeout, no-retry, and fail-closed exit-code boundaries are
  unchanged.
- Leakage review: PASS. Static inspection confirms no raw exception, response
  body, URL, title, language/field value, path, Cookie, token, payload, user
  data, or credential flows to the new stdout call. The Fake failure probes
  independently assert these values are absent from stdout and existing JSONL;
  stderr is empty for the exercised successful and directory-failure paths.
  Existing JSONL remains limited to its established safe-message schema.

### Re-run evidence

| Command/check | Result | Evidence |
|---|---|---|
| Git branch/HEAD/sole-parent/status/range/path scope | PASS | Branch, `ce4b472...`, sole parent `b1ea7a...`, clean worktree, and exact three-path range verified. |
| `git diff --check b1ea7a...ce4b472...` | PASS | No whitespace errors. |
| `.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py` | PASS | `10 passed`; offline Fakes cover default read, directory-only `1/1/0`, fixed JSON summaries, safe directory failure, global configuration rejection, ID limits, and no retry. |
| `.venv/bin/pytest tests/integration/test_operations.py` | PASS | `9 passed`; non-smoke command boundary remains intact. |
| `.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py` | PASS | `Success: no issues found in 2 source files`. |
| `.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py tests/integration/test_public_subtitle_smoke.py tests/integration/test_operations.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Existing command topology remains available; no smoke execution occurred. |
| Static output/leak scan and code-path review | PASS | New stdout is the single `_emit_summary` call; all emitted value sources are safe/fixed as above. |

### Reviewer conclusion

- Findings: `P0=0, P1=0, P2=0, P3=0`.
- Not run: build/package installation, full suite, real CLI subcommands, real
  smoke, YouTube/network, media/ffmpeg, authentication/Cookie/credentials,
  Vault, model/Ollama/OpenAI, SQLite diagnostics, launchd, push, or merge. The
  task package forbids them; all executed validation used offline Fakes.
- Verdict: `APPROVE`.
- TASK-014 remains `IN_PROGRESS / No-Go`. This offline review neither validates
  a real service nor grants release approval, final Go, or any real-resource
  authorization.

## TASK-014B6 Implementer Evidence — 2026-07-28

### Fixed assignment and implementation

- Task: `TASK-014B6 — safe subtitle directory shape diagnostics`; role:
  `Implementer`.
- Base and required sole parent for the implementation commit:
  `7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`.
- Worktree/branch: `task-014b6-safe-directory-shape-diagnostics` /
  `codex/task-014b6-safe-directory-shape-diagnostics`.
- Reuse decision: `DIRECT` — reused the locked subtitle Adapter, existing
  `directory_diagnostic` route, directory-only boundary, safe stdout/JSONL
  output, and offline Fake/fixture integration infrastructure. No external
  code, dependency, license, lockfile, schema, logging, or CLI change was made.
- The Adapter now exposes exactly these fixed B6 categories only when directory
  enumeration ends as `INVALID_RESPONSE`: `directory_shape_missing`,
  `directory_shape_not_object`, `directory_shape_not_list`,
  `directory_shape_empty_list`, `directory_shape_unsupported_entry`,
  `directory_extractor_directory_error`, and `directory_shape_unknown`.
  Existing safe summary outlets consume the same `directory_diagnostic`; no
  output schema or additional output surface was added.

### TDD and acceptance evidence

| Check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Completed once solely from the locked local cache; no lockfile change or download failure. |
| Focused integration suite before Adapter implementation | RED | `16 failed, 86 passed`; new B6 expectations demonstrated the former B3 diagnostics and the accepted missing-field case. |
| Focused integration suite after implementation | PASS | `103 passed`; covers every fixed B6 category, exact allowed-category set, safe stdout/JSONL outlet, default body-read count, directory-only `1/1/0`, exit handling, ID limits, no retry, and zero business records. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py` | PASS | `Success: no issues found in 1 source file`. |
| `.venv/bin/ruff check src/youtube_intel/providers/subtitles.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Command topology is unchanged. |

### Safety and scope review

- Added one sanitized structural fixture and no runtime data. The regression
  suite asserts that each diagnostic is a fixed category, is emitted only via
  the established safe outlets, and carries no response-derived value.
- The Adapter retains strict identity, URL, field, length, count, and format
  checks. An unsupported-only directory remains rejected; a directory with a
  supported track retains the existing selection behavior and does not expand
  the accepted input surface.
- Default and directory-only body-read behavior, exit semantics, temporary
  root, ID bound, retry prohibition, and zero-business-record boundary are
  unchanged by focused regressions. No real service, network, media,
  authentication, Vault, model, or paid resource was accessed.
- Product diff is limited to the authorized Adapter, one fixture, two
  integration tests, and this handoff. No generated artifacts or control-plane
  files are included.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the single fixed-parent implementation
  commit.
- Commit SHA: pending the required final diff, leak, and scope checks.
- Remaining risk: offline fixtures prove only the bounded diagnostic and output
  contract; they do not demonstrate real-service compatibility or alter
  TASK-014 `IN_PROGRESS / No-Go`.
- `DECISION NEEDED`: `None`.

## TASK-014B6 Correction 1 Implementer Evidence — 2026-07-28

### Fixed assignment and minimal correction

- Required source branch/HEAD/sole parent were verified before writing:
  `codex/task-014b6-safe-directory-shape-diagnostics` at
  `9403e37eedbd2513aea631c7272c6d650d41ef40`, whose sole parent is
  `7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`; the worktree and index were
  clean.
- Reuse decision: `DIRECT` — reused the existing locked subtitle Adapter
  vocabulary, smoke safe-summary route, directory-only boundary, JSONL outlet,
  and offline Fake test infrastructure. No external code, dependency, license,
  lockfile, schema, Provider, CLI, or logging change was made.
- The sole behavioral change makes an unknown directory `INVALID_RESPONSE`
  fallback exactly `directory_shape_unknown`; it does not alter the seven
  existing ADR-017 codes or the directory parser's accepted input surface.

### TDD and offline validation

| Check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Run once from the locked local cache: `Resolved 84 packages` and `Checked 61 packages`; no download or lockfile change. |
| New unknown-directory regression before implementation | RED | Focused suite: `1 failed, 10 passed`; the new stdout assertion observed old `directory_unknown_invalid_response` instead of exact `directory_shape_unknown`. |
| `.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py` | PASS | `11 passed`; the new offline Fake verifies directory-only `metadata=1 / enumerate=1 / read=0`, `INVALID_RESPONSE`, exact safe stdout and exact JSONL `safe_message`. |
| `.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py` | PASS | `Success: no issues found in 1 source file`. |
| `.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py tests/integration/test_public_subtitle_smoke.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Help only; command topology unchanged and no smoke was run. |

### Safety, scope, and remaining risk

- The new regression injects a private URL, token, title, field value, Cookie,
  body, payload, and temporary path through the Fake exception, then proves
  each is absent from both stdout and JSONL. It also proves the former fallback
  is absent from both surfaces.
- Focused regression preserves the nonzero execution-failed exit, zero body
  reads, no retry, temporary-root isolation, ID boundary, and zero business
  records. Default-mode behavior remains covered by the unchanged focused
  suite.
- Final diff is restricted to `public_subtitle_smoke.py`, its integration test,
  and this handoff; no real YouTube, network, smoke, authentication, media,
  Vault, model, or paid resource was used.
- TASK-014 and TASK-014B6 remain `IN_PROGRESS / No-Go`; this offline correction
  is not real-service validation, release approval, or a status transition.

## TASK-014B6 Correction 1 Range-Corrected Independent Reviewer Evidence — 2026-07-28

### Fixed review object and scope

- Role: new independent Reviewer. Reviewed source branch/HEAD:
  `codex/task-014b6-safe-directory-shape-diagnostics` at
  `b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78`.
- The correction's sole parent is
  `9403e37eedbd2513aea631c7272c6d650d41ef40`; the original implementation's
  sole parent is `7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`.
- Dynamic reviewer authorization was verified at
  `main@44e7c0c45f59914d58a184ad1d3f0975c67c3c2d`, a clean single-parent
  descendant of the stated control-plane base. The source worktree and index
  were clean before this evidence append.
- Correction range contains exactly `public_subtitle_smoke.py`,
  `test_public_subtitle_smoke.py`, and this handoff. Complete B6 range contains
  exactly the six range-corrected paths: subtitle Provider, smoke adapter,
  sanitized directory-shape fixture, the two integration tests, and this
  handoff. Both range checks are whitespace-clean.

### Independent behavior and security review

- Unknown directory `INVALID_RESPONSE` is emitted to the existing safe stdout
  and JSONL outlets only as `directory_shape_unknown`; the former
  `directory_unknown_invalid_response` value is absent from the source output
  path and is explicitly rejected by the offline regression.
- The frozen set is exact and complete: `directory_shape_missing`,
  `directory_shape_not_object`, `directory_shape_not_list`,
  `directory_shape_empty_list`, `directory_shape_unsupported_entry`,
  `directory_extractor_directory_error`, and `directory_shape_unknown`.
  The adapter maps structural failures only to this set and keeps unknown
  failures fail-closed.
- The regression injects URL, title, field value, Cookie, token, body, payload,
  temporary path, and the former fallback through a Fake directory error, then
  proves each is absent from stdout and JSONL. Static outlet review found one
  stdout emission and only fixed codes/counts in the diagnostic path; the
  fixture contains structural synthetic values only.
- Default one-body-read behavior; directory-only `1/1/0`; nonzero failure exit;
  CLI/global-option rejection; new-empty temporary-root requirement; 1--3
  unique-ID bounds; no retry; zero business records; URL, format, size, count,
  language, entry, and unsupported-directory fail-closed behavior remain
  covered by the focused suites and unchanged control flow.

### Independent checks and verdict

| Check | Result |
|---|---|
| `git` identity, parent-chain, authorization, status, both ranges, and `git diff --check` | PASS |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py` | PASS — 93 passed |
| `.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py` | PASS — 11 passed |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS — no issues in 2 source files |
| `.venv/bin/ruff check` on B6 Provider/smoke source and integration tests | PASS |
| `.venv/bin/youtube-intel --help` | PASS — help only; no smoke subcommand run |
| Static category/output/fixture leak scan | PASS |

- Findings: `P0=0, P1=0, P2=0, P3=0`.
- Not run: `uv`, build/package checks, full suite, Python/import probes, any
  smoke invocation, network/YouTube, media/ffmpeg, authentication/Cookie/API
  key handling, Vault/user data, SQLite diagnostics, models/Ollama/OpenAI,
  launchd, push, or merge.
- Verdict: `APPROVE` for the fixed offline correction range only. TASK-014
  remains `IN_PROGRESS / No-Go`; this is neither real-service verification nor
  release approval or final Go.

## TASK-014B7 Correction 1 Implementer Evidence — 2026-07-28

### Fixed source and scope

- Required source branch, HEAD, sole-parent chain, and cleanliness were verified
  before writing: `codex/task-014b7-safe-directory-origin-fingerprint` at
  `8d06197557de4ce92c2752f4a8ef74582a0efdca`, whose sole parent is
  `5b7dcca2ba9bd9e52e254a8944e584542838e24b`.
- Reuse decision: `DIRECT` — retained the locked subtitle Adapter, ADR-017 B6
  diagnostic outlet, ADR-018 frozen labels, B4 directory-only boundary, B5
  safe stdout/JSONL outlets, and existing offline integration infrastructure.
  No external code, dependency, lockfile, schema, Provider, CLI, logging, or
  configuration changed.
- Actual correction paths are exactly the approved fixture deletion, the two
  integration tests, and this handoff. No production path was modified.

### TDD and offline validation

| Check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Ran once; `Resolved 84 packages` and `Checked 61 packages`; no download or lockfile change. |
| Fixture-removal regression before replacement double | RED | `11 failed, 102 passed`: six fingerprint cases identified the absent replacement helper; the remaining five confirmed an empty error message cannot bypass the existing domain validation. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `113 passed`; offline only. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS | `Success: no issues found in 2 source files`. |
| `.venv/bin/ruff check tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Help only; CLI topology unchanged and no smoke was run. |

### Contract, leakage, and range review

- The deleted fixture is replaced only in memory by an opaque Mapping double:
  it supplies structural outcomes and opaque objects, not directory field names,
  field values, URLs, titles, languages, track names, paths, or original
  response text. The six ADR-018 fingerprints, their mapping origin, and their
  existing B6 diagnostics remain individually covered.
- Existing offline Fakes retain all four fixed origins, all six fingerprints,
  B6 diagnostic preservation, directory failure `enumerate=1/read=0`, optional
  safe fingerprint omission, and body-stage suppression of directory labels.
  Exact stdout JSON and JSONL `safe_message` assertions constrain output to
  fixed labels/counts; stderr is asserted empty on the directory-only failure
  path, and failure records cannot contain dynamic message or error fields.
- Default one-body-read behavior, directory-only `1/1/0`, nonzero failure exit,
  no-retry, temporary-root isolation, ID bounds, and zero business records stay
  covered by the focused suite. `git diff --check` is clean after the handoff
  update.
- No real YouTube/network request, smoke, authentication, Cookie/credential,
  media, Vault, model, OpenAI/Ollama, paid call, push, merge, source cleanup,
  or control-plane edit occurred. TASK-014 remains `IN_PROGRESS / No-Go`.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the required single fixed-parent
  Correction commit.
- Commit SHA: reported to the orchestrator after commit creation; not
  self-recorded before the commit.
- Remaining risk: offline doubles prove only the bounded structural and output
  contract; they neither validate a real service nor grant release approval.
- `DECISION NEEDED`: `None`.

## TASK-014B7 Correction 2 Implementer Evidence — 2026-07-28

### Fixed source and scope

- Required branch, source HEAD, three-step parent chain, and cleanliness were
  verified before writing: `codex/task-014b7-safe-directory-origin-fingerprint`
  at `069e62ececada5152871fb7c626e64c146a270ad`; its sole parent is
  `8d06197557de4ce92c2752f4a8ef74582a0efdca`, whose sole parent is
  `5b7dcca2ba9bd9e52e254a8944e584542838e24b`.
- Reuse decision: `DIRECT` — retained the locked Adapter, ADR-017 B6
  diagnostics, ADR-018 fixed labels, B4 directory-only boundary, B5 safe
  summary outlets, and offline integration infrastructure. No external code,
  dependency, lockfile, schema, CLI, logging, or configuration changed.
- Actual correction paths are the private Adapter implementation, its
  integration test, and this handoff. The permitted smoke integration test was
  intentionally unchanged because its existing outlet regressions remain valid.

### TDD and offline validation

| Check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Ran once; `Resolved 84 packages` and `Checked 61 packages`; no download or lockfile change. |
| New state-classification regression before implementation | RED | Collection stopped with `AttributeError` because the private state enum did not exist. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `114 passed`; offline only. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py` | PASS | `Success: no issues found in 1 source file`. |
| `.venv/bin/ruff check src/youtube_intel/providers/subtitles.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `All checks passed!` |
| `.venv/bin/youtube-intel --help` | PASS | Help only; command topology unchanged and no smoke was run. |

### Contract, safety, and range review

- Adapter structure checks remain in their existing branches. Their only path
  to ADR-018 mapping labels now goes through a private function that accepts a
  closed enum state and returns a fixed origin/fingerprint pair. The enum uses
  no response-derived values; non-enum input is rejected.
- The regression uses only closed enum states and an opaque non-state object.
  It covers the mapping origin and every frozen fingerprint without restoring a
  fixture or materializing any response-shaped test object. Existing regressions
  retain B6 diagnostics, extractor/decode/unknown origins, body-stage label
  suppression, directory `enumerate=1/read=0`, fixed stdout and JSONL output,
  empty stderr, exit handling, no retry, temporary-root isolation, ID bounds,
  and zero business records.
- `git diff --check` is clean. The correction does not alter parsing outcomes,
  read counts, default or directory-only behavior, output schema, or resource
  permissions. No real external resource, authentication material, media,
  Vault, model, paid call, push, merge, source cleanup, or control-plane edit
  occurred. TASK-014 remains `IN_PROGRESS / No-Go`.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the required single fixed-parent
  Correction commit.
- Commit SHA: reported to the orchestrator after commit creation; not
  self-recorded before the commit.
- Remaining risk: offline tests prove only the fixed internal classification
  and bounded output contract; they neither validate a real service nor grant
  release approval.
- `DECISION NEEDED`: `None`.

## TASK-014B7 Correction 2 Independent Reviewer Evidence — 2026-07-28

### Fixed review object

- Role: `Independent Reviewer`.
- Source/branch: `/Users/hua/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint` /
  `codex/task-014b7-safe-directory-origin-fingerprint`.
- Reviewed correction: `4d4366f6a6403403a0d9bed65fbbf862a362eede`.
- Parent chain: Correction 2 has sole parent `069e62ececada5152871fb7c626e64c146a270ad`,
  then `8d06197557de4ce92c2752f4a8ef74582a0efdca`, then
  `5b7dcca2ba9bd9e52e254a8944e584542838e24b`.
- Dynamic authorization: clean `main@a14bf1b2405bb90eea175c8da2ec4763eec64a69`
  descends from the control-plane baseline. Both source and main were clean at
  the pre-write verification.

### Independent review and evidence

- Correction range is exactly `src/youtube_intel/providers/subtitles.py`,
  `tests/integration/test_subtitle_provider.py`, and this handoff. The complete
  B7 range is the permitted five-path subset; the unsafe fixture is absent and
  no matching/replacement fixture path exists.
- The private `_DirectoryStructureState` has exactly six closed, no-value
  structural states. `_classify_directory_structure` rejects non-state input
  and maps every state to fixed mapping origin plus exactly one ADR-018
  fingerprint. Existing adapter branches retain ADR-017 B6 diagnostics and
  delegate only fixed local state to that classifier; no parsed response value
  becomes a label.
- Static review confirms the four ADR-018 origins, six fingerprints, B6
  diagnostics, directory-only `enumerate=1/read=0`, body-stage label
  suppression, fixed stdout/JSONL outlets, and the existing default/no-retry,
  temporary-root, ID-bound, zero-business-record and fail-closed paths are
  unchanged outside the intentional internal classification delegation.
- Static scans of Correction 2 added source/test lines found no URL, field
  name/value, language, track name, identity value, raw response, Cookie,
  token, payload, or user-data material. The deleted fixture was not restored,
  renamed, embedded, or moved.

| Check | Result |
|---|---|
| source/main branch, HEAD, three-parent chain, authorization, and cleanliness | PASS |
| Correction three-path range; complete B7 five-path subset; smoke test intentionally unchanged | PASS |
| fixture deletion/non-reappearance and added-line leakage scan | PASS |
| static private-state/classifier call-path and unaffected-boundary review | PASS |
| `git diff --check` for Correction and complete B7 ranges | PASS |
| focused pytest, mypy, Ruff, and console `--help` | NOT RUN — no existing source `.venv` executable was available |

### Reviewer conclusion

- Findings: `P0=0, P1=0, P2=0, P3=0`.
- Verdict: `APPROVE` for the fixed offline Correction 2 range.
- Not run: `uv`, build/package checks, full suite, Python/import probes, any
  smoke invocation, network/YouTube, media/ffmpeg, authentication/Cookie/API
  key handling, Vault/user data, SQLite diagnostics, models/Ollama/OpenAI,
  launchd, push, or merge.
- TASK-014 remains `IN_PROGRESS / No-Go`; this review is neither real-service
  verification nor release approval or final Go.

## TASK-014B8 Implementer Evidence — 2026-07-29

### Fixed assignment, reuse, and scope

- Task: `TASK-014B8 — restricted directory keyname diagnostic`; role:
  `Implementer`.
- Required base, verified branch, and pre-write HEAD:
  `43f2c748c43215facb231f76a0c93ac45d350657` on
  `codex/task-014b8-restricted-directory-keyname-diagnostic`.
- Reuse decision: `DIRECT` — reused the existing subtitle Adapter, B4
  directory-only boundary, B5 safe summary outlets, B6 diagnostics, B7
  origin/fingerprint labels, and offline integration infrastructure. No
  third-party code, dependency, lockfile, schema, CLI, logging, configuration,
  fixture, or control-plane change was made.
- Actual implementation range is the Adapter, smoke composition, the two
  approved integration tests, and this handoff only.

### Contract and TDD evidence

- RED: the new offline regressions first failed with two missing Adapter
  attributes and one missing safe-summary field. After the bounded
  implementation, the required suite passed. A first GREEN iteration exposed
  a pre-existing exact iterator-consumption regression for a non-`dict`
  Mapping; the implementation now treats every non-`dict` Mapping as an
  unreliable candidate set and omits the optional field, preserving that
  fail-closed boundary.
- The Adapter examines only direct keys of a plain directory `dict`; it neither
  recurses nor reads mapping values for this diagnostic. Any non-string or
  non-canonical key, more than 16 unique keys, or unreliable mapping omits the
  complete set. Accepted sets are deduplicated and ASCII-sorted before they can
  be attached to a mapping/unknown directory error.
- The smoke outlet independently requires directory-only, `INVALID_RESPONSE`,
  mapping origin, unknown fingerprint, `enumerate=1`, and `read=0`. It
  revalidates tuple type, canonical ordering, uniqueness, the 16-item cap, and
  the approved ASCII pattern before emitting the optional
  `directory_key_names` array in stdout and the existing JSONL safe message.
  Default mode, known fingerprints, non-mapping origins, body reads, malformed
  sets, and over-limit sets omit it.

### Offline checks and safety review

| Check | Result | Evidence |
|---|---|---|
| `uv sync --locked --offline` | PASS | Ran once from cache; lockfile unchanged and no download occurred. |
| RED focused pytest | PASS (expected failure) | Three new assertions failed before implementation; no pre-existing test was changed or skipped. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | `119 passed`; offline only. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS | No issues in 2 source files. |
| `.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS | All checks passed. |
| `.venv/bin/youtube-intel --help` | PASS | Help only; no smoke was invoked and CLI topology is unchanged. |
| `git diff --check` | PASS | No whitespace errors. |

- Added regressions use only synthetic, canonical key identifiers and opaque
  invalid candidates. They assert stdout, stderr, JSONL, default/directory-only
  read counts, exit behavior, and no-retry behavior. The allowed key-name array
  is the sole new response-derived output; no other response material is added
  to tests, summaries, logs, or this handoff.
- No real service, network request, smoke, authentication material, media,
  Vault, model, paid call, push, merge, source cleanup, or control-plane edit
  occurred. TASK-014 remains `IN_PROGRESS / No-Go`.

### Implementer conclusion

- Suggested status: `IN_REVIEW` after the required single fixed-parent commit.
- Commit SHA: reported to the orchestrator after commit creation.
- Remaining risk: offline Fakes prove only the restricted diagnostic and its
  fail-closed output boundary; they do not validate a real service or grant
  release approval.
- `DECISION NEEDED`: `None`.

## TASK-014B8 Independent Reviewer Evidence — 2026-07-29

### Fixed review object and preflight

- Role: `Independent Reviewer`.
- Source/branch: `/Users/hua/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic` /
  `codex/task-014b8-restricted-directory-keyname-diagnostic`.
- Reviewed implementation: `2334374f66497546108d12be541ab137b4a8981a`; its sole
  parent is `43f2c748c43215facb231f76a0c93ac45d350657`.
- Dynamic authorization: clean `main@a3a905db8bfef0326a2625eac76e199b8b01f2f3`
  descends from `main@a8ea95775f452203958ec2abb56b8eeb317917f3`; its only
  intervening changes are the B8 control-plane documents. Source and main were
  clean before this evidence append.
- The complete product range is exactly the five authorized paths: Adapter,
  smoke composition, two integration tests, and this handoff. No dependency,
  lockfile, Schema, logging, CLI, fixture, configuration, or control-plane
  product change is present. Reuse decision remains `DIRECT`.

### Independent ADR-019 review

- The Adapter examines only direct keys of an exact directory `dict`, never
  traverses or reads values, and fails closed for non-dict mappings, iteration
  faults, malformed keys, and more than 16 unique keys. Accepted keys are
  deduplicated, ASCII-sorted, and fully constrained by the ADR-019 pattern.
- The smoke outlet independently requires directory-only, directory
  `INVALID_RESPONSE`, mapping origin, unknown fingerprint, and exactly one
  enumeration with zero reads. It revalidates tuple type, canonical order,
  uniqueness, cap, and pattern before adding the permitted key-name array to
  stdout or the existing JSONL safe message.
- Default mode, successful directories, known/non-mapping directory failures,
  body failures, malformed sets, and over-limit sets omit the optional field.
  B6/B7 labels and the existing read counts, exit behavior, CLI, temporary-root,
  ID-bound, no-retry, zero-business-record, parsing, and fail-closed boundaries
  are unchanged outside the narrow diagnostic path.
- Diff and added-line leakage review found no response-derived value, URL,
  subtitle text, title, language or track value, path, raw exception,
  credential, payload, or user-data material. The only newly emitted
  response-derived material is the ADR-019-authorized synthetic safe key-name
  array.

| Check | Result |
|---|---|
| source/main authorization, branch, HEAD, sole parent, cleanliness, and dynamic-main product-surface check | PASS |
| fixed range, five-path allowlist, `git diff --check`, dependency/logging/CLI exclusion | PASS |
| static ADR-019 trigger, negative-boundary, B6/B7 preservation, and output-leak review | PASS |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS — 119 passed |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS |
| `.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS |
| `.venv/bin/youtube-intel --help` | PASS — help only |

### Reviewer conclusion

- Findings: `P0=0, P1=0, P2=0, P3=0`.
- Verdict: `APPROVE` for `43f2c748c43215facb231f76a0c93ac45d350657...2334374f66497546108d12be541ab137b4a8981a`.
- Not run: `uv`, build/package checks, full suite, Python/import probes, any
  smoke invocation, network/YouTube, media/ffmpeg, authentication/Cookie/API
  key handling, Vault/user data, database diagnostics, models/Ollama/OpenAI,
  launchd, push, or merge.
- TASK-014B8 remains `IN_REVIEW`; TASK-014 remains `IN_PROGRESS / No-Go`.
  This offline review is neither real-service verification nor release approval
  or final Go.

## TASK-014B10 Implementer Evidence — 2026-07-29

### Fixed assignment and scope

- Role: `Codex Implementer`.
- Source/branch: `/Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic` /
  `codex/task-014b10-safe-content-availability-diagnostic@6fd7b5cc3fae6466fb6181151513f4854d196683`.
- Required sole parent of the Implementer commit: `6fd7b5cc3fae6466fb6181151513f4854d196683`;
  its source parent is `e975ff4f343442e69bb88e09e36bffc7996341cf`. Source and dynamic control-plane main
  were clean before writing.
- Reuse decision: `DIRECT` — existing locked subtitle Adapter, B4 directory-only composition, B5 safe summary outlet,
  ADR-015--ADR-019 safety boundaries, `JsonlLogger.safe_message`, and offline integration tests. No third-party code,
  dependency, lockfile, or license change was introduced; existing `yt-dlp` reuse and license evidence remain in
  `docs/REUSE_REGISTER.md`.
- Actual product and test paths: `src/youtube_intel/providers/subtitles.py`,
  `src/youtube_intel/public_subtitle_smoke.py`, `tests/integration/test_subtitle_provider.py`, and
  `tests/integration/test_public_subtitle_smoke.py`. No other product path changed.

### Product behavior and TDD evidence

- Adapter error mapping now attaches only a closed, value-free availability code from its private internal state.
  The existing `CONTENT_UNAVAILABLE` error code, retry behavior, and parsing branches remain unchanged.
- Only directory-only failures with `CONTENT_UNAVAILABLE`, one enumeration, and zero body reads append the code to
  the existing stdout summary and JSONL `safe_message`; a missing or invalid internal state emits the fixed
  `content_availability_unknown` fallback. Default smoke, all body reads, successes, other error codes, and B4--B8
  directory diagnostics omit it.
- RED command: `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py`
  exited `1` with the new eight assertions failing: the internal state classifier did not exist and the safe
  directory-only `CONTENT_UNAVAILABLE` summary lacked `content_availability`.
- GREEN and REFACTOR: the same focused offline command passed with `127 passed`. Tests use only fixed codes and
  no-value internal states or stand-ins; no response-shaped fixture was added.

### Offline checks and safety review

| Check | Result |
|---|---|
| `uv sync --locked --offline` | PASS — run once; lockfile unchanged, no download or network action. |
| Focused provider/smoke pytest | PASS — `127 passed`. |
| mypy on the two allowed source files | PASS — no issues. |
| Ruff on the two source and two integration-test files | PASS. |
| `youtube-intel --help` | PASS — help only; no smoke invoked. |
| `git diff --check` | PASS. |
| Allowed-path range check | PASS — only the four actual product/test paths plus this handoff. |
| stdout/stderr/JSONL/test/handoff added-line leak scan | PASS — only fixed availability codes and authorized safety material. |

- No real YouTube, network, smoke, authentication material, media, Vault, model, cloud call, push, merge, source
  cleanup, fixture, configuration, Schema, logging schema, CLI, or control-plane modification occurred.
- Suggested status: `IN_REVIEW` after the required single fixed-parent Implementer commit. TASK-014 remains
  `IN_PROGRESS / No-Go`; this offline result is not real-service validation or release approval.
- Remaining risk: the closed classifications are intentionally limited to existing local mapping states. They do
  not establish a real-service cause or authorize compatibility remediation.
- `DECISION NEEDED`: `None`.
