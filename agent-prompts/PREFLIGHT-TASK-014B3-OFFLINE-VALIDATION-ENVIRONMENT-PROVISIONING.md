# TASK-014B3 — 离线验证环境预配（一次性受控预检）

你是独立的离线环境预配执行者，不是 TASK-014B3 Implementer 或 Reviewer。本包只授权为既有 B3 source 验证锁定环境是否已可离线使用；它不授权任何实现、测试、构建、审查或真实资源操作。

## 固定对象与前置门禁

```text
Task: TASK-014B3 — offline validation environment provisioning
Role: controlled preflight executor
Control-plane baseline: main@99651ec8e32f18f5592310ab3a46fdf692c270ea
Sole source worktree: /Users/hua/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics-implementation
Sole source branch: codex/task-014b3-public-subtitle-diagnostics-implementation
Required source HEAD: 9c5f08ec829629591b095bd68841ca3ce0b22532
```

- 开始前只读确认 source 分支、HEAD 和工作树；HEAD 必须精确匹配且 `git status --short` 为空。任一不满足立即停止并报告，不能修复、切换、清理或写入。
- TASK-014 保持 `IN_PROGRESS / No-Go`；TASK-014B3 保持 `READY`。不得启动 Implementer、Reviewer 或任何后续任务。
- 唯一 source 是上述 implementation worktree。旧 B3 worktree/branch 禁止访问、修改、合并、清理或复用。

## 唯一允许命令（按此顺序，仅在 source worktree）

```text
uv lock --check
uv sync --locked --offline
uv lock --check
```

除必要的只读 Git 门禁外，不得执行任何其他命令。不得运行 pytest、Ruff、mypy、build、产品 CLI、Python/import、安装器或网络诊断。

## 强制停止与禁止项

- 若 `uv sync --locked --offline` 报告缺少缓存包或以任何原因失败，立即停止；不得重试、联网、下载、安装替代包或改动任何文件。
- 禁止网络、下载、依赖或锁文件变更、源码/测试/配置/文档修改、暂存、提交、push、merge、rebase、reset、checkout、清理、worktree/branch 创建。
- 禁止 YouTube、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、OpenAI、付费调用、launchd 和 `.codebase-memory` 工件。
- 不得把预配成功表述为 B3 测试通过、Implementer 已启动、真实兼容性、发布批准或 TASK-014 Go。

## 回传格式（只在聊天中，不写仓库）

```text
Preflight: TASK-014B3 offline validation environment provisioning
Control-plane baseline: 99651ec8e32f18f5592310ab3a46fdf692c270ea
Source: codex/task-014b3-public-subtitle-diagnostics-implementation@9c5f08ec829629591b095bd68841ca3ce0b22532 / clean | blocked
Commands: uv lock --check -> <PASS|FAIL>; uv sync --locked --offline -> <PASS|FAIL>; uv lock --check -> <PASS|FAIL|not run>
Network/download/file changes: none observed | blocked before any change
Result: environment ready | blocked
TASK-014 / TASK-014B3 state: unchanged
Implementer/Reviewer: not started
```

仅当三条允许命令全部成功、source 在结束后仍保持精确 HEAD 且干净时，报告 `environment ready`；否则只报告 `blocked` 及首个失败命令和安全停止原因。
