# TASK-014B2 — Codex Implementer（正式 console entry）

你是 TASK-014B2 的唯一 Codex Implementer。只实现 ADR-014 与任务卡允许的最小打包入口；不得启动真实 smoke、
修改 CLI/业务代码或扩大资源边界。

## 固定分配

```text
Task: TASK-014B2 — formal console entry
Role: Implementer
Agent: Codex
Control-plane base: main@820ff34fbd481e31b50d9d9d54828810d8ab7ca4
Worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b2-console-entry
Branch: codex/task-014-phase-b2-console-entry
Reviewer: 全新独立 Codex Reviewer（本包不启动）
Reuse decision: DIRECT — youtube_intel.cli:main、现有 uv build backend 与已锁定依赖
```

开始前确认 main 授权文件解析为本控制面提交、worktree/branch/HEAD 正确且干净。B-1 source 的 `4a349055…`
仅为入口缺失阻断 evidence；不得合并、引用为成功、写入 handoff 为 smoke 通过，或因此执行真实 smoke。

## 唯一允许路径

1. `pyproject.toml`
2. `uv.lock`（仅必要时）
3. `tests/integration/test_console_entry.py`
4. `README.md`
5. `docs/operations.md`
6. `handoffs/TASK-014B2.md`

`pyproject.toml` 只可新增 `[project.scripts]` 中的 `youtube-intel = "youtube_intel.cli:main"`。不得修改
`src/`、既有测试、依赖声明、build backend、工具配置、Schema/migration、配置、任务状态、控制面或项目 LICENSE。

## 锁文件与离线验证

先运行 `uv lock --check`。只有它要求时才可运行 `uv lock`，并以重生成前后 `uv.lock` 的包名、版本、来源和
依赖关系 Diff 证明完全不变；否则立即停止。允许 `uv sync --locked` 与离线 CLI/安装包验证，但不得联网或改变
任何依赖。必须验证：focused 入口测试、`uv run youtube-intel --help`、`uv run python -m youtube_intel --help`、
`uv run mypy src`、`uv run ruff check .`、`uv build --offline` 与 Diff 范围。

## 禁止项与完成

禁止真实 YouTube、网络 smoke、媒体、ffmpeg、模型、Ollama、OpenAI、付费调用、Cookie、登录、API key、真实 Vault、
用户数据、发布、push、merge、rebase、reset 或清理。不得把入口测试通过写成 B-1 或发布通过。

完成后只提交允许路径，填写 handoff 的复用/命令/结果/跳过项/风险，报告 SHA，保持 TASK-014 `IN_PROGRESS / No-Go`，
交由独立 Reviewer；不得自行 `ACCEPTED` 或 `DONE`。
