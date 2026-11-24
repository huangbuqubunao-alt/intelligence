# TASK-014B11 — 安全字幕目录契约状态诊断独立 Reviewer

你是 TASK-014B11 的全新独立 Codex Reviewer。只审查固定 source 上的 implementation 与 ADR-021
契约；不得依赖 Implementer 自报结论，不得修复、重构、重新设计、修改产品代码或访问真实资源。
本包只创建授权，不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B11 — safe subtitle directory contract-state diagnostics
Role: Independent Reviewer
Control-plane baseline: main@6f5336098406f95ad1773d2ea36da24aaa97530f
Execution main: dynamic clean single-parent main commit containing this prompt and synchronized TASK-014B11/TASK-014/status/index control documents; its sole parent must be 6f5336098406f95ad1773d2ea36da24aaa97530f
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Reviewed source branch: codex/task-014b11-safe-directory-contract-diagnostics
Reviewed implementation HEAD: f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
Required sole parent of implementation: 80aff83fc033a8bd2950108cad2e34feea5d396f
Complete B11 review range: 80aff83fc033a8bd2950108cad2e34feea5d396f...f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
Read-only real execution evidence: 51d9749943270cb75c2b166e77bce0a5f663d92c (must remain unmerged)
Read-only B9 failure evidence: bd770ef9d212ebe75689b8f33145bf2556fe93c2 (must remain unmerged)
Allowed product scope: src/youtube_intel/providers/subtitles.py; src/youtube_intel/public_subtitle_smoke.py; tests/integration/test_subtitle_provider.py; tests/integration/test_public_subtitle_smoke.py; handoffs/TASK-014.md
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary and JSONL schema, ADR-017--ADR-020 diagnostics, and offline integration infrastructure; no dependency or third-party change
```

## 开始前 Git-only 门禁

1. 完整阅读仓库协作资料、ADR-017--ADR-021、TASK-014、TASK-014B6/B7/B8/B10/B11、
   Implementer handoff 与本正式包；如有冲突立即停止并报告 `DECISION NEEDED`。
2. 核验 dynamic main 是包含本包的干净单父控制面提交，唯一父提交为固定 control-plane baseline；
   核验 source worktree/branch/HEAD 精确匹配，暂存区、tracked/untracked worktree 均干净。
3. 核验 implementation 的唯一父提交为固定 base，完整 Diff 精确且仅为五条 allowed product scope，
   `git diff --check` 通过。确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认
   CLI、`logging.py`/日志 schema、控制面或 evidence 文档变化，也未扩大字幕解析接受面。
4. 核验 `51d974…` 的唯一父提交为 `f00aa9cffa25dcb9b7165edf21a4d476263c1dc5` 且只改三份
   授权 evidence 文档；核验它和 `bd770e…` 均不是 main 或 source 的祖先。两份 evidence 只读、
   未合并，不得修改、清理、合并、改写为成功或作为本轮产品通过证据。

任一身份、父链、洁净度、范围或 evidence 门禁不符，立即停止且不得写入 source。

## 必须独立审查

1. **固定六字段契约与正确性**：字段必须完整且严格按
   `video_identity_shape`、`manual_directory_shape`、`automatic_directory_shape`、
   `caption_bucket_shape`、`track_entry_shape`、`required_members_shape` 排序。逐一验证 ADR-021
   固定枚举，不得增删值；前置层未安全到达只可为 `not_evaluated`，已到达但无法安全判断只可为
   `unknown`，不得将推断写成事实。
2. **严格输出门禁**：矩阵只可在 directory-only、最终 `INVALID_RESPONSE`、metadata=`1` /
   enumerate=`1` / read=`0`、B7 `directory_origin_mapping` 且零正文全部成立时出现。逐项破坏每个
   门禁时必须省略整个矩阵。
3. **stdout/JSONL 完整性与 schema**：stdout 与 JSONL 必须完整、按同一固定顺序提供六字段。为
   避免既有 300 字符 `safe_message` 上限而使用的独立事件，必须沿用既有 JSONL 顶层 schema，
   不新增任意字段、自由文本或无界事件；独立验证其安全消息完整且不会被截断。
4. **固定事件上界与性能**：每个符合门禁的失败目标至多额外产生一个固定 contract-state 安全事件，
   不符合门禁时为零；事件不得按字段、外部 key、轨道、语言、异常链或其他输入循环产生，确保固定
   有限数量、无日志放大。结合实现复杂度与输出长度给出性能轴结论。
5. **默认行为与回归**：默认 smoke 仍恰有一次正文读取；directory-only 保持 `1/1/0`；退出码、
   计数、无重试、临时根、ID 上限、零业务记录与 fail-closed 不变。独立回归 B4--B10 的既有词表、
   门禁和含义，B11 不得替换、细分或反推既有诊断。
6. **Adapter 架构边界**：状态只能来自既有生产 Adapter 校验分支的封闭、无值内部状态；不得基于
   异常文本、URL、响应文本、动态类型名或外部字段名/值猜测，也不得新增接受分支、放宽类型或成员
   校验、修复真实兼容性或扩大字幕解析接受面。
7. **隐私与安全**：独立扫描 stdout、stderr、JSONL、测试新增行与 handoff 新增行。B11 矩阵及其
   新 `safe_message` 不得输出或持久化任意外部 key、视频 ID 值、URL、标题、语言、轨道、字段值、
   数量、异常原文、原始响应、路径、Cookie、token、payload、用户数据或凭据。既有 B5 stdout
   安全目标标识与既有 JSONL `video_id` schema 字段保持原样，不属于 B11 矩阵；B11 不得把该值复制、
   拼接或嵌入新的安全消息。
8. **测试与 handoff 安全性**：新增测试必须使用无值内部状态或仅含 ADR-021 项目契约概念的合成
   替身，不得重现真实响应结构；不得新增、恢复、修改、移动或内嵌敏感 fixture。handoff 不得保存
   原始命令输出、外部结构或任何禁止材料。
9. **禁止范围**：确认无依赖、锁文件、Schema/migration、配置、认证、默认 CLI、`logging.py`/
   日志 schema、fixture 或控制面变化；新增独立事件仍必须使用既有 JSONL schema。
10. **五轴结论**：分别按正确性、可读性、架构、安全/隐私、性能记录发现，使用 P0、P1、P2、P3
    分级并给出 `APPROVE` 或 `REJECT`。不得预写或省略任一轴。

## 独立离线门禁与停止规则

- 先完成 Git-only 门禁和静态五轴审查。不得把 Implementer handoff 的 focused `147 passed`、mypy、
  Ruff、CLI help、范围或泄漏扫描自报计为独立证据。若静态审查已确认 P0/P1，立即停止后续产品命令，
  按下述 handoff-only 规则记录 `REJECT`、已取得证据与未运行项。
- 无 P0/P1 时，只可先运行一次：

```text
uv sync --locked --offline
```

  缓存缺失、锁变化、下载/网络迹象或失败立即停止，不得修复、重试、换命令或使用替代环境。同步成功
  且固定 source 的绝对 `.venv` 工具存在时，按序各运行一次：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check 80aff83fc033a8bd2950108cad2e34feea5d396f...f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
```

- 独立检查五路径精确范围、全部禁止路径、固定字段/枚举/事件上界，并扫描 stdout、stderr、JSONL、
  test、handoff 与 fixture 输出面。不得运行 full pytest、build、其他 CLI 子命令、网络、真实 YouTube/
  smoke、认证/Cookie/netrc、媒体/ffmpeg、模型/Ollama/OpenAI、云端、真实 Vault、用户数据或其他真实资源。
- 任一授权门禁失败立即停止，不得修复、重试或换命令；如实记录失败与未运行项。发现 P0/P1 后立即
  停止剩余产品命令。P2/P3 仍须如实记录并完成其余安全门禁，除非继续执行本身不安全。

## 唯一写入与交付

- Reviewer 唯一允许写入是向 source `handoffs/TASK-014.md` 追加独立审查 evidence。不得修改业务
  代码、测试、ADR、任务卡、prompt、项目状态或其他 source 路径。
- 使用 `handoffs/TEMPLATE.md` 的证据结构，记录五轴、P0--P3、`APPROVE`/`REJECT`、实际独立命令、
  结果、停止点、未运行项与剩余风险；不得把 Implementer 自报、真实失败 evidence 或静态推断记为
  独立通过。
- 创建一个且仅一个 handoff-only commit，其唯一父提交必须为
  `f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50`。提交前后核验精确暂存范围、SHA-256、LF/EOF、
  `git diff --check`、父链、HEAD 与 source 洁净度。
- 禁止 merge、push、source 清理和 `.codebase-memory` 工件。不得修改任务状态；TASK-014B11 保持
  `IN_REVIEW`，TASK-014 保持 `IN_PROGRESS / No-Go`。离线审查不构成真实 smoke、普遍兼容性证明、
  正文可读、发行批准或最终 Go。
