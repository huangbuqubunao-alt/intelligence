# TASK-014B11：安全字幕目录契约状态诊断

- Status: `INTEGRATED / CLOSED`
- Assignee: `Historical source retained as evidence only`
- Reviewer: `Independent integration / no-op review APPROVE`
- 依赖：TASK-014B4/B5/B6/B7/B8/B10 `DONE`、ADR-021 `Accepted`
- 实施基线：`main@80aff83fc033a8bd2950108cad2e34feea5d396f`
- Worktree：`/Users/developer/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics`
- Branch：`codex/task-014b11-safe-directory-contract-diagnostics`
- Correction 2 base / prior accepted source：`f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d`
- Implementation evidence：`f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50`（唯一父提交
  `80aff83fc033a8bd2950108cad2e34feea5d396f`）
- First Reviewer evidence：`4aebc01360fa9684fe6b052f266a00ecc2de57dc`（唯一父提交为
  implementation，handoff-only；`REJECT`，P1=`1`）
- Correction 1 evidence：`ed250baf752182adbc4d98f5271d34995865d192`（唯一父提交为
  First Reviewer evidence；coverage-only 三路径）
- Reviewer 2 evidence：`f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d`（唯一父提交为
  Correction 1；handoff-only；`APPROVE`，P0--P3=`0`）
- Reuse decision：`DIRECT` — 既有锁定 subtitle Adapter、B4 directory-only、B5 安全摘要、
  ADR-017--ADR-020 固定诊断、既有 JSONL `safe_message` 与离线 integration 基础设施；不新增
  第三方代码或依赖。

## 背景与目标

B10-classified 真实 evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` 是
`f00aa9cffa25dcb9b7165edf21a4d476263c1dc5` 的 evidence-only 唯一子提交，只修改正式
授权的三份 evidence 文档，且保持未合并、只读。它记录固定目标在 `1/1/0` 后以
`INVALID_RESPONSE` 停止；B7 origin 为 mapping，但现有安全诊断不能确定失败所在的项目契约层。

实现 ADR-021 的固定、无值六字段状态矩阵，帮助后续独立兼容任务区分顶层视频标识、人工/
自动字幕目录、字幕桶、轨道条目和必需成员边界。B11 不修复真实兼容性、不扩大解析接受面，
也不构成真实 smoke、正文读取或发行批准。

## Implementation evidence 与独立审查授权

- Status Integrator 已以 Git-only 方式核验固定 implementation HEAD、唯一父链、main/source 身份与
  洁净度。implementation Diff 精确为 Adapter、safe smoke、两份 integration test 与
  `handoffs/TASK-014.md` 五路径，`git diff --check` 通过；无 fixture、依赖、`uv.lock`、
  Schema/migration、配置、认证、默认 CLI、`logging.py` 或日志 schema 变化。
- 只读真实 evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` 与 B9 evidence
  `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 均未进入 main。它们不得修改、合并、清理或改写为成功。
- Implementer handoff 自报 focused `147 passed`、mypy、Ruff、CLI help、范围、Diff 与泄漏扫描；这些只登记为
  implementation evidence，不得替代 Reviewer 独立复跑或独立结论。实现为规避既有 300 字符 `safe_message`
  上限而使用一个独立、既有 schema 的固定安全事件；其完整性、固定顺序、每目标固定有限事件数和无日志放大
  必须由 Reviewer 独立核验。
- 全新独立审查包为
  `agent-prompts/TASK-014B11-SAFE-DIRECTORY-CONTRACT-DIAGNOSTICS-REVIEWER-CODEX.md`。Reviewer
  唯一允许写入是向 source `handoffs/TASK-014.md` 追加审查 evidence，并创建以 implementation HEAD 为
  唯一父提交的 handoff-only commit；不得修改业务代码、测试、控制面或任务状态。
- 首轮 Reviewer evidence `4aebc01360fa9684fe6b052f266a00ecc2de57dc` 已完成该轮审查；其 Verdict
  为 `REJECT`、P1=`1`。不得把原授权或 Implementer 自报写成独立通过。

## First review reject 与 Correction 1

- 唯一 P1：现有 Provider tests 直接检查私有枚举/tuple helper，safe smoke test 又由 Fake 直接
  构造私有错误和最终矩阵；它们绕过生产 `YtDlpSubtitleAdapter.enumerate_tracks()` 的目录校验、
  诊断状态构造与 `TranscriptError` 传递边界，因而不能证明真实字段错配会生成正确六字段矩阵，
  也不能捕获 `unknown`/`not_evaluated` 的生产映射错误。
- Reviewer 按 P1 立即停止规则未运行 `uv sync --locked --offline`、focused pytest、mypy、Ruff、
  CLI help 或运行时 stdout/stderr/JSONL 扫描；这些项目不得登记为 Reviewer PASS。静态父链、五路径、
  禁止范围、Diff、固定契约与泄漏检查只按 evidence 中的实际结果记录。
- Correction 1 正式包为
  `agent-prompts/TASK-014B11-SAFE-DIRECTORY-CONTRACT-DIAGNOSTICS-CORRECTION-1-IMPLEMENTER-CODEX.md`。
  原 Implementer 只能从 Reviewer evidence 继续同一 source 谱系，先以真实 Adapter→真实 smoke
  生产传递链补齐测试；若生产代码正确，只补测试与 handoff，只有 RED 确证传递缺陷时才可最小修复。
- 首个 Correction commit 的唯一父提交必须为 Reviewer evidence；最大范围仍为原五路径，实际 Diff
  必须是最小子集。不得启动 Implementer/Reviewer、预写 Correction 结果、Reviewer verdict、
  `ACCEPTED`、merge 或 `DONE`。
- First review reject 控制面据此曾将 TASK-014B11 退回 `IN_PROGRESS / Codex`；该历史状态随后由
  下述 Correction 1 review authorization 更新。TASK-014 始终保持 `IN_PROGRESS / No-Go`。

## Correction 1 evidence、Reviewer 2 验收与整合授权

- Correction 1 唯一父提交为 First Reviewer evidence；Diff 精确为两份 integration tests 与
  `handoffs/TASK-014.md` 三路径。完整 B11 Diff 仍精确位于 Adapter、safe smoke、两份 tests 与
  handoff 原五路径，Correction/完整范围 `git diff --check` 均通过。
- Correction 是 coverage-only：新增生产链测试先调用真实
  `YtDlpSubtitleAdapter.enumerate_tracks()`，再由真实 `PublicSubtitleSmoke` 观察 stdout/JSONL；
  新增三个节点在未修改产品源码时首次即自报 `3 passed`，因此没有有效产品 RED，也没有产品修复。
  Adapter 与 safe smoke 产品源码相对首轮 implementation 未改变。这只补齐首轮缺少的生产传递链
  证据，不得写成修复了已证实的产品代码 bug。
- Reviewer 2 evidence 是 Correction HEAD 的 handoff-only 唯一子提交，Verdict=`APPROVE`、
  P0--P3=`0`。独立通过 locked offline sync、三个生产链节点 `3 passed`、Provider/Smoke focused
  `149 passed`、mypy、Ruff、CLI help、Correction/完整/evidence Diff、五/三/handoff-only 范围及
  stdout/stderr/JSONL/test/handoff/fixture 泄漏扫描；full pytest 与 build 未运行，不得登记为通过。
- Reviewer 2 独立确认真实 Adapter→Smoke 生产链、无私有最终诊断构造、字段/回退/门禁/事件上界、
  B4--B10 回归、解析接受面与隐私边界。Correction 仍是 coverage-only，没有有效产品 RED，也没有
  产品修复；不得将 Reviewer APPROVE 改写成产品 bug 已修复。
- Product Integrator 正式包为
  `agent-prompts/TASK-014B11-SAFE-DIRECTORY-CONTRACT-DIAGNOSTICS-PRODUCT-INTEGRATOR-CODEX.md`。
  仅在完整离线门禁通过后允许一次 `git merge --no-ff`，accepted source 必须精确为
  `f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d`；任一失败立即停止，不得修复、换命令或重试。
- TASK-014B11 现为 `ACCEPTED`；首次 Product Integrator 已按下述 fail-closed 门禁停止，未产生
  merge SHA，未预写 `DONE`、真实兼容性、真实 smoke 或发行批准。TASK-014 始终保持
  `IN_PROGRESS / No-Go`。

## Product Integrator 预合并停止与 Leak Triage Scout 授权

- Product Integrator 从固定 main `a92e321216f418e0add6f01f7d1f300dcce11ea6` 和 accepted source
  `f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d` 启动。Git-only 父链、Reviewer 2 handoff-only、
  Correction coverage-only 三路径、完整五路径、禁止范围、三组 `git diff --check` 与双方洁净度
  前置核验通过。
- 预合并离线门禁实际通过：`uv lock --check`、locked offline sync、三个生产链节点 `3 passed`、
  Provider/Smoke focused `149 passed`、full pytest `520 passed`、mypy、Ruff、CLI help、offline build
  与三组固定 `git diff --check`。这些通过项不能覆盖后续泄漏门禁失败，也不构成合并授权。
- 综合静态泄漏扫描以 `exit 32` 停止，表示完整五路径新增材料命中
  `credential-name-followed-by-assignment` 规则类别。扫描未回显命中内容；按正式包要求没有定位、
  修复、换规则、重试或执行 merge。main/source 保持固定 SHA 和干净状态，accepted source 尚未合并。
- 唯一新的只读分诊包为
  `agent-prompts/TASK-014B11-PRE-MERGE-CREDENTIAL-SHAPE-LEAK-TRIAGE-SCOUT-CODEX.md`。Scout 只可对
  `80aff83…...f57b21c…` 五路径 Diff 执行一次专用最小 locator，并且只回传路径、行号、固定规则
  类别、匹配行 SHA-256、是否新增行及固定五类分类；不得回显值、整行或上下文。
- Scout 不修复、不放宽扫描器、不重跑 Integrator、不写 source，也不得自行批准合并。该只读阶段
  已由下述脱敏报告关闭；其结论要求 Correction 2，原 accepted source 的 merge 继续阻断。

## Leak Triage Scout 报告与 Correction 2 授权

- Scout 没有 evidence commit，只向主控回传只读脱敏报告。总命中 `11`：其中 `9` 个非新增命中为
  `scanner-self-match`，不属于 Correction；另有 `2` 个新增 `unknown`，分别位于
  `tests/integration/test_public_subtitle_smoke.py:210` 与
  `tests/integration/test_subtitle_provider.py:105`。
- 两个新增命中的匹配行 SHA-256 相同，均为
  `f950e2195fb88b36b457dc65bd53c632676bbd127a2378788d6fea3ade392e0d`。没有确认真实凭据，但风险
  不能排除；不得显示、推断或记录匹配内容，merge 继续阻断。
- TASK-014B11 已从 `ACCEPTED` 退回 `IN_PROGRESS / Codex`。Correction 2 正式包为
  `agent-prompts/TASK-014B11-SAFE-DIRECTORY-CONTRACT-DIAGNOSTICS-CORRECTION-2-IMPLEMENTER-CODEX.md`；
  原 Implementer 只能在同一 source 谱系从 `f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d` 继续，首个
  Correction 2 commit 必须以该提交为唯一父提交。
- Implementer 必须先本地只读分类两行；任一真实或无法排除的凭据风险都立即零提交停止，并只做
  脱敏报告与轮换建议。只有两行均确认是纯合成测试材料或安全局部标识后，才可在两份 integration
  tests 与 `handoffs/TASK-014.md` 三路径上限内做最小修正。
- 修正不得删除/skip/弱化测试或泄漏断言，不得修改/放宽扫描规则、增加通用忽略/allowlist、隐蔽
  拼接、产品源码、fixture、依赖、锁、Schema、配置、CLI、`logging.py` 或控制面。专用 locator
  必须关闭两个新增命中，综合泄漏扫描及正式离线生产链/focused/mypy/Ruff/CLI/范围/Diff 门禁必须通过。
- 本控制面不启动 Implementer/Reviewer，不构成新的 accepted source 或 merge 授权。TASK-014 始终
  保持 `IN_PROGRESS / No-Go`。

## 冻结契约

- 矩阵字段顺序严格为：`video_identity_shape`、`manual_directory_shape`、
  `automatic_directory_shape`、`caption_bucket_shape`、`track_entry_shape`、
  `required_members_shape`。
- 每个值必须来自 ADR-021 对应封闭枚举；前置层未安全到达只能为 `not_evaluated`，已到达但
  无法安全分类只能为 `unknown`。六字段完整输出，不得增加动态字段或自由文本。
- 只有 directory-only、`INVALID_RESPONSE`、metadata=`1`/enumerate=`1`/read=`0`、
  `directory_origin_mapping` 且未读取正文时，才可经既有 B5 stdout/JSONL `safe_message`
  出口附加矩阵；任一条件缺失必须省略整个矩阵。
- 字段名仅是项目内契约概念。B11 新增矩阵禁止视频 ID 值、任意外部响应 key、URL、标题、语言代码、
  轨道名、字段值、数量、顺序、类型名、异常原文、原始响应、路径、Cookie、token、payload、用户数据或
  凭据；既有 B5 安全目标标识与其他既有安全摘要语义保持不变，不属于 B11 矩阵。
- 不改变 B6/B7/B8/B10 的词表、触发条件或含义；不新增 JSONL schema 字段、`logging.py`、Provider
  metadata、CLI 参数、配置或持久化状态。
- 不扩大 Adapter 字幕解析接受面，不改变默认 smoke、退出码、metadata/enumerate/read 计数、
  默认一次正文读取、directory-only 零正文、无重试、临时根、ID 上限、零业务记录、认证或
  fail-closed 边界。
- 测试只能使用无值内部状态，或仅含 ADR-021 项目契约概念的合成替身；不得新增、恢复或读取
  真实/结构化目录 fixture。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

实际产品 Diff 必须是上述允许范围的最小子集；不得为凑范围修改无需变化的文件。不得修改
fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`、日志 schema、
任务状态、ADR/prompt 或任何 evidence 文档。

## 离线验收

- 先由测试覆盖六字段的全部固定状态、`unknown` 与 `not_evaluated`，再做满足契约的最小实现；
  不得只测试私有格式化出口而绕过生产 Adapter 校验到 safe smoke 的传递边界。
- 独立证明矩阵只在完整严格门禁出现；默认 smoke 仍读取一次正文，directory-only 保持 `1/1/0`，
  退出码、无重试和零业务记录不变。
- 回归 ADR-017--ADR-020 的 B6/B7/B8/B10 固定诊断、成功/其他错误码省略规则、CLI 边界、
  Adapter fail-closed 与解析接受面。
- stdout、stderr、JSONL `safe_message`、测试新增行和 handoff 必须通过全输出面泄漏扫描；不得包含
  禁止材料或新增 fixture。
- Implementer 只可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁变化、下载/网络迹象或失败立即停止。仅在已有离线 `.venv` 可用时按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## Git、交付与红线

- 首个且唯一产品提交的唯一父提交必须为
  `80aff83fc033a8bd2950108cad2e34feea5d396f`；控制面提交不进入 source 历史。
- 开始与提交前后核验 source 身份、父链、精确 Diff、允许范围、SHA-256、LF/EOF、
  `git diff --check` 和洁净度。只在 `handoffs/TASK-014.md` 追加实现 evidence。
- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、登录、认证、Cookie/API key/凭据、真实 Vault、
  用户数据、模型、Ollama、OpenAI、付费/云端调用、push、合并、source 清理、测试/检查外产品命令
  和 `.codebase-memory` 工件。
- 不得修改任务状态、启动 Reviewer 或把 B11 写成真实成功。TASK-014 始终
  `IN_PROGRESS / No-Go`；完成后只报告 Implementer commit、检查、跳过项和剩余风险。

## Independent integration / no-op closeout — 2026-08-30

- Historical Correction 2 source is
  `codex/task-014b11-safe-directory-contract-diagnostics@4b86ecb27012dd4c1c9fd2e8c2496160e64aa3bf`.
  Its effective five-path B11 delta has stable patch ID `700128137ec309dfbfcd8c7b1eaf245f0bd31e7f`.
- Forward-integration anchor `e04f52269d94dfe1317c088d49dc8ad78ae490b9` contains byte-identical blobs for all five B11 paths, including both Correction 2 test files and this handoff. No historical merge, cherry-pick, replay, push, or tag is required.
- At `main@05ceb22d27a7aaa59f90d06e9adf6d06fd2f826d`, later overlap is limited to this handoff, `providers/subtitles.py`, and its integration test. The source change adds silent dependency logging and fixed safe error categories; the B11 matrix, output gates, restricted key-name validation, and corrected synthetic fixture methods remain unchanged.
- Current B11-focused tests, scanner regression tests, full pytest, `uv run mypy src`, Ruff, and Diff checks pass. The current repository security scan reports 11 findings in newer TASK-016 test fixtures; this is outside B11, is not an exemption or scanner weakening, and must be handled under separately authorized scope.
- Verdict: `INTEGRATED / CLOSED`. The historical branch is retained as evidence only; TASK-014 remains `IN_PROGRESS / No-Go` and this closure is not real smoke, compatibility, release, or project-Go evidence.
