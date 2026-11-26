# TASK-009A — Codex Implementer

你是 TASK-009A 的唯一 Codex Implementer。只在指定 source worktree 实现本卡的共享领域契约与依赖基线；不得合并 main、修改任务状态、启动 Reviewer、push 或清理任何其他 worktree。

## 分配事实

- Source worktree：`/Users/developer/Documents/yia-worktrees/task-009a`
- Source branch：`codex/task-009a-obsidian-note-shared-contracts`
- Source base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- Main assignment authority：
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-009A-IMPLEMENTER-CODEX.md`
  必须解析为包含 TASK-009A=`IN_PROGRESS`/Codex 的当前 main 提交。

source 的 `tasks/TASK-009A-obsidian-note-shared-contracts.md` 仍显示 `BLOCKED/UNASSIGNED` 是从固定 base 创建时的预期冻结快照；它不与本分配冲突。开工前必须读取 main 上的当前任务卡和本包，并以 main 控制面为实时任务状态；若 main 的授权、分支、base、范围或状态不符，立即 `BLOCKED`。

## 目标与唯一产品范围

按 ADR-009 N-01 至 N-04、N-14，在没有 Vault 或文件 I/O 的前提下，冻结 `KnowledgeSink` keyword-only 签名、`NoteRef` 逻辑相对身份与 Jinja2 直接依赖基线，供后续 TASK-009 消费 TASK-008A 的 `AnalysisOutcome`。

仅允许：

1. `src/youtube_intel/domain.py`
2. `tests/unit/test_contracts.py`
3. `pyproject.toml`
4. `uv.lock`
5. `handoffs/TASK-009A.md`

不得改配置、`state.py`、Schema/migration、`complete_stage`、CLI、Provider、`notes.py`、模板、Repository、任务/ADR/main 或其他任何文件。范围不足时报告 `DECISION NEEDED`。

## 已批准依赖与复用

- `DIRECT`：`Jinja2>=3.1.6,<3.2`（BSD-3-Clause）和必要传递依赖；仅在此 worktree 可执行一次 `uv add`/锁定/包下载。复核已解析的 `MarkupSafe` 边界和许可证。
- `DIRECT`：既有 Pydantic 领域对象和 Python 标准库路径类型。
- `REFERENCE`：登记的 yt2md 仅作输出结构参考；不复制代码、不读取 Obsidian 配置。
- `REJECT/DEFER`：模板 loader、用户模板、成功笔记 refresh、真实 Vault/文件 I/O 均留给 TASK-009/010。

## 红线和验收

- 不创建、读取、写入、移动、删除临时或真实 Vault/笔记/目录/symlink；不实现 `notes.py`、Obsidian Provider 或模板。
- 不调用云端、读取凭据、访问用户内容、启动模型或改变 TASK-008A 的 OpenAI 隔离边界。
- `KnowledgeSink.upsert_video_note` 必须精确采用 ADR-009 N-02 的 keyword-only 参数：`video`、`transcript`、`scoring`、`analysis`、稳定 UTC-aware `processed_at`、非空且无首尾空白的 `pipeline_version`；返回 `NoteRef`。
- `NoteRef` 仅接受规范 POSIX 相对 `.md` 路径与 64 位小写 SHA-256，拒绝绝对/反斜杠/盘符/`.`/`..`/空组件/NUL/首尾空白和所有未验证 `model_copy(update=...)`。
- 补充正反类型与运行时契约测试，证明低价值评分和 `AnalysisSkipped` 可被静态消费；不要把这种消费实现为任何 I/O。

## 必须验证

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check e4271e41910bba54b37b48df709dcf632fe3b0eb...HEAD
```

人工检查：Jinja2 为批准范围内显式直接依赖，既有直接依赖未意外升级；无 Vault/文件/Provider/Repository/Schema/模板/网络行为；sdist/wheel 仍包含 migration。填写 handoff 后创建一个范围明确的 commit，保持 worktree 干净，回传 commit SHA、命令结果、实际复用/许可证、范围和未运行真实资源的说明。
