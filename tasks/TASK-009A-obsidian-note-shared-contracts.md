# TASK-009A：Obsidian 笔记共享契约与依赖基线

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Reviewer: `全新独立 Codex，等待实现 commit`
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
- Worktree：`/Users/hua/Documents/yia-worktrees/task-009a`
- Branch：`codex/task-009a-obsidian-note-shared-contracts`
- Implementer：Codex；Reviewer：实现提交后启动全新独立 Codex 会话。
- 允许产品范围严格为 `domain.py`、`test_contracts.py`、`pyproject.toml`、`uv.lock` 和
  `handoffs/TASK-009A.md`。本任务 source 从固定 base 创建，保留的 `BLOCKED/UNASSIGNED`
  卡片是预期快照；main 上本卡/分配包是实时授权。
- 已批准 `Jinja2>=3.1.6,<3.2`、必要传递依赖、包下载、锁定与本卡离线验证。真实 Vault、
  用户笔记、文件 I/O、移动/删除、云端和凭据仍未授权。

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
