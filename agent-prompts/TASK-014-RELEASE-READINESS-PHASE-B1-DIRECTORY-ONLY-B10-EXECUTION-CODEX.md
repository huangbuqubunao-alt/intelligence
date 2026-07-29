# TASK-014 Phase B-1 — 一次性 B10-classified directory-only 真实公开字幕验证 Executor

你是 TASK-014 Phase B-1 的唯一 Codex Smoke Executor。本包只授权一个新的、一次性的 B10-classified 真实调用窗口；本包本身不执行
任何命令。prompt 仅存在于 main 控制面，不得复制、暂存或提交到 source。

## 固定分配与历史证据边界

```text
Task: TASK-014 Phase B-1 — B10-classified single-video directory-only public subtitle validation
Role: Smoke Executor
Agent: Codex
Control-plane baseline: main@f00aa9cffa25dcb9b7165edf21a4d476263c1dc5
Worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b10-execution
Branch: codex/task-014-phase-b1-directory-only-b10-execution
Required source HEAD: f00aa9cffa25dcb9b7165edf21a4d476263c1dc5
Only executable: /Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b10-execution/.venv/bin/youtube-intel
Fixed ID: eIho2S0ZahI
B9 historical failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2
Reuse decision: DIRECT — integrated B4 restricted `smoke-public-subtitles --directory-only`, B5 fixed safe summary, B6 ADR-017 fixed diagnostics, B7 ADR-018 fixed origin/fingerprint, B8 ADR-019 restricted keyname evidence, B10 ADR-020 fixed content-availability classification, locked `youtube_intel.cli:main`, and existing release-evidence documents; no dependency or third-party change
```

- B9 evidence 是未合并的只读历史失败记录，只证明同一固定 ID 曾以 `metadata=1`、`enumerate=1`、`read=0`、
  `CONTENT_UNAVAILABLE` 停止；它不包含 B10 分类。不得 checkout、merge、cherry-pick、修改、清理、重写或称为成功，也不得把其结果
  当成本次调用或分类证据。
- 开始前必须确认 source 分支、HEAD、暂存区和工作树精确匹配且干净；不符立即停止。不得访问、修改、合并、清理或复用 B9、历史
  B-1、Retry 或其他 directory-only execution worktree。
- TASK-014 始终为 `IN_PROGRESS / No-Go`；TASK-014B10 保持 `DONE`。本次授权、任何分类或目录成功都不构成发布批准或最终 Go。

## 唯一允许的离线预配与 launcher 静态核验

只可在固定 source 中按以下顺序各运行一次；缓存缺失、锁文件变化、任何下载/网络迹象、命令不可用或任一失败均立即停止并如实记录，
不得修复、重试、换命令、安装或更新依赖：

```text
uv lock --check
uv sync --locked --offline
uv lock --check
```

三步全部通过后，才可静态确认唯一绝对 launcher 存在、为常规文件且可执行，并通过既有打包元数据/launcher 内容确认它映射
`youtube_intel.cli:main`。不得修改 `PATH`、激活 venv、运行 `--help`、`python -m`、裸 `youtube-intel`、其他 launcher 或任何替代入口；
launcher 不符立即停止。预配及静态核验不得访问网络或真实资源，且不得改变 tracked 文件或 `uv.lock`。

## 唯一一次真实调用

1. 新建一个临时父目录，并在其中选择名为 `smoke-root` 的子路径；执行前必须确认父目录存在，而该子路径事先不存在，且不是文件、目录或
   符号链接。不得把临时父目录或 smoke-root 的绝对路径写入 evidence、checklist、handoff、commit message 或聊天回传。
2. 只有以上全部门禁通过后，才可执行且只能执行一次下列固定命令。保留精确数值退出码；不得重定向、复制或持久化原始 stdout/stderr：

```text
/Users/hua/Documents/yia-worktrees/task-014-phase-b1-directory-only-b10-execution/.venv/bin/youtube-intel smoke-public-subtitles --directory-only --temporary-root ABSOLUTE_NEW_PARENT/smoke-root --video-id=eIho2S0ZahI
```

- 此命令是唯一允许访问真实 YouTube 的产品调用。唯一目标的调用上限为 metadata=`1`、enumerate=`1`、read=`0`；绝不读取字幕正文。
- 禁止第二次调用、循环、并发、重试、换 ID、增加 ID、其他子命令或产品命令。失败、非零退出、计数不符、输出缺失或安全边界无法确认时
  均立即停止，不修复产品、环境或证据。
- 禁止登录、Cookie、`.netrc`、浏览器 profile、认证、API key、`.env`、Keychain、token、凭据、媒体或字幕正文下载、ffmpeg、模型、
  Ollama、OpenAI、云端/付费服务、真实 Vault、用户笔记、用户数据、launchd 或其他真实资源。

## 安全证据与固定分类

唯一允许修改或新建的 source 路径：

1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-DIRECTORY-ONLY-B10-CLASSIFIED-PUBLIC-YOUTUBE.md`
2. `docs/RELEASE_CHECKLIST.md`（仅追加本次 B-1 条目）
3. `handoffs/TASK-014.md`

- 必须记录固定目标标识、产品调用是否发生、发生时的精确数值退出码、`metadata`/`enumerate`/`read` 整数计数和最终固定安全 error code。
  若预配或 launcher 门禁在调用前失败，只能如实记录安全停止点、调用 `NOT RUN` 与相关未执行项，不得制造退出码或摘要。
- 仅当实际安全摘要为 directory-only、`CONTENT_UNAVAILABLE`、enumerate=`1`、read=`0` 且既有 B10 出口实际输出时，才可精确记录以下
  一个固定 `content_availability`；不得从 B9、异常、退出码、文本或未输出材料推断：

```text
content_availability_video_unavailable
content_availability_environment_restricted
content_availability_extractor_compatibility
content_availability_unknown
```

- 仅当其既有门禁实际满足并实际输出时，才可记录 ADR-017 `directory_diagnostic`、ADR-018
  `directory_origin`/`directory_fingerprint`，以及 ADR-019 最多 16 个稳定排序、去重、规范 ASCII 的 `directory_key_names`。
  不得让 B6/B7/B8 的 `INVALID_RESPONSE` 证据与 B10 `CONTENT_UNAVAILABLE` 分类互相替代或反推；任何未输出字段必须省略。
- 除上述明确允许的固定字段外，不得保存或持久化 URL、标题、语言、轨道名、其他字段名、任何字段值、字幕正文、异常原文、原始响应、
  原始 stdout/stderr、完整命令、路径、Cookie、token、payload、用户数据、凭据或凭据形状。意外输出或无法安全判断均视为失败并停止，
  不得把敏感材料复制到任何证据面。

## 分类后的固定产品决策

- `content_availability_video_unavailable`：停止使用该候选，不换写成项目普遍不可用。
- `content_availability_environment_restricted`：进入独立环境处理，不继续换视频，不在本执行步骤修复。
- `content_availability_extractor_compatibility`：提出独立、范围最小的兼容任务；本执行步骤不得修改产品或依赖。
- `content_availability_unknown`：停止重试并保留 `No-Go`，不得猜测原因。
- 成功目录发现：只说明本次 directory-only smoke 通过；不得推断字幕正文可读、真实服务普遍兼容或发布获批。
- 若 `CONTENT_UNAVAILABLE` 满足计数门禁但未实际输出合法 `content_availability`，必须记录“分类未输出/证据不足”，停止且不得重试；
  不能把缺失值改写为 `unknown`。

## 提交、停止与禁止

- 执行后只允许创建一个 evidence commit，且其唯一父提交必须为
  `f00aa9cffa25dcb9b7165edf21a4d476263c1dc5`，Diff 必须严格且仅为上述三路径；提交后 source 必须干净。
- 不得修改任务状态、产品代码、测试、依赖、`uv.lock`、Schema/migration、配置、默认 CLI、日志 schema、ADR、prompt 或其他控制面；
  不得 merge、rebase、squash、reset、push、发布、清理 source 或启动 Reviewer。
- 无论预检停止、调用失败、分类结果或目录成功，TASK-014 都保持 `IN_PROGRESS / No-Go`。完成后只报告安全摘要、evidence commit SHA、
  三路径范围、实际跳过项与后续固定产品决策；不得自行批准发布。
