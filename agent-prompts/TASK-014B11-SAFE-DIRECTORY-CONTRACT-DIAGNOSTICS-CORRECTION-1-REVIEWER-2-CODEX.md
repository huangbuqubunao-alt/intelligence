# TASK-014B11 — 安全字幕目录契约状态诊断 Correction 1 独立 Reviewer 2

你是 TASK-014B11 的全新独立 Codex Reviewer 2。只审查固定 source 上 coverage-only Correction 1
与完整 B11 Diff；不得依赖 Implementer 自报，不得修复、重构、修改测试/产品或访问真实资源。
本包只创建授权，不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B11 — safe subtitle directory contract-state diagnostics, Correction 1 review
Role: Independent Reviewer 2
Control-plane baseline: main@f902aec309927751d173145e46a617a467745e85
Execution main: dynamic clean single-parent main commit containing this prompt and synchronized TASK-014B11/TASK-014/status/index documents; its sole parent must be f902aec309927751d173145e46a617a467745e85
Reviewed source worktree: /Users/hua/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Reviewed source branch: codex/task-014b11-safe-directory-contract-diagnostics
Reviewed Correction HEAD: ed250baf752182adbc4d98f5271d34995865d192
Required sole parent of Correction: 4aebc01360fa9684fe6b052f266a00ecc2de57dc
First Reviewer evidence: 4aebc01360fa9684fe6b052f266a00ecc2de57dc (sole parent f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50; handoff-only; REJECT, P1=1)
Original implementation: f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
Original implementation base: 80aff83fc033a8bd2950108cad2e34feea5d396f
Correction review range: 4aebc01360fa9684fe6b052f266a00ecc2de57dc...ed250baf752182adbc4d98f5271d34995865d192
Complete B11 review range: 80aff83fc033a8bd2950108cad2e34feea5d396f...ed250baf752182adbc4d98f5271d34995865d192
Read-only real evidence: 51d9749943270cb75c2b166e77bce0a5f663d92c (must remain unmerged)
Read-only B9 evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must remain unmerged)
Reuse decision: DIRECT — existing locked yt-dlp Adapter, B4 directory-only, B5 safe stdout/JSONL schema, ADR-017--ADR-021 fixed diagnostics, and offline integration infrastructure; no dependency or third-party change
```

## 开始前 Git-only 门禁

1. 完整阅读仓库协作资料、ADR-017--ADR-021、TASK-014、TASK-014B6/B7/B8/B10/B11、
   Implementer/首轮 Reviewer/Correction 1 handoff 与本包；冲突时立即停止并报告
   `DECISION NEEDED`。
2. 核验 dynamic main 是包含本包的干净单父控制面提交，唯一父为固定 control-plane baseline；
   核验 source worktree/branch/HEAD 精确匹配 Correction，暂存区、tracked/untracked 均干净。
3. 核验 implementation→First Reviewer evidence→Correction 的逐提交唯一父链；First Reviewer evidence
   必须 handoff-only，Correction Diff 必须精确且仅为两份 integration tests 与
   `handoffs/TASK-014.md` 三路径，完整 B11 Diff 必须精确且仅为 Adapter、safe smoke、两份 tests
   与 handoff 五路径。两组 `git diff --check` 必须通过。
4. 以 Git blob/diff 确认 `src/youtube_intel/providers/subtitles.py` 与
   `src/youtube_intel/public_subtitle_smoke.py` 相对首轮 implementation 在 Correction 中完全未变；
   确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`/
   日志 schema 或控制面产品变化。
5. 核验 `51d974…` 与 `bd770e…` 均不是 main/source 祖先，保持未合并只读；不得修改、清理、
   合并、改写为成功或作为本轮通过证据。

任一身份、父链、洁净度、范围或 evidence 门禁不符立即停止，且不得写 source。

## coverage-only 事实与必须独立验证

Correction 不是产品 bug 修复：Implementer 记录新增生产链节点在未改产品源码时首次即 `3 passed`，
没有有效产品 RED，产品源码也未变化。Reviewer 2 必须把它视为对首轮 P1 的测试证据补齐，不得写成
修复了已证实的产品代码缺陷；Implementer 的 `3/149 passed` 均不作独立证据。

1. **真实 Adapter 入口**：新测试必须实际实例化并调用
   `YtDlpSubtitleAdapter.enumerate_tracks()`，而不是调用私有分类、tuple 或 error helper 代替。
2. **替身边界**：Fake/monkeypatch 只能位于 downloader/transport 外部 I/O 边界。允许既有测试注入
   hook 仅用于安装 outer `ydl_factory`/clock；进入 Adapter 后不得由测试调用私有诊断、matrix、
   classification 或 error helper，不得设置最终私有状态 tuple、构造最终私有诊断错误或直接返回矩阵。
3. **生产校验与错误映射**：必须由 Adapter 自己完成目录概念访问、字段/形状校验、六字段状态构造、
   B6/B7 诊断与 `TranscriptError(INVALID_RESPONSE)` 映射。非用户合成 Mapping 不得枚举或保存任意
   外部 key/value，也不得伪装成录制的真实响应结构。
4. **真实 smoke 传递**：`PublicSubtitleSmoke` 必须使用上述真实 Adapter 产生的错误，通过既有 factory
   和真实失败路径生成 stdout 与 JSONL 六字段矩阵；测试不得在 Adapter 与 smoke 之间替换错误、
   tuple 或最终摘要。
5. **覆盖充分性**：独立确认至少一个字段错配的完整生产链、`unknown`/`not_evaluated` 的正确生产
   选择、门禁不满足时整个矩阵/事件省略、stdout/JSONL 六字段完整固定顺序与封闭值域、符合门禁时
   每目标至多一个 contract-state 事件且不符合时为零。既有非生产 helper 测试只能作补充，不能替代
   新生产链证据。
6. **回归与架构**：验证 B4--B10 词表/门禁/含义、默认 smoke 一次正文读取、directory-only 零正文、
   退出码、metadata/enumerate/read 计数、无重试、临时根、ID 上限、零业务记录及 fail-closed 不退化；
   Adapter 解析接受面未扩大，产品源码确实未因 Correction 改动。
7. **隐私与禁止范围**：扫描 Correction 与完整 B11 新增行以及运行时 stdout、stderr、JSONL、test、
   handoff、fixture 表面；不得新增真实响应结构、任意外部 key、URL、标题、语言、轨道、字段值、
   异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据。确认无依赖、锁文件、fixture、
   Schema、配置、认证、CLI、`logging.py` 或日志 schema 变化。

## 独立离线门禁与停止规则

- 先完成 Git-only 门禁和静态审查。若确认 P0/P1，立即停止后续产品命令；只按 handoff-only 规则记录
  `REJECT`、已取得证据和未运行项。不得把 Implementer 的 `3 passed`、focused `149 passed`、mypy、
  Ruff、CLI 或泄漏扫描自报计为独立证据。
- 无 P0/P1 时，只可先运行一次：

```text
uv sync --locked --offline
```

  缓存缺失、锁变化、下载/网络迹象或失败立即停止，不得修复、重试、换命令或使用替代环境。同步成功
  且固定 source 的 `.venv` 工具存在时，按序各运行一次：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py::test_ytdlp_adapter_maps_contract_mismatch_to_frozen_no_value_state tests/integration/test_public_subtitle_smoke.py::test_directory_only_emits_frozen_directory_contract_state_matrix tests/integration/test_public_subtitle_smoke.py::test_production_contract_state_is_omitted_without_directory_only_gate
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check 4aebc01360fa9684fe6b052f266a00ecc2de57dc...ed250baf752182adbc4d98f5271d34995865d192
git diff --check 80aff83fc033a8bd2950108cad2e34feea5d396f...ed250baf752182adbc4d98f5271d34995865d192
```

- 独立核验 Correction 三路径、完整 B11 五路径、产品 source blob 未变、禁止范围与锁文件，并完成
  stdout/stderr/JSONL/test/handoff/fixture 全输出面泄漏扫描。不得运行 full pytest、build、其他 CLI
  子命令、网络、真实 YouTube/smoke、认证/Cookie/netrc、媒体/ffmpeg、模型/Ollama/OpenAI、云端、
  真实 Vault、用户数据或其他真实资源。
- 任一门禁失败立即停止，不得修复、重试或换命令。以正确性、可读性、架构、安全/隐私、性能五轴
  记录发现，使用 P0、P1、P2、P3 并给出 `APPROVE` 或 `REJECT`。P2/P3 仍须如实记录并完成其他
  安全门禁，除非继续执行本身不安全。

## 唯一写入与交付

- Reviewer 唯一允许写入是向 source `handoffs/TASK-014.md` 追加独立 Reviewer 2 evidence；不得
  修改产品源码、测试、ADR、任务卡、prompt、项目状态或其他 source 路径。
- 记录 coverage-only 判断、生产链静态/运行时证据、五轴、P0--P3、`APPROVE`/`REJECT`、实际命令、
  结果、停止点、未运行项与剩余风险；不得把 Implementer 自报或真实失败 evidence 当作通过。
- 创建一个且仅一个 handoff-only commit，其唯一父提交必须为
  `ed250baf752182adbc4d98f5271d34995865d192`。提交前后核验精确暂存范围、SHA-256、LF/EOF、
  `git diff --check`、父链、HEAD 与 source 洁净度。
- 禁止 merge、push、source 清理和 `.codebase-memory` 工件。不得修改任务状态；TASK-014B11 保持
  `IN_REVIEW`，TASK-014 保持 `IN_PROGRESS / No-Go`。离线审查不构成真实 smoke、产品兼容性修复、
  正文可读、发行批准或最终 Go。
