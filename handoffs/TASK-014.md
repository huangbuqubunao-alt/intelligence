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

## TASK-014B10 Independent Reviewer Evidence — 2026-07-29

### Fixed review object and preflight

- Role: `Independent Reviewer`.
- Reviewed branch: `codex/task-014b10-safe-content-availability-diagnostic`.
- Reviewed implementation: `3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20`; its sole
  parent is `6fd7b5cc3fae6466fb6181151513f4854d196683`.
- Dynamic authorization `main@16f168b032d060fc9f2e46ced5744d81b7db6d2b` is a
  clean single-parent descendant of the fixed control-plane baseline and changes
  only control-plane documents. Source was clean before this evidence append.
- B9 failure evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` is not an
  ancestor of the implementation or authorization commit and remains unmerged.
- The complete implementation range is exactly the five authorized paths. No
  fixture, dependency, lockfile, Schema/migration, configuration, default CLI,
  logging schema, authentication, or control-plane product path changed.
  `git diff --check` passed. Reuse remains `DIRECT`.

### Tests-first and five-axis review

- Tests were reviewed before implementation. They directly exercise the four
  private availability states and a missing-state fallback, but construct the
  private state/error helper instead of exercising the Adapter error-mapping
  boundary that production uses.
- Correctness and product semantics have one blocking finding below. Static
  review otherwise confirmed the closed four-code vocabulary and the smoke-side
  directory-only / `CONTENT_UNAVAILABLE` / enumerate=`1` / read=`0` outlet gate.
- Readability, architecture, privacy, and performance review found no additional
  issue before the mandatory P1 stop. They were not exhaustively completed after
  the stop, and no unrun gate is reported as passing.

### Findings

- `P0=0`.
- `P1=1` — `src/youtube_intel/providers/subtitles.py:422`: the
  extractor-compatibility classification is selected only when the caught
  exception has the exact type `ExtractorError`. The locked yt-dlp production
  boundary catches extractor errors and raises `DownloadError` when errors are
  not ignored, so the default Adapter cannot reach this branch. The new tests
  bypass that boundary by directly constructing the private state, allowing all
  four code assertions to pass without proving a production mapping. In
  addition, a generic extractor exception type alone does not safely establish
  compatibility as the next-action category. This violates ADR-020's requirement
  to classify only from trustworthy local facts and to use unknown for partial
  or unreliable judgments. The Adapter boundary needs a safe reachable mapping
  and a regression that exercises it; this Reviewer is not authorized to fix it.
- `P2=0 recorded before stop`; no exhaustive P2 review after the P1.
- `P3=0 recorded before stop`; no exhaustive P3 review after the P1.

### Checks and mandatory stop

| Check | Result |
|---|---|
| branch, HEAD, sole parent, authorization ancestry, source/main cleanliness, B9 unmerged | PASS |
| exact five-path range, forbidden-path exclusion, initial `git diff --check` | PASS |
| tests-first static review and implementation Diff review | FAIL — blocking P1 above |
| locked yt-dlp exception-boundary static inspection | FAIL — production converts extractor errors to `DownloadError` |
| `uv sync --locked --offline` | NOT RUN — mandatory P1 immediate stop |
| focused pytest, mypy, Ruff, CLI help, final Diff check, formal full-output leak scan | NOT RUN — mandatory P1 immediate stop |

### Reviewer conclusion

- Verdict: `REJECT` for
  `6fd7b5cc3fae6466fb6181151513f4854d196683...3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20`.
- Unresolved P0/P1: the P1 above remains open.
- Not run: full pytest, build/package checks, any smoke or other product command,
  network/YouTube, media/ffmpeg, authentication/Cookie/API key handling,
  Vault/user data, models/Ollama/OpenAI, launchd, push, merge, or source cleanup.
- TASK-014B10 remains `IN_REVIEW`; TASK-014 remains `IN_PROGRESS / No-Go`.
  This review is not real-service verification, compatibility-fix authorization,
  release approval, or final Go.

## TASK-014B10 Correction 1 Implementer Evidence — 2026-07-29

### Fixed assignment, preflight, and reuse

- Role: original `Codex Implementer`; task state remains `IN_PROGRESS / Codex`.
- Source/branch: `/Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic` /
  `codex/task-014b10-safe-content-availability-diagnostic`.
- Required source HEAD and sole parent of this Correction commit:
  `2ea3455246a596f8304d2b0c00435862f8f3ea9e`; its sole parent is implementation
  `3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20`.
- Dynamic authorization was clean `main@78bb8b402ee47403ed37f38a27f0ffd5a359b719`,
  the single-parent Correction authorization descendant of control-plane baseline
  `16f168b032d060fc9f2e46ced5744d81b7db6d2b`. Source was clean at fixed HEAD.
- B9 evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` was not an ancestor of source or
  main and remains unmerged and untouched. First Reviewer evidence was verified as a
  handoff-only child, and the complete pre-Correction B10 range was exactly the five
  authorized paths.
- Reuse remains `DIRECT`: locked yt-dlp exception types and their typed `exc_info` /
  `cause` information, the existing subtitle Adapter mapping boundary, ADR-020
  vocabulary, and existing offline integration infrastructure. No dependency,
  lockfile, third-party source, or license evidence changed; the existing yt-dlp
  source and license record remains in `docs/REUSE_REGISTER.md`.

### RED, GREEN, and actual boundary behavior

- RED was created before production changes and invoked
  `YtDlpSubtitleAdapter.enumerate_tracks` through the existing no-network Fake factory.
  Command:
  `.venv/bin/pytest tests/integration/test_subtitle_provider.py::test_wrapped_extractor_error_reaches_compatibility_through_adapter tests/integration/test_subtitle_provider.py::test_unreliable_exception_chains_fail_closed_to_unknown_through_adapter`.
  Result: exit `1`, `7 failed`; every actual result was `PROVIDER_UNAVAILABLE` while the
  new production-boundary assertions required the closed `CONTENT_UNAVAILABLE`
  availability outcome.
- GREEN for the same command: `7 passed`. The final expanded matrix also covers a
  direct generic `ExtractorError` and the two other locked typed availability states,
  producing `10` passing boundary cases inside the final focused suite.
- A compatibility result now requires an exact outer locked `DownloadError`, a finite
  typed chain, a well-formed three-item exception-info tuple whose declared type
  exactly matches its exception object, a traceback that is absent or typed, and a
  reachable locked exception type. Exact `GeoRestrictedError` selects environment,
  exact `UnavailableVideoError` selects video-unavailable, and another reliable
  `ExtractorError` selects compatibility. `ExtractorError.cause` and its exception
  information must be typed and mutually consistent. The walk is capped at eight
  nodes and rejects cycles.
- An ordinary `DownloadError`, direct generic `ExtractorError`, empty/missing chain,
  malformed tuple, uncertain non-extractor terminal, cycle, or overdeep chain maps to
  fixed `content_availability_unknown`. Compatibility selection does not read or use
  exception text, URLs, response material, names, or outside field values.
- The tests use only the fixed generic placeholder `synthetic provider failure` and
  no classification marker or response-shaped material. They do not directly
  construct a private availability state or private content-error helper as proof.
- Reliable typed availability evidence is evaluated before the pre-existing mapping
  branches. Their existing error-code behavior and order remain, but message-only
  `CONTENT_UNAVAILABLE` branches now attach fixed unknown instead of inferring an
  availability source. The smoke source/test were not changed, so the directory-only +
  `CONTENT_UNAVAILABLE` + enumerate=`1` + read=`0` output gate, default body read,
  counts, exit behavior, no-retry behavior, and B4--B8 output boundaries remain intact.

### Authorized offline checks

| Check | Result |
|---|---|
| `uv sync --locked --offline` | PASS — run exactly once; `Resolved 84` / `Checked 61`, no download, network action, or lock change. |
| RED production-boundary tests | Expected FAIL — exit `1`, `7 failed`; actual `PROVIDER_UNAVAILABLE` evidence recorded above. |
| GREEN production-boundary tests | PASS — `7 passed` before final direct-extractor regression was added. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS — final `137 passed`; offline only. |
| Initial mypy run | FAIL — `subtitles.py:417`: exact-type branch did not statically narrow `BaseException` to the locked `DownloadError`. |
| Mypy after one-line narrowing correction | PASS — no issues in the two authorized source files. |
| Ruff on the two source and two integration-test files | PASS — all checks passed. |
| `.venv/bin/youtube-intel --help` | PASS — help only; no smoke or other product operation ran. |
| `git diff --check` | PASS. |
| Correction/full-B10 allowlist review | PASS — Correction uses only Adapter, provider integration test, and this handoff; full B10 remains exactly the authorized five paths. |
| Added-line and output-surface leak scans | PASS — Correction source/test adds no stdout, stderr, JSONL, URL, response, credential, user, or dynamic material; full B10 product/test added-line scan also passed and ADR-019 was not expanded. |

### Scope, skips, and remaining risk

- Actual Correction paths: `src/youtube_intel/providers/subtitles.py`,
  `tests/integration/test_subtitle_provider.py`, and this appended handoff section.
  `src/youtube_intel/public_subtitle_smoke.py` and its integration test were authorized
  upper bounds but demonstrably unnecessary and were not changed by Correction 1.
- No fixture, JSONL schema, dependency, `uv.lock`, Schema/migration, configuration,
  default CLI, `logging.py`, authentication boundary, task state, or control-plane file
  changed. Diff review found no formatting churn or unrelated refactor.
- Not run by formal prohibition: full pytest, build/package checks, real smoke,
  network/YouTube, authentication/Cookie/API key handling, media/ffmpeg, Vault/user
  data, models/Ollama/OpenAI, cloud calls, launchd, push, merge, Reviewer startup, or
  source cleanup.
- Remaining risk: offline typed synthetic exceptions prove the locked Adapter mapping
  boundary only. They do not establish a real-service cause, broad yt-dlp
  compatibility, release approval, or final Go. TASK-014 remains
  `IN_PROGRESS / No-Go`.
- Commit SHA: reported to the orchestrator after creation of the required single
  Correction commit. `DECISION NEEDED`: `None`.

## TASK-014B10 Correction 1 Independent Reviewer 2 Evidence — 2026-07-29

### Fixed object, authorization, and scope preflight

- Role: fresh independent `Codex Reviewer 2`.
- Reviewed source: `codex/task-014b10-safe-content-availability-diagnostic@c65502e3680d14a88ae52a1c27eea47d42b5e8b0`.
  Its sole parent is first Reviewer evidence
  `2ea3455246a596f8304d2b0c00435862f8f3ea9e`; that commit is the handoff-only
  child of implementation `3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20`, whose sole parent is fixed base
  `6fd7b5cc3fae6466fb6181151513f4854d196683`.
- Dynamic authorization was clean `main@62c9beed8d5b6430733872eb35d13705a87402d1`,
  a single-parent child of control-plane baseline
  `78bb8b402ee47403ed37f38a27f0ffd5a359b719`. Its five changed paths are only
  the Reviewer prompt and task/status control documents; it contains no product
  change. Source and main were clean before review.
- B9 failure evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` is not an
  ancestor of source or dynamic main and remains unmerged and untouched.
- Correction range is exactly Adapter, provider integration test, and this
  handoff. Complete B10 range is exactly those three paths plus smoke source and
  smoke integration test. Both `git diff --check` ranges passed. No fixture,
  dependency/lock, Schema/migration, configuration, default CLI, `logging.py`,
  authentication, or control-plane product path changed.
- Reuse remains `DIRECT`: locked yt-dlp typed exceptions and the existing
  Adapter catch/convert boundary, ADR-020 vocabulary, B4 directory-only, B5 safe
  summary, B6--B8 diagnostics, and existing offline integration infrastructure.
  No dependency, third-party source, or license evidence changed.

### Tests-first and production-boundary review

- Tests were reviewed before implementation. Correction tests invoke production
  `YtDlpSubtitleAdapter.enumerate_tracks` through the existing no-network Fake
  factory with an exact outer `DownloadError`; they do not use the private
  classifier or private availability-error helper as their production mapping
  proof. They cover wrapped `GeoRestrictedError`, `UnavailableVideoError`, and a
  generic reliable `ExtractorError`, plus ordinary/direct, empty, malformed,
  uncertain, cyclic, and overdeep unknown cases.
- Locked local yt-dlp `2026.7.4` source was independently inspected. It confirms
  `DownloadError` preserves a supplied three-item `exc_info`, `ExtractorError`
  preserves typed `cause`/`exc_info`, `GeoRestrictedError` derives from
  `ExtractorError`, and `UnavailableVideoError` is a distinct locked exception.
- Production mapping requires the caught outer object to have exact type
  `DownloadError`. The walk is capped at eight nodes, records object identities
  to reject cycles, validates tuple length, declared/actual exact exception type,
  optional traceback type, `cause` type, and `cause`/`exc_info` consistency, and
  fails closed on malformed attribute access. Conflicting geo/video evidence and
  any nonterminal chain beyond the cap return unknown.
- Known availability selection reads only locked exception types and typed chain
  structure. Exception strings and legacy error-code mapping may not select any
  known availability state; message-only content-unavailable outcomes carry the
  fixed unknown state. No URL, response, status, external field, or other value
  is used to choose the three known codes.
- The smoke outlet independently requires directory-only,
  `CONTENT_UNAVAILABLE`, enumerate=`1`, and read=`0`; missing or invalid private
  state becomes fixed unknown. Default smoke still performs one body read, and
  existing tests preserve counts, exit behavior, no retry, temporary-root and ID
  bounds, zero business records, B4--B8 diagnostics, other B10 outcomes, and
  fail-closed output omission.

### Findings and independent gates

- Findings: `P0=0`, `P1=0`, `P2=0`, `P3=0`.
- Five-axis result: correctness, readability/simplicity, architecture, privacy/
  security, and bounded performance all pass for the fixed Correction and full
  B10 ranges.

| Check | Result |
|---|---|
| `uv sync --locked --offline` | PASS — run exactly once; `Resolved 84` / `Checked 61`, no download/network indication or lock change. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS — independently collected and ran `137`; all passed. |
| Production Adapter wrapped mapping/unknown matrix inside the focused suite | PASS — all three fixed typed mappings and ordinary/direct/missing/malformed/uncertain/cycle/overdeep fail-closed cases passed through `enumerate_tracks`. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS — no issues in two source files. |
| `.venv/bin/ruff check` on the two source and two integration-test files | PASS — all checks passed. |
| `.venv/bin/youtube-intel --help` | PASS — help only; no smoke or other product subcommand ran. |
| Correction and complete-B10 `git diff --check` | PASS — both fixed ranges. |
| Three-path/five-path, forbidden-path, parser/CLI/logging/schema/auth, and fixture review | PASS — exact allowlists; no acceptance-surface expansion or forbidden change. |
| stdout, stderr, JSONL `safe_message`, test-added-line, and handoff leak review | PASS — output remains fixed/allowlisted; no sensitive runtime material or credential-shaped value found. |

- A supplemental inline production-Adapter probe is explicitly not counted as
  pass evidence: two attempts exited `1` while constructing its custom
  `FaultyExtractor` test double, before that case entered the Adapter. The key
  line was `RuntimeError: synthetic provider failure` from the test double's
  attribute hook; the second attempt delayed enabling the hook but yt-dlp's own
  constructor still accessed it. The same harness failure was not retried again.
  The prior nine cases in the second probe reached the production Adapter without
  an assertion before this harness error, including real `sys.exc_info()` shape
  and exact eight/nine-node boundaries, but the whole supplemental probe remains
  excluded rather than reported as passing. The required focused production-
  boundary tests above passed independently and are the dynamic evidence used.

### Reviewer conclusion, skips, and residual risk

- Verdict: `APPROVE` for Correction
  `2ea3455246a596f8304d2b0c00435862f8f3ea9e...c65502e3680d14a88ae52a1c27eea47d42b5e8b0`
  and complete B10
  `6fd7b5cc3fae6466fb6181151513f4854d196683...c65502e3680d14a88ae52a1c27eea47d42b5e8b0`.
- Unresolved P0/P1: none.
- Not run by formal prohibition: full pytest, build/package checks, real smoke,
  network/YouTube, authentication/Cookie/API key handling, media/ffmpeg,
  Vault/user data, models/Ollama/OpenAI, cloud calls, launchd, push, merge, task
  status change, source cleanup, or index creation/refresh.
- Residual risk: synthetic offline typed chains validate the locked production
  Adapter boundary but do not establish a real-service cause, broad future
  yt-dlp compatibility, release approval, or final Go. TASK-014B10 remains
  `IN_REVIEW`; TASK-014 remains `IN_PROGRESS / No-Go`.
- Evidence commit SHA: reported after creation of the required handoff-only child
  of `c65502e3680d14a88ae52a1c27eea47d42b5e8b0`. `DECISION NEEDED`: `None`.

## TASK-014B11 Implementer Evidence — 2026-07-29

### Fixed assignment, scope, and reuse

- Role: `Codex Implementer`; fixed branch
  `codex/task-014b11-safe-directory-contract-diagnostics` at implementation base
  `80aff83fc033a8bd2950108cad2e34feea5d396f`.
- Dynamic main authorization `6f5336098406f95ad1773d2ea36da24aaa97530f`
  was clean and had the implementation base as its sole parent. The source branch,
  HEAD, tracked/untracked worktree, and index were clean before implementation.
- Read-only failure evidence `51d9749943270cb75c2b166e77bce0a5f663d92c`
  had sole parent `f00aa9cffa25dcb9b7165edf21a4d476263c1dc5`, changed only the
  three authorized evidence documents, and was not an ancestor of source or main.
  It remained unmerged and untouched.
- Reuse is `DIRECT`: the locked subtitle Adapter, B4 directory-only execution,
  B5 safe stdout/JSONL `safe_message`, B6--B10 fixed diagnostics, Python standard
  library, and existing offline integration infrastructure. No dependency,
  third-party source, lockfile, or license evidence changed.
- Actual paths are the Adapter, safe smoke composition, the two authorized
  integration tests, and this handoff. No fixture or control-plane document changed.

### RED, GREEN, and frozen behavior

- RED was written before production code. Command:
  `.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py::test_directory_only_emits_frozen_directory_contract_state_matrix`.
  Result: exit `1`, `1 failed`; the assertion expected the six ADR-021 fields at
  the end of stdout, while the actual summary ended at the existing directory
  fingerprint. This proves the previous safe summary could not express the matrix.
- The first GREEN attempt reached complete stdout but exposed the existing
  300-character JSONL safe-message limit: direct concatenation after B6/B7 was
  truncated during `automatic_directory_shape`. That attempt remained a failure
  and was not counted as passing evidence.
- Final GREEN for the same node passed. Existing `smoke.target.failed`
  safe-message content remains unchanged; a fixed
  `smoke.target.directory_contract_state` event uses the same existing JSONL schema
  and its existing `safe_message` field for the complete six-field fragment. The
  stdout summary appends the same six fields in the same order. No `logging.py` or
  JSONL schema field changed.
- Field order is exactly `video_identity_shape`, `manual_directory_shape`,
  `automatic_directory_shape`, `caption_bucket_shape`, `track_entry_shape`, and
  `required_members_shape`. Each field is backed by its exact frozen private enum;
  all values, including every `unknown` and `not_evaluated`, are asserted.
- The matrix gate requires directory-only, `INVALID_RESPONSE`, metadata/enumerate/read
  exactly `1/1/0`, mapping origin, and zero body reads. Any missing gate, untrusted
  state object, invalid tuple length/type/value, default smoke, other error code,
  non-mapping origin, or body read omits the entire matrix.
- Adapter states are produced only at existing validation branches. They describe
  top-level identity shape, manual/automatic directory shape, caption bucket,
  track entry, and required-member completeness/type. Generic iteration failures
  fail closed to `caption=unknown` with later layers `not_evaluated`. No arbitrary
  external key is enumerated or emitted, and no parser acceptance rule changed.

### Authorized offline checks

| Check | Result |
|---|---|
| `uv sync --locked --offline` | PASS — run once before tests; local cache only, `Resolved 84`, installed the locked environment, and `uv.lock` SHA-256 remained `6773017a8426873d62d6c33588c2661809436bb733e531961c3b593e04a0dd43`. |
| RED matrix node | Expected FAIL — exit `1`, `1 failed`, missing six-field stdout assertion recorded above. |
| Final GREEN matrix node | PASS — `1 passed`; stdout and JSONL safe-message matrix complete and ordered. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS — final run `147 passed`; offline Provider/Smoke regression only. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS — no issues in two source files. |
| Ruff on the two source and two integration-test files | PASS after one resolved `I001`; two manual order attempts reproduced the same import-only failure, Ruff's read-only diff supplied the exact order, and the final run reported all checks passed. |
| `.venv/bin/youtube-intel --help` | PASS — help only; no smoke or other product operation ran. |
| `git diff --check`, five-path allowlist, forbidden-path, LF/EOF, SHA-256, added-line/output/handoff/fixture leak scans | PASS — final checks completed before commit; no unexpected or generated path. |

### Review, skips, and remaining risk

- Five-axis self-review found no correctness, readability, architecture, security,
  or performance blocker. The state tuple is fixed at six validated strings; output
  work is constant-sized and existing bounded directory iteration is unchanged.
- No B6/B7/B8/B10 vocabulary, gate, or meaning changed. Default smoke still reads
  one selected body, directory-only remains `1/1/0`, and focused regression confirms
  exit codes, no retry, temporary-root/ID bounds, zero business records, and all
  fail-closed behavior remain intact.
- Not run by formal prohibition: full pytest, build/package checks, real smoke,
  network/YouTube, authentication/Cookie/API key handling, media/ffmpeg, real Vault
  or user data, models/Ollama/OpenAI, cloud calls, launchd, push, merge, Reviewer
  startup, task-state change, or source cleanup.
- Remaining risk: this is offline synthetic contract-state evidence only. It does
  not establish a real-service cause, compatibility fix, body readability, broad
  yt-dlp compatibility, release approval, or final Go. TASK-014 remains
  `IN_PROGRESS / No-Go`; TASK-014B11 remains `IN_PROGRESS / Codex` pending an
  independently authorized Reviewer.
- Implementer commit SHA: reported after creation of the required single commit.
  `DECISION NEEDED`: `None`.

## TASK-014B11 Independent Reviewer Evidence — 2026-07-29

### Metadata, fixed object, and reuse

- Role: fresh independent Codex Reviewer; Verdict: `REJECT`.
- Reviewed branch: `codex/task-014b11-safe-directory-contract-diagnostics`.
- Reviewed implementation: `f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50`, with sole
  parent `80aff83fc033a8bd2950108cad2e34feea5d396f`.
- Dynamic main authorization was exactly
  `63911ff6c478bf89cb724474c3ab34e518652440`, with sole parent
  `6f5336098406f95ad1773d2ea36da24aaa97530f`; main and source were clean at
  the initial gate. The implementation range was exactly the five authorized
  paths and passed the initial fixed-range `git diff --check`.
- The read-only evidence commits `51d9749943270cb75c2b166e77bce0a5f663d92c`
  and `bd770ef9d212ebe75689b8f33145bf2556fe93c2` were not ancestors of main or
  source. The former had the required sole parent and three-document evidence
  scope. Both remained unmerged and untouched.
- Reuse remained `DIRECT`: the locked subtitle Adapter, B4 directory-only,
  B5 safe summary and existing JSONL schema, ADR-017--ADR-020 diagnostics, and
  offline integration infrastructure. No dependency, lockfile, fixture,
  license, third-party source, Schema, configuration, authentication, default
  CLI, `logging.py`, or log-schema change was present.

### Finding and P0--P3

- `P0=0`, `P1=1`, `P2=0`, `P3=0`.
- **P1 — the tests bypass the production Adapter validation-to-output path
  required by TASK-014B11.**
  `tests/integration/test_subtitle_provider.py:500` only introspects the private
  enum vocabularies, and the behavioral assertion at line 544 directly calls
  the private tuple constructor. In
  `tests/integration/test_public_subtitle_smoke.py:169`, the matrix Fake builds
  a tuple by calling the same private constructor and raises a private
  `_directory_structure_error` directly at lines 184--198; the stdout/JSONL
  test at line 647 then injects that Fake. No new test drives
  `YtDlpSubtitleAdapter.enumerate_tracks()` through its production validation
  branches and asserts the resulting six states at the safe stdout/JSONL
  boundary. Consequently, incorrect field assignment, swapped manual/automatic
  state, or incorrect `unknown`/`not_evaluated` selection in the production
  branches at `src/youtube_intel/providers/subtitles.py:1300--1415` would not be
  caught. This directly violates the frozen acceptance requirement that tests
  must not bypass the production Adapter validation-to-safe-smoke transfer.
  Correction must add safe, no-value production-boundary coverage without
  reproducing a real response structure or adding a fixture.

### Five-axis review

- Correctness: `REJECT` because the required production-path regression proof is
  absent. Static implementation inspection otherwise found the six field names,
  order, and closed value sets aligned with ADR-021; the smoke gate checks
  directory-only, exact `1/1/0`, `INVALID_RESPONSE`, mapping origin, and zero
  reads before accepting a validated six-string tuple.
- Readability: no additional finding. The private enums and fixed tuple helpers
  are explicit, though the instrumentation is necessarily verbose.
- Architecture: no additional finding. Static inspection found state generation
  confined to the Adapter and output composition confined to the existing smoke
  boundary; the independent event calls the unchanged logger schema.
- Security/privacy: no additional static finding. The new event message is built
  only from six fixed field names and independently validated closed values; the
  existing top-level `video_id` schema field is not copied into the new message.
  Added test/handoff lines contained no URL, known real target ID, or
  credential-shaped material; fixtures were unchanged. Runtime stdout/stderr/
  JSONL verification was skipped by the P1 stop rule and is not counted as pass.
- Performance: no additional finding. State construction is constant-sized per
  existing bounded validation step, and there is one source occurrence of the
  contract-state event emitted at most once in a failed target path. The longest
  fixed fragment checked statically was 197 characters, below the existing 300
  character sanitizer limit; no per-field event loop or unbounded event
  amplification was introduced.

### Independent gates, stop point, and skips

- PASS: branch/HEAD/sole-parent identity; dynamic main authorization and sole
  parent; clean main/source; five-path complete range; read-only evidence parent,
  scope, and non-ancestor checks; initial fixed-range `git diff --check`.
- PASS: prohibited-path review. `pyproject.toml`, `uv.lock`,
  `src/youtube_intel/logging.py`, and `src/youtube_intel/cli.py` blobs were
  identical at base and implementation; no fixture, migration, or configuration
  path changed. All five changed files used LF, ended with LF, and had no CR.
- PASS (static only): exact ADR-021 field/value comparison, strict output gate
  inspection, unchanged JSONL top-level schema inspection, single fixed event
  callsite/event bound, 197-character maximum fixed fragment, Adapter acceptance
  Diff inspection, and added-line/handoff/fixture material scan.
- An initial auxiliary blob/hash scan was invalid because its shell used zsh's
  special `path` variable and thereby hid standard commands. It was excluded
  from evidence; a corrected static scan using non-system variable names passed.
- STOP: the P1 was established during the required tests-first static review.
  Per the formal package, no product command was run after that finding.
- SKIPPED (not pass): `uv sync --locked --offline`; focused Provider/Smoke
  pytest; mypy; Ruff; `youtube-intel --help`; runtime stdout/stderr/JSONL scan;
  and the final ordered offline-command repetition of `git diff --check`. Full pytest,
  build, real/network smoke, authentication, media, Vault, model/cloud, merge,
  push, and cleanup were also not run, as prohibited.

### Reviewer conclusion

- Verdict: `REJECT`.
- Unresolved P0/P1: the single P1 production-boundary test gap above.
- Remaining risk: this static review does not independently establish runtime
  matrix output, regression counts/exit codes, or offline tool success because
  the mandatory immediate-stop rule applied. It does not establish a real-service
  cause, compatibility, body readability, release approval, or final Go.
- TASK-014 remains `IN_PROGRESS / No-Go`; TASK-014B11 remains under review.
- Reviewer evidence commit: reported after creation of the required single
  handoff-only commit. `DECISION NEEDED`: `None`.

## TASK-014B11 Correction 1 Implementer Evidence — 2026-07-29

### Metadata, goal, scope, and reuse

- Role: original Codex Implementer for Correction 1; fixed source branch
  `codex/task-014b11-safe-directory-contract-diagnostics` started clean at
  Reviewer evidence `4aebc01360fa9684fe6b052f266a00ecc2de57dc`, whose sole
  parent is implementation `f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50`.
- Dynamic main authorization `f902aec309927751d173145e46a617a467745e85`
  had sole parent `63911ff6c478bf89cb724474c3ab34e518652440`; its formal
  Correction prompt matched the external prompt byte-for-byte by SHA-256.
- Git-only gates confirmed the implementation/review parent chain, the original
  five-path B11 range, handoff-only Reviewer evidence, clean source, and both
  read-only evidence commits remaining outside main/source.
- Goal: close the sole P1 with offline production-boundary proof through real
  `YtDlpSubtitleAdapter.enumerate_tracks()` and real `PublicSubtitleSmoke`.
  Actual Correction paths are the two authorized integration tests and this
  handoff; both production files remain unchanged.
- Reuse remains `DIRECT`: the locked yt-dlp Adapter, B4 directory-only, B5 safe
  stdout/JSONL schema, ADR-017--ADR-021 diagnostics, and existing offline test
  wiring. No dependency, third-party code, fixture, lockfile, Schema, migration,
  configuration, authentication, default CLI, or log-schema change was made.

### Tests-first production chain and coverage-only result

- Before any production edit, tests were added/replaced so the only Fake is the
  outer downloader transport. It returns a non-user synthetic sentinel through
  a `Mapping`; it does not call a classification helper, construct a private
  final diagnostic error, set a private state tuple, or return a matrix.
- The direct Provider node calls real `YtDlpSubtitleAdapter.enumerate_tracks()`.
  The Adapter itself validates the directory concept mismatch, constructs the
  exact state `other/unknown/unknown/not_evaluated/not_evaluated/not_evaluated`,
  maps it to `TranscriptError(INVALID_RESPONSE)`, and preserves mapping origin.
- The real smoke node injects that Adapter through the existing factory, then
  verifies complete ordered stdout fields and exactly one bounded
  `smoke.target.directory_contract_state` event with the unchanged top-level
  JSONL schema. A second real-chain node removes the directory-only gate and
  verifies all six fields and the event are absent.
- Initial new-node command, run after the single authorized offline sync:
  `.venv/bin/pytest tests/integration/test_subtitle_provider.py::test_ytdlp_adapter_maps_contract_mismatch_to_frozen_no_value_state tests/integration/test_public_subtitle_smoke.py::test_directory_only_emits_frozen_directory_contract_state_matrix tests/integration/test_public_subtitle_smoke.py::test_production_contract_state_is_omitted_without_directory_only_gate`.
  Result: `3 passed` on unchanged production source. Therefore there was no
  valid product RED; Correction 1 is coverage-only, and no production repair or
  GREEN rerun was permitted or needed.

### Authorized checks and regression evidence

| Check | Result |
|---|---|
| `uv sync --locked --offline` | PASS once: `Resolved 84`, `Checked 61`; no download/network indication. |
| Initial production-chain nodes | PASS: `3 passed`; coverage-only, no valid product RED. |
| `.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py` | PASS: `149 passed`; default smoke, B4--B10, counts, exit codes, no retry, and body-read behavior remain covered. |
| `.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py` | PASS: no issues in two source files. |
| Authorized Ruff command on two source and two integration-test files | PASS: all checks passed. |
| `.venv/bin/youtube-intel --help` | PASS; help only, with no other product command. |
| Pre-commit Correction/full B11 scope, lock/forbidden paths, LF/EOF, SHA-256, and output-surface scans | PASS: Correction is three paths, full B11 remains five; forbidden files/fixtures unchanged; EOF byte `10`, no CR, and all material scans clear. |

### Diff review, skips, and remaining risk

- The Correction is the minimum permitted subset: Provider integration test,
  smoke integration test, and this appended handoff. Adapter and smoke
  production sources are unchanged because the production chain passed first
  run. No fixture was added, restored, read, modified, moved, or embedded.
- The new material contains only ADR-021 project contract concepts and non-user
  synthetic sentinels. Tests assert empty stderr, ordered/complete stdout,
  unchanged JSONL fields, one event when gated, and zero when ungated; no real
  URL, title, language, track, response content, exception text, external key,
  credential, payload, path, or user data was added.
- Formally skipped/prohibited: full pytest, build/package checks, other CLI
  subcommands, network/YouTube/real smoke, authentication/Cookie/netrc, media or
  ffmpeg, real Vault/user data, models/Ollama/OpenAI/cloud calls, task-state
  changes, Reviewer startup, merge, push, and source cleanup.
- Remaining risk: evidence is offline and synthetic. It proves the current
  production Adapter-to-smoke transfer for a safe contract mismatch, not a real
  service cause, compatibility repair, body readability, broad yt-dlp
  compatibility, release approval, or final Go. TASK-014 remains
  `IN_PROGRESS / No-Go`; TASK-014B11 remains `IN_PROGRESS / Codex`.
- Correction commit SHA: reported after creation of the required single commit.
  `DECISION NEEDED`: `None`.

## TASK-014B11 Correction 1 Independent Reviewer 2 Evidence — 2026-07-29

### Metadata, fixed object, scope, and reuse

- Role: fresh independent Codex Reviewer 2; Verdict: `APPROVE`.
- Reviewed Correction: `ed250baf752182adbc4d98f5271d34995865d192`, with sole
  parent `4aebc01360fa9684fe6b052f266a00ecc2de57dc`; the parent is the
  handoff-only first Reviewer evidence, whose sole parent is implementation
  `f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50`.
- The implementation has sole parent/base
  `80aff83fc033a8bd2950108cad2e34feea5d396f`. Dynamic main authorization was
  exactly `95fa9e41d34086434ef10a425bc418a782f43196`, with sole parent
  `f902aec309927751d173145e46a617a467745e85`; main and source were clean at
  the initial gate.
- Correction scope is exactly the two integration tests plus this handoff;
  complete B11 scope is exactly the Adapter, safe smoke, those two tests, and
  this handoff. The two production blobs are unchanged from the first
  implementation through Correction 1.
- Read-only evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` has the
  required sole parent and three-document evidence scope. It and
  `bd770ef9d212ebe75689b8f33145bf2556fe93c2` are not ancestors of main or
  source and remained unmerged and untouched.
- Reuse remains `DIRECT`: the locked yt-dlp Adapter, B4 directory-only, B5
  safe stdout/JSONL schema, B6--B10 fixed diagnostics, and existing offline
  integration infrastructure. No dependency, third-party source, lockfile,
  fixture, Schema, migration, configuration, authentication, default CLI,
  `logging.py`, or log-schema change is present.

### Coverage-only production-boundary proof

- Correction 1 is coverage-only. Its three new nodes passed against unchanged
  production source; this is not product RED and is not evidence that a
  product bug was fixed.
- The direct Provider node instantiates and calls real
  `YtDlpSubtitleAdapter.enumerate_tracks()`. The only substitute is the outer
  downloader transport installed through the existing test hook, together
  with a deterministic clock. Its non-user synthetic `Mapping` exposes no
  arbitrary external key set or recorded value and does not model a captured
  response.
- The real Adapter performs the project-known identity access and mismatch
  validation, constructs all six states as
  `other/unknown/unknown/not_evaluated/not_evaluated/not_evaluated`, and maps
  them to `TranscriptError(INVALID_RESPONSE)` with mapping origin. The tests do
  not call a private classification/matrix/error helper, set a final private
  tuple, or construct a final private diagnostic error on this production
  path; `_bind_test_hooks` is used only for the authorized outer factory/clock.
- The real `PublicSubtitleSmoke` receives that Adapter error through its
  existing factory and failure path. It produces complete ordered stdout and
  one existing-schema `smoke.target.directory_contract_state` JSONL event.
  The paired real-chain default-smoke node proves the matrix/event are omitted
  when the directory-only gate is absent.
- The production-chain assertions are causally sensitive: changing the
  Adapter's identity/unknown/not-evaluated mapping changes both Provider and
  smoke assertions; changing smoke field order, directory-only gating, or
  event emission changes the ordered summary, zero/one event, or ungated
  assertions. Existing focused gate tests additionally break each of the
  metadata/enumerate/read/error/origin conditions and require whole-matrix
  omission; helper-level tests are supplemental rather than substitutes for
  the new production chain.

### Five-axis findings and P0--P3

- Correctness: no finding. The real boundary covers a field-shape mismatch,
  production `unknown` versus `not_evaluated`, strict output omission, fixed
  six-field order/closed values, and zero/one event bound. The complete focused
  suite independently preserves B4--B10, default single body read,
  directory-only zero body read, exit codes, counts, no retry, temporary-root
  and ID bounds, zero business records, and fail-closed behavior.
- Readability: no finding. The synthetic payload and transport helpers are
  small, named for the boundary they exercise, and replace the prior Fake that
  directly built the final private error/matrix.
- Architecture: no finding. External I/O alone is replaced; Adapter validation,
  internal state/error mapping, smoke gating, stdout composition, and JSONL
  emission remain production code. No parser acceptance branch or public
  interface changed in Correction.
- Security/privacy: no finding. Runtime assertions require empty stderr, exact
  safe stdout values, unchanged JSONL top-level fields, one bounded fixed
  message, and no event when ungated. Added-line scans found no real response
  structure, arbitrary external key, URL, title, language, track, external
  field value, exception text, user data, real target, or credential material;
  fixtures are unchanged. The Provider test's existing synthetic identifier
  is not external response material and is not emitted.
- Performance: no finding. State/output work is a fixed six-value operation and
  the production failure path has one event callsite. The passing production
  test observes exactly one event when gated and zero when ungated; no input,
  key, language, track, field, or exception loop can amplify B11 events.
- Severity totals: `P0=0`, `P1=0`, `P2=0`, `P3=0`.

### Independent gates and results

| Command or review gate | Result |
|---|---|
| Branch/HEAD/sole-parent chain, dynamic-main authorization, source/main initial cleanliness, two read-only evidence non-ancestor checks | PASS |
| Correction three-path, complete B11 five-path, first-reviewer handoff-only, production-blob equality, and forbidden-path review | PASS |
| `uv sync --locked --offline` | PASS once: 84 packages resolved and 61 checked; no download/network indication and no lock change. |
| Three specified production-chain pytest nodes | PASS: `3 passed`; counted only as coverage proof, not a product fix. |
| Provider/Smoke focused pytest | PASS: `149 passed`. |
| Mypy on the two production files | PASS: no issues in two source files. |
| Ruff on the two production and two integration-test files | PASS: all checks passed. |
| `youtube-intel --help` | PASS; help only, no other product command. |
| Correction and complete B11 `git diff --check` | PASS for both fixed ranges. |
| stdout/stderr/JSONL/test/handoff/fixture, real-target/secret, CR, LF/EOF, SHA-256, lock and final scope scans | PASS; every reviewed file ends LF, no CR, fixtures/forbidden files are unchanged, and the single B11 event callsite remains fixed. |

### Diff review, skips, remaining risk, and conclusion

- The Reviewer will append only this evidence. No business code, test, task
  state, ADR, prompt, control-plane file, fixture, dependency, lockfile, Schema,
  configuration, CLI, authentication, or logging schema is modified.
- Formally skipped/prohibited: full pytest, build/package checks, other CLI
  subcommands, network/YouTube/real smoke, authentication/Cookie/netrc, media or
  ffmpeg, real Vault/user data, models/Ollama/OpenAI/cloud calls, merge, push,
  task-state changes, source cleanup, and index generation. These are not pass
  evidence.
- Remaining risk: this is synthetic offline coverage proof. It does not establish
  a real-service cause, a compatibility repair, body readability, broad yt-dlp
  compatibility, release approval, or final Go. TASK-014B11 remains
  `IN_REVIEW`; TASK-014 remains `IN_PROGRESS / No-Go`.
- Verdict: `APPROVE`; unresolved P0/P1: none. Reviewer evidence commit is
  reported after creation. `DECISION NEEDED`: `None`.

## TASK-014B11 Correction 2 Implementer evidence

- Fixed diagnostic evidence:
  - path: tests/integration/test_public_subtitle_smoke.py; original line: 210;
    original line SHA-256:
    f950e2195fb88b36b457dc65bd53c632676bbd127a2378788d6fea3ade392e0d;
    classification: safe-local-identifier.
  - path: tests/integration/test_subtitle_provider.py; original line: 105;
    original line SHA-256:
    f950e2195fb88b36b457dc65bd53c632676bbd127a2378788d6fea3ade392e0d;
    classification: safe-local-identifier.
- Safe disposition: both local test identifiers were changed to neutral test
  expressions with all local references changed consistently. Runtime inputs,
  assertions, safety cleanup, test count, and test behavior remain equivalent;
  normalized AST comparison passed for both files. No real credential risk was
  found and credential rotation is not indicated.
- Verification commands and results:
  - python3 - read-only AST classification: PASS for both fixed paths and
    hashes.
  - python3 - normalized AST comparison: PASS for both test files.
  - python3 - specialized locator: PASS; both original-hash new-hit counts
    were 0, and target-rule new-hit count was 0.
  - uv sync --locked --offline: PASS; no network indicator and no lock or
    dependency change.
  - .venv/bin/pytest with the three authorized production-chain nodes:
    PASS, 3 passed.
  - .venv/bin/pytest tests/integration/test_subtitle_provider.py
    tests/integration/test_public_subtitle_smoke.py: PASS, 149 passed.
  - .venv/bin/mypy for the two authorized production modules: PASS.
  - .venv/bin/ruff check for the authorized production and test modules: PASS.
  - .venv/bin/youtube-intel --help: PASS.
  - Correction three-path and complete B11 five-path scope, forbidden-surface,
    LF/EOF, and git diff --check checks: PASS.
  - Combined static leak scan across stdout/stderr/JSONL safe-message surfaces,
    B11 added test and handoff lines, and fixture surface: PASS.
  - Not run because prohibited or outside Correction 2 authorization: full
    pytest, build/package checks, other CLI subcommands, network, real smoke,
    authentication, media, Vault, models or cloud services, merge, push,
    Reviewer startup, task-state changes, source cleanup, and index generation.

## WorkBuddy P1 Remediation Evidence (2026-08-11)

Performed on branch `workbuddy/fix-rc-p1` from base `qoder/continue-dev` @ `296f701`.
Scope: fix the three P1 blockers raised in the Codex Maintainer Review of the
RC on `qoder/continue-dev`. No redesign of TASK-014B11; no new features.

### P1-1: Security scanner fail-closed, cross-platform, redaction, AST shell=True

- Rewrote `scripts/security_scan.sh` to call new helper `scripts/_security_scan.py`.
- Credential patterns now match `KEY="value"`, `KEY='value'`, `KEY = "value"`,
  `KEY = 'value'` for required key names using Python `re`; compatible with
  macOS BSD and Linux without GNU-only extensions.
- Added AST traversal detecting `subprocess.run/Popen/call/check_call/check_output(..., shell=True)`.
- Scanner is fail-closed: enumeration/read/AST/extract failures return non-zero.
- Findings are redacted: only `rule=`, `path=`, `line=`, and a short SHA-256
  fingerprint are emitted; the secret text is never echoed.
- Scan scope expanded to all tracked `.py/.sh/.toml/.yaml/.yml/.json/.md/.txt/.cfg/.ini`
  plus wheel/sdist contents.
- Added `tests/scripts/test_security_scan.py` with positive/negative probes.
- Scanner result after remediation: `status=clean` (documented WARNs are false
  positives: legitimate hashes, print in smoke command, missing LICENSE).

### P1-2: Backup/recovery drill deterministic validation and honest reporting

- Rewrote `scripts/backup_recovery_drill.sh` (v3) with explicit PASS/WARN/FAIL
  state model.
- Corruption detection is deterministic:
  - SQLite magic-header overwrite (rejected by sqlite3 open/integrity_check);
  - 50% file truncation (rejected by integrity_check);
  - backup manifest SHA-256 mismatch (rejected by manifest verification);
  - recovered-file checksum mismatch after byte-level corruption.
- Data-level verification covers schema, user_version, migration record,
  migration checksum, videos/jobs row counts and key business-field values,
  pre- and post-recovery `PRAGMA integrity_check`, backup/recovered checksums,
  read-only post-recovery query, and CLI `doctor` on the recovered project.
- Idempotency proven by running the same verification a second time on the
  SAME recovered database and asserting row counts do not change.
- Honest limitations preserved: real power-fail, kernel crash, concurrent
  writers, real Vault restore, and exactly-once semantics are NOT proven.
- Drill result after remediation: 17 PASS, 1 WARN, 0 FAIL; exit code 0.

### P1-3: Obsidian Markdown/HTML safe rendering per ADR-009

- `src/youtube_intel/notes.py` now distinguishes `_safe_inline()` for
  single-line primitives and `_safe_block()` for multi-line block text, with
  context-appropriate HTML and Markdown neutralization.
- Active HTML tags and boundary characters (`< > & " '`) are escaped.
- Markdown structures are neutralized: links, images, wiki links, Obsidian
  embeds, headings, blockquotes, lists, fenced code, horizontal rules.
- Source URL scheme is validated; only `http` and `https` are allowed.
- Marker shape validation ensures auto/user region markers are not forged by
  model/external input.
- `src/youtube_intel/reporting.py` applies the same escaping to weekly report
  items, keywords, and directions.
- Expanded `tests/unit/test_note_rendering.py` and added
  `tests/unit/test_weekly_rendering.py` covering payloads and user-region
  preservation on note update.

### Full regression run on `workbuddy/fix-rc-p1`

| Gate | Command | Result |
|---|---|---|
| Lock consistency | `uv lock --check` | PASS |
| Offline sync | `uv sync --locked --offline` | PASS |
| Unit + integration tests | `uv run pytest -x -q` | **583 passed** |
| Type checking | `uv run mypy src` | PASS (24 files) |
| Lint | `uv run ruff check .` | PASS |
| CLI help | `uv run youtube-intel --help` | PASS |
| Offline build | `uv run uv build --offline` | PASS (sdist + wheel) |
| Git diff check | `git diff --check` | PASS |
| Security scan | `bash scripts/security_scan.sh` | PASS (status=clean) |
| Backup/recovery drill | `bash scripts/backup_recovery_drill.sh` | PASS WITH WARNINGS (17/1/0) |

Distribution blockers documented in `docs/RELEASE_BLOCKERS.md` remain unresolved;
public distribution is still blocked pending human decisions on license, SBOM,
and third-party NOTICE items.

Verdict: REMEDIATION READY FOR CODEX REVIEW.

## TASK-014B11 Independent Integration / No-Op Closeout — 2026-08-30

- Historical source retained as evidence:
  `codex/task-014b11-safe-directory-contract-diagnostics@4b86ecb27012dd4c1c9fd2e8c2496160e64aa3bf`.
  Its effective delta from `80aff83…` spans the original five B11 paths; the Correction 2 sub-delta from `f57b21c…` changes only this handoff and the two synthetic Mapping-fixture tests.
- Forward-integration anchor `e04f52269d94dfe1317c088d49dc8ad78ae490b9` has the same stable path-scoped patch ID (`700128137ec309dfbfcd8c7b1eaf245f0bd31e7f`) and byte-identical blobs for all five B11 paths. Historical merge, cherry-pick, and replay are therefore redundant and were not performed.
- At verification `main@05ceb22d27a7aaa59f90d06e9adf6d06fd2f826d`, post-anchor overlap is restricted to this handoff, `providers/subtitles.py`, and `test_subtitle_provider.py`. The later Provider change suppresses dependency output and adds fixed safe error categories; its test asserts silence. Independent review found no change to B11 state values, output gates, restricted key-name validation, safe diagnostics, or the two corrected fixture methods.
- Current evidence: B11 focused tests, scanner regression tests, full pytest, `uv run mypy src`, Ruff, and `git diff --check` pass. The current repository scanner fails on 11 newer TASK-016 test-fixture findings; this is outside B11, is not hidden by an exemption, and receives no code change in this closeout.
- Independent verdict: `APPROVE`; `P0=0`, implementation-critical `P1=0`, `P2=0`. TASK-014B11 is `INTEGRATED / CLOSED`; its historical branch remains retained evidence. This does not change TASK-014 `IN_PROGRESS / No-Go`, real-smoke, compatibility, release, or distribution conclusions.

## TASK-014B9 Final Closed-Loop Disposition — 2026-08-30

- Historical authorization `e975ff4…` and evidence `bd770ef…` remain consumed and preserved with
  `CONTENT_UNAVAILABLE` at `1/1/0`. The distinct PO one-shot on
  `codex/task-014b9-po-one-shot-qualification@d75988a..e5642fc` remains consumed and preserved with
  fail-closed `INVALID_RESPONSE` at `1/1/0`; neither record is rewritten or replayed.
- Existing evidence does not prove a product defect, a permanently unsuitable sample, or material upstream change;
  ownership is `EVIDENCE_INSUFFICIENT`. A third execution of the fixed sample is `NOT_JUSTIFIED` and was not made.
- The current B9 package fixes one candidate and expressly forbids expansion, replacement, and reordering. With no
  committed replacement inventory or formal replacement package, this final PO disposition made zero live calls and
  concludes `CONTRACT_AMENDMENT_REQUIRED` before any future candidate qualification.
- B9 remains `BLOCKED / NOT QUALIFIED`; B11 remains `INTEGRATED / CLOSED`; TASK-016 is unchanged. No scanner
  policy, safe-directory behavior, source, dependency, or release conclusion changed. Details are in
  `docs/SMOKE_EVIDENCE/TASK-014B9-FINAL-CLOSED-LOOP-DISPOSITION.md`.

## TASK-014B9 ADR-022 Replacement-Sample Amendment — 2026-08-30

- ADR-022 is the PO/TL-authorized minimum amendment after the preserved `CONTENT_UNAVAILABLE` and
  `INVALID_RESPONSE` B9 one-shots. It retires `eIho2S0ZahI` only from current qualification use; the historical
  authorizations, attempts, counts, and evidence remain consumed and permanent.
- This PO/TL message may create one separately committed package for one replacement public sample and one
  directory-only invocation. Selection is metadata-only and may not be hidden qualification. There is no
  automatic replacement, candidate iteration, fallback, semantic retry, post-start substitution, timeout
  escalation, source fix/live-rerun, or authority for a future package.
- B11 directory safety, fail-closed result handling, scanner policy, evidence secrecy, B9 pass criteria, and
  TASK-016 remain unchanged. See `docs/decisions/ADR-022-task-014b9-replacement-sample-one-shot.md`.

## TASK-014B9 ADR-022 Replacement Selection Disposition — 2026-08-31

- The sole authorized metadata-only discovery returned the retired historical B9 ID. It was not selected;
  no other discovery, existing failed candidate, fallback, or qualification command was used.
- No eligible replacement package was frozen, so no B9 invocation occurred (`metadata/enumerate/read=0/0/0`).
  The current PO/TL package cannot proceed further without violating the one-operation/no-iteration contract.
- B9 returns to `BLOCKED / NOT QUALIFIED`. The next possible live path requires a fresh explicit PO/TL package
  with a pre-frozen eligible replacement sample. B11 and TASK-016 remain unchanged.

## TASK-014B9 Replacement Sample Nomination — 2026-08-31

- A new nomination-only PO/TL cycle applied the stricter ADR-022 single-discovery limit. The sole flat public
  metadata result provided `5MWT_doo68k`, a new official TED-source stable ID with no known credential gate,
  retirement, or prior directory failure. No title, URL, subtitle data, or public body content is retained.
- `5MWT_doo68k` is `PRE-FROZEN / ELIGIBLE FOR QUALIFICATION`, not qualified. Its directory response, subtitle
  availability, tracks, language, and B9 outcome remain unknown because the project smoke entrypoint,
  enumeration, and read paths were not invoked (`0/0/0`).
- `agent-prompts/TASK-014B9-PRE-FROZEN-REPLACEMENT-ONE-SHOT-QUALIFICATION-CODEX.md` names this sole sample
  and is ready for a separate PO execution authorization. It permits one directory-only call only, zero retry,
  zero substitution, no fallback, and no timeout escalation. B11 and TASK-016 remain unchanged.

## TASK-014B9 Final Named-Sample Qualification — 2026-08-31

- The separately authorized final package consumed exactly one canonical directory-only invocation for
  `5MWT_doo68k`. It passed with exit `0`, safe `OK`, and metadata/enumerate/read=`1/1/0`; no subtitle body was
  read, no retry/substitution/fallback/timeout escalation occurred, and the historical ID was not used.
- The fresh smoke root produced only its state file, empty data/test-vault directories, and a safe JSONL log;
  all were removed after safe inspection. B11 remained enforced. The global security scan still fails only on
  the same 11 Task-016 fixtures; B9 introduced none and scanner policy is unchanged.
- Evidence is `docs/SMOKE_EVIDENCE/TASK-014B9-FINAL-NAMED-SAMPLE-QUALIFICATION.md`. B9 is
  `QUALIFIED / CLOSED`, not a TASK-014 release approval. The next gate is PO/TL/QA/Privacy final release
  checklist sign-off; TASK-016 remains unchanged.

## Final Release Checklist Sign-Off — 2026-08-31

- The B9 evidence branch was cleanly fast-forwarded onto `main@21bf38f`; B9 is
  `QUALIFIED / CLOSED` and B11 remains `INTEGRATED / CLOSED`. No production,
  test, dependency, or lockfile content was introduced by that integration.
- The evidence-only final review is `NO-GO`, not a release authorization. It
  preserves five release-critical P1 gates: licensing/distribution and notices;
  qualified live Deep Analysis provider plus Product Owner acceptance before
  TASK-016G; a closed global security scan; Security/Privacy/PO/TL signatures
  and at-most-once acceptance; and authorized operational smoke/recovery/Vault
  validation. P0 is `0`; no push, tag, merge beyond B9 fast-forward, or public
  release occurred.
- Canonical matrix and exact validation evidence: `docs/RELEASE_SIGNOFF.md`.
  The next action is a PO/TL project-license and distribution decision package;
  it does not authorize TASK-016 provider work, TASK-016G, push, tag, or public
  distribution.

## PO/TL Private Distribution Decision — 2026-08-31

- PO/TL selected `PRIVATE / PROPRIETARY / LIMITED-DISTRIBUTION` for controlled
  source/wheel/sdist testing only. Root `NOTICE` and `pyproject.toml`
  `license.file=NOTICE` record this without inventing a copyright-holder
  identity; it is not a public-release grant.
- The current wheel/sdist contain the ADR-008 `o200k_base.tiktoken` resource,
  but primary tiktoken evidence identifies its origin/hash without an express
  file-level redistribution grant. ADR-008's no-download/fail-closed design
  prevents safe removal. Licensing remains blocked pending BPE rights/NOTICE
  and legal-owner identity; model weights, spaCy model assets, ffmpeg, Ollama,
  dependency wheels, and dev tools remain unbundled.

## `o200k_base.tiktoken` Evidence Disposition — 2026-08-31

- `O200K_BASE_REDISTRIBUTION_EVIDENCE.md` verifies the local resource against
  the canonical OpenAI Blob and classifies the available authoritative evidence
  as `C`: official OpenAI distribution/provenance is proven, but downstream
  file-level redistribution and NOTICE rights are ambiguous. The MIT license
  for the `tiktoken` repository is not extended to the separately hosted data.
- The release blocker remains. No BPE file was removed and ADR-008 received no
  fallback/network change. The document prepares—but does not authorize or
  implement—a bounded operator-provisioning alternative for a later PO/TL
  architecture decision.

## ADR-028 External `o200k_base` Provisioning — 2026-08-31

- PO/TL selected and implemented the prepared Option 1 with ADR-028: project
  source, wheel, and sdist no longer carry `o200k_base.tiktoken`. A lawful
  user/admin must explicitly provision it at `storage.data_dir/tokenizers/`
  before enabled cloud analysis can use the exact first-party SHA-256.
- The historical classification C, canonical identity, and absence of an
  downstream redistribution grant remain preserved. Runtime has no BPE
  download, cache/network fallback, tokenizer substitution, or caller-defined
  expected hash; missing, invalid, malformed, or unsafe local data fails closed
  before credentials or provider side effects.
- Offline archive inspection and provisioned-asset golden vectors are required
  evidence; the completed record is `1918 passed, 1 warning`, lock/sync,
  mypy/Ruff, offline build and direct archive checks PASS, while the canonical
  scanner remains the same eleven TASK-016 fixtures only. This resolves only
  the BPE redistribution sub-blocker for the
  controlled artifact; it does not close remaining licensing, security,
  privacy, provider, operational, or release-signature gates.
