# TASK-009A：Obsidian 笔记共享契约与依赖基线

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Reviewer: `UNASSIGNED`
- Owner role: Codex Implementer + 全新独立 Codex Reviewer
- Size: S
- Risk: High
- Depends on: TASK-008A
- Decision gate: ADR-009 N-01 至 N-15 尚待产品负责人批准
- Resource gate: Jinja2 直接依赖、锁文件和包下载尚未任务级授权

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
- [ ] `uv build`
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

- `DIRECT-PENDING`：`Jinja2>=3.1.6,<3.2`，BSD-3-Clause；实际安装/锁定仍需任务级
  批准。
- `DIRECT`：现有 Pydantic、PyYAML、领域对象和 Python 标准库路径类型。
- `REFERENCE`：已登记 yt2md 项目只提供输出结构参考，不复制代码、不读取 Obsidian
  配置。
- `REJECT/DEFER`：任意模板 loader、用户模板、成功笔记 refresh、真实 Vault 和文件
  写入留给正式 TASK-009/010 与独立授权。

## 交付证据

- ADR-009 N-01 至 N-04、N-14 的契约/依赖追溯表。
- KnowledgeSink/NoteRef 的正反类型与运行时测试。
- 依赖解析、许可证、完整 Diff 和零文件/Vault 行为声明。
