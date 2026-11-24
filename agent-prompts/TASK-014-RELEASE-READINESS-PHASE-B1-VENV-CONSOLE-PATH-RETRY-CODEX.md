# TASK-014 Phase B-1 — venv console-path 最后一次 smoke Retry

> **已完成并废止，不得执行。** 本包授权的绝对 venv console-path 调用已产生
> `365c8fca966a3fb7608f41b2d3ac530504193c7b` blocker evidence：上次把已存在的空目录传给
> `--temporary-root`，而 smoke 入口 fail-closed 地要求“已存在临时父目录内、尚不存在的 smoke-root 子路径”。runner
> 未初始化，YouTube 未触达。后续唯一可能的 B-1 尝试仅由
> `TASK-014-RELEASE-READINESS-PHASE-B1-TEMPORARY-ROOT-RETRY-CODEX.md` 授权；不得再次运行本包。

你是 TASK-014 Phase B-1 的唯一 Codex venv Console-path Smoke Retry Executor。此包只授权一次以项目虚拟环境绝对 console 路径执行的受限 smoke；它本身不执行任何命令。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/operations.md`、`3c3dd4ac45cb6ea66bc927a1542c4612554a56fa` blocker evidence 与本包。若任一边界冲突，停止并报告。

## 固定对象与状态

```text
Task: TASK-014 Phase B-1 — final venv console-path smoke retry
Role: venv Console-path Smoke Retry Executor
Agent: Codex
Control-plane baseline: main@0b45d8e9fcf49e6c450279c00b787069fa665520
Worktree: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry
Branch: codex/task-014-phase-b1-console-entry-retry
Source HEAD / blocker evidence: 3c3dd4ac45cb6ea66bc927a1542c4612554a56fa
Required sole parent: 49869c6ff2bbc53673c6a35071c5f1407c269cba
Only executable: /Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel
Reuse decision: DIRECT — 已锁定项目虚拟环境、已整合的 console entry、smoke-public-subtitles 与 yt-dlp Adapter；不新增或复制第三方代码
```

- source HEAD 必须精确为 `3c3dd4ac45cb6ea66bc927a1542c4612554a56fa`，唯一父提交必须精确为
  `49869c6ff2bbc53673c6a35071c5f1407c269cba`，且工作树干净；这是唯一可执行 source。
- `3c3dd4a…` 只记录 shell `PATH` 未包含项目 `.venv/bin`：先前一次命令以 exit `127` 在产品入口前停止，两个
  固定 ID 均未触达 YouTube。它**不是** B2 console entry 缺失，也不是 B-1 smoke 通过、发布批准或任何 Go 结论。
- TASK-014 始终为 `IN_PROGRESS / No-Go`。本包不授权发布、法律结论、风险接受或最终 Go/No-Go。

## 唯一允许的核验与执行

1. 只读核验唯一绝对路径
   `/Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel` 存在且可执行，
   并通过静态读取该 launcher 的内容确认其映射既有项目 `youtube_intel.cli:main` 入口。不得调用 `--help`、
   `python -m`、裸 `youtube-intel` 或任何其他产品命令作为核验替代。
2. 不得运行 `uv sync`、任何其他 `uv` 命令、安装、下载、依赖解析、锁文件更新或网络预配。
3. 只有第 1 步通过后，才可仅调用以下命令一次：

```text
/Users/developer/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry/.venv/bin/youtube-intel smoke-public-subtitles \
  --temporary-root ABSOLUTE_NEW_EMPTY_DIR \
  --video-id=--khbXchTeE \
  --video-id=JTxsNm9IdYU
```

- 固定且仅有两个 ID：`--khbXchTeE`、`JTxsNm9IdYU`；每个目标最多一次。不得增加、替换、重新排序目标，修改 `PATH`、
  激活 venv、使用符号链接或任何替代入口，或调用 `retry`、循环、并发扇出、第二次 smoke。
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

必须在证据中区分：launcher 静态核验、每个固定 ID 是否实际被调用、元数据/目录/正文次数、停止条件和未执行项。成功只表示
**B-1 smoke 通过**；不代表发行批准、mutagen GPL 结论、BPE 文件归属/NOTICE 结论、真实 Vault 边界关闭、
at-most-once best-effort 风险签署或最终 PO/TL/QA Go-No-Go。

完成时仅在 source 创建一个只含上述三路径的提交，报告 SHA，交由全新独立 Reviewer。不得自行 `ACCEPTED`/`DONE`、
合并、push、清理 source 或启动 Reviewer。
