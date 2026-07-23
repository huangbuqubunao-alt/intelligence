# TASK-011 交接报告

## 元数据

- Task: `TASK-011`
- Role: `Implementer`
- Agent/session: `Codex / TASK-011`
- Base branch/commit: `main@44fc64be2cb4602cb93c1d03f84d6dd2a1677750`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-011`
- Branch: `codex/task-011-weekly-report`
- Head commit: pending
- Started: `2026-07-23`
- Reported: `2026-07-23`

## 目标与范围

- 任务目标：实现 ADR-010 的确定性、无 Provider 调用的 ISO 周报。
- 允许修改：`reporting.py`、只读候选查询、Obsidian 周报 upsert、包内 weekly 模板、周报测试和本报告。
- 实际修改：完成时区 ISO 周计算、`COMPLETE`/高价值/受管 NoteRef 候选查询与验证、Top N、固定模板、原子临时 Vault 周报写入和 reports 唯一 upsert。
- 明确未做：未触及 Schema/migration、`complete_stage`、CLI、配置/领域契约、依赖/锁、网络、模型、凭据、真实 Vault 或外部删除。

## 复用与许可证

- `DIRECT`：锁定的 `Jinja2>=3.1.6,<3.2`，BSD-3-Clause；以 `ImmutableSandboxedEnvironment`、`StrictUndefined`、包内固定模板和无 loader 使用。
- `DIRECT`：Python 标准库 `zoneinfo`、`hashlib`、`pathlib`、`os`；用于 ISO 周、内容哈希和现有原子写入路径。
- 未复制第三方应用代码；未新增或升级依赖。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 配置时区、跨年与 DST 周边界 | PASS | `tests/unit/test_week_period.py`：2 passed |
| 稳定 Top N、双链、空周和重复运行 | PASS | `tests/integration/test_weekly_report.py`：3 passed |
| 崩溃补偿与同目录临时文件清理 | PASS | 注入 reports upsert 失败后重试，临时 Vault 仅保留一个 `Weekly/YYYY-Www.md`，无 `.tmp` |
| 全量回归 | PASS | `uv run python -m pytest`：404 passed |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | Resolved 84 packages；未改 lock |
| `uv sync --locked` | PASS | Checked 61 packages |
| focused pytest | PASS | unit 2 passed；integration 3 passed |
| `uv run python -m pytest` | PASS | 404 passed |
| `uv run mypy src` | PASS | 21 source files，无问题 |
| `uv run ruff check .` | PASS | All checks passed |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常退出 |
| `uv build --offline` | PASS | sdist/wheel 成功构建 |
| sdist/wheel 内容核验 | PASS | 均包含 `migrations/001_initial.sql`、`templates/video.md`、`templates/weekly.md` |

## 临时 Vault I/O

- 仅 pytest `tmp_path` 下的最小 Vault：`vault/Knowledge/Weekly/`。
- 使用锚定根目录、相对路径、目录 symlink 拒绝、同目录临时文件、`fsync` 和 `os.replace`；没有真实 Vault 或用户笔记 I/O。

## Diff 复核

- 修改文件：仅任务包批准的八个路径组中的七个（无 fixture 需求）。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否；`dist/` 为忽略的本地验证产物，未暂存。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否。

## 失败、跳过与风险

- 已解决失败：TDD 初始导入失败（`youtube_intel.reporting` 尚不存在）已由最小实现覆盖；第一次全量门禁因 sandbox 不能打开共享 uv cache，获用户批准后仅用已锁定缓存重跑并通过。
- 跳过检查及原因：无。
- 剩余风险：TASK-012 尚未接入 CLI；当前服务接口保持纯本地、由后续任务编排。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：pending
- 复现/验证说明：使用临时 Artifact 根目录和临时 Vault；未调用任何 Provider 或网络。

## Independent Codex Reviewer — 2026-07-23

### 审查对象与洁净度

- Reviewer: `Codex / independent TASK-011 reviewer`
- Authorization: `main` 中 reviewer prompt 的最新提交为
  `0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`（与指定授权一致）。
- Source/base/head: `codex/task-011-weekly-report@0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e` /
  `44fc64be2cb4602cb93c1d03f84d6dd2a1677750` /
  `0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`；唯一父提交为固定 base。
- `git status --short --untracked-files=all` 在审查开始和本报告写入前均无输出；未运行会写入
  `.codebase-memory/` 的索引操作。
- 完整产品 Diff 为允许范围内的 7 个代码/测试路径及本 handoff；`pyproject.toml`、`uv.lock`、
  Schema/migration、`complete_stage`、CLI 和 TASK-012 均无 Diff。`git diff --check` 通过。

### 独立检查

| 命令 | 结果 | 证据 |
|---|---|---|
| `uv lock --check` | PASS | Resolved 84 packages；锁文件无差异。 |
| `uv sync --locked` | PASS | 初次受 sandbox 共享 uv cache 权限限制；经明确授权重跑后 `Checked 61 packages`。 |
| `uv run python -m pytest tests/unit/test_week_period.py tests/integration/test_weekly_report.py` | PASS | 5 passed。 |
| `uv run python -m pytest` | PASS | 404 passed。 |
| `git diff --check <base> HEAD` | PASS | 无输出。 |

### ADR-010 / AC / 五轴矩阵

| 项目 | 结论 | 证据 |
|---|---|---|
| W-01（ISO 周、跨年、DST） | PASS | focused 单元测试覆盖 Asia/Shanghai 跨年与 America/New_York DST 边界。 |
| W-02（候选、稳定排序、Top N、唯一 upsert） | PARTIAL | SQLite 查询为 `score DESC, video_id ASC`，现有测试覆盖 Top N 和重复 upsert；并列排序未独立复跑。 |
| W-03 / AC（趋势、关键词、持续方向均由已验证本地事实确定性聚合） | **FAIL — P1-1** | 见下方 finding。 |
| W-04（空周稳定报告） | PASS | focused 集成测试通过。 |
| W-05（固定包内 Jinja sandbox/StrictUndefined） | PASS | `reporting.py:202-210` 使用 `ImmutableSandboxedEnvironment`、`StrictUndefined`、`loader=None` 和包资源。 |
| W-06（无全局 Job/Schema/`complete_stage` 改动） | PASS | 固定 Diff 审查通过。 |
| W-07（临时 Vault 原子边界） | PARTIAL | 现有临时 Vault 与 DB-upsert 失败重试测试通过；symlink、fsync/replace 失败矩阵尚未执行，因 P1 停止。 |
| 五轴：正确性 / 回归 / 安全 / 范围 / 复用许可证 | FAIL / PASS / PARTIAL / PASS / PASS | 正确性被 P1 阻断；其余结论如上，Jinja2 直接复用与 BSD-3-Clause 证据符合登记表。 |

### Findings

- **P1-1 — 周报没有实现要求的趋势聚合，且关键词/持续方向忽略已验证 Analysis。**
  `src/youtube_intel/reporting.py:179-198` 仅将 title、score reason 和 one-sentence summary 提供给模板，
  `_keyword_counts()`（第 213 行起）只遍历 `item.score.topics`，`directions` 只是前三个相同 keyword。
  `src/youtube_intel/templates/weekly.md:1-26` 也没有“趋势”部分或趋势输入。因而两个具有不同
  `AnalysisResult.keywords` / opportunities / recommendations、但评分 topics 相同的候选会得到相同
  周报趋势与持续方向；这违反 TASK-011 AC 的“趋势、重复关键词和持续关注方向”以及 ADR-010 W-03 的
  已验证 `ANALYSIS_STRUCTURED` 确定性聚合要求。现有测试未构造或断言该反例，故 404 个通过测试不能
  覆盖该缺口。

### 停止项、风险与结论

- 任务包要求发现任一 P0/P1 后立即 `REJECT` 并停止。因此未继续运行 mypy、Ruff、CLI help、offline
  build、sdist/wheel 包含性、并列/repeated-run NoteRef、Artifact tamper、symlink 与 fsync/replace
  故障矩阵；这些均为 **skipped due to P1-1**，不是 PASS。
- P0：0。P1：1（P1-1）。P2/P3：在按 P1 停止前未新增发现，且并非完整无问题结论。
- 未触及真实 Vault、用户笔记、Provider/云调用、网络、凭据、外部删除或 TASK-012。
- Reviewer verdict: **REJECT**。
- Required correction: 在不扩大 ADR-010 范围的前提下，基于已验证 Analysis/Score/NoteRef 实现并测试
  明确、稳定的趋势、关键词和持续方向算法；补齐该 P1 的反例回归后，由全新独立 Reviewer 从新 head 重审。

## Correction 1 — Codex Implementer — 2026-07-23

### 修复范围与算法

- 仅修改 `reporting.py`、周报测试与本 handoff；未修改 `state.py`、Obsidian Adapter、模板、公共领域契约、依赖或 Schema。
- `WeeklyReportService` 现在为每个入选候选保留已验证的 `AnalysisResult` 于内部、非公共的
  `WeeklyReportInput` 子类；不会改变任何共享 domain/state 契约。
- 关键词只从 `AnalysisResult.keywords` 聚合：Unicode NFC、空白折叠、casefold 作为身份；每项 Analysis
  内去重后按频率降序、规范化键升序排列。显示文本使用确定性的最小规范表示。
- 趋势由同一 Analysis 关键词计数渲染为 `趋势：关键词（次数）`；持续关注方向仅聚合已验证 Analysis 的
  actionable directions、action recommendations、product/business opportunities，以相同文本规范化和排序规则输出。
- `ScoreResult` 和受管 `NoteRef` 仍是候选的必需验证输入，但不再作为关键词、趋势或持续方向的 fallback。
- 任何候选的 Analysis 文件缺失、内容 hash 篡改、JSON/领域验证失败或 Artifact identity/provenance 不匹配都会在
  调用 Knowledge Sink 前抛出 `WeeklyReportValidationError`；因此不写 Vault 或 reports 表。

### Correction 1 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| Analysis-only 关键词/趋势/方向 | PASS | 两个相同 Score topic、不同 Analysis keyword/direction 的候选渲染出各自 Analysis 结果，且没有 score topic fallback。 |
| 规范化、频率、并列排序 | PASS | NFC/空白/casefold 的 `Alpha`/`alpha` 聚合为 `Alpha（2）`，频率较低的 `Beta（1）` 稳定排后。 |
| 缺失、篡改、identity mismatch fail-closed | PASS | 临时 Analysis 文件删除/篡改和错误 artifact key 均在写入前失败；无 `Weekly/` 文件、无 reports upsert。 |
| 既有 W-01/W-02/W-04/W-05/W-07 回归 | PASS | focused unit=2、integration=8、full pytest=409。 |

### Correction 1 检查与边界

- `uv lock --check`、`uv sync --locked`、focused pytest、全量 pytest、mypy、Ruff、CLI help 与 offline build 全部通过。
- sdist/wheel 均核验包含 migration SQL、`templates/video.md` 和 `templates/weekly.md`。
- 临时 I/O 仍仅发生在 pytest `tmp_path` 的 Artifact 根目录、SQLite stub 与最小 Vault；没有 Provider、云调用、网络、凭据、真实 Vault 或外部删除。
- `DECISION NEEDED`：`None`。

## Correction 1 — Second Independent Codex Reviewer — 2026-07-23

### 审查对象、授权与洁净度

- Reviewer: `Codex / independent TASK-011 reviewer 2`。
- Authorization: `main` 中本 Reviewer prompt 的最新提交为
  `0bc9950d9818c739f5932d884d4803634d60eea7`；`tasks/README.md` 记录 TASK-011 为
  `IN_REVIEW`。
- Source/base/head: `codex/task-011-weekly-report@f4e30a56ddcf7d654bda4e0579f6080af59698f5` /
  `44fc64be2cb4602cb93c1d03f84d6dd2a1677750` /
  `f4e30a56ddcf7d654bda4e0579f6080af59698f5`。其唯一父为 Correction 1 review
  evidence `3759d54a74abaa8e6627b8107298d0938fbe3441`，后者唯一父为原实现
  `0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`。
- 审查开始时 `git status --short --untracked-files=all` 无输出；未运行会写入
  `.codebase-memory/` 的索引。完整 base...HEAD Diff 为允许的 7 个路径；Correction 1
  Diff 仅为 `reporting.py`、既定 integration test 和本 handoff。依赖/锁、Schema/
  migration、`complete_stage`、CLI、TASK-012 均无 Diff，`git diff --check` 通过。

### 独立检查

| 命令 | 结果 | 证据 |
|---|---|---|
| `uv lock --check`、`uv sync --locked` | PASS | Resolved 84 packages；Checked 61 packages。 |
| `uv run python -m pytest tests/unit/test_week_period.py tests/integration/test_weekly_report.py` | PASS | 10 passed。 |
| `uv run python -m pytest` | PASS | 409 passed。 |
| `uv run mypy src` | PASS | 21 source files，无问题。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常退出。 |
| `uv build --offline` | PASS | sdist 与 wheel 均成功构建。 |

### Findings

- **P1-1 — 受管视频 NoteRef 的文件存在性和内容哈希从未验证，缺失或篡改笔记仍会生成周报。**
  `src/youtube_intel/reporting.py:107-125` 对 `note_artifact` 只检查索引行的 kind/root/
  video_id/path，然后直接用该行的 `content_hash` 构造 `NoteRef`；它既没有 Vault 根目录，
  也没有读取 `Videos/...` 文件并复核哈希。`tests/integration/test_weekly_report.py` 的
  `_candidate()` 只将 score/analysis 写到 Artifact 根目录，完全不创建
  `vault/Knowledge/Videos/<video_id>.md`，但稳定周报测试仍通过。这是可复现的 missing-
  NoteRef 反例；同一索引行对应的笔记被删除、替换或篡改时，`generate()` 仍会调用
  Knowledge Sink 并写入链接到不存在或不受管内容的周报。它违反本任务包强制条件：候选必须
  具有 verified managed NoteRef，且 verified Score/Analysis/NoteRef 任一缺失或篡改必须在
  Knowledge Sink 或 `reports` 写入前 fail-closed；也不满足 ADR-010 W-02/W-03。

### ADR-010 / AC / 五轴矩阵与结论

| 项目 | 结论 | 证据 |
|---|---|---|
| W-01（配置时区、跨年、DST） | PASS | focused unit tests 2 passed。 |
| W-02（候选、稳定排序、Top N、受管 NoteRef） | **FAIL — P1-1** | NoteRef 未验证文件存在性/哈希。 |
| W-03（verified Analysis/Score/NoteRef 聚合） | **FAIL — P1-1** | Score/Analysis fail-closed 已有回归；NoteRef 不具同等保证。 |
| W-04（空周唯一稳定报告） | PASS | focused integration tests 通过。 |
| W-05（固定 Jinja sandbox/StrictUndefined） | PASS | `reporting.py` 使用 `ImmutableSandboxedEnvironment`、`StrictUndefined`、`loader=None` 与包资源。 |
| W-06（无 Schema/Job/CLI 越界） | PASS | 固定 Diff 通过。 |
| W-07（仅临时 Vault 原子写） | PARTIAL | 已有临时 Vault 集成测试通过；因 P1 停止后续 symlink/fsync/replace 故障探针。 |
| 五轴：正确性 / 可读性 / 架构 / 安全 / 性能 | FAIL / PASS / PARTIAL / FAIL / PARTIAL | P1-1 同时破坏输入完整性与输出链接正确性；其余未形成完整无问题结论。 |
| 复用/许可证 | PASS | 仅复用登记的 Jinja2（BSD-3-Clause）与标准库；无新增依赖或锁变更。 |

- P0：0。P1：1（P1-1）。P2/P3：按任务包在 P1 后停止，不构成无问题结论。
- skipped due to P1-1：sdist/wheel 内容清单、剩余临时 SQLite/Vault 反例（含 NoteRef
  修复后的 symlink、fsync/replace 和 DB 补偿矩阵）、ISO repeated-run/并列稳定性扩展
  探针以及最终无 P1/P2 的完整审查。以上不是 PASS。
- 未触及真实 Vault、用户笔记、Provider/云调用、网络、凭据、外部删除、TASK-012 或业务代码。
- Reviewer verdict: **REJECT**。
- Required correction: 在不扩大 ADR-010 范围的前提下，把受管视频 NoteRef 的存在性、受锚定路径/
  symlink 安全性和内容哈希验证纳入候选验证，并在任何 Knowledge Sink 或 reports 写入前拒绝缺失、
  篡改或身份不匹配的 NoteRef；为该反例增加临时 Vault 回归后，交由全新独立 Reviewer 从新 head 重审。

## Correction 2 — Third Independent Codex Reviewer — 2026-07-23

### 审查对象、授权与洁净度

- Reviewer: `Codex / independent TASK-011 reviewer 3`。
- Authorization: `main` 中本 Reviewer prompt 的最新提交为
  `6bc019d4d7ad0e1d04a05bdcece376ea02e7cd7f`；`main:tasks/README.md` 记录 TASK-011 为
  `IN_REVIEW`。
- Source/base/head: `codex/task-011-weekly-report@0f589aca501ea4559aeb7f4dd7aeab2a41f52b79` /
  `44fc64be2cb4602cb93c1d03f84d6dd2a1677750` /
  `0f589aca501ea4559aeb7f4dd7aeab2a41f52b79`。唯一父为 Reviewer 2 evidence
  `6f9c75df90e10b964b36dbcefc52618422d83216`，再上游为 Correction 1
  `f4e30a56ddcf7d654bda4e0579f6080af59698f5`。
- 审查开始时 `git status --short --untracked-files=all` 无输出；未运行会写入
  `.codebase-memory/` 的索引。完整 base...HEAD Diff 严格为既定 7 个路径，Correction 2
  Diff 严格为 `reporting.py`、既定 integration test 与本 handoff；依赖/锁、Schema/
  migration、`complete_stage`、CLI、TASK-012 和真实资源均无 Diff。固定 Diff check 通过。

### 独立检查

| 命令 | 结果 | 证据 |
|---|---|---|
| `uv lock --check`、`uv sync --locked` | PASS | Resolved 84 packages；Checked 61 packages。 |
| `uv run python -m pytest tests/unit/test_week_period.py tests/integration/test_weekly_report.py` | PASS | 15 passed。 |
| `uv run python -m pytest` | PASS | 414 passed。 |
| `uv run mypy src` | PASS | 21 source files，无问题。 |
| `uv run ruff check .` | PASS | All checks passed。 |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常退出。 |
| `uv build --offline` | PASS | sdist 与 wheel 成功构建。 |
| sdist/wheel 内容 | PASS | 两者均含 `migrations/001_initial.sql`、`templates/video.md`、`templates/weekly.md`。 |
| `git diff --check <base> HEAD` | PASS | 无输出。 |

### 独立临时资源探针

- 在 `/private/tmp` 的 pytest probe 中使用新建 SQLite、真实 `SQLiteStateRepository`、最小
  Vault 和 `ObsidianNoteSink`：验证候选查询、`COMPLETE`/高价值筛选、受管 NoteRef 的
  pipeline/video/provenance identity、内容 SHA-256、同一 reports key 的重复运行及同一
  `NoteRef` 均通过；删除已验证视频笔记后，在周报/`reports` 更新前 fail-closed。
- 已独立验证 `os.replace` 注入失败时不创建周报文件或 reports 行；既定 focused 回归还覆盖
  NoteRef 缺失、篡改、路径逃逸、文件和目录 symlink，及 verified Analysis-only 的趋势、
  关键词、持续方向、NFC/空白/casefold/频率/并列排序。无 Score topics fallback。
- 所有 I/O 仅在 pytest 临时 SQLite、Artifact 根目录与最小 Vault；零 Provider/云调用、网络、
  凭据或真实用户内容。

### ADR-010 / AC / 五轴矩阵

| 项目 | 结论 | 证据 |
|---|---|---|
| W-01（ISO 周、跨年、DST） | PASS | focused unit tests 覆盖。 |
| W-02（候选、稳定排序、Top N、受管 NoteRef） | PASS | SQLite 查询的稳定排序与受管 NoteRef identity/文件哈希验证；focused 与独立 probe 通过。 |
| W-03（verified Analysis/Score/NoteRef 聚合） | PASS | 分析产物、Score 与 NoteRef 缺失/篡改/identity mismatch 均在写入前拒绝；趋势无 score-topic fallback。 |
| W-04（空周稳定报告、重复 upsert） | PASS | focused integration tests 与 real SQLite repeated-run probe 通过。 |
| W-05（固定 Jinja sandbox/StrictUndefined） | PASS | 固定包内模板、`ImmutableSandboxedEnvironment`、`StrictUndefined`、`loader=None`。 |
| W-06（无 Schema/Job/CLI 越界） | PASS | 固定 Diff 审查通过。 |
| W-07（仅临时 Vault 原子写） | PASS | anchored path、symlink/普通文件拒绝、同目录原子替换与 DB-failure/recovery 覆盖通过。 |
| W-08（范围/复用） | PASS | Jinja2（BSD-3-Clause）与标准库直接复用；无新增依赖或锁变更。 |
| 五轴：正确性 / 可读性 / 架构 / 安全 / 性能 | PASS / PASS / PASS / PASS / PASS | 所有必要路径、故障边界与离线门禁通过。 |

### Findings、风险与结论

- P0：0；P1：0；P2：0；P3：0。
- skipped：无。构建产物仅位于忽略的 `dist/`，未被清理或提交。
- 未触及真实 Vault、用户笔记、Provider/云调用、网络、凭据、外部删除、TASK-012 或业务范围外文件。
- Reviewer verdict: **APPROVE**。

## Correction 2 — Codex Implementer — 2026-07-23

### 修复范围与验证策略

- 仅修改 `reporting.py`、周报 integration test 与本 handoff；没有修改 `state.py`、Obsidian Adapter、模板、
  domain/config 公共契约、依赖/锁、Schema/migration、`complete_stage` 或 CLI。
- 在候选的 Score/Analysis 校验之后、任何周报渲染或 Knowledge Sink/reports 写入之前，服务从既有
  `ObsidianNoteSink` 的受锚定 Vault root/subdir 只读配置取得根目录；未扩展公开接口或状态模型。
- 使用目录 file descriptor、`O_NOFOLLOW`、相对两段 `Videos/<name>--<video_id>.md`、普通文件 `fstat`、
  有界读取和 SHA-256 对比验证受管 NoteRef。root/subdir/Videos/file 任一 symlink、路径逃逸、缺失、非普通
  文件、过大内容、hash 不匹配或 Artifact key 与 pipeline/video identity 不匹配都 fail-closed。
- 通过后才构造 `WeeklyReportItem`；故任一候选 NoteRef 失败不会调用 Knowledge Sink、写 weekly Vault 文件或 upsert reports。

### Correction 2 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 缺失/篡改 NoteRef | PASS | pytest 临时 `Videos/` 文件删除或替换后，`generate()` 在写入前抛出，`Weekly/` 不存在且 reports 为空。 |
| symlink/逃逸防护 | PASS | 文件 symlink、`Videos` 目录 symlink 和 `Videos/../...` 路径均被拒绝，未跟随 pytest 临时 Vault 外目标。 |
| identity/provenance 不匹配 | PASS | 错误 `video-note/<pipeline>/<video>` key 在写入前被拒绝。 |
| Analysis-only 聚合与既有周报行为 | PASS | existing Analysis regression、ISO 周、空周、Top N、DB 失败补偿继续通过。 |
| 完整门禁 | PASS | focused unit=2、integration=13、full pytest=414；mypy、Ruff、CLI、locked sync、offline build 通过。 |

### Correction 2 边界与风险

- 实际 Vault/Artifact I/O 只存在于 pytest `tmp_path`；没有真实 Vault、网络、Provider/云调用、模型、凭据或测试目录外文件操作。
- sdist/wheel 已核验包含 migration SQL、`templates/video.md` 和 `templates/weekly.md`。
- 复用：现有 Python 标准库 `os`/`stat`/`hashlib` 与既有 Jinja2（BSD-3-Clause）；未新增依赖。
- `DECISION NEEDED`：`None`。

## Product Integration and Closure — 2026-07-23

- Accepted source `1ecd4bc8c6138bab6683a011cbbecddf281263c3` was merged by
  `2ba42c2f55082f5ce74ddc04d8aa18a7ef85fae1`; merge parents are execution base
  `3cdc9fc94568a4a836dc187995f98ec5148b6e97` followed by the accepted source.
- The first-parent product diff is limited to the seven approved TASK-011 paths; dependencies and lockfiles are unchanged.
- Product Integrator reran locked sync, focused tests (`15`), full pytest (`414`), mypy, Ruff, CLI help and offline build; both archives include migration SQL and video/weekly templates.
- TASK-011 is `DONE`. The retained source worktree remains clean; no push or worktree cleanup occurred. Real Vault, Provider/cloud calls, network and credentials remain unauthorized.
