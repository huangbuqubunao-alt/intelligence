# TASK-014B11 — 安全字幕目录契约状态诊断 Correction 1 Implementer

你是 TASK-014B11 的原 Codex Implementer。只在固定 source 谱系离线关闭首轮 Reviewer 的唯一
P1：用真实 `YtDlpSubtitleAdapter.enumerate_tracks()` 到真实 `PublicSubtitleSmoke` 的生产传递链
证明 ADR-021 六字段矩阵；不得依赖私有 helper/Fake 直接构造最终错误或矩阵。本包只创建授权，
不启动 Implementer。

## 固定分配

```text
Task: TASK-014B11 — safe subtitle directory contract-state diagnostics, Correction 1
Role: original Codex Implementer
Control-plane baseline: main@63911ff6c478bf89cb724474c3ab34e518652440
Execution main: dynamic clean single-parent main commit containing this prompt and synchronized TASK-014B11/TASK-014/status/index documents; its sole parent must be 63911ff6c478bf89cb724474c3ab34e518652440
Worktree: /Users/developer/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Branch: codex/task-014b11-safe-directory-contract-diagnostics
Original implementation: f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
Original implementation base: 80aff83fc033a8bd2950108cad2e34feea5d396f
First Reviewer evidence / required source HEAD: 4aebc01360fa9684fe6b052f266a00ecc2de57dc
Required sole parent of first Correction commit: 4aebc01360fa9684fe6b052f266a00ecc2de57dc
Maximum allowed Correction scope: src/youtube_intel/providers/subtitles.py; src/youtube_intel/public_subtitle_smoke.py; tests/integration/test_subtitle_provider.py; tests/integration/test_public_subtitle_smoke.py; handoffs/TASK-014.md
Reuse decision: DIRECT — existing locked yt-dlp Adapter, B4 directory-only, B5 safe stdout/JSONL schema, ADR-017--ADR-021 fixed diagnostics, and offline integration infrastructure; no dependency or third-party change
```

## 开始前 Git-only 门禁

1. 完整阅读仓库协作资料、ADR-017--ADR-021、TASK-014、TASK-014B6/B7/B8/B10/B11、
   Implementer handoff、首轮 Reviewer evidence 与本包；如有冲突立即停止并报告
   `DECISION NEEDED`。
2. 核验 dynamic main 是包含本包的干净单父控制面提交，唯一父为固定 control-plane baseline；
   核验 source worktree/branch/HEAD 精确匹配 Reviewer evidence，暂存区、tracked/untracked 均干净。
3. 核验 implementation 的唯一父为固定 implementation base；Reviewer evidence 的唯一父为
   implementation，且 evidence commit 只追加 `handoffs/TASK-014.md`。完整 implementation Diff
   精确为原五路径并通过 `git diff --check`。
4. 核验只读真实 evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` 与 B9 evidence
   `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 均未进入 main/source；不得修改、清理、合并、
   重写或称为通过。

任一身份、父链、洁净度、范围或 evidence 门禁不符立即停止；不得修改历史或 source 来通过门禁。

## 首轮 REJECT 与唯一 P1

首轮 Reviewer Verdict=`REJECT`、P0=`0`、P1=`1`、P2=`0`、P3=`0`。现有 Provider tests
直接检查私有枚举与 tuple helper；safe smoke test 的 Fake 又直接调用私有 tuple/error helper 构造
最终诊断错误和矩阵。它们未驱动生产 Adapter 的目录校验、状态构造、`TranscriptError` 映射及真实
smoke 输出，因此不能捕获字段错配、manual/automatic 互换或 `unknown`/`not_evaluated` 的生产映射错误。

Reviewer 按 P1 立即停止规则未运行 uv/sync、focused tests、mypy、Ruff、CLI help 或运行时
stdout/stderr/JSONL 扫描；不得把这些未运行项或 Implementer 原 `147 passed` 自报当作独立通过。

## 测试优先的生产传递链

1. **先补生产路径测试**：在修改任何生产代码前，新增最小离线测试并调用真实
   `YtDlpSubtitleAdapter.enumerate_tracks()`。只允许在最外层 downloader/transport factory 使用
   Fake 或 monkeypatch；禁止网络。必须由真实 Adapter 执行目录校验、ADR-017--ADR-021 状态构造和
   `TranscriptError` 映射。
2. **再走真实 smoke**：把上述真实 Adapter 通过既有 factory 注入真实 `PublicSubtitleSmoke` 路径，
   验证 directory-only stdout 与 JSONL 中完整六字段矩阵。Fake 不得直接创建最终私有诊断错误、
   调用私有 matrix/error helper、设置最终私有状态 tuple，或直接返回最终矩阵。
3. **测试先于修复**：新增生产链测试后、修改生产 source 前，先运行新测试。若它在现有生产代码上
   失败，记录该 RED、失败断言与所穿过的生产边界，再做满足 RED 的最小产品修复；若它直接通过，
   如实记录“生产代码正确、缺口仅为覆盖”，只补测试与 handoff，不得为了制造 RED 修改产品代码。
   测试替身自身的构造/monkeypatch 错误不算产品 RED；同一 harness 失败重复两次必须停止并报告。
4. **最低覆盖矩阵**：至少覆盖：

   - 一个字段错配由真实 Adapter 校验生成六字段矩阵并传至真实 smoke 的完整路径；
   - `unknown` 与 `not_evaluated` 的生产路径，且二者不得互换或由测试预先指定；
   - directory-only、`INVALID_RESPONSE`、精确 `1/1/0`、mapping origin 任一门禁不满足时矩阵完全省略；
   - stdout/JSONL 六字段名、固定顺序、封闭枚举，符合门禁时每目标至多一个独立 contract-state
     事件、不符合时为零，以及 stdout/stderr/JSONL 无泄漏。

## 冻结产品与隐私边界

- 若 RED 证明生产传递缺陷，只可做关闭该缺陷的最小修改；不得扩大 Adapter 接受面、接受此前拒绝
  的目录形状、增加兼容规则或基于异常文本、响应值、动态类型名/字段猜测状态。
- 保持 ADR-021 六字段名、顺序、枚举和 `unknown`/`not_evaluated` 语义；输出仍只允许在
  directory-only + `INVALID_RESPONSE` + metadata/enumerate/read=`1/1/0` + B7 mapping + 零正文
  全部成立时出现。独立安全事件必须继续复用既有 JSONL schema 且固定有界。
- 不改变 B4--B10 词表、门禁或含义，不改变默认 smoke 一次正文读取、directory-only 零正文、退出码、
  计数、无重试、临时根、ID 上限、零业务记录、CLI 或 fail-closed 行为。
- 只使用 ADR-021 允许的无值、非用户合成替身。不得新增或保存真实 URL、标题、语言、轨道、响应
  内容、异常原文、路径、Cookie、token、payload、用户数据或凭据；不得新增、恢复、读取、修改、
  移动或内嵌真实/敏感 fixture。
- 不新增依赖，不修改 `uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`/日志 schema、
  ADR、任务状态、Reviewer prompt、真实 evidence 或其他控制面。

## 允许范围与离线验证

实际 Correction Diff 必须是最大五路径范围的最小子集，不要求每个允许文件变化。若生产代码正确，
预期只修改必要 integration test 与 `handoffs/TASK-014.md`；不得为凑范围修改 source。完整 B11 Diff
相对 original implementation base 仍必须位于原五路径内。

只可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁变化、下载/网络迹象或失败立即停止，不得修复环境、重试或换命令。同步成功且固定
source 的 `.venv` 工具存在时，先按上述测试优先规则运行新增生产链测试；如产生有效产品 RED，
最小修复后只重跑同一节点一次确认 GREEN。随后按序各运行一次：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check 4aebc01360fa9684fe6b052f266a00ecc2de57dc...HEAD
git diff --check 80aff83fc033a8bd2950108cad2e34feea5d396f...HEAD
```

- 独立检查 Correction/完整 B11 路径、禁止范围、锁文件不变、LF/EOF 与 SHA-256；扫描 stdout、
  stderr、JSONL、test、handoff 与 fixture 输出面。不得运行 full pytest、build、其他 CLI 子命令、
  网络、真实 YouTube/smoke、认证/Cookie/netrc、媒体/ffmpeg、模型/Ollama/OpenAI、云端、真实 Vault、
  用户数据或其他真实资源。
- 任一门禁失败立即停止，不得修复产品、重试或换命令；测试先行阶段仅允许上文明确授权的单次最小
  GREEN 修复。禁止 push、merge、source 清理和 `.codebase-memory` 工件。

## 交付

- 只向 source `handoffs/TASK-014.md` 追加 Correction 1 evidence，记录生产链测试的先后顺序、
  是否产生有效 RED、RED/GREEN 或 coverage-only 结果、实际命令、范围、泄漏扫描、跳过项与剩余风险。
- 首个且本轮唯一 Correction commit 的唯一父提交必须为
  `4aebc01360fa9684fe6b052f266a00ecc2de57dc`。提交前后核验精确暂存范围、SHA-256、LF/EOF、
  `git diff --check`、父链、HEAD 与 source 洁净度。
- 不得启动 Reviewer、修改任务状态、预写 Reviewer verdict、合并、push 或清理 source。
  TASK-014B11 保持 `IN_PROGRESS / Codex`，TASK-014 保持 `IN_PROGRESS / No-Go`；Correction 不构成
  真实 smoke、兼容性结论、正文可读、发行批准或最终 Go。
