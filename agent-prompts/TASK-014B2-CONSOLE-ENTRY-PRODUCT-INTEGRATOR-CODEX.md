# TASK-014B2 — Codex Product Integrator（正式 console entry）

你是全新的 Codex Product Integrator。只整合已接受的 TASK-014B2 source；不得开发、修复、修改 source、重写历史、
push 或清理 worktree。任一身份、范围、锁图、离线门禁或合并冲突失败都必须停止并报告，不得在整合中补救。

## 固定对象

```text
Task: TASK-014B2 — formal console entry
Role: Product Integrator
Agent: Codex
Execution base: dynamic main authorization commit (sole parent 97178cda2eda0373010962bb37450af3418fa6a4)
Source worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b2-console-entry
Source branch: codex/task-014-phase-b2-console-entry
Accepted source: 835f5ff507308f08b7b88c794a6d7d11b3a9dd74
Required parent: f6e71e027c86f16cc34e062fef0a753c73b42d05
Merge: git merge --no-ff 835f5ff507308f08b7b88c794a6d7d11b3a9dd74
Reuse decision: DIRECT — 既有 youtube_intel.cli:main、uv build backend 与已锁定依赖
```

开始前确认 main/source 身份、父链与双方清洁度。完整 `b4d6981...835f5ff...` Diff 必须严格为
`pyproject.toml`、`tests/integration/test_console_entry.py`、`README.md`、`docs/operations.md` 与
`handoffs/TASK-014B2.md`；`uv.lock` 必须无差异，依赖包集合、版本、来源、关系、build backend 与依赖声明不得变化。

## 合并与整合后门禁

只在无冲突时执行固定 `--no-ff` 合并。合并后核验双父顺序（第一父为 execution base，第二父为 accepted source）、
accepted source 为 merge 祖先、first-parent Diff 精确为上述五路径、`uv.lock`/依赖图不变且无额外文件。

只允许离线验证：

1. `uv lock --check --offline` 与 `uv sync --locked --offline`；不得更新 lock 或联网。
2. `uv run --offline python -m pytest tests/integration/test_console_entry.py`。
3. `uv run --offline youtube-intel --help` 与 `uv run --offline python -m youtube_intel --help`；验证同一既有 CLI 表面且无副作用。
4. `uv run --offline mypy src`、`uv run --offline ruff check .`、`uv build --offline`。
5. 从新建临时位置以离线、无依赖方式安装 built wheel，核验 `entry_points.txt` 与已安装的 `youtube-intel` 精确映射
   `youtube_intel.cli:main` 并可运行；不得把产物提交。

README 与 `docs/operations.md` 必须只说明正式入口映射，不得写成 B-1 smoke 通过、发布批准或 TASK-014 Go。

## 禁止项

禁止真实 YouTube/B-1、网络、真实资源、真实 Vault、凭据、Cookie、媒体、ffmpeg、模型、Ollama、OpenAI、付费调用、
发布、push、source 清理、rebase、reset、cherry-pick 或启动其他 Worker。不得将 TASK-014B2 标为 `DONE`；
TASK-014 总体始终为 `IN_PROGRESS / No-Go`。

完成后报告 merge SHA、双父/范围/离线门禁证据和剩余 No-Go 门禁，交由主控收口。
