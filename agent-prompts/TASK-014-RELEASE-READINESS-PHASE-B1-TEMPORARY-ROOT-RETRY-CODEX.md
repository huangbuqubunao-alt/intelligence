# TASK-014 Phase B-1 — non-existing temporary-root 参数纠正最终 Retry

> **已完成并废止，不得执行。** 本包授权的最终真实 smoke 已产生
> `9acab5d876b38d64a9aeab7aca3474be2676ce38` evidence：两个固定公开视频各完成一次元数据与字幕目录读取，
> 但均在正文读取前以 `INVALID_RESPONSE` 失败；没有认证、媒体、用户数据或重试。此 evidence 是 `FAIL`，不合并、
> 不得写成通过，也不改变 TASK-014 `IN_PROGRESS / No-Go`。后续仅授权只读
> `PREFLIGHT-TASK-014-PHASE-B1-PUBLIC-SUBTITLE-ADAPTER-COMPATIBILITY-SCOUT.md`；不得再次执行 smoke。

你是 TASK-014 Phase B-1 的唯一 Codex non-existing Temporary-root Smoke Retry Executor。此包只授权一次以正确的、不存在的 smoke-root 子路径执行的受限 smoke；它本身不执行任何命令。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/operations.md`、`365c8fca966a3fb7608f41b2d3ac530504193c7b` blocker evidence 与本包。若任一边界冲突，停止并报告。

## 固定对象与状态

```text
Task: TASK-014 Phase B-1 — final non-existing temporary-root smoke retry
Role: non-existing Temporary-root Smoke Retry Executor
Agent: Codex
Control-plane baseline: main@f5bcac5e9fa7dac7bdac1e859873d369adbb7880
Worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry
Branch: codex/task-014-phase-b1-console-entry-retry
Source HEAD / blocker evidence: 365c8fca966a3fb7608f41b2d3ac530504193c7b
Required sole parent: 3c3dd4ac45cb6ea66bc927a1542c4612554a56fa
Only executable: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel
Reuse decision: DIRECT — 已核验项目虚拟环境 console entry、smoke-public-subtitles 与 yt-dlp Adapter；不新增或复制第三方代码
```

- source HEAD 必须精确为 `365c8fca966a3fb7608f41b2d3ac530504193c7b`，唯一父提交必须精确为
  `3c3dd4ac45cb6ea66bc927a1542c4612554a56fa`，且工作树干净；这是唯一可执行 source。
- `365c8fc…` 只记录 smoke 入口的 fail-closed 根目录契约：上次传入的是已存在的空目录，而入口要求一个已存在
  临时父目录内**尚不存在**的 `smoke-root` 子路径。因此 runner 未初始化，两个固定 ID 均未触达公开视频。它不是 B-1
  smoke 成功、发布批准或任何 Go 结论。
- TASK-014 始终为 `IN_PROGRESS / No-Go`。本包不授权发布、法律结论、风险接受或最终 Go/No-Go。

## 唯一允许的准备与执行

1. 不得运行 `uv`、安装、下载、依赖解析、锁文件更新、网络预配、PATH 修改、venv 激活、`python -m`、裸
   `youtube-intel` 或任何替代入口。只可使用已核验的唯一绝对 launcher。
2. 创建一个新的临时**父目录**；在其内指定 `smoke-root` 子路径。执行前静态确认父目录存在，且该
   `smoke-root` 子路径尚不存在（包括文件、目录或符号链接均不存在）。不得把父目录本身、既有空目录或任意已存在
   路径传给 `--temporary-root`。
3. 只有第 2 步通过后，才可仅调用以下命令一次，并保留其数值退出码：

```text
/Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel smoke-public-subtitles \
  --temporary-root ABSOLUTE_NEW_PARENT_DIR/smoke-root \
  --video-id=--khbXchTeE \
  --video-id=JTxsNm9IdYU
```

- 固定且仅有两个 ID：`--khbXchTeE`、`JTxsNm9IdYU`；每个目标最多一次。不得增加、替换、重新排序目标，或调用
  `retry`、循环、并发扇出、第二次 smoke、替代 launcher 或替换 temporary-root。
- 其他已批准资源边界不变：仅允许元数据、字幕目录和一份选中字幕正文的内存读取；必须使用新的临时 SQLite、DATA、
  测试 Vault 与日志根；不得提交临时绝对路径、字幕正文、元数据 payload、临时 URL、凭据或用户内容。
- 严禁登录、Cookie、浏览器 profile、API key、`.env`、Keychain、媒体下载、ffmpeg、Whisper、模型、Ollama、OpenAI、
  付费调用、真实 Vault、用户笔记、用户数据、launchd 或任何其他产品命令。任何认证、速率限制、付费、非公开内容、
  越界配置或资源调用立即停止该目标，不规避、不重试。

## 唯一允许写入与交付

只可修改以下三条 source 路径：

1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`
2. `docs/RELEASE_CHECKLIST.md`（仅追加本次 B-1 记录）
3. `handoffs/TASK-014.md`

必须如实记录：父目录/子路径存在性核验（不泄露绝对路径）、数值退出码、runner 初始化、每个固定 ID 是否实际被调用、
元数据/目录/正文次数、停止条件和未执行项。成功只表示 **B-1 smoke 通过**；不代表发行批准、mutagen GPL 结论、BPE
文件归属/NOTICE 结论、真实 Vault 边界关闭、at-most-once best-effort 风险签署或最终 PO/TL/QA Go-No-Go。

完成时仅在 source 创建一个只含上述三路径的提交，报告 SHA，交由全新独立 Reviewer。不得自行 `ACCEPTED`/`DONE`、
合并、push、清理 source 或启动 Reviewer。
