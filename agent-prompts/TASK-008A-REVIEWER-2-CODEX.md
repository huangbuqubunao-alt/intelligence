# TASK-008A Correction 1 — 第二轮独立 Codex Reviewer

你是一个全新的、独立的 Codex Reviewer。你没有参与 TASK-008A 的原实现、第一轮
审查、Correction 1 或 main 控制面写入。你只审查固定 Correction 1 提交是否关闭了
全部 6 个 P1，并是否满足 TASK-008A、ADR-008 A-01 至 A-17 中属于共享契约/依赖
基线的要求及 correctness、architecture、security、performance、readability 五轴质量。

你不得修改业务代码、测试、配置、依赖、锁文件、任务状态或 main。唯一允许写入并
提交的是 source worktree 的 `handoffs/TASK-008A.md` Reviewer 部分。Verdict 只能为
`APPROVE` 或 `REJECT`；不得自行修复 finding。

## 固定对象与启动门禁

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main review authorization：动态运行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008A-REVIEWER-2-CODEX.md`
- Required authorization parent：`4eec2e186fce6dedbb105234f624fcb93274c938`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Original task base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- First review evidence：`0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`
- Reviewed Correction 1 head：`d95745fd04b115369a9fd70362cd735d1eb70917`
- Required identity：`Mozhu <maintainer@example.invalid>`；
  `user.useConfigOnly=true`

开始时 main 必须位于动态 authorization commit；该提交必须是 Required authorization
parent 的单一直接后继，main 干净且 TASK-008A=`IN_REVIEW`。source 必须精确位于
reviewed Correction 1 head、分支正确且干净。source 中任务/状态文件是 assignment
前历史快照，这是预期差异，不得修改。

任一 SHA、父链、身份、洁净度、范围或动态授权不符，立即报告 `BLOCKED`。不得
stash、reset、restore、checkout、merge、rebase、cherry-pick、pull、清理或选择其他
SHA。审查期间独占 source worktree；如 main 或 source 出现其他写入，立即停止。

## 必读与审查方法

完整读取 source 的：

1. `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PRD.md`、
   `docs/SYSTEM_DESIGN.md`
2. ADR-002、ADR-005、ADR-008 与 `docs/REUSE_REGISTER.md`
3. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`、`handoffs/TEMPLATE.md`
4. source `handoffs/TASK-008A.md`、Correction 1 Implementer 包和本 Reviewer 包

从 main 读取动态 authorization、TASK-008A 卡和 Project Status，确认实时控制面。
代码定位优先使用 Codebase Memory 图谱；图谱不足时再读取精确文件。不得以
Implementer 自报、测试数量或现有测试通过替代独立探针。

后续职责边界：精确 evidence 子串运行时核验、采样/token 计数、请求构造/hash 算法、
CredentialResolver、CloudCallBudget、OpenAI Provider、匿名管道协议、SDK 参数、缓存
和 SQLite 事务属于 TASK-008/TASK-010。不得仅因这些组件尚未实现而拒绝；但本共享
切片必须提供可供它们安全 fail-closed 消费的公共形状与 A-16/A-17 前提。

## Git、范围与红线门禁

确认：

1. Correction 1 head 的唯一父提交是 first review evidence，非 merge commit；
2. evidence...Correction 1 精确为以下 5 个路径：
   - `handoffs/TASK-008A.md`
   - `src/youtube_intel/config.py`
   - `src/youtube_intel/domain.py`
   - `src/youtube_intel/resources/o200k_base.tiktoken`
   - `tests/unit/test_contracts.py`；
3. original base...Correction 1 精确为原 7 路径加 resource 的 8 个路径；
   `pyproject.toml`、`uv.lock` blob 不得变化；
4. 无 Provider、`analysis.py`、Prompt、Schema/migration、`state.py`、
   `complete_stage`、CLI、task/ADR、真实数据、凭据、cache 或构建产物改动；
5. A-16 resource 必须为 `3,613,922` bytes 且 SHA-256 精确为
   `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`；
   只作本地 hash/归档验证，不运行任何 URL 或其他网络请求。

真实 OpenAI/API、密钥/环境变量值、付费调用、云端 token-count、真实
YouTube/Vault/用户内容、媒体、模型和凭据路径均未授权。审查中 `uv sync`、build 和
所有探针都必须离线；若本地 cache 缺失，报告 `BLOCKED`，绝不联网。

## 必须独立复跑

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 82d1fd7c7f2f82e77df0518e63755bad0bf240f2...d95745fd04b115369a9fd70362cd735d1eb70917
```

记录实际测试计数。构建后检查 sdist/wheel 均包含
`youtube_intel/migrations/001_initial.sql` 与
`youtube_intel/resources/o200k_base.tiktoken`，归档内资源大小/哈希精确匹配。只可清理
本轮生成且被忽略的 `dist/`。

## 六组独立探针

### A：哈希、语义非空与完成审计一致

独立构造并检查：

- 三个审计 hash 拒绝 63/65 位、uppercase、non-hex、前后空白与纯空白，只接受
  64 位 lowercase SHA-256；
- A-04 payload、evidence/point/keyword、AnalysisResult provider/model 和
  AnalysisCompleted 的 call provider/model 全部拒绝纯空白，且不 strip/改写原值，
  `description=""` 仍合法；
- `AnalysisCompleted` 拒绝 result/call provider mismatch、model mismatch、`None`
  model 和 whitespace model；完整匹配正例通过；
- 新分析对象的 `model_copy(update=...)` 仍无法绕过所有字段/模型验证，无 update
  shallow/deep copy 仍合法 frozen。

### B：完整 ConfigError 脱敏图

用新 secret-shaped YAML 合成哨兵触发 `load_settings`。递归遍历异常、cause、context、
Pydantic errors、repr、traceback 和所有项目帧 `f_locals`；哨兵不得出现。确认仍保留
安全字段路径/分类，且修复没有通过删除 traceback、吞掉 cause 或仅格式化替换来掩盖
原始 mapping。

### C：A-16 固定 tokenizer 资源与无网络回退

在空 tiktoken cache、socket/HTTP 拒绝和无网络条件下，从 package resource 的本地路径
配合 expected hash 解析 encoding；不得调用 `tiktoken.get_encoding("o200k_base")` 或
触发任何 HTTP。独立测试资源缺失、单字节篡改、错误 hash、解析失败和打包遗漏均在
任何 Provider/凭据/网络副作用前 fail-closed。确认 source、sdist、wheel 的资源 hash
相同；不得因 resource 本身是官方 Blob 而联网复核或下载。

### D：A-17 SDK 隔离导入

静态检查产品源码与 pytest 主进程没有直接/间接 `import openai`。以绝对
`sys.executable`、无 shell、新建 env 运行独立子进程，env 必须精确仅含：

```text
PYTHONNOUSERSITE=1
PYTHONDONTWRITEBYTECODE=1
PYTHONUTF8=1
```

在父进程仅设置合成 `OPENAI_*`、`AZURE_*`、代理和凭据型哨兵，证明子进程不继承、不
读取且离线 SDK 导入成功；不得读取、输出或断言任何真实环境值，子进程不得构造
client、请求 API 或实现匿名密钥管道。检查 ADR/公共契约明确把导入后匿名管道留给
TASK-008。

### E：原有契约、范围和回归

复查 A-04 10 字段 payload 白名单、4,000 code-point 描述边界、固定 skip reason、
evidence source/kind/cardinality/time=None、CloudSettings 默认关闭、model/encoding、
5/28k/30k/4k/120s/版本和未知 YAML/字段失败关闭。确认没有 `dict`、`Any`、宽
`object`、SDK 类型、Provider、Prompt、Schema/state 或配置兼容性回归。

### F：五轴、复用与 ADR 矩阵

按 correctness、architecture、security、performance、readability 审查完整 Diff。逐项
判定 TASK-008A 全部 AC 和 ADR-008 A-01 至 A-17：把运行时 Provider/匿名管道协议/采样/
token 计数/事务等标明为后续任务，但本切片冻结的 A-02/A-04/A-05 前提/A-06 表示、
A-08 隐私前提、A-13、A-14 离线前提、A-16/A-17 必须判定。核对复用和许可证记录：
OpenAI SDK Apache-2.0、tiktoken MIT、官方 BPE 文件级许可/NOTICE 留 TASK-014。

## Finding、证据与提交

- 任一未解决 P0/P1、必需门禁失败或独立探针无法证明：`REJECT`；
- 只有明确 P2/P3 且所有 AC/本任务 ADR 条款通过：可 `APPROVE`；
- 不得因未获授权的真实云/Vault 路径未运行而拒绝。

只在 `handoffs/TASK-008A.md` 追加 Reviewer 结论，然后只暂存该文件并提交：

```text
docs: review TASK-008A correction 1
```

evidence commit 的唯一父提交必须是 Correction 1 head，且只能修改 handoff。提交后
source/main 均应干净；不得 merge、push、修改任务状态、启动 TASK-009A/008/009 或清理
worktree。

## 回传格式

```text
Task: TASK-008A
Role: Second Independent Codex Reviewer
Reviewed Correction 1 head: d95745fd04b115369a9fd70362cd735d1eb70917
Review evidence commit:
Checks rerun:
Probe A hash/semantic/completion boundary:
Probe B complete ConfigError redaction:
Probe C A-16 local-resource/no-network boundary:
Probe D A-17 isolated SDK import:
Probe E regression/scope:
Acceptance matrix:
ADR-008 traceability:
Findings: P0/P1/P2/P3
Five-axis/scope/red-line/reuse review:
Verdict: APPROVE | REJECT
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
