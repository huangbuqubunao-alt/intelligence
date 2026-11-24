# TASK-009A：Obsidian 笔记共享契约与依赖基线

- Status: `DONE`
- Assignee: `已整合并关闭`
- Reviewer: `第二轮全新独立 Codex APPROVE；Product Integrator 已完成`
- Owner role: Codex Implementer + 全新独立 Codex Reviewer
- Size: S
- Risk: High
- Depends on: TASK-008A
- Decision gate: ADR-009 N-01 至 N-15 已于 2026-07-20 批准
- Resource gate: Jinja2、必要传递依赖、网络包下载、锁文件和本卡离线命令已批准；
  已获固定 base/worktree/角色/文件范围分配

## 2026-07-20 产品审批

- 批准 `Jinja2>=3.1.6,<3.2`、必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改和本卡列出的 uv 离线验证/构建。
- TASK-008A 已为 `DONE`；本任务已获固定 worktree/角色/文件范围。不得与任何其他
  写入任务并发修改 `domain.py`/锁文件。
- 真实 Vault、真实用户笔记、最终文件删除/移动/重命名、真实 OpenAI/密钥/付费调用
  继续未授权。

## 2026-07-22 正式分配

- Base：`main@e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Worktree：`/Users/developer/Documents/yia-worktrees/task-009a`
- Branch：`codex/task-009a-obsidian-note-shared-contracts`
- Implementer：Codex；Reviewer：实现提交后启动全新独立 Codex 会话。
- 允许产品范围严格为 `domain.py`、`test_contracts.py`、`pyproject.toml`、`uv.lock` 和
  `handoffs/TASK-009A.md`。本任务 source 从固定 base 创建，保留的 `BLOCKED/UNASSIGNED`
  卡片是预期快照；main 上本卡/分配包是实时授权。
- 已批准 `Jinja2>=3.1.6,<3.2`、必要传递依赖、包下载、锁定与本卡离线验证。真实 Vault、
  用户笔记、文件 I/O、移动/删除、云端和凭据仍未授权。

## 2026-07-22 实现证据与审查授权

- Implementation source：`75158be08d6442a7b18099f459654e9da86ebcee`；唯一父提交为
  固定 base `e4271e41910bba54b37b48df709dcf632fe3b0eb`，完整 Diff 精确为任务批准的五路径。
- Implementer 自报 Jinja2 `3.1.6` 已设为直接依赖，contracts `74 passed`、全量 `326 passed`、
  mypy、Ruff、CLI、lock/sync、offline build 与 migration package inclusion 均 PASS；这些是
  待独立复跑证据，不构成验收。
- 状态进入 `IN_REVIEW`；全新独立 Codex Reviewer 只可在 source handoff 记录结论，不得
  改产品代码、依赖、锁文件、main 或任务状态。真实 Vault、用户笔记、文件 I/O、云端与凭据
  继续未授权。

## 2026-07-22 首轮审查拒绝与 Correction 1

- Reviewer evidence：`f73b28756c371d80fb7525bd7e4defb6b82b1a3c`；唯一父为 implementation
  `75158be08d6442a7b18099f459654e9da86ebcee`，且仅修改 source handoff。
- Verdict=`REJECT`，P1：纯 `KnowledgeSink` Protocol 虽冻结 keyword-only 签名，但没有
  调用时 fail-closed 边界，naive `processed_at`、首尾空白 `pipeline_version` 和
  `final_should_summarize=false` 的低价值写入可通过。
- 产品负责人批准保持 ADR-009 N-02 的公开签名不变，改为带公共验证入口的抽象基类；
  成功校验后才进入受保护 abstract 实现钩子。Correction 1 仅允许 `domain.py`、
  `test_contracts.py` 与 `handoffs/TASK-009A.md`，禁止依赖、Vault、文件 I/O、Schema 或
  其他产品范围变化。

## 2026-07-22 Correction 1 实现证据与第二轮审查授权

- Correction source：`9ef4b2f63df65d09569ba119c6873805dcd9de17`；唯一父为首轮 review
  evidence `f73b28756c371d80fb7525bd7e4defb6b82b1a3c`，Correction 精确为
  `domain.py`、`test_contracts.py` 和 source handoff 三路径，完整产品 Diff 仍为五路径。
- 公开 `KnowledgeSink.upsert_video_note` 的 ADR-009 N-02 keyword-only 参数与 `NoteRef`
  返回类型保持不变；公共入口现在在委派前验证 UTC-aware 时间、clean version 和高价值评分，
  仅成功后调用受保护抽象钩子。`AnalysisCompleted`/`AnalysisSkipped` 均保留合法输入语义。
- Implementer 自报 contracts `75 passed`、全量 `327 passed`、mypy、Ruff、CLI、lock/sync、
  offline build 与 migration package inclusion 均 PASS；这仅构成待第二轮独立复跑的证据。
- 状态为 `IN_REVIEW`；Reviewer 2 仅可写 source handoff，不得预写 `APPROVE`、`ACCEPTED`、
  merge 或 `DONE`。

## 2026-07-22 第二轮独立审查、验收与整合授权

- Reviewer evidence：`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`；唯一父为 Correction 1，
  且只修改 source handoff。Verdict=`APPROVE`，P0/P1/P2/P3 均无。
- 独立复跑 contracts `75`、全量 `327`、mypy、Ruff、CLI、locked sync、offline build、
  migration inclusion、固定 Diff 与 KnowledgeSink/NoteRef 探针均 PASS；真实 Vault、
  文件 I/O、云端、凭据和网络仍未授权。
- 主控验收为 `ACCEPTED`。Product Integrator 仅可 non-fast-forward merge、复跑离线门禁、
  验证五路径 first-parent Diff 与 Jinja2/MarkupSafe 依赖边界；不得提前写 merge 或 DONE。

## 2026-07-22 主线整合与收口

- Codex Product Integrator 已以 merge commit `9b0269eddbd29cee83a056d44951d7973c87492b`
  整合 accepted source `e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`；双父顺序为
  `1fd031629fc6a7fda2a81e1944ef7a439b9b8259`、`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`。
- 整合后 locked sync、contracts `75 passed`、全量 `327 passed`、mypy、Ruff、CLI、offline build、
  sdist/wheel migration inclusion 及五路径 first-parent Diff 均 PASS；Jinja2 `3.1.6` 为直接依赖，
  MarkupSafe `3.0.3` 为必要传递依赖，既有直接依赖未升级。
- 本任务收口为 `DONE`。source branch/worktree 保留作审计；真实 Vault、用户笔记、文件 I/O、云端、
  凭据与网络路径仍未因本共享契约任务获得授权。

## 目标

在不写任何 Vault 文件、不实现 sink 的前提下，冻结 TASK-009 所需的
`KnowledgeSink`、`NoteRef` 和 Jinja2 依赖基线，并消费 TASK-008A 的结构化
`AnalysisOutcome`。

## 范围

- 把 `KnowledgeSink.upsert_video_note` 收紧为 ADR-009 N-02 的 keyword-only
  签名，使用 `ScoringOutcome`、`AnalysisOutcome`、稳定 `processed_at` 和
  `pipeline_version`。
- 强化 `NoteRef` 为安全 POSIX `.md` 相对路径和 64 位小写 SHA-256；禁止未验证
  `model_copy(update=...)`。
- 补领域契约正反测试，证明低价值资格、分析跳过原因和稳定写入上下文可被静态类型
  直接消费；不实现文件 I/O。
- 把 `Jinja2>=3.1.6,<3.2` 提升为显式直接依赖；锁定、导入并复核许可证和
  `MarkupSafe` 传递边界。

## 范围外

- 不实现 `notes.py`、`providers/obsidian.py`、模板、文件名或原子写算法。
- 不创建临时/真实 Vault、目录、文件、symlink 或删除任何路径。
- 不修改 `state.py`、Schema/migration、`complete_stage`、配置或 CLI。
- 不实现已成功笔记的主动 refresh Repository 方法。
- 不调用云端、读取凭据或访问真实用户内容。

## 验收标准

- [ ] KnowledgeSink 签名只接受最终评分和结构化分析结果，缺少稳定时间/版本时不能
  通过类型/运行时契约。
- [ ] NoteRef 拒绝绝对路径、反斜杠、盘符、`.`/`..`、空组件、非 `.md`、非小写
  SHA-256 和未验证 update。
- [ ] Jinja2 成为批准范围内的显式直接依赖，可离线导入；现有直接依赖不被意外升级。
- [ ] 无文件 I/O、Provider、Repository、Schema、模板、网络或 Vault 行为。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv run python -m pytest tests/unit/test_contracts.py`
- [ ] `uv run python -m pytest`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv build --offline`
- [ ] `git diff --check <base>...HEAD`
- [ ] 人工审计：无 Vault/文件/state/Schema 写入；sdist/wheel 仍包含 migration。

## 预计触达文件

- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `pyproject.toml`
- `uv.lock`
- `handoffs/TASK-009A.md`

若需要 `state.py`、Schema、配置、模板或任何文件 I/O 才能完成，必须报告
`DECISION NEEDED`。

## 复用决定

- `DIRECT`：已批准 `Jinja2>=3.1.6,<3.2`，BSD-3-Clause；只可在本任务正式分配后
  执行安装、下载和锁定。
- `DIRECT`：现有 Pydantic、PyYAML、领域对象和 Python 标准库路径类型。
- `REFERENCE`：已登记 yt2md 项目只提供输出结构参考，不复制代码、不读取 Obsidian
  配置。
- `REJECT/DEFER`：任意模板 loader、用户模板、成功笔记 refresh、真实 Vault 和文件
  写入留给正式 TASK-009/010 与独立授权。

## 交付证据

- ADR-009 N-01 至 N-04、N-14 的契约/依赖追溯表。
- KnowledgeSink/NoteRef 的正反类型与运行时测试。
- 依赖解析、许可证、完整 Diff 和零文件/Vault 行为声明。
