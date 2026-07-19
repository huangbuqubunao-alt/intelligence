# TASK-007：Ollama 本地评分

- Status: `IN_REVIEW`
- Assignee: `Codex`
- Owner role: 全新独立 Codex Reviewer（Correction 1；离线复审）
- Size: M
- Risk: Medium
- Depends on: TASK-005A

## 2026-07-16 只读预检

- Scout observed main：`b335b12358bbbc9dada1abfafc5a2fe9a68494be`
- Repository changes：None
- 结论：`DECISION NEEDED`
- ADR-007 L-01 至 L-15 已于 2026-07-17 接受；本任务仍为 `BLOCKED/UNASSIGNED`，
  不得创建 worktree、安装 Ollama 或拉取模型。
- 共享配置、采样、决策对象与评分摘要原子持久化必须先由 TASK-005A 整合为 `DONE`；
  TASK-007 继续不修改依赖或锁文件。Ollama 安装/启动、模型拉取与本机文本冒烟仍须
  独立任务级授权。

## 2026-07-19 离线实现分配与边界

- Main control-plane base：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。worktree：
  `/Users/hua/Documents/yia-worktrees/task-007`；branch：
  `codex/task-007-local-scoring`；Implementer：Codex；完成后由全新独立 Codex
  Reviewer 审查。
- 仅允许本卡“预计触达文件”列出的 `scoring.py`、`providers/ollama.py`、
  `prompts/scoring.md`、两份测试、`tests/fixtures/scoring/**` 和
  `handoffs/TASK-007.md`。复用 Python 标准库 HTTP/JSON 与既有锁定依赖；不得修改
  `pyproject.toml`、`uv.lock`、Schema/migration、共享 `config.py`/`domain.py`/`state.py`
  或任务状态。
- 所有验证必须离线：允许 Fake transport/本地测试替身，不得请求实际 `127.0.0.1:11434`
  或任何外部地址。若环境缺少已锁定包，只允许 `uv sync --locked --offline`；它失败时停止，
  不得联网补包。
- 继续禁止：Ollama 安装或启动、`qwen3:8b` 拉取、真实模型/服务调用、cloud tag、模型
  下载、媒体/YouTube、Cookie/登录、remote components、ffmpeg、真实 Vault/密钥或文件
  删除。真实文本冒烟属于后续单独授权。

## 实现证据与独立审查授权

- Source：`codex/task-007-local-scoring@258358fcd5227e144c9294beafdf7ec6e2feea63`；
  唯一父提交为共同 base `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`，worktree 已干净。
- base...source 精确包含本卡允许的 7 个路径组、共 11 个文件：`scoring.py`、
  `providers/ollama.py`、`prompts/scoring.md`、两份测试、5 个评分夹具和 handoff。
  `pyproject.toml` 与 `uv.lock` 无差异，`git diff --check` 通过。
- Implementer 自报评分单测 `4`、Fake Ollama 集成 `6`、全量 `261`、mypy、Ruff、CLI、
  离线 sync/build 和 migration packaging 全部通过；这些只构成待复跑证据，不构成验收。
- Reviewer：必须为全新独立 Codex 会话，仅可在 source worktree 的
  `handoffs/TASK-007.md` 追加审查并创建一个以 `258358f...` 为唯一父提交的 evidence
  commit。不得改业务代码、测试、依赖、锁文件、任务状态或 main；审查包由动态 main
  commit 解析。不得读取、检查或操作 TASK-006 worktree。

## 目标

使用可配置的 Ollama Provider 对元数据和规范文本做本地价值评分，严格解析结构化结果，并由应用策略决定是否进入深度分析。

## 范围

- 实现评分输入采样、Prompt 版本、Provider 调用、Schema 校验和一次格式修复。
- 记录总分、理由、主题、建议值、应用阈值结果和不一致诊断。
- 建立输入/模型/Prompt/Schema 版本感知的评分缓存。

## 范围外

- 不调用云端模型。
- 不写 Obsidian 或周报。
- 不把模型输出直接当可信对象或让模型绕过配置阈值。
- 不自动安装/启动 Ollama、不自动拉取模型、不访问 cloud tag 或远程地址。

## 验收标准

- [ ] 固定响应覆盖合法评分、越界分数、缺字段、非法 JSON、修复成功和修复失败。
- [ ] 字幕采样覆盖开头/正文/结尾且受长度限制；同一规范输入重复评分命中缓存。
- [ ] `should_summarize` 的最终值由批准阈值策略决定，模型建议冲突会被记录。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_scoring.py`
- [ ] `uv run python -m pytest tests/integration/test_ollama_provider.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build`
- [ ] `git diff --check`
- [ ] 可选本地冒烟：对一个固定文本运行已批准模型，记录模型名、版本、耗时和结构化结果，不记录全文。

## 预计触达文件

- `src/youtube_intel/scoring.py`
- `src/youtube_intel/providers/ollama.py`
- `prompts/scoring.md`
- `tests/unit/test_scoring.py`
- `tests/integration/test_ollama_provider.py`
- `tests/fixtures/scoring/**`
- `handoffs/TASK-007.md`

本任务使用 Python 标准库 HTTP，不新增 `httpx`/Ollama SDK，不修改
`pyproject.toml`/`uv.lock`。共享 `config.py`、`domain.py`、`state.py`、示例配置和
既有契约/状态测试必须由 TASK-005A 先行完成。

## 交付证据

- 测试和可选冒烟结果。
- Prompt/Schema 版本示例。
- 黄金样例人工评分偏差说明。
- Ollama 版本、模型 tag/digest/许可证、Fake HTTP、安全读取和 no-cloud 边界证据。

## 第一轮独立审查拒绝与 Correction 1

- 第一轮审查证据：`266c488c17fc82cb648053b5e1066211a7bea9a9`；唯一父提交为原实现
  `258358fcd5227e144c9294beafdf7ec6e2feea63`，且仅修改 `handoffs/TASK-007.md`。
- Verdict：`REJECT`；P0=0、P1=2、P2=0、P3=0。审查已独立复跑 lock/sync、评分测试、全量
  测试、mypy、Ruff、CLI、离线构建、迁移包内容和完整 Diff；真实 Ollama/模型/媒体/Vault
  路径均未运行。
- P1-1：`providers/ollama.py` 的异常边界会让修复响应正文经 cause/context/traceback 可达；
  `http.client.IncompleteRead`、缺失/超长 `response` 等路径也可能以私有异常逃逸，而非返回
  具名、脱敏、含请求视频身份的应用错误。
- P1-2：`scoring.py` 仅有进程内缓存，未把 `SCORING_RAW`、`SCORING_STRUCTURED`、Provider
  Call、`ScoringSummaryWrite`、Pipeline CAS 与 Job 成功放在已有 `complete_stage` 的同一
  SQLite 事务中，因此成功评分既不可持久恢复也不能保证状态真实。

### Correction 1 的冻结边界

- 起点必须是上述 review evidence；Correction commit 必须以它为唯一父提交。只允许修改：
  `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、
  `tests/unit/test_scoring.py`、`tests/integration/test_ollama_provider.py`、必要的
  `tests/fixtures/scoring/**` 和 `handoffs/TASK-007.md`。
- 必须复用已有 SQLite Repository/`ProviderCallRequest`、`ProviderCallCompletion`、
  `ArtifactWrite`、`ScoringSummaryWrite` 与 `complete_stage`；不得修改或绕过
  `state.py`、Schema/migration、`domain.py`、配置、依赖或锁文件，也不得重写现有公共
  Provider 契约。
- 成功路径必须在一个 `TRANSCRIPT_READY -> SCORED` 事务中持久化原始响应
  (`SCORING_RAW`/`RAW_RESPONSE_30D`)、结构化结果
  (`SCORING_STRUCTURED`/`LONG_LIVED`)、成功 Provider Call、最终评分摘要、Pipeline CAS
  和 Job 成功；注入任一后写失败必须全部回滚。相同已验证输入必须复用持久结果，改变
  输入/模型/Prompt/Schema/operation 必须未命中。
- 所有公开评分调用的异常边界必须抑制未受信任正文、URL、Prompt、字幕及本机绝对路径在
  `message`、`__cause__`、`__context__` 或 traceback 中泄漏；短读必须映射为
  `TRANSIENT_NETWORK`，畸形/超限响应映射为安全 `INVALID_RESPONSE`，且只允许一次修复调用。
- 继续只使用 Fake transport 与临时 SQLite；禁止真实 Ollama/网络、安装或启动服务、模型
  拉取、媒体/YouTube、Cookie、ffmpeg、Vault/凭据和文件删除。Correction 完成后必须再次由
  全新独立 Codex Reviewer 审查，Implementer 不得自行改变任务状态、合并或启动 Reviewer。

### Correction 1 实现证据与第二次独立审查

- Correction source：`f46881bc4a8ca0fda4d5ef7006b372bc566cff97`，唯一父提交为第一轮
  review evidence `266c488c17fc82cb648053b5e1066211a7bea9a9`；source worktree 干净。
- Correction 精确修改 `src/youtube_intel/scoring.py`、`src/youtube_intel/providers/ollama.py`、
  `tests/unit/test_scoring.py`、`tests/integration/test_ollama_provider.py` 和
  `handoffs/TASK-007.md`。相对共同 base 的完整产品范围仍为原批准的 11 个文件；
  `pyproject.toml`、`uv.lock` 无差异。
- Implementer 自报完整异常图脱敏、`IncompleteRead`/畸形/超限安全映射、一次 repair、
  repository-backed `SCORING_RAW`/`SCORING_STRUCTURED`、Provider Call、评分摘要、
  `complete_stage` 原子完成、已验证持久缓存和 injected rollback 已有离线回归；它只构成待复跑
  证据，不构成 `APPROVE` 或验收。
- 第二次 Reviewer 必须是全新独立 Codex 会话，只能在 source handoff 写入并创建以
  `f46881bc...` 为唯一父提交的 evidence commit；禁止改业务代码、测试、依赖、锁文件、任务
  状态或 main，也不得访问 TASK-006 worktree。
