# TASK-014B11 — Pre-merge Leak Gate Correction 2 Implementer

你是 TASK-014B11 的原 Codex Implementer，负责在同一 source 谱系内处理预合并
`credential-name-followed-by-assignment` 泄漏门禁的两个新增 `unknown` 命中。先安全分类，只有确认
两行是纯合成测试材料或安全局部标识后才可做最小测试材料修正；不得修改产品、扫描规则或控制面。
本包只创建授权，不启动 Implementer。

## 必读资料与固定对象

开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、ADR-021、
`tasks/TASK-014-release-readiness.md`、`tasks/TASK-014B11-safe-directory-contract-diagnostics.md`、
B11 Implementer/两轮 Reviewer/Correction 1/Integrator/Leak Triage Scout 包、全部 B11 handoff 及本包。
若任一边界冲突，立即停止并报告。

```text
Task: TASK-014B11 — pre-merge leak gate Correction 2
Role: Original Codex Implementer
Control-plane parent/base: main@18af86361cc152d043723758b1b5548cfbdfe4ff
Source worktree: /Users/hua/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Source branch: codex/task-014b11-safe-directory-contract-diagnostics
Correction 2 base / required initial HEAD: f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Required sole parent of first Correction 2 commit: f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Original B11 product base: 80aff83fc033a8bd2950108cad2e34feea5d396f
Reuse decision: DIRECT — existing synthetic integration-test infrastructure, fixed leak gates and Git/SHA-256 evidence only; no dependency or third-party change
```

- 开始前核验 main 包含本动态授权，source 分支/HEAD/工作树/暂存区精确且干净；accepted source
  尚未进入 main。任一不符立即停止，不得修复、同步、rebase 或清理。
- 原 Product Integrator 已在综合静态泄漏扫描 `exit 32` 后停止，merge 未执行。不得重启或复用原
  Integrator 授权，也不得把此前通过的产品门禁用于覆盖本次泄漏阻断。

## 固定脱敏诊断事实

- Scout 只在聊天回传只读脱敏报告，没有 evidence commit，也没有写 source。
- 总命中数为 `11`；其中 `9` 个非新增命中已分类为 `scanner-self-match`，不属于本 Correction，
  不得借机修改、忽略或重写。
- 仅以下两个新增命中仍为 `unknown`：

  1. `tests/integration/test_public_subtitle_smoke.py:210`
  2. `tests/integration/test_subtitle_provider.py:105`

- 两条匹配行的 SHA-256 均为
  `f950e2195fb88b36b457dc65bd53c632676bbd127a2378788d6fea3ade392e0d`。
- 没有确认真实凭据，但风险仍不能排除；在完成安全分类和最小修正前 merge 保持阻断。

以上元数据是唯一可写入 handoff 或聊天的原命中证据。不得补充匹配值、整行、上下文或内容摘要。

## 阶段一：安全分类与立即停止规则

Implementer 可在本地只读检查上述两行实际内容，但不得在终端输出、聊天、handoff、命令参数、
临时文件、patch 说明或任何其他工件中回显匹配值、整行、前后文或可逆摘要。

必须先分别判断两行是否为真实或无法排除的凭据：

- 若任一行为真实凭据、可能来自真实材料，或仍无法安全排除，立即停止；不得修改、暂存或提交
  source，不得运行后续 locator、uv、测试、构建或 CLI。聊天只报告
  `confirmed-secret-or-credential` 或 `unknown`、固定路径/行号/行 SHA-256，并说明是否建议凭据
  轮换或独立安全响应；不得显示值。
- 只有两行均能确认是纯合成测试材料或安全局部标识，才可继续阶段二；handoff 分类只能使用
  `synthetic-test-sentinel` 或明确的 `safe-local-identifier`，并记录无真实凭据风险的判断边界。

不得依据“位于 tests”“已有 Reviewer 通过”或相同行哈希自动判定安全；必须完成本地只读内容判断。

## 阶段二：最小 Correction 2

唯一允许修改范围严格为：

1. `tests/integration/test_public_subtitle_smoke.py`
2. `tests/integration/test_subtitle_provider.py`
3. `handoffs/TASK-014.md`

- 最小修正必须从两份测试源码中移除 `credential-name-followed-by-assignment` 形态，同时保持原测试
  意图、行为覆盖和断言强度。
- 不得删除测试、删除或弱化泄漏断言、skip/xfail、降低覆盖、改变扫描规则、增加通用忽略/allowlist，
  或通过隐蔽字符串拼接、编码、分段拼接、哈希替代等方式掩盖真实凭据。
- 若该材料用于验证脱敏或拒绝逻辑，必须改用明确、固定、非秘密且不形成凭据赋值形状的合成输入，
  保持同等测试覆盖。不得引入真实响应、URL、标题、语言、轨道、字段值、异常原文、路径值、Cookie、
  token、payload、用户数据或凭据。
- 禁止修改生产代码、fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认 CLI、
  `logging.py`/日志 schema、ADR、任务/项目状态、prompt 或其他控制面。
- `handoffs/TASK-014.md` 只能追加 Correction 2 evidence；只记录固定路径、原行号、原行 SHA-256、
  分类、处理方式和安全门禁结果，不得记录原匹配内容、替换值、整行、上下文或可逆摘要。

首个且唯一 Correction 2 commit 的唯一父提交必须为
`f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d`。实际 Diff 必须是上述三路径的最小子集；完成前后核验
父链、精确范围、SHA-256、LF/EOF、`git diff --check` 与 source 洁净度。

## 专用 locator、离线验证与泄漏门禁

只有阶段一确认安全并完成最小修正后，才可依次执行以下检查；任一缓存缺失、下载/网络迹象、
命令失败、命中或无法安全判定都立即停止，不得修复、换命令或重试：

1. 重新执行一次专用最小 locator，只验证上述两个新增命中已关闭。输出仍只能是路径、行号、固定
   规则类别、行 SHA-256、是否新增行与计数；预期这两个原行哈希的新增命中数均为 `0`。不得把
   `9` 个非新增 `scanner-self-match` 纳入 Correction 或建立忽略。
2. `uv sync --locked --offline`
3. 三个既有生产链节点：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py::test_ytdlp_adapter_maps_contract_mismatch_to_frozen_no_value_state tests/integration/test_public_subtitle_smoke.py::test_directory_only_emits_frozen_directory_contract_state_matrix tests/integration/test_public_subtitle_smoke.py::test_production_contract_state_is_omitted_without_directory_only_gate
```

4. 完整 Provider/Smoke focused tests：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
```

5. 类型、Lint 与 CLI help：

```text
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
```

6. Correction 2 `f57b21c…...HEAD` 三路径上限、完整 B11 `80aff83…...HEAD` 原五路径上限、
   `uv.lock`/依赖/fixture/Schema/config/CLI/logging 禁止范围与 `git diff --check`。
7. 正式综合泄漏扫描必须通过，覆盖 stdout、stderr、JSONL `safe_message`、测试新增行、handoff 与
   fixture 表面；只能回传安全 pass/fail 与路径级摘要，不得显示匹配材料。不得修改或放宽扫描器。

full pytest、build、其他 CLI 子命令、真实资源与 merge 不在本 Correction 授权内，必须明确记录为
未运行/禁止，不得写成通过。

## 交付、状态与禁止

- 成功时只创建一个上述最小范围内的 Correction 2 commit，并报告 SHA、唯一父、实际路径、分类、
  locator/综合扫描及离线检查结果；不得启动 Reviewer、合并或修改 main 控制面。
- 禁止网络、YouTube、真实 smoke、登录/认证、Cookie/API key/凭据、媒体/ffmpeg、真实 Vault、
  用户数据、模型、Ollama、OpenAI、云端/付费调用、push、source 清理及 `.codebase-memory`/
  `.codegraph`/索引工件。
- TASK-014B11 保持 `IN_PROGRESS / Codex`；TASK-014 保持 `IN_PROGRESS / No-Go`。Correction 2
  即使通过也不是 Reviewer APPROVE、merge 授权、真实凭据安全证明、真实 smoke、普遍兼容性证明、
  正文可读或发行批准。
