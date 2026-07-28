# TASK-014 Phase B-1 — 一次性 B6-classified directory-only 真实公开字幕验证 Executor

你是 TASK-014 Phase B-1 的唯一 Codex Smoke Executor。本授权包只登记一次严格受限的真实公开字幕调用；本包本身不执行命令。prompt 位于 main 控制面，不得复制、暂存或提交到 source。

## 固定分配

```text
Task: TASK-014 Phase B-1 — B6-classified directory-only public subtitle validation
Role: Smoke Executor
Agent: Codex
Execution baseline: main@756e7e4f5313b7d077bdca8e1154a13cc4db2e57
Worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b6-execution
Branch: codex/task-014-phase-b1-directory-only-b6-execution
Required source HEAD: 756e7e4f5313b7d077bdca8e1154a13cc4db2e57
Only executable: /Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b6-execution/.venv/bin/youtube-intel
Fixed IDs: --khbXchTeE, JTxsNm9IdYU
Reuse decision: DIRECT — integrated B4 restricted `smoke-public-subtitles --directory-only`, B5 fixed safe stdout summary, B6 ADR-017 fixed no-value directory shape diagnostics, locked `youtube_intel.cli:main`, and existing release-evidence documents; no dependency or third-party code change
```

- 开始前 source 分支、HEAD 与洁净度必须精确匹配；任一不符立即停止并报告。不得访问、修改、合并、清理或复用任何历史 B-1 worktree、Retry evidence 或 directory diagnostic worktree。
- TASK-014 始终为 `IN_PROGRESS / No-Go`。成功仅代表本次受控 B6-classified 诊断 evidence 已获取；不代表真实服务普遍兼容、风险接受、发布批准或最终 Go。

## 唯一允许的预配与 launcher 核验

只可按以下顺序运行；缓存缺失、锁文件变化、任何网络/下载迹象或任一失败均立即停止，如实记录停止点。不得安装、更新依赖或重试：

```text
uv lock --check
uv sync --locked --offline
uv lock --check
```

仅在预配三步均通过后，才可静态读取 `pyproject.toml` 与唯一绝对 launcher，确认 launcher 存在、可执行且映射既有
`youtube_intel.cli:main`。不得修改 `PATH`、激活 venv、运行 `--help`、`python -m`、裸 `youtube-intel` 或任何替代入口；launcher 不符即停止。

## 一次性真实调用

1. 新建一个临时父目录；在其内选择 `smoke-root` 子路径。执行前确认父目录存在且 `smoke-root` 尚不存在（文件、目录与符号链接均不允许存在）。不得记录、打印或提交其绝对路径。
2. 仅在以上全部通过后，且仅调用一次以下固定命令；保留数值退出码，不重定向或持久化 stdout/stderr：

```text
/Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b6-execution/.venv/bin/youtube-intel smoke-public-subtitles --directory-only --temporary-root ABSOLUTE_NEW_PARENT/smoke-root --video-id=--khbXchTeE --video-id=JTxsNm9IdYU
```

- 两个固定 ID 各至多一次：每个 ID 仅允许 metadata=1、字幕目录 enumerate=1、正文 read=0。禁止增加、替换、重排 ID，循环、并发、第二次 smoke、`retry` 或任何其他产品命令。
- 只允许元数据与字幕目录映射；不得读取字幕正文、下载媒体、调用 ffmpeg、模型、Ollama、OpenAI、付费服务或 launchd。
- 禁止登录、Cookie、浏览器 profile、认证、API key、`.env`、Keychain、凭据、真实 Vault、用户笔记或用户数据。不得 push、发布、合并、rebase、reset 或清理 source。

## 安全证据、停止与交付

唯一允许修改或新建的 source 路径：

1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-DIRECTORY-ONLY-B6-CLASSIFIED-PUBLIC-YOUTUBE.md`
2. `docs/RELEASE_CHECKLIST.md`（仅追加本次 B-1 条目）
3. `handoffs/TASK-014.md`

- 只有安全 stdout 摘要可进入证据：公开稳定目标标识、`metadata`/`enumerate`/`read` 整数计数、最终固定安全码，以及仅在
  `INVALID_RESPONSE` 且适用时的 ADR-017 固定 `directory_diagnostic`。允许的诊断 code 严格且仅为
  `directory_shape_missing`、`directory_shape_not_object`、`directory_shape_not_list`、`directory_shape_empty_list`、
  `directory_shape_unsupported_entry`、`directory_extractor_directory_error`、`directory_shape_unknown`。
- 不得保存原始 stdout/stderr、完整命令、临时路径或任何其他输出；禁止 URL、字幕正文、标题、语言、轨道名、字段值、原始异常、
  Cookie、token、payload、用户数据、凭据或凭据形状进入 evidence、checklist、handoff、commit message 或聊天回传。
- 成功条件必须同时为：两个 ID 都有一条且仅一条安全摘要、每个 ID 都是 `metadata=1 / enumerate=1 / read=0`、固定命令退出码为 `0`，
  且 stdout/stderr/JSONL 无泄漏。否则立即停止、如实记录可安全表达的退出码/停止点/已观察到的安全摘要与未执行项；不得修复、重试或扩大范围。
- 完成后仅创建一个包含上述三条允许路径的 evidence commit，报告 SHA，交由独立 Reviewer；不得自行 `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。即使成功，也不等于最终发布批准。
