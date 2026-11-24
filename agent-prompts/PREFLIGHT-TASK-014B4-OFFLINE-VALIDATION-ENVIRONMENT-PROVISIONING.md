# TASK-014B4 — 离线验证环境预配（一次性受控预检）

你是独立的离线环境预配执行者，不是 TASK-014B4 Implementer 或 Reviewer。本包只授权验证既有 B4 source
是否已能使用锁定的离线环境；不授权实现、测试、构建、审查、真实资源或修改任何文件。

## 固定对象与前置门禁

```text
Task: TASK-014B4 — offline validation environment provisioning
Role: controlled preflight executor
Control-plane baseline: ccc747800b59e2bacc918f1e7b81e065b1520d9a
Sole source worktree: /Users/developer/Documents/yia-worktrees/task-014b4-directory-only-smoke
Sole source branch: codex/task-014b4-directory-only-smoke
Required pre-control source HEAD: ccc747800b59e2bacc918f1e7b81e065b1520d9a
```

- 本包的控制面提交只能是 `ccc747800b59e2bacc918f1e7b81e065b1520d9a` 的唯一直接子提交。
  执行前只读确认 source 分支、控制面 HEAD 与工作树；控制面 HEAD 必须是承载本包的直接子提交，
  其唯一父提交必须精确为 `ccc747800b59e2bacc918f1e7b81e065b1520d9a`，且 `git status --short` 为空。
  任一不满足立即停止并报告；不能修复、切换、清理或写入。
- TASK-014 保持 `IN_PROGRESS / No-Go`；TASK-014B4 保持 `READY`。不得启动 Implementer、Reviewer
  或任何后续任务。

## 唯一允许命令（按此顺序，仅在 source worktree）

```text
uv lock --check
uv sync --locked --offline
uv lock --check
```

除必要的只读 Git 前后门禁外，不得执行任何其他命令。不得运行 pytest、Ruff、mypy、build、产品 CLI、
Python/import、安装器或网络诊断。

## 强制停止与禁止项

- 若 `uv sync --locked --offline` 报告缓存缺包，或任一命令显示网络访问、下载、锁文件变化或其他失败，立即停止；
  不得重试、联网、下载、安装替代包、修改、暂存或提交任何文件。
- 结束时只读核验 source HEAD 仍为本控制面提交且工作树干净；否则报告 `blocked`。预配执行者不得改动
  source HEAD、暂存区或工作树。
- 禁止 YouTube、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、
  OpenAI、付费调用、launchd 和 `.codebase-memory` 工件。
- 不得把预配成功表述为 B4 测试通过、Implementer 已启动、真实兼容性、发布批准或 TASK-014 Go。

## 回传格式（只在聊天中，不写仓库）

```text
Preflight: TASK-014B4 offline validation environment provisioning
Control-plane baseline: ccc747800b59e2bacc918f1e7b81e065b1520d9a
Source: codex/task-014b4-directory-only-smoke@<control-plane-commit> / clean | blocked
Commands: uv lock --check -> <PASS|FAIL>; uv sync --locked --offline -> <PASS|FAIL>; uv lock --check -> <PASS|FAIL|not run>
Network/download/lock/file changes: none observed | blocked before any change
Result: environment ready | blocked
TASK-014 / TASK-014B4 state: unchanged
Implementer/Reviewer: not started
```

仅当三条允许命令全部成功、没有网络/下载/锁文件变化、source 在结束后仍保持控制面 HEAD 且干净时，报告
`environment ready`；否则只报告 `blocked`、首个失败命令和安全停止原因。
