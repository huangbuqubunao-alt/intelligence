# TASK-014B10 — 安全内容可用性诊断独立 Reviewer

你是 TASK-014B10 的全新独立 Codex Reviewer。只审查固定 source 的离线实现；不得依赖 Implementer 自报结论，不得修复、重构、
重新设计、修改产品代码或启动真实资源。本包只创建授权，不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B10 — safe content availability diagnostic
Role: Independent Reviewer
Control-plane baseline: main@1bf30c89c23316b89d5fc2ad6c4af885db493669
Execution main: dynamic clean main at the single-parent Reviewer authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic
Reviewed source branch: codex/task-014b10-safe-content-availability-diagnostic
Reviewed implementation HEAD: 3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
Required sole parent of implementation: 6fd7b5cc3fae6466fb6181151513f4854d196683
Review range: 6fd7b5cc3fae6466fb6181151513f4854d196683...3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
Read-only B9 failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must remain unmerged; do not modify, clean, rewrite, or call passing)
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-015--ADR-020 diagnostics, existing JsonlLogger safe_message, and offline integration tests; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、唯一父链、双方洁净度、B9 evidence 未合并状态、完整五路径范围及
  `git diff --check`；任一不符立即停止，不写 evidence。
- 完整产品 Diff 必须严格且仅为：`src/youtube_intel/providers/subtitles.py`、`src/youtube_intel/public_subtitle_smoke.py`、
  `tests/integration/test_subtitle_provider.py`、`tests/integration/test_public_subtitle_smoke.py`、`handoffs/TASK-014.md`。
  必须确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、默认 CLI、`logging.py`/日志 schema、认证或控制面产品改动。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，且只能追加独立审查 evidence；evidence commit 必须以
  `3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20` 为唯一父提交。不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。

## 必须独立审查

1. **正确性**：确认词表严格且仅为 `content_availability_video_unavailable`、
   `content_availability_environment_restricted`、`content_availability_extractor_compatibility`、
   `content_availability_unknown`；独立覆盖各固定分类、非法/缺失内部状态和 unknown 回退。code 只可在受限 directory-only、
   最终 `CONTENT_UNAVAILABLE`、enumerate=`1`、read=`0` 全部成立时进入既有安全 stdout 摘要与 JSONL `safe_message`；成功、
   default、其他错误码、正文读取或任一条件缺失时必须省略。
2. **产品语义**：前三类只能表达用于选择后续动作的受限诊断分类，帮助判断应检查候选视频、访问环境或提取器兼容性；不得把
   本地错误映射的推断写成真实原因或已确认事实。任何部分、冲突、不可靠或不安全的判断必须归为 unknown。
3. **回归**：确认默认 smoke 仍恰有一次正文读取，directory-only 仍为 `1/1/0`；退出码、调用计数、无重试、临时根、ID 上限、
   零业务记录、B4--B8 固定分类及所有 fail-closed 边界不变。
4. **隐私与安全**：独立扫描 stdout、stderr、JSONL、测试及 handoff；B10 新增/变更材料禁止 URL、标题、语言、轨道、响应字段名/
   字段值、异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据。ADR-019 既有受限合成键名例外只能保持原边界，
   不得被 B10 扩大；不得新增、恢复、内嵌、重命名或移动含真实/结构化目录材料的 fixture。
5. **架构**：确认只复用既有安全摘要与 JSONL `safe_message`，没有新增 JSONL/schema 字段、Provider metadata、依赖、锁、
   Schema/migration、配置、默认 CLI、`logging.py`/日志 schema 或认证边界；字幕目录/正文解析接受面和兼容规则未扩大。

## 独立门禁与停止规则

- 不得复用 Implementer 的 PASS 自报。仅允许先运行一次 `uv sync --locked --offline`；缓存缺失、锁变化、下载/网络迹象或失败立即停止，
  不得重试、修复或替换环境。同步成功且绝对 `.venv` 工具存在时，按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check 6fd7b5cc3fae6466fb6181151513f4854d196683...3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
```

- 另做五路径范围、禁止路径和 stdout/stderr/JSONL/test/handoff 全输出面泄漏扫描。不得运行 full pytest、build、真实 smoke、其他 CLI
  子命令、网络或任何真实资源。
- 以 P0、P1、P2、P3 记录每项发现并给出 `APPROVE` 或 `REJECT`。一旦确认 P0 或 P1，立即停止后续产品命令，不修复、不重试；只可把
  已取得证据、未运行项和 `REJECT` 追加到 source handoff，并创建唯一的 handoff-only commit。P2/P3 仍须如实记录并完成其余门禁，
  除非继续执行本身不安全。
- 禁止真实 YouTube、网络、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、
  push、合并、source 清理和 `.codebase-memory` 工件。TASK-014B10 保持 `IN_REVIEW`，TASK-014 保持 `IN_PROGRESS / No-Go`；
  离线审查不构成真实服务验证、兼容性修复授权、发行批准或最终 Go。
