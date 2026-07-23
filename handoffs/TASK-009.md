# TASK-009 交接报告

## 元数据

- Task: `TASK-009`
- Role: `Implementer`
- Agent/session: `Codex / root`
- Base branch/commit: `main@473119704c7638d7afd4e68d84d00e85064ceabd`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-009`
- Branch: `codex/task-009-obsidian-notes`
- Head commit: `Pending implementation commit`
- Started: `2026-07-22`
- Reported: `2026-07-22`

## 目标与范围

- 任务目标：在仅由 pytest 创建的临时 Vault/SQLite 中，将高价值视频安全、幂等地渲染并写入受管 Obsidian 笔记，保留用户区并原子完成 NOTE_WRITE 阶段。
- 允许修改：`notes.py`、Obsidian Provider、固定模板、notes 夹具组、unit/integration 测试和本报告。
- 实际修改：新增纯渲染/安全文件名模块、`ObsidianNoteSink`、固定包内 Jinja2 模板、4 个渲染单测、6 个临时 Vault/SQLite 集成测试和本报告；未需要新增 fixture。
- 明确未做：未修改领域/配置/状态/Schema/migration/依赖/锁文件/CLI/云 Provider/任务状态；未访问真实 Vault、用户笔记、凭据、网络、模型或云端。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 稳定身份、文件名、Frontmatter 和固定模板 | PASS | `test_note_rendering.py` 4 项覆盖 Unicode/保留名/无效 video ID、字段顺序/类型、marker、跳过分析与结构控制文本。 |
| 临时 Vault 原子创建、Artifact 和阶段完成 | PASS | `test_obsidian_sink.py::test_sink_writes_one_managed_note_and_completes_note_stage` 证明 `ANALYSIS_READY -> NOTE_WRITTEN`、VIDEO_NOTE/VAULT/LONG_LIVED Artifact 与 Job 成功。 |
| 用户区与普通已完成重跑零改写 | PASS | `test_completed_note_keeps_user_bytes_and_is_not_replaced` 修改 `我的思考` 后验证 inode 不变及用户文本保留。 |
| SQLite replace 后补账 | PASS | `test_sqlite_failure_after_replace_is_recovered_by_a_retried_note_job` 注入 `stage.after_artifacts` 事务失败，保留完整文件并由重排 Job 补账。 |
| 路径/文件安全失败关闭 | PASS | symlinked `Videos`、legacy 非受管文件、fsync 故障均在测试临时目录拒绝；未改写目标、清理本次临时文件且数据库状态保持 `ANALYSIS_READY`。 |
| 固定模板打包 | PASS | 离线 sdist/wheel 均包含 `youtube_intel/templates/video.md`；既有 migration `001_initial.sql` 仍包含。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages`；锁文件未改。 |
| `uv sync --locked` | PASS | `Checked 61 packages`。 |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS | 4 passed。 |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS | 6 passed。 |
| `uv run python -m pytest` | PASS | 337 passed。 |
| `uv run mypy src` | PASS | 15 source files，无问题。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常。 |
| `uv build --offline` | PASS | 成功生成 sdist 与 wheel。 |
| sdist/wheel 内容检查 | PASS | 两者均含 `templates/video.md` 和 `migrations/001_initial.sql`。 |
| `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd` | PASS | 提交前工作树 diff 无空白错误。提交后将按任务包精确 base 再运行。 |

## 复用与许可证证据

- `DIRECT`：TASK-009A 已锁定的 `Jinja2==3.1.6`；使用固定包内模板、`ImmutableSandboxedEnvironment`、`StrictUndefined`、无 loader/用户模板/自定义 globals。许可证为 ADR-009 N-14 与 `docs/REUSE_REGISTER.md` 记录的 BSD-3-Clause；必要传递边界为既有 `MarkupSafe==3.0.3`（BSD-3-Clause）。
- `DIRECT`：既有 PyYAML 安全加载仅用于验证受管 Frontmatter；Python 标准库 `os`、directory FD、`O_NOFOLLOW`、`fsync`、`os.replace`、`hashlib` 和 `importlib.resources`。
- `REFERENCE`：登记的 yt2md 候选未复制代码、未读取 Obsidian 配置、未访问真实 Vault。

## Diff 复核

- 修改文件：`src/youtube_intel/notes.py`、`src/youtube_intel/providers/obsidian.py`、`src/youtube_intel/templates/video.md`、`tests/unit/test_note_rendering.py`、`tests/integration/test_obsidian_sink.py`、`handoffs/TASK-009.md`。
- 是否存在任务范围外修改：否；上述 6 个路径都属于本卡 7 个允许路径组，`tests/fixtures/notes/**` 为允许但未需要触达的组。
- 是否存在生成文件或格式化噪声：否；`dist/` 与 `.venv` 为 ignored 验证产物，未纳入提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：TDD 首次 RED 因新模块缺失；随后覆盖并修正测试中字幕 fixture 的必填 provenance 字段与安全标题的空格预期。SQLite 注入失败回归确认文件成功、数据库失败时不会删除最终笔记。
- 跳过检查及原因：无。
- 剩余风险：文件系统与 SQLite 仍仅承诺 ADR-009 的 at-most-once best effort；replace 后至 SQLite 事务之间的崩溃由下次重排补账，非跨系统严格事务。真实 Vault/用户笔记路径未运行且未授权。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`Pending implementation commit`
- 复现/验证说明：运行本报告的固定 uv 命令；全部文件 I/O 测试只在 pytest 的临时目录中执行。

## Reviewer 结论

- Reviewer agent/session: `Codex / root` (independent reviewer)
- 审查 commit: `956e37a15ab29106f16c45873fccb813cc5a959f` (sole parent `473119704c7638d7afd4e68d84d00e85064ceabd`)
- Main authorization: `d44477bd0fa945383769b83f3672d1c606f3c365`; the dynamic authorization packet records TASK-009 as `IN_REVIEW`.
- Branch/initial cleanliness: confirmed `codex/task-009-obsidian-notes@956e37a15ab29106f16c45873fccb813cc5a959f`, sole fixed parent, and clean source before review actions. The complete implementation diff has six changed files, all in the authorized source paths; `git diff --check base...HEAD` passed.
- 重新运行的检查: `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...956e37a15ab29106f16c45873fccb813cc5a959f` passed. All required `uv` checks and independent probes were intentionally not run after the mandatory immediate-stop gate below.
- Findings:
  - **P1 / scope abnormality:** During review, an attempted required code-graph index created untracked `.codebase-memory/.gitattributes`, `.codebase-memory/artifact.json`, and `.codebase-memory/graph.db.zst` in the source worktree. These paths are outside the seven explicitly authorized path groups and make the source non-clean. The reviewer packet requires immediate `REJECT` and stop for any scope abnormality; no business-code, real-Vault, cloud, network, credential, or external-file operation followed. Per the packet, the reviewer did not clean or otherwise alter those paths.
  - P0: none observed before the mandatory stop.
  - P2/P3: not assessed because the required immediate-stop rule supersedes further review.
- AC/ADR matrix: `BLOCKED` for task ACs and ADR-009 N-01–N-15; independent test and probe evidence is not validly complete after the P1 scope gate. Five-axis review is likewise incomplete by design.
- Reuse/license review: `BLOCKED`; no conclusion beyond the implementer report is adopted without the mandated independent review.
- Skipped/risks: all focused/full tests, mypy, Ruff, CLI help, offline build/package-inclusion checks, and probes A–E were skipped solely because the review packet mandates stopping immediately on P1. The untracked out-of-scope index artifacts remain a source-tree integrity risk requiring orchestrator direction.
- Verdict：`REJECT`
- 未解决 P0/P1: `P1` unresolved — untracked `.codebase-memory/` artifacts outside the fixed allowed scope.

## Reviewer 2 结论（清理后复审）

- Reviewer agent/session: `Codex / root` (fresh independent reviewer)
- 审查对象：`codex/task-009-obsidian-notes@d16498fe2a1939c6bec7babd03039e623782d027`；唯一父提交为 implementation `956e37a15ab29106f16c45873fccb813cc5a959f`，固定 base 为 `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Main authorization：`33ab12dc8abe6267c8c011c85822e34c6fbc8274`（动态读取 `main` 的 Reviewer-2 授权包）；`main` 项目状态将 TASK-009 列为等待独立审查，即 `IN_REVIEW`。
- 初始门禁：PASS。审查开始与写入本节前均执行 `git status --short --untracked-files=all`，无输出；没有 `.codebase-memory/` 或其他未跟踪工件。未运行任何会写入代码索引的动作。`git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD` 通过，完整 Diff 仅为本报告、`notes.py`、Obsidian Provider、固定模板和两个允许的测试文件。

### 独立检查

| 命令 | 结果 | 证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 84 packages`；未改锁文件。 |
| `uv sync --locked` | PASS | `Checked 61 packages`。 |
| `uv run mypy src` | PASS | 15 source files，`Success: no issues found`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS | 4 passed。 |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS | 6 passed。 |
| `uv run python -m pytest` | PASS | 337 passed。 |
| `uv run python -m youtube_intel --help` | PASS | 正常输出帮助。 |
| `uv build --offline` | PASS | 成功构建 sdist 与 wheel。 |
| sdist/wheel template 与 migration inclusion | SKIPPED | P1 出现后的立即停止规则；本轮未解包检查。 |

### 独立探针与 Findings

- **P1 — ADR-009 N-05 / AC 稳定身份和 fail-closed 候选冲突失效：**
  `src/youtube_intel/notes.py:81` 每次从当前标题重新派生路径，而
  `src/youtube_intel/providers/obsidian.py:194-205` 只检查该单个文件名，既不保存首次路径，也不扫描/拒绝同一 `--<video_id>.md` 候选。隔离临时 Vault/SQLite 探针先放置非受管 `Legacy--video-123.md`，随后调用 sink；实现仍创建 `A safe product note--video-123.md`，最终存在两份相同 video_id 的笔记。ADR 要求多个候选或非受管占位全部失败关闭，不能创建第二份。
- **P1 — ADR-009 N-03/N-05 / 标题变化回放失效：** 同一探针首次完成 `A safe product note--video-123.md` 后，仅改变 `VideoMetadata.title` 再普通重排。渲染后的相对路径变为新标题路径，`_verify_existing` 在 `obsidian.py:183-189` 找不到该新文件并抛出 `NotePersistenceError`。已 `NOTE_WRITTEN` 的普通重跑必须验证并返回首次 NoteRef、零改写；标题变化不得改名或导致失败。
- **P2 — ADR-009 N-06 / 可移植路径校验不完整：** `_safe_subdir`（`obsidian.py:261-267`）接受 `C:`；独立构造探针确认未抛出 `ValueError`。该值在当前 POSIX 主机不逃逸，但 ADR 明确要求拒绝盘符，需随实现修复。
- 探针 A（低价值零写、completed/skipped、frontmatter/StrictUndefined/资源）：现有 focused tests 覆盖部分；本轮在出现 P1 后不继续扩展。
- 探针 B（Unicode/保留名/casefold/穿越、symlink/目录替换/legacy/marker/UTF-8）：已复现同 video_id 非受管候选未 fail-closed；其余不在 P1 后继续。
- 探针 C（用户 bytes、无变化零 replace、成功状态重排、标题变化）：标题变化失败已复现；其余不在 P1 后继续。
- 探针 D（临时 Vault/SQLite 的短写/fsync/replace、补账、原子性/回滚）：现有 tests 与全量 suite 通过；P1 后不另作更多故障注入。
- 探针 E（ADR/AC/五轴/复用与许可证/范围）：范围、依赖/锁、Schema/migration、CLI、云 Provider、真实 Vault/网络/凭据均未见变更；因 P1 不给出通过结论。

### AC / ADR-009 / 五轴矩阵

| 项目 | 结论 | 依据 |
|---|---|---|
| AC：稳定身份、标题变化、候选冲突 | FAIL / P1 | 上述两个临时目录独立复现。 |
| AC：其他临时 Vault/SQLite、原子写与恢复项 | BLOCKED | P1 后按任务包停止，不将已通过 suite 视为完整 AC 证据。 |
| ADR N-01、N-02、N-04、N-07–N-15 | BLOCKED | 未发现范围外公共契约/依赖变更，但立即停止规则阻止逐项验收。 |
| ADR N-03、N-05 | FAIL / P1 | 普通重排与固定文件身份不符合契约。 |
| ADR N-06 | FAIL / P2 | 未拒绝 drive-style subdir。 |
| 正确性 | FAIL / P1 | video_id 的稳定一对一笔记身份不成立。 |
| 可读性、架构、性能 | BLOCKED | 不以未完成的五轴审查掩盖 P1。 |
| 安全 | BLOCKED | 路径契约 P2 待修复，P1 已要求停止。 |
| 复用/许可证 | BLOCKED | Jinja2/PyYAML/标准库路径和实现者声明表面符合登记，但本轮不完成独立接受。 |

### 范围、跳过项与风险

- Diff/红线复核：PASS。没有依赖或锁文件、`state.py`、Schema/migration、CLI、云 Provider、TASK-008 或真实 Vault 变更；测试运行和独立探针只在临时目录/临时 SQLite。
- 跳过：因首个 P1 的固定“立即 REJECT 并停止”门禁，未执行 package archive inclusion 解包，且未继续所有 A–E 的扩展故障探针。
- 剩余风险：修复必须保存/检索首次稳定路径，并在写入或补账前按 video_id 检测所有候选、NFC/casefold 冲突和非受管占位；不得通过重命名、删除或接管既有笔记规避冲突。
- Verdict：`REJECT`
- 未解决 P0/P1：`P1` unresolved — title-derived path breaks completed replay and same-video candidate conflicts are silently accepted.

## Correction 1 — Implementer evidence

- Dynamic authorization: `main@2717609961e054001a0aef800f8c568c568b51ef` is the current
  `TASK-009-CORRECTION-1-CODEX.md` control-plane commit and records TASK-009 as
  `IN_PROGRESS`. Source started clean at
  `f778163dca83807f1baec5e568c4dbd734829171` with sole parent
  `d16498fe2a1939c6bec7babd03039e623782d027`; no `.codebase-memory/` index was run or created.
- Scope: modified only `src/youtube_intel/notes.py`,
  `src/youtube_intel/providers/obsidian.py`,
  `tests/integration/test_obsidian_sink.py`, and this handoff. The permitted
  unit-test path was reviewed but did not require a change. No template, fixture,
  dependency/lockfile, shared contract, configuration, state, schema/migration,
  CLI, TASK-008, or main file changed.
- Stable identity: completed normal replay now retrieves the existing
  `VIDEO_NOTE` Artifact via the already-approved `get_artifact_by_key` repository
  method, validates its VAULT/video provenance, scans all same-video candidates,
  and verifies that exact original path without rendering, replacing, or renaming.
  No Schema or Repository method was introduced.
- Fail-closed candidates: every verification, write, and replace/recovery path
  enumerates directory entries whose NFC/casefold-normalized suffix claims the
  video ID. Multiple candidates, an Artifact/path mismatch, an unmanaged
  placeholder, or an unsafe existing entry fail before any final-file write,
  rename, move, or deletion. A singleton valid managed candidate remains usable
  only for the existing SQLite replace-before-commit recovery path.
- Path hardening: `vault_subdir` now rejects every drive-style component such as
  `C:` and `C:notes`, in addition to the pre-existing absolute, traversal,
  backslash, NUL, and whitespace boundaries.
- Regression evidence: temporary Vault/SQLite tests cover completed title change
  (same NoteRef, bytes and inode unchanged), unmanaged `--<video_id>.md`,
  multiple, casefold, and NFC candidates (original bytes unchanged and no new
  file), and `C:` rejection with no Vault child created. All filesystem/database
  I/O in these regressions used pytest temporary paths only.

### Correction 1 checks

| Command | Result |
|---|---|
| `uv lock --check` | PASS — Resolved 84 packages; lockfile unchanged. |
| `uv sync --locked` | PASS — Checked 61 packages; used the existing local uv cache only. |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS — 4 passed. |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS — 12 passed. |
| `uv run python -m pytest` | PASS — 343 passed. |
| `uv run mypy src` | PASS — 15 source files, no issues. |
| `uv run ruff check .` | PASS. |
| `uv run python -m youtube_intel --help` | PASS. |
| `uv build --offline` | PASS — sdist and wheel built without network access. |
| Archive inclusion check | PASS — both archives contain `youtube_intel/templates/video.md` and `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check` before commit | PASS. |

### Correction 1 reuse, risks, and conclusion

- Reuse: `DIRECT` existing SQLite `VIDEO_NOTE` Artifact lookup, Jinja2/PyYAML
  boundaries, and Python standard-library `os`/`unicodedata`; no new component or
  license obligation. The registered `yt2md` candidate remains `REFERENCE` only.
- Unauthorised operations not run: no real Vault or user-note access, no
  test-directory-external note operation, no network/cloud/credential/media/model
  path, and no code-graph indexing action.
- Diff review: restricted to the four paths above; no generated artifacts,
  dependency, Schema, secret, real-resource, or unrelated changes.
- Remaining risk: the existing ADR-009 at-most-once boundary remains unchanged;
  recovery after a crash between atomic replace and SQLite commit still depends on
  a later eligible job. It now fails closed if note identity is ambiguous.
- `DECISION NEEDED`: `None`.

## Reviewer 3 — Correction 1 independent review

- Reviewer agent/session: `Codex / root` (fresh independent reviewer)
- Reviewed source: `codex/task-009-obsidian-notes@60ed077452faf5fe41b105b21b4221f89cb6e02c`; fixed base `473119704c7638d7afd4e68d84d00e85064ceabd`; sole parent `f778163dca83807f1baec5e568c4dbd734829171`, whose evidence chain is `f778163... -> d16498... -> 956e37...`.
- Main authorization: dynamic packet commit `5874f4569ced297b6b827735a44959bebc306243`; its main task card records TASK-009 as `IN_REVIEW`.
- Cleanliness/scope gate: PASS before review. `git status --short --untracked-files=all` had no output. No code-graph or codebase-memory indexing ran. Full base...HEAD diff contains only the six allowed path groups; Correction 1 itself changes only `notes.py`, `providers/obsidian.py`, the integration test, and this handoff. No dependency/lock, public contract, `state.py`, schema/migration, CLI, cloud-provider, TASK-008, credential, network, model, real-Vault, or user-note operation occurred.

### Re-run checks

| Command/check | Result | Independent evidence |
|---|---|---|
| `uv lock --check` | PASS | Resolved 84 packages; lock unchanged. |
| `uv sync --locked` | PASS | Checked 61 packages, using only the existing local uv cache. |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS | 4 passed. |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS | 12 passed. |
| `uv run python -m pytest` | PASS | 343 passed. |
| `uv run mypy src` | PASS | Success, no issues in 15 source files. |
| `uv run ruff check .` | PASS | All checks passed. |
| `uv run python -m youtube_intel --help` | PASS | Help rendered normally. |
| `uv build --offline` | PASS | sdist and wheel built offline. |
| Archive inclusion | PASS | Both archives contain `youtube_intel/templates/video.md` and `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...60ed077452faf5fe41b105b21b4221f89cb6e02c` | PASS | No whitespace errors. |

### Finding

- **P1 — ADR-009 N-13 error-code contract is violated:**
  `src/youtube_intel/providers/obsidian.py:157-158` catches every `OSError` from
  Vault operations and unconditionally maps it to `ErrorCode.LOCAL_RESOURCE`.
  ADR-009 N-13 instead requires `EACCES`, `EPERM`, and `EROFS` to map to
  `ErrorCode.PERMISSION_DENIED`; only resource errors such as `ENOSPC`,
  `EDQUOT`, `EIO`, fsync, and replace failures map to `LOCAL_RESOURCE`.
  The only current injected OS-error regression (`test_obsidian_sink.py:463`)
  raises an errno-less fsync failure, so it cannot detect this required
  distinction. This gives a caller the wrong remediation and violates the
  approved failure semantics. Per the review authorization, discovery of this
  P1 requires immediate rejection and no business-code repair.
- P0: none observed before the required stop.
- P2/P3: not assessed; the mandatory immediate-stop rule takes precedence.

### Independent probes and acceptance matrix

| Item | Result | Evidence |
|---|---|---|
| A — completed title-change replay; `NOTE_WRITTEN`/`COMPLETE` zero rewrite | BLOCKED | Correction tests pass, but no new probe after the P1 stop. |
| B — non-managed/multiple/NFC/casefold candidate fail-closed | BLOCKED | Correction tests pass, but no new probe after the P1 stop. |
| C — drive-style, Unicode/reserved/traversal, symlink/directory replacement, legacy/marker/UTF-8 safety | BLOCKED | Correction tests pass, but no new probe after the P1 stop. |
| D — low-value zero write; completed/skipped rendering; frontmatter/StrictUndefined/limits; user bytes/no-op replace | BLOCKED | Focused suite passes, but no new probe after the P1 stop. |
| E — temporary Vault/SQLite short-write/fsync/replace, recovery/Artifact/Pipeline/Job atomicity | FAIL / P1 | The approved OS-error mapping used by these paths is incorrect for permission failures. |
| Task AC: stable identity, conflict safety, rendering and recovery | BLOCKED | No P0/P1 found in those areas before the mandated stop; not independently accepted. |
| ADR-009 N-01–N-12, N-14–N-15 | BLOCKED | Scope/reuse/build evidence is compatible, but a P1 prevents approval. |
| ADR-009 N-13 | FAIL / P1 | All `OSError` values collapse to `LOCAL_RESOURCE`. |
| Correctness | FAIL / P1 | Error contract is externally observable and wrong for permission failures. |
| Readability / architecture / performance | BLOCKED | Not completed after mandatory stop. |
| Security | FAIL / P1 | Permission failures are not classified according to the approved safe failure boundary. |
| Reuse / license | BLOCKED | Jinja2/MarkupSafe and existing dependencies appear unchanged; no acceptance after P1. |

### Reviewer 3 conclusion

- Skipped: expanded independent probes A–D and any further code inspection after the P1; the authorization requires stopping at the first P0/P1. No real Vault, user note, network, cloud, credential, model, or test-directory-external file I/O was run.
- Remaining risk: Correction 2 must add errno-aware, safe error mapping and focused temporary-directory regressions for `EACCES`, `EPERM`, and `EROFS`; it must not weaken the ADR, change unrelated contracts, or treat permission failures as storage-resource exhaustion.
- Verdict: `REJECT`
- Unresolved P0/P1: `P1` — `EACCES`/`EPERM`/`EROFS` are mapped to `LOCAL_RESOURCE` instead of `PERMISSION_DENIED`.

## Correction 2 — Implementer evidence

- Dynamic authorization: `main@14585b834b342b8db3b6d70730a1639fc2fb1eff` is the
  current `TASK-009-CORRECTION-2-CODEX.md` control-plane commit; main records
  TASK-009 as `IN_PROGRESS` for this correction.
- Starting source: `codex/task-009-obsidian-notes@f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`,
  sole parent `60ed077452faf5fe41b105b21b4221f89cb6e02c`; the worktree was clean,
  with no `.codebase-memory/` artifact.
- Scope: modified only `src/youtube_intel/providers/obsidian.py`,
  `tests/integration/test_obsidian_sink.py`, and this handoff. No notes,
  templates, fixtures, dependencies/lockfiles, shared contracts, configuration,
  `state.py`, schema/migrations, CLI, TASK-008, or main files changed.

### N-13 fix and regression evidence

- The sink now maps only `EACCES`, `EPERM`, and `EROFS` from Vault I/O to
  `ErrorCode.PERMISSION_DENIED`; every other `OSError`, including `ENOSPC` and
  errno-less fsync/replace failures, remains `ErrorCode.LOCAL_RESOURCE`.
  The public message remains the fixed safe text `note persistence failed` and
  chains no filesystem exception.
- A temporary Vault/SQLite parametrized integration regression injects all three
  permission errno values, `ENOSPC`, errno-less `fsync`, and errno-less
  `replace`. It asserts the exact error code, unchanged pre-existing managed
  note bytes, cleanup of the owned temporary file, `ANALYSIS_READY` Pipeline,
  `RUNNING` Job, and no `VIDEO_NOTE` Artifact. All I/O stays under pytest's
  temporary directory.
- TDD evidence: before the implementation change, the new permission cases
  failed `3` times because they returned `LOCAL_RESOURCE`; after the minimal
  errno mapping they pass together with all resource cases.

### Correction 2 checks

| Command | Result |
|---|---|
| `uv lock --check` | PASS — resolved 84 packages; lockfile unchanged. |
| `uv sync --locked` | PASS — checked 61 packages from the existing local cache. |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS — 4 passed. |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS — 17 passed. |
| `uv run python -m pytest` | PASS — 348 passed. |
| `uv run mypy src` | PASS — 15 source files, no issues. |
| `uv run ruff check .` | PASS. |
| `uv run python -m youtube_intel --help` | PASS. |
| `uv build --offline` | PASS — sdist and wheel built locally. |
| sdist/wheel template and migration inclusion | PASS — both contain `youtube_intel/templates/video.md` and `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check` before commit | PASS. |

### Correction 2 reuse, risks, and conclusion

- Reuse: `DIRECT` Python standard-library `errno` and existing `OSError`/atomic
  write boundary; no dependency, version, license, or adapter boundary changed.
  Jinja2/PyYAML and the registered yt2md candidates remain untouched.
- Unauthorized operations not run: no real Vault or user note, test-directory-
  external note operation, network/cloud/credential/media/model path, or
  codebase-memory index action.
- Diff review: restricted to the three authorized paths; no generated artifact,
  dependency, Schema, secret, real-resource, or unrelated change is included.
- Remaining risk: the established at-most-once boundary after successful replace
  and before SQLite completion remains unchanged; real-Vault behavior is still
  untested and unapproved.
- `DECISION NEEDED`: `None`.
- Suggested state: `IN_REVIEW`; this implementer does not change task status or
  start a Reviewer.

## Reviewer 4 — Correction 2 independent review

- Reviewer agent/session: `Codex / root` (fourth independent reviewer).
- Authorization and object: dynamic main authorization
  `3b7ab34e27ba996fdbf7a95f47f40d24634b020e` records TASK-009 as `IN_REVIEW`.
  Reviewed `codex/task-009-obsidian-notes@22147b087157a6bbb0adc7e78f2f5d3eae700f8e`,
  whose sole parent is reviewer-3 evidence
  `f4a231b503ea6c1a25bf73c7d8aa584147cbdc03`; the chain continues through
  Correction 1 `60ed077452faf5fe41b105b21b4221f89cb6e02c` to implementation
  `956e37a15ab29106f16c45873fccb813cc5a959f` and fixed base
  `473119704c7638d7afd4e68d84d00e85064ceabd`.
- Cleanliness and scope: PASS. `git status --short --untracked-files=all` was
  empty before review and again after checks. No codebase-memory or CodeGraph
  index action ran. Correction 2 changes only the authorized Obsidian Adapter,
  existing integration test, and this handoff; the complete base...HEAD diff is
  exactly the six authorized TASK-009 path groups. No dependency/lock, public
  contract, `state.py`, Schema/migration, CLI, cloud Provider, TASK-008,
  credential, network, model, real-Vault, or user-note path changed or ran.

### Re-run checks

| Command/check | Result | Independent evidence |
|---|---|---|
| `uv lock --check` | PASS | Resolved 84 packages; lock unchanged. |
| `uv sync --locked` | PASS | Checked 61 packages from the existing cache. |
| `uv run python -m pytest tests/unit/test_note_rendering.py` | PASS | 4 passed. |
| `uv run python -m pytest tests/integration/test_obsidian_sink.py` | PASS | 17 passed. |
| `uv run python -m pytest` | PASS | 348 passed. |
| `uv run mypy src` | PASS | Success, no issues in 15 source files. |
| `uv run ruff check .` | PASS | All checks passed. |
| `uv run python -m youtube_intel --help` | PASS | Help rendered normally. |
| `uv build --offline` | PASS | sdist and wheel built offline. |
| Archive inclusion | PASS | sdist and wheel both contain `youtube_intel/templates/video.md` and `youtube_intel/migrations/001_initial.sql`. |
| `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...22147b087157a6bbb0adc7e78f2f5d3eae700f8e` | PASS | No whitespace errors. |

### Independent probes and review matrix

- ADR-009 N-13: PASS. A separate reviewer-run temporary Vault/SQLite matrix
  injected `EACCES`, `EPERM`, `EROFS`, `ENOSPC`, errno-less `fsync`, and
  errno-less `replace`. The first three returned `PERMISSION_DENIED`; the last
  three returned `LOCAL_RESOURCE`. Every case retained the original managed-note
  bytes, removed only the owned temporary file, left Pipeline at
  `ANALYSIS_READY`, Job at `RUNNING`, and wrote no `VIDEO_NOTE` Artifact. The
  public error was the fixed `note persistence failed` text and contained no
  temporary absolute path, user bytes, injected exception text, or errno.
- ADR-009 N-03/N-05/N-06: PASS. Code and regression review confirm completed
  title-change replay returns the stored NoteRef without replacement; unmanaged,
  multiple, NFC, and casefold candidates fail closed; and drive-style subdirs are
  rejected. No rename, deletion, or unmanaged-note takeover occurs.
- ADR-009 N-07–N-12 and N-15: PASS. Focused rendering/integration and full-suite
  evidence cover fixed Frontmatter/markers, skipped analysis, low-value zero
  write, bounded fixed template, user-byte/no-op preservation, symlink/legacy
  rejection, atomic temporary-file cleanup, stage completion, and replace-before-
  SQLite recovery. The implementation keeps the specified at-most-once boundary.
- ADR-009 N-01/N-02/N-04/N-14: PASS. Shared `KnowledgeSink`/`NoteRef` behavior
  and the locked Jinja2/PyYAML/standard-library boundaries were unchanged;
  Correction 2 adds only standard-library `errno` classification and no license
  or dependency obligation.
- Five-axis review: correctness PASS (errno-aware mapping is safe and exact);
  readability PASS (small named helper and focused regression); architecture PASS
  (existing Adapter error boundary retained); security PASS (safe error text and
  fail-closed permission classification); performance PASS (constant-time errno
  membership check and no new I/O or scans).

### Findings, skipped work, and conclusion

- P0: none. P1: none. P2: none. P3: none.
- Skipped only as unauthorized: real Vault/user notes, external deletion/move,
  real cloud/network/credentials/media/models, and TASK-008 source access. All
  review filesystem and SQLite I/O was confined to pytest or reviewer-created OS
  temporary directories.
- Remaining risk: ADR-009 intentionally remains at-most-once best effort after a
  successful `os.replace` and before SQLite completion; a later eligible retry
  performs the approved verification-and-backfill path. Real-Vault behavior is
  still untested and unapproved.
- Verdict: `APPROVE`.
- `DECISION NEEDED`: `None`.
