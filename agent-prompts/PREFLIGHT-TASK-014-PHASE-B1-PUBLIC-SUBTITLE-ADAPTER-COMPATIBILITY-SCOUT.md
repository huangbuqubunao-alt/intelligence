# TASK-014 Phase B-1 — 公开字幕 Adapter 兼容性诊断 Scout（只读）

你是 TASK-014 Phase B-1 的只读 Codex Scout。本包只授权离线静态诊断，不执行、修改、创建 worktree 或提交。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/operations.md`、本包及固定 B-1 evidence。若任一边界冲突，停止并报告。

## 固定对象与诊断目标

```text
Task: TASK-014 Phase B-1 — public subtitle Adapter compatibility diagnostic
Role: Read-only Scout
Agent: Codex
Control-plane baseline: main@f73d79b3e2f22632393bd314b9a87433e505f1ba
Evidence source worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry
Evidence source branch: codex/task-014-phase-b1-console-entry-retry
Evidence HEAD: 9acab5d876b38d64a9aeab7aca3474be2676ce38
Required sole parent: 365c8fca966a3fb7608f41b2d3ac530504193c7b
Reuse decision: DIRECT — 既有 yt-dlp Adapter、公开字幕 smoke 组合入口、离线 Fake 夹具与 B-1 脱敏 evidence；不新增或复制第三方代码
```

- 开始前只读核验 evidence HEAD、唯一父提交、分支与干净工作树。不得修改、合并、cherry-pick、清理或把
  `9acab5d…` evidence 写成通过；它记录最终真实 smoke `FAIL`，不改变 TASK-014 `IN_PROGRESS / No-Go`。
- 固定事实：`--khbXchTeE`、`JTxsNm9IdYU` 各一次元数据读取和字幕目录读取，均在正文选择/读取前以
  `INVALID_RESPONSE` 失败；正文读取均为零。没有认证、Cookie、媒体、用户数据、重试或替代入口。

## 仅允许的离线只读诊断

只允许阅读已跟踪的静态材料和 Git 历史：

1. 公开字幕 Adapter 的字段/响应结构假设、JSON/错误处理和 `INVALID_RESPONSE` 映射；
2. `smoke-public-subtitles` 的组合与调用计数/停止语义；
3. 现有离线 Fake、fixture 与集成测试对字幕目录、选中字幕和正文读取的覆盖；
4. 固定 B-1 evidence、发布检查表与 handoff 中的脱敏真实结果及已执行安全边界。

优先使用已配置的 CodeGraph 或代码库知识图谱做代码定位；若不足，才对已跟踪代码和文档作精确文本阅读。可使用
`git show`、`git diff`、`git status` 和只读文件查看。诊断必须保持离线、无副作用。

## 绝对禁止

- 禁止网络、YouTube、真实资源、烟雾命令、测试、构建、lint、typecheck、`uv`、安装、下载、依赖/锁文件操作。
- 禁止代码、测试、文档、evidence、配置、任务状态、handoff 或任何其他仓库文件写入；禁止创建 worktree、分支、commit、
  `.codebase-memory` 或任何索引/缓存工件。
- 禁止读取或使用登录、Cookie、浏览器 profile、API key、`.env`、Keychain、真实 Vault、用户笔记/数据、媒体、ffmpeg、
  模型、Ollama、OpenAI、付费服务或 launchd。
- 禁止把候选修复、离线 Fake 通过或推测的真实 Provider 行为写成真实 smoke 成功；不得执行任何后续验证。

## 聊天回传格式（不写仓库）

仅向主控对话回传一份紧凑报告：

1. 证据核验：固定 HEAD/父提交/干净状态，以及每个 ID 的真实读取计数与 `INVALID_RESPONSE` 停止点；
2. 对照表：Adapter 字段/响应假设 → 现有 Fake/fixture 覆盖 → 真实 B-1 证据 → 最可能不兼容处；
3. 最小修复建议：明确文件、函数/契约、测试夹具或断言的最小范围，并区分事实与推断；
4. 后续一次验证所需的精确授权：执行 source/base、允许写入路径、命令、固定目标/调用次数、临时根、网络/凭据/媒体边界、
   必要 Reviewer 与客观通过/失败证据；
5. `DECISION NEEDED`：`None` 或阻断原因。

本 Scout 不是实现、验证、Reviewer、发布批准或 TASK-014 状态变更授权。
