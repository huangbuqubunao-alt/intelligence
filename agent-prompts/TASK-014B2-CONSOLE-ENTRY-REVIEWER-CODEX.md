# TASK-014B2 — 独立 Codex Reviewer（正式 console entry）

你是全新的独立 Codex Reviewer。只审查固定的 TASK-014B2 source；不得修改业务代码、测试、打包元数据、锁文件、
任务状态或 main。唯一允许写入是向 source 的既有 `handoffs/TASK-014B2.md` 追加审查证据。

## 固定对象

```text
Task: TASK-014B2 — formal console entry
Role: Reviewer
Agent: Codex
Main control-plane base: main@b4d6981e56da8366f0c512a8f0544396d47cd209
Source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b2-console-entry
Source branch: codex/task-014-phase-b2-console-entry
Review HEAD: f6e71e027c86f16cc34e062fef0a753c73b42d05
Required parent: b4d6981e56da8366f0c512a8f0544396d47cd209
```

开始时必须确认 main/source 身份、父链、source 清洁度和 `b4d6981...f6e71e0...` Diff。范围必须精确为：
`pyproject.toml`、`tests/integration/test_console_entry.py`、`README.md`、`docs/operations.md` 与
`handoffs/TASK-014B2.md`；`uv.lock` 必须无差异，依赖包集合、版本、来源和关系不得变化。否则 `REJECT`，不得修复。

## 独立离线审查

仅允许离线本地验证；若缓存不足或命令试图联网，立即停止并记录 `BLOCKED/REJECT`，不得联网重试。

1. 核验 `[project.scripts]` 只有 `youtube-intel = "youtube_intel.cli:main"`，并追踪该既有 `cli.main`；不得存在
   新包装模块、第二套 parser 或 CLI 行为改变。
2. 运行 `uv lock --check` 和离线 locked sync；复核 lock 无 Diff。
3. 独立运行 focused console-entry 测试、`youtube-intel --help` 与 `python -m youtube_intel --help`，确认二者 CLI
   表面一致且不触发 Provider、Vault、网络、媒体、模型或配置写入。
4. 离线构建 wheel，并在新的临时位置以离线/无依赖方式安装，核验 wheel `entry_points` 与安装后的
   `youtube-intel` 均精确映射、可运行。
5. 独立运行任务包列出的离线 mypy、Ruff 与 Diff/范围检查；README 和 operations 必须只说明同一入口，
   不得把它写成 B-1 smoke 通过、发布批准或 TASK-014 Go。

## 红线与结论

禁止真实 YouTube/B-1、网络、真实资源、真实 Vault、凭据、Cookie、媒体、ffmpeg、模型、Ollama、OpenAI、付费调用、
发布、push、merge、rebase、reset 或清理。不得启动其他 Worker。

仅在所有门禁通过时把 Verdict=`APPROVE`（P0–P3）写入 source handoff；否则写 `REJECT` 和可定位证据。无论结论，
TASK-014B2 仍由主控决定 `ACCEPTED/DONE`，TASK-014 总体保持 `IN_PROGRESS / No-Go`。
