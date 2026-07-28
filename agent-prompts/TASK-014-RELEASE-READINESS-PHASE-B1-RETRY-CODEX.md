# TASK-014 Phase B-1 — 受控环境预配与单次 smoke Retry

> **已完成并废止，不得执行。** 本包授权的预配与 PATH 上的首次 smoke 已产生
> `3c3dd4ac45cb6ea66bc927a1542c4612554a56fa` blocker evidence：shell `PATH` 未包含项目 `.venv/bin`，产品入口和
> YouTube 均未触达。这不是 B2 console entry 缺失。后续唯一可能的 B-1 尝试仅由
> `TASK-014-RELEASE-READINESS-PHASE-B1-VENV-CONSOLE-PATH-RETRY-CODEX.md` 授权；不得再次运行本包的 `uv`、
> PATH 上的入口或任何其他替代路径。

你是 TASK-014 Phase B-1 的唯一 Codex Smoke Retry Executor。此包只授权一次受控环境预配和一次受限 smoke 重试；它本身不执行任何命令。开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、`docs/PRODUCT_DECISIONS.md`、全部 Accepted ADR、`tasks/TASK-014-release-readiness.md`、`tasks/README.md`、`docs/operations.md`、历史阻断 evidence 与本包。若任一边界冲突，停止并报告。

## 固定对象与状态

```text
Task: TASK-014 Phase B-1 — controlled environment pre-provisioning and one smoke retry
Role: Smoke Retry Executor
Agent: Codex
Control-plane baseline: main@49869c6ff2bbc53673c6a35071c5f1407c269cba
Worktree: /Users/hua/Documents/yia-worktrees/task-014-phase-b1-console-entry-retry
Branch: codex/task-014-phase-b1-console-entry-retry
Source HEAD: 49869c6ff2bbc53673c6a35071c5f1407c269cba
Reuse decision: DIRECT — 已整合的 smoke-public-subtitles、锁定依赖与 yt-dlp Adapter；不新增或复制第三方代码
```

- source HEAD 必须先精确为 `49869c6ff2bbc53673c6a35071c5f1407c269cba`，且工作树干净；这是唯一可执行
  source。旧 final worktree 及其 `5698802ba13b9c953eb6ae41d7f827d38654c7c8` evidence 不得访问、修改、
  合并、清理或复用为执行 source。该旧 evidence 仅记录 `fsspec==2026.6.0` 缓存缺失导致的环境阻断：两个公开
  YouTube 目标均未调用，**不是 smoke 通过结果**，不得改写为通过或发布批准。
- TASK-014 始终为 `IN_PROGRESS / No-Go`。本包不授权发布、法律结论、风险接受或最终 Go/No-Go。

## 唯一允许的环境动作

只允许按以下顺序各执行一次：

1. `uv lock --check`（预配前）；若失败立即停止，不改 `pyproject.toml` 或 `uv.lock`。
2. `uv sync --locked`；若本机缓存缺失，仅允许从包索引下载 `uv.lock` 已锁定的既有包。不得解析、升级、替换、添加或删除依赖。
3. `uv lock --check`（预配后）；若失败立即停止，不进行 smoke。

除第 2 步受限的锁定包下载外，不得联网。不得修改 `pyproject.toml`、`uv.lock`、依赖版本、源码、测试、配置、Schema/migration、任务状态或项目 LICENSE。若任一步失败，记录并停止；不得再次运行 `uv sync`、安装替代包或扩大网络访问。

## 单次 smoke 重试边界

只有三步环境动作全部通过后，才可调用一次已整合入口：

```text
youtube-intel smoke-public-subtitles \
  --temporary-root ABSOLUTE_NEW_EMPTY_DIR \
  --video-id=--khbXchTeE \
  --video-id=JTxsNm9IdYU
```

- 固定且仅有两个 ID：`--khbXchTeE`、`JTxsNm9IdYU`；每个目标最多一次。不得增加、替换、重新排序目标，或调用
  `retry`、循环、并发扇出或第二次 smoke。
- 仅允许元数据、字幕目录和一份选中字幕正文的内存读取。必须使用新的临时 SQLite、DATA、测试 Vault 与日志根；不得提交
  临时绝对路径、字幕正文、元数据 payload、临时 URL、凭据或用户内容。
- 严禁登录、Cookie、浏览器 profile、API key、`.env`、Keychain、媒体下载、ffmpeg、Whisper、模型、Ollama、OpenAI、
  付费调用、真实 Vault、用户笔记、用户数据、launchd 或任何其他产品命令。任何认证、速率限制、付费、非公开内容、
  越界配置或资源调用立即停止该目标，不规避、不重试。

## 唯一允许写入与交付

只可修改以下三条 source 路径：

1. `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`
2. `docs/RELEASE_CHECKLIST.md`（仅追加本次 B-1 记录）
3. `handoffs/TASK-014.md`

必须在证据中区分：预配是否通过、每个固定 ID 是否实际被调用、元数据/目录/正文次数、停止条件和未执行项。成功只表示
**B-1 smoke 通过**；不代表发行批准、mutagen GPL 结论、BPE 文件归属/NOTICE 结论、真实 Vault 边界关闭、
at-most-once best-effort 风险签署或最终 PO/TL/QA Go-No-Go。

完成时仅在 source 创建一个只含上述三路径的提交，报告 SHA，交由全新独立 Reviewer。不得自行 `ACCEPTED`/`DONE`、
合并、push、清理 source 或启动 Reviewer。
