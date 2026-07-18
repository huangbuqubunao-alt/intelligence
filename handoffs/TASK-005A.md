# TASK-005A 交接报告

## 元数据

- Task: `TASK-005A`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `codex/task-005a-local-model-shared-contracts@82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-005a`
- Branch: `codex/task-005a-local-model-shared-contracts`
- Head commit: `Pending creation of this single implementation commit`
- Started: `2026-07-17`
- Reported: `2026-07-17`

## 目标与范围

- 任务目标：冻结 ADR-007 为 TASK-006/TASK-007 共享的配置、领域与 SQLite Repository 契约，不实现任何模型或 Provider。
- 允许修改：`config.py`、`domain.py`、`state.py`、无密钥 settings 示例、三个指定测试文件和本报告。
- 实际修改：新增固定转写/评分配置、具名评分领域对象、评分摘要原子完成、Artifact 删除确认/过期枚举及离线回归测试。
- 明确未做：未修改 migration、依赖、锁文件、Provider、`transcripts.py`、CLI、任务/ADR 或 main；未访问网络 Provider、模型、媒体、Cookie、Vault 或密钥。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 配置与示例 | PASS | `TranscriptionSettings` 固定 revision、`mlx-whisper-v1` 解码参数和 8 GiB/6 GiB/2,000,000,000 资源门禁；`LocalScoringSettings` 校验 loopback `http`、digest、3 字符下限与 4,000 字符描述默认值。`test_contracts.py` 52 PASS。 |
| 具名评分领域契约 | PASS | 新增 frozen `TranscriptSample`、`ScoringDecision`、`ScoringOutcome`；`ScoringInput` 绑定 sample 与完整 SHA-256，Outcome 校验分数阈值和模型分歧。 |
| SQLite 评分摘要原子性 | PASS | `ScoringSummaryWrite` 只允许 `TRANSCRIPT_READY -> SCORED`；同一事务提交 Artifact、Provider call、视频摘要、Pipeline CAS 和 Job 成功。故障注入验证全部回滚。`test_state_store.py` 34 PASS。 |
| Artifact 索引契约 | PASS | `mark_artifact_deleted` 使用 artifact ID + content hash CAS，仅写 `deleted_at`；`list_expired_artifacts` 按 retention、UTC 截止时间与稳定排序枚举已登记未删除记录，不删除文件。 |
| 范围/红线 | PASS | 相对 base 的产品 Diff 仅限批准 8 路径；无 migration、Provider、模型、网络、依赖或锁文件变更。 |

## ADR-007 追溯

| 条款 | 落地或明确延后 |
|---|---|
| L-01 | 已以 TASK-005 `DONE` 后的指定 base 开工；TASK-006/TASK-007 未分配、未修改。 |
| L-02 | 本交付即共享契约切片；范围严格限于配置、领域、Repository、示例和测试。 |
| L-03 | `ScoringDecision` 保留最终应用决定；`ScoringOutcome` 强制 `score >= threshold` 与 `model_disagrees` 关系，不覆盖 `ScoreResult.should_summarize`。 |
| L-04 | `ScoringSummaryWrite` 与 `complete_stage` 在单一 SQLite 事务中写入最终摘要并回滚所有关联写入。 |
| L-05 | `TranscriptSample` 固定 `sampling-v1`、三段字段、字符计数和完整哈希绑定；实际 head/body/tail 采样函数、Prompt 属 TASK-007。 |
| L-06 | 配置冻结 4,000 字符描述预算，领域绑定完整内容哈希；稳定元数据编排和 request hash 计算属 TASK-007。 |
| L-07 | 配置拒绝非 loopback/非 `http`/userinfo/query/fragment/path；标准库 HTTP 实现、`/api/tags` 与 `/api/generate` 属 TASK-007。 |
| L-08 | 示例和配置固定 `qwen3:8b` 的批准 `sha256:` digest；Ollama 安装、服务和模型验证未执行。 |
| L-09 | Repository 已能随评分阶段原子索引 response Artifact/Provider call；JSON 修复、Provider 错误映射和缓存流程属 TASK-007。 |
| L-10 | 配置表达并校验固定 MLX Whisper revision policy、解码参数和参数版本；不导入或调用 `mlx-whisper`。 |
| L-11 | 配置表达模型 revision、weights 大小和 SHA-256；下载、清单验证与许可证清单属 TASK-006/TASK-014。 |
| L-12 | 音频获取、ffmpeg、真实媒体与安装均未实现，留给具备单独授权的 TASK-006。 |
| L-13 | 180 分钟门禁、`--force` 与审计 migration 均留给 TASK-010。 |
| L-14 | 实现 audio Artifact 的删除 CAS 与按保留类别的过期索引枚举；实际 DATA 根文件删除由 TASK-006/TASK-012 执行。 |
| L-15 | 配置冻结 8 GiB/6 GiB/2,000,000,000 初始资源门禁；spawn 子进程超时与真实资源校准属 TASK-006。 |

## 复用与许可证

- `DIRECT`：既有 Pydantic 2.13.4（MIT）配置/领域模型、既有 SQLite Repository 事务与已有 `videos`/Artifact/Provider-call Schema；Python 标准库 `urllib.parse`、`math` 与 SQLite（CPython/PSF 与 SQLite public-domain 组件）能力。
- `REFERENCE`：ADR-007 中的 MLX Whisper、Ollama、Qwen 和 ffmpeg 版本/许可证事实，只用于冻结字段；未复制、导入、下载或调用外部实现。
- `REJECT/DEFER`：`mlx-whisper`、Ollama SDK、`httpx`、ORM、迁移框架、模型下载、服务和网络调用均未引入；无新增依赖或许可证义务。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 锁定环境解析成功。 |
| `uv sync --locked` | PASS | 使用锁定 34 packages；仅补齐缓存缺失的既有 `uv-build` 构建依赖。 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | 52 passed。 |
| `uv run python -m pytest tests/unit/test_state_transitions.py` | PASS | 10 passed。 |
| `uv run python -m pytest tests/integration/test_state_store.py` | PASS | 34 passed。 |
| `uv run python -m pytest` | PASS | 250 passed。 |
| `uv run mypy src` | PASS | Success: no issues in 9 source files。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI help returned successfully。 |
| `uv build --offline` | PASS | sdist/wheel built; both contain `youtube_intel/migrations/001_initial.sql`。 |
| `pyproject.toml` / `uv.lock` blob audit | PASS | Base and worktree blob IDs matched exactly; no byte changes。 |

## Diff 复核

- 修改文件：`config/settings.example.yaml`、`src/youtube_intel/{config,domain,state}.py`、`tests/unit/{test_contracts,test_state_transitions}.py`、`tests/integration/test_state_store.py`、本报告。
- 是否存在任务范围外修改：否；仅上述 8 个批准路径。
- 是否存在生成文件或格式化噪声：否；离线 build 产生的、已忽略的 `dist/` 已在验证后移除。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：TDD RED 先确认新增领域/状态公开类型缺失；一次 `uv sync --locked` 因沙箱网络限制失败，获批准后仅下载锁定构建依赖并成功。
- 跳过检查及原因：无。真实模型、Ollama 服务、ffmpeg、媒体、网络、Cookie、Vault 与密钥操作未运行，因为不在授权范围内。
- 剩余风险：实际采样算法、Ollama JSON/HTTP 处理、MLX 安装/模型完整性、资源实测和文件删除者仍需后续任务独立验证。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`Pending creation of this single implementation commit`
- 复现/验证说明：使用上述锁定 uv 命令；默认测试完全离线，无 Provider、模型或真实文件系统资源调用。

## Reviewer 结论

- Reviewer agent/session：Independent Codex Reviewer
- 审查 commit：`85cd5362460044773317a48cbaae58e55aa735af`（唯一父提交：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`）
- 审查控制面：main 动态 authorization `315d4490ed60b051411ee7eef8d1127d72898c95` 是要求父提交 `3ee490c19950482ecd014668ce510ba5c742b743` 的唯一直接后继；main/source 均在开始时干净，main TASK-005A 为 `IN_REVIEW`，source 分支/head/身份均符合 Reviewer 包。source 任务卡的 `BLOCKED/UNASSIGNED` 是分配前快照。
- 范围/红线/复用：relative base...head 精确为 8 个批准路径；`pyproject.toml` 与 `uv.lock` 无差异，`git diff --check` 通过。未发现 migration、Provider、`transcripts.py`、`discovery.py`、CLI、网络/模型/媒体/密钥或文件删除实现；仅复用现有 Pydantic、SQLite Repository 与标准库。

### 重新运行的检查

| 命令/检查 | 结果 |
|---|---|
| `uv lock --check` | PASS — 34 packages resolved |
| `uv sync --locked` | PASS — 30 packages checked |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS — 52 passed |
| `uv run python -m pytest tests/unit/test_state_transitions.py` | PASS — 10 passed |
| `uv run python -m pytest tests/integration/test_state_store.py` | PASS — 34 passed |
| `uv run python -m pytest` | PASS — 250 passed |
| `uv run mypy src` | PASS — 9 source files, no issues |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS |
| `uv build --offline` | PASS — sdist/wheel both include `youtube_intel/migrations/001_initial.sql`; generated ignored `dist/` removed after inspection |
| `git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...85cd5362460044773317a48cbaae58e55aa735af` | PASS |

### 独立探针

- Probe A — configuration/resource boundary：PASS。以未复用既有测试的输入核验固定 Whisper revision/weights/decode policy、`8/6/2_000_000_000` 默认资源门禁、`0` 边界拒绝、`max_description_chars` 边界、正确 digest，以及 `127.0.0.1`/`localhost`/`[::1]` 的 `http` origin；https、非 loopback、userinfo、path/query/fragment、空白和错误 digest 均 fail-closed。静态扫描未发现 Provider/模型/网络导入或调用；userinfo sentinel 未出现在验证错误中。
- Probe B — public contracts/final policy：FAIL（见 P1-1）。普通 attribute assignment 被 frozen 拒绝，但公开 `model_copy(update=...)` 无验证地构造了所有四个对象的非法实例：`TranscriptSample(head="", selected_char_count=0)`、hash 不匹配的 `ScoringInput`、字段类型错误的 `ScoringDecision`，以及 `score == threshold` 却 `final_should_summarize=False` 的 `ScoringOutcome`。因此无法独立证明 immutable named contract、hash binding 和 final policy 的 fail-closed 语义。
- Probe C — SQLite scoring atomicity：PASS。使用真实临时 SQLite、不同 job/video/artifact/provider-call 样本验证只有 `TRANSCRIPT_READY -> SCORED` 接受 summary；缺 summary、其他阶段、bool/NaN/infinity/越界 score、pipeline/job CAS mismatch 都拒绝。对 artifact、provider-call、score summary、pipeline 和已写入 Job success 后的故障分别注入失败；每次 Artifact/Provider call/score/should_summarize/Pipeline/Job 均完整回滚。成功路径保留独立的 `ScoreResult.should_summarize=False`，并持久化 policy summary `True`。
- Probe D — Artifact cleanup index：PASS。使用真实临时 SQLite 和 sentinel file 验证 hash CAS、unknown/hash mismatch/repeat、UTC、正 limit、retention class、`expires_at/created_at/artifact_id` 稳定排序；两个 API 未读取、枚举或删除 sentinel filesystem path。

### 验收与 ADR-007 追溯

| 项目 | 结果 | 说明 |
|---|---|---|
| AC-1 配置与示例 | PASS | Probe A 与 config/example 审查通过。 |
| AC-2 不可变公共评分契约与最终策略 | FAIL | P1-1 允许 `model_copy` 绕过字段、hash 和 outcome validators。 |
| AC-3 评分摘要原子写入 | PASS | Probe C 覆盖真实 SQLite 与五个故障点。 |
| AC-4 Artifact 删除确认/过期索引 | PASS | Probe D 证明 index-only、CAS 与排序边界。 |
| AC-5 范围、复用、无 Provider/网络/Schema/lock 改动 | PASS | Git/static 审计通过。 |
| L-02 | PARTIAL/FAIL | 共享切片范围正确，但公共领域契约未 fail-closed。 |
| L-03 | FAIL | `ScoringOutcome.model_copy` 可令 final policy 偏离 `score >= threshold`。 |
| L-04 | PASS | `ScoringSummaryWrite` 与 `complete_stage` 事务探针通过。 |
| L-05/L-06 | FAIL | `TranscriptSample` 计数与 `ScoringInput` 完整 hash binding 可被 `model_copy` 绕过；实际采样/request-hash 编排仍正确留给 TASK-007。 |
| L-07/L-08/L-09 | PARTIAL/PASS boundary | 本任务负责的 config/repository 边界通过；标准库 HTTP、`/api/tags`/`/api/generate`、JSON repair/cache 与实际模型调用仍留给 TASK-007。 |
| L-10/L-11/L-15 | PARTIAL/PASS boundary | 固定配置/资源表达通过；mlx-whisper install/download/manifest/spawn timeout/实测仍留给 TASK-006/TASK-014。 |
| L-12 | DEFERRED | 音频/ffmpeg/真实媒体按 ADR 留给 TASK-006。 |
| L-13 | DEFERRED | 180 分钟 `--force` 与审计 migration 留给 TASK-010。 |
| L-14 | PASS boundary | index-only CAS/enumeration 已完成；DATA 根实际删除仍由 TASK-006/TASK-012 负责。 |

### Findings

- P1-1 — `src/youtube_intel/domain.py:27-31`, `src/youtube_intel/domain.py:540-592`: the new public Pydantic contracts rely only on `frozen=True`, but `BaseModel.model_copy(update=...)` intentionally applies updates without validation. It creates an invalid `TranscriptSample` (`head=""`, `selected_char_count=0`), a hash-mismatched `ScoringInput`, a wrongly typed `ScoringDecision`, and an outcome whose final decision contradicts `score >= threshold`. This defeats the shared fail-closed contract required by AC-2 / ADR-007 L-03, L-05 and L-06. Make public functional updates revalidate (or disallow unchecked copying) and add regression tests for each affected invariant.
- P0：None。
- P2：None。
- P3：None。

### 五轴结论与交付

- Correctness：REJECT，P1-1 breaks required public invariant enforcement.
- Architecture：otherwise follows the named config/domain/repository boundary; no Provider or Schema coupling observed.
- Security：loopback parsing and index-only Artifact APIs passed independent probes; no secrets, network or deletion capability introduced.
- Performance：bounded config/domain checks and indexed Artifact query are appropriate; no unbounded new processing observed.
- Readability：implementation and tests are clear; the missing revalidation is the material issue.
- Skipped checks：none of the required offline checks. Real model/service/media/network/Vault/file-deleter operations were intentionally not run because they are later-task, unauthorized boundaries.
- Remaining risks：P1-1 must be fixed and independently re-reviewed. Later TASK-006/007/010/012 responsibilities above remain out of scope.
- `DECISION NEEDED`：None.
- Verdict：`REJECT`
- 未解决 P0/P1：P1-1.

## Correction 1 — Pydantic `model_copy(update=...)` P1 closure

- Role: `Codex Implementer (Correction 1)`
- Starting review evidence: `3cec2d6a7b60b11912c10e714dc1473197d7374f`
- Scope: only `src/youtube_intel/domain.py`, `tests/unit/test_contracts.py`, and this
  handoff; no task status, Reviewer, merge, dependency, lockfile, Schema, Provider,
  network, model, media, Cookie, Vault, or deletion work.

### RED / GREEN

- RED: before the implementation change,
  `uv run python -m pytest tests/unit/test_contracts.py -k model_copy_rejects_all_updates`
  failed because `TranscriptSample.model_copy(update={...})` did not raise; that
  independently reproduced P1-1 from the Reviewer evidence.
- GREEN: `_UpdateProtectedScoringContract` is private and inherited only by the four
  TASK-005A public contracts: `TranscriptSample`, `ScoringInput`, `ScoringDecision`,
  and `ScoringOutcome`. It explicitly rejects every `model_copy(update=...)` call,
  including empty updates; `model_copy()` without an update still returns a new frozen
  instance. `_DomainModel` and all pre-existing domain objects retain their public
  behavior.
- Regression coverage independently exercises the Reviewer's empty/count-mismatched
  sample, transcript-hash mismatch, wrong-type decision, and `score == threshold` /
  `final_should_summarize=False` outcome updates. It also covers unknown, valid, and
  empty updates plus the no-update copy path.

### Checks

| Command | Result |
|---|---|
| `uv lock --check` | PASS — 34 locked packages resolved. |
| `uv sync --locked` | PASS — 30 packages checked; no relock or dependency change. |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS — 53 passed. |
| `uv run python -m pytest tests/unit/test_state_transitions.py` | PASS — 10 passed. |
| `uv run python -m pytest tests/integration/test_state_store.py` | PASS — 34 passed. |
| `uv run python -m pytest` | PASS — 251 passed. |
| `uv run mypy src` | PASS — no issues in 9 source files. |
| `uv run ruff check .` | PASS. |
| `uv run python -m youtube_intel --help` | PASS. |
| `uv build --offline` | PASS — sdist and wheel both contain `youtube_intel/migrations/001_initial.sql`; the newly generated ignored `dist/` was removed. |
| Pre-commit `git diff --check` | PASS. |

### Reuse, range, and risk

- `DIRECT`: the existing locked Pydantic 2.13.4 API and Python typing/collections
  interfaces. No new dependency, public free-form payload, `Any`, wide `object`,
  cast, ignore, construction bypass, or shared `_DomainModel` behavior change was
  introduced.
- Full product range remains the approved eight TASK-005A paths; the correction range
  is the three permitted paths above. `pyproject.toml` and `uv.lock` match the
  original base byte-for-byte.
- Skipped checks: none. Real models, services, media, network, authentication, Vault,
  and file deletion remain intentionally unrun and unauthorized later-task work.
- Remaining risk: public functional updates for these four contracts are deliberately
  unavailable; a future need for validated updates requires a separately specified
  API and regression suite. `DECISION NEEDED`: `None`.

## Second Independent Codex Reviewer — Correction 1

- Task: `TASK-005A`
- Role: `Second Independent Codex Reviewer`
- Reviewed Correction 1 head: `3a7df1029a77b7dec84a76c304c10e372f755b77`
- Starting evidence / only parent: `3cec2d6a7b60b11912c10e714dc1473197d7374f`
- Review authorization: main `22d65d4a27a7dfe95fec88f1985ed8ae98703d65`, the sole
  direct child of required `bb61921bc93c17e01e9b3f4e2971933b30802b21`.

### Checks rerun

| Command or inspection | Result |
|---|---|
| `uv lock --check` | PASS — 34 packages resolved |
| `uv sync --locked` | PASS — 30 locked packages checked |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS — 53 passed |
| `uv run python -m pytest tests/unit/test_state_transitions.py` | PASS — 10 passed |
| `uv run python -m pytest tests/integration/test_state_store.py` | PASS — 34 passed |
| `uv run python -m pytest` | PASS — 251 passed |
| `uv run mypy src` | PASS — no issues in 9 source files |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS |
| `uv build --offline` | PASS — sdist and wheel both contain `youtube_intel/migrations/001_initial.sql`; only the newly generated ignored `dist/` was removed afterwards |
| `git diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...3a7df1029a77b7dec84a76c304c10e372f755b77` | PASS |

### P1 `model_copy` boundary probe

- PASS. With independently constructed valid instances, every `update` for all four
  new public contracts fails closed with the stable `ValueError`: empty mapping,
  original invalid sample, valid update, unknown field, hash mismatch, wrong type,
  nested sample/decision replacement, and `score == threshold` with final `false`.
- PASS. `model_copy(update=None)` in both shallow and `deep=True` modes returns a
  distinct instance of the same type, revalidates from its dumped value, and remains
  frozen for `TranscriptSample`, `ScoringInput`, `ScoringDecision`, and
  `ScoringOutcome`.
- PASS. Static probe with `MYPYPATH=src` accepts the no-update public signature and
  rejects a normal mapping update as incompatible with `Mapping[str, Never]`; the
  runtime boundary also rejects calls widened through a base type. No product caller
  exposes a bypass. `ScoreResult.model_copy(update=...)` remains available, proving
  the correction did not alter pre-existing `_DomainModel` behavior.
- Static/diff audit found no `model_construct`, `__dict__`, `object.__setattr__`,
  free public `dict`, `Any`, wide `object`, `cast`, or `type: ignore` bypass.

### Regression, AC, and ADR-007 matrix

| Item | Result | Independent evidence |
|---|---|---|
| Probe A / AC-1 | PASS | Fixed decode/resource values and rejection of zero resources, malformed digest, non-loopback/non-http/userinfo/path/query/fragment URLs, and transcript/description boundaries. |
| AC-2 / L-03, L-05, L-06 | PASS | P1 probe above preserves immutable named contracts, full-hash binding, and threshold-derived final policy. |
| Probe C / AC-3 / L-04 | PASS | Real temporary SQLite uses a distinct scoring Job/video/artifact/call: injected post-summary failure rolls back artifact, provider call, summary, Pipeline, and Job; success commits all five atomically. |
| Probe D / AC-4 / L-14 | PASS | Real temporary SQLite verifies expiry ordering/limit and hash CAS for unknown, mismatched, successful, and repeated calls; a sentinel registered relative path was neither read nor deleted. |
| AC-5 / L-02 | PASS | Scope and static audit show no Provider, model, network, media, authentication, Vault, migration, dependency, lockfile, or file-deletion capability. |
| L-07/L-08/L-09 | PASS at this task boundary | Config and repository boundary are present; loopback HTTP, service/model preflight, JSON repair, and caching flow remain TASK-007 work. |
| L-10/L-11/L-15 | PASS at this task boundary | Fixed configuration and initial resource thresholds are present; installation, download, spawn execution, and calibration remain TASK-006/TASK-014 work. |
| L-12/L-13 | DEFERRED as specified | Audio/ffmpeg/media and duration `--force`/audit migration remain TASK-006 and TASK-010 work. |

### Scope, reuse, and five-axis review

- Correction Diff is exactly `src/youtube_intel/domain.py`,
  `tests/unit/test_contracts.py`, and this handoff; its sole parent is first-review
  evidence. Original base...Correction head remains exactly the approved eight
  TASK-005A paths. `pyproject.toml` and `uv.lock` blobs match base exactly.
- Reuse remains limited to locked Pydantic, the existing SQLite/Artifact Repository,
  and Python standard library. No new dependency, SDK, model, network/media/auth,
  Vault, Schema/migration, real data, credential, build artifact, or deletion ability
  was introduced.
- Correctness: PASS — the prior P1 and all independent probes are closed. Architecture:
  PASS — a private, narrowly inherited guard isolates the four new contracts without
  widening existing domain behavior. Security: PASS — updates fail closed and no new
  external or file-deletion surface exists. Performance: PASS — constant-time guard
  and bounded existing SQLite queries add no material overhead. Readability: PASS —
  the guard, its stable error, and regression intent are compact and explicit.

### Findings and verdict

- P0: None.
- P1: None.
- P2: None.
- P3: None.
- Skipped checks: None of the required offline checks. Real models, services, media,
  network, authentication, Vault, and actual file deletion were deliberately not run:
  they are unauthorized later-task responsibilities, not review omissions.
- Remaining risks: future validated functional-update support for these four public
  contracts needs a separately specified API and regression suite. TASK-006/007/010/012
  responsibilities remain intentionally out of scope.
- Decision needed: `None`.
- Verdict: `APPROVE`.

## Product integration and closure

- Product Integrator execution base: `7cdea4b1ff5996bfdcb42c00a245d5ae2b4e02e7`.
- Accepted source: `e726656ffcc96b3c61d12f649c5574dc927add62`.
- Merge: `865f4fed90dcc22ea43688442c1c4f210b4d31b7`, with those commits as its
  exact first and second parents.
- First-parent product range is exactly the 8 approved TASK-005A paths; lockfiles
  are unchanged. Post-merge focused `53/10/34`, full `251`, mypy, Ruff, CLI,
  `uv sync --locked`, and offline build/package migration checks all passed.
- Final status: `DONE`. The source worktree remains retained and clean. No push,
  source cleanup, or ignored `dist/` cleanup was performed.
- Deferred work: TASK-006/TASK-007 now have their code dependency satisfied but
  remain `BLOCKED/UNASSIGNED` pending their separate resource approvals.
