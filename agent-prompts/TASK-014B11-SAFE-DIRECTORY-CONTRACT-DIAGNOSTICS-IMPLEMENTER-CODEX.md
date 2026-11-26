# TASK-014B11 — 安全字幕目录契约状态诊断 Implementer

你是 TASK-014B11 的 Codex Implementer。只在固定 source worktree 离线实现 ADR-021；不得
修复真实兼容性、扩大字幕解析接受面、修改控制面或访问真实资源。本包只建立动态授权，
不启动 Implementer。

## 固定分配

```text
Task: TASK-014B11 — safe subtitle directory contract-state diagnostics
Role: Implementer
Agent: Codex
Implementation baseline: main@80aff83fc033a8bd2950108cad2e34feea5d396f
Control-plane authorization: dynamic clean single-parent main commit containing ADR-021, TASK-014B11, this prompt, and the synchronized status/index documents; its sole parent must be 80aff83fc033a8bd2950108cad2e34feea5d396f
Worktree: /Users/developer/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Branch: codex/task-014b11-safe-directory-contract-diagnostics
Required source HEAD: 80aff83fc033a8bd2950108cad2e34feea5d396f
Required sole parent of first and only product commit: 80aff83fc033a8bd2950108cad2e34feea5d396f
Read-only real evidence: 51d9749943270cb75c2b166e77bce0a5f663d92c
Required evidence parent: f00aa9cffa25dcb9b7165edf21a4d476263c1dc5
Allowed scope: src/youtube_intel/providers/subtitles.py; src/youtube_intel/public_subtitle_smoke.py; tests/integration/test_subtitle_provider.py; tests/integration/test_public_subtitle_smoke.py; handoffs/TASK-014.md
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017--ADR-020 diagnostics, existing JSONL safe_message, and offline integration tests; no dependency or third-party change
```

## 开始前 Git-only 门禁

1. 完整阅读仓库协作资料、main 上的 ADR-017--ADR-021、TASK-014、TASK-014B6/B7/B8/B10/B11
   与本正式包；如冲突立即停止并报告 `DECISION NEEDED`。
2. 核验 main 位于包含本包的动态单父控制面提交，且其唯一父提交为固定实施基线；main 干净。
3. 核验 source branch/worktree 精确匹配，HEAD 为固定实施基线，暂存区与 tracked/untracked
   worktree 均干净。控制面文档不得复制、暂存或提交到 source。
4. 核验 `51d974…` 的唯一父提交为 `f00aa9c…`，且只修改以下三份 evidence 文档：

   - `docs/RELEASE_CHECKLIST.md`
   - `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-DIRECTORY-ONLY-B10-CLASSIFIED-PUBLIC-YOUTUBE.md`
   - `handoffs/TASK-014.md`

5. 核验 `51d974…` 不是 main 或 source 的祖先。它只能作为失败输入引用；不得修改、合并、
   cherry-pick、rebase、清理、重跑或改写为成功。

任一 Git-only 门禁不符立即停止；不得为通过门禁修改历史或 source。

## 固定设计契约

矩阵字段必须完整且严格按以下顺序；值域不得增删：

| 顺序 | 字段 | 固定允许值 |
|---:|---|---|
| 1 | `video_identity_shape` | `missing` / `string` / `other` / `unknown` |
| 2 | `manual_directory_shape` | `missing` / `mapping` / `other` / `unknown` |
| 3 | `automatic_directory_shape` | `missing` / `mapping` / `other` / `unknown` |
| 4 | `caption_bucket_shape` | `not_evaluated` / `absent` / `sequence` / `other` / `unknown` |
| 5 | `track_entry_shape` | `not_evaluated` / `absent` / `mapping` / `other` / `unknown` |
| 6 | `required_members_shape` | `not_evaluated` / `complete` / `missing` / `wrong_type` / `unknown` |

- `not_evaluated` 只用于前置层未安全到达；`unknown` 只用于已到达但无法由可信无值内部状态
  安全分类。不得将推断写成事实。
- 字段名是项目内契约概念，不是外部 response key。只诊断项目已知概念，不枚举、复制、
  排序、计数、哈希或输出任意外部 key/value。
- Adapter 只可从既有校验分支产生封闭、无值内部状态。禁止基于异常文本、URL、响应文本、
  动态类型名、外部字段名/值或其他内容猜测状态。

## 严格输出门禁

完整矩阵只可在下列条件全部成立时，经既有 B5 stdout 摘要和既有 JSONL `safe_message`
附加：directory-only；最终 `INVALID_RESPONSE`；metadata=`1` / enumerate=`1` / read=`0`；
`directory_origin_mapping`；未读取字幕正文。任一条件缺失必须省略整个矩阵。

- 六字段固定顺序和固定值域必须在 stdout 与 JSONL `safe_message` 一致。
- 不新增 JSONL schema 字段、`logging.py`、Provider metadata、CLI 参数、配置、证据模型或
  持久化状态。
- 不改变 B6/B7/B8/B10 的词表、门禁或含义；不得用 B11 替换、细分或反推既有诊断。
- 不改变 Adapter 接受范围、默认 smoke、退出码、metadata/enumerate/read 计数、默认一次正文
  读取、directory-only 零正文、无重试、临时根、ID 上限、零业务记录、认证或 fail-closed。
- B11 新增矩阵绝不输出或持久化视频 ID 值、外部响应键名、URL、标题、语言代码、轨道名、
  字段值、数量、顺序、异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据；
  既有 B5 安全目标标识与其他既有安全摘要语义保持不变，不属于 B11 矩阵。

## 测试优先与最小实现

1. 先检查既有 Adapter 校验和 safe smoke 传递边界；在改生产代码前，用无值内部状态或仅含
   ADR-021 项目概念的合成替身新增失败测试。
2. 测试必须覆盖每个固定状态、`unknown`/`not_evaluated`、六字段顺序、完整严格门禁、省略
   规则和 Adapter 到 stdout/JSONL 的生产传递；不得只直接调用私有格式化函数。
3. 做满足失败测试的最小实现。不得新增或恢复 fixture，不得扩大解析接受面或顺手修复真实
   yt-dlp 兼容性。
4. 回归默认 smoke 一次正文读取、directory-only `1/1/0`、退出码、无重试、B4--B10、CLI
   与全部 fail-closed 边界。

实际 Diff 必须是允许五路径的最小子集，不要求所有允许文件都有变化。不得修改 fixture、依赖、
`uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`/日志 schema、ADR、任务卡、
prompt、项目状态或 evidence 文档。

## 唯一离线命令序列

只可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、下载/网络迹象或任何失败立即停止；不得修复、重试或换命令。只有已有
离线 `.venv` 可用时，才可按序各运行一次：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

除 CLI help 外禁止其他产品命令。不得运行 full pytest、build、网络、YouTube、真实 smoke、
认证/Cookie/netrc、媒体/ffmpeg、模型/Ollama/OpenAI、云端、真实 Vault、用户数据或其他真实资源。

## 泄漏、范围与交付门禁

- 扫描 stdout、stderr、JSONL `safe_message`、测试新增行和 handoff 新增行，确认仅含固定无值
  词表及其他既有授权安全材料；不得保留原始运行输出或任何禁止材料。
- 核验完整 Diff 为允许五路径的最小子集，无 fixture、依赖、锁、Schema/config/auth、默认 CLI、
  日志 schema、控制面或 evidence 变化；运行 `git diff --check`，核验 SHA-256、LF/EOF 和精确暂存范围。
- 仅向 source `handoffs/TASK-014.md` 追加 Implementer evidence，记录实际命令、结果、跳过项、
  Reuse=`DIRECT` 和剩余风险。不得声称真实服务、普遍兼容、正文可读或发布通过。
- 创建一个且仅一个 Implementer commit，其唯一父提交必须为固定实施基线。提交后核验父链、
  精确范围、HEAD、暂存区和 worktree 洁净度并报告 SHA。

不得修改 TASK-014B11/TASK-014 状态、启动 Reviewer、合并、push 或清理 source。TASK-014B11
保持 `IN_PROGRESS / Codex`，TASK-014 保持 `IN_PROGRESS / No-Go`。
