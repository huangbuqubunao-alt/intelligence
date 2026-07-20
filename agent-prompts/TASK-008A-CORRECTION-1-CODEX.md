# TASK-008A Correction 1 — Codex Implementer

你是 TASK-008A 的原 Codex Implementer。第一轮独立审查已拒绝；你只修复 6 个 P1，
并落实已批准的 ADR-008 A-16/A-17。不得重做已通过的契约/依赖工作，不得实现
Provider、请求构造、采样、缓存、事务或编排，不得扩大功能、重新分配任务或启动
Reviewer。

## 固定状态与启动门禁

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main correction authorization：动态运行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008A-CORRECTION-1-CODEX.md`
- Required authorization parent：`3eac5f9897bdfb59e764afde411e632822dcfb66`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- First review evidence / required source start：
  `0f52c3056379bcfcd9b7bb0805ccdb5dba99a9dd`
- Reviewed implementation：`382251298af7fcbfadba66c1902af6de0a425179`
- Original base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；
  `user.useConfigOnly=true`

开始时 main 必须位于动态 correction authorization、其唯一父为 Required
authorization parent、main 控制面为 `TASK-008A=IN_PROGRESS` 且干净；source 必须
位于 first review evidence、分支正确且干净。source 中历史任务状态是 assignment 前
快照，只以 main 控制面判定当前状态。任一条件不符立即 `BLOCKED`；不得 stash、
reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许的 source 修改

1. `src/youtube_intel/domain.py`
2. `src/youtube_intel/config.py`
3. `config/settings.example.yaml`
4. `tests/unit/test_contracts.py`
5. `pyproject.toml`
6. `uv.lock`
7. `handoffs/TASK-008A.md`
8. `src/youtube_intel/resources/o200k_base.tiktoken`

相对 first review evidence 的 Correction Diff 与相对 original base 的完整产品 Diff
都必须严格受上述 8 路径约束。`uv.lock` 必须与 reviewed implementation 字节一致；
不得新增、删除或升级任何依赖。`pyproject.toml` 只有在 `uv_build` 无法自动包含固定
资源时，才可做最小 package-data 配置；不得修改依赖或工具门禁。未确有必要时，
`pyproject.toml`、settings example 均保持不变。

禁止修改 Provider、`analysis.py`、Prompt、Schema/migration、`state.py`、
`complete_stage`、Repository、CLI、其他测试、任务/ADR/main。除 A-16 的一次精确
BPE GET 外，不得访问网络、API、真实环境变量值/密钥、OpenAI、token-count、
YouTube、Vault、媒体、模型或用户数据。

## A-16 唯一下载授权

唯一允许的联网目标和资源身份：

```text
URL: https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken
Path: src/youtube_intel/resources/o200k_base.tiktoken
SHA-256: 446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d
```

- source 开始时该路径必须不存在；只允许一次无认证 HTTPS GET，不跟随到其他主机，
  不附加 Cookie、header、token 或 query。
- 下载后先用本机 SHA-256 校验；不匹配立即 `BLOCKED`，不得提交、重试其他 URL 或
  使用 tiktoken cache 代替。
- sdist/wheel 必须包含完全相同的资源和哈希；记录大小、来源、哈希和 TASK-014
  文件级许可证待决。
- 本切片不实现正式 token 采样/计数模块。测试可用 `importlib.resources` 与
  tiktoken 的低层本地 loader 证明包内资源可读/可解析，但不得调用
  `tiktoken.get_encoding("o200k_base")` 或任何 HTTP/cache fallback。

下载完成后的所有命令必须离线。若已有依赖 cache 缺失，报告 `BLOCKED`，不得联网补包。

## 六个 P1 的精确修复标准

### P1-1：审计哈希

以下三处只接受正则 `^[0-9a-f]{64}$`：

- `AnalysisInput.transcript_content_hash`
- `AnalysisInput.request_hash`
- `AnalysisResult.request_hash`

覆盖 63/65 字符、大写、非 hex、前后空白和合法边界；不得静默 lowercase/strip，
不得改变其他旧领域对象的兼容行为。

### P1-2：语义非空

TASK-008A 新增契约中所有宣称非空的出站、grounding 和可信元数据字段都必须拒绝
纯空白；保留原值以支持 A-11 精确子串验证，不得以 strip 后文本替换内容。

至少覆盖：

- `AnalysisPayload` 的 `video_id`、`title`、`channel_name`、
  `transcript_language`、`output_language`、`transcript_sample`，以及非 `None`
  的 `default_language`；
- `EvidenceExcerpt.evidence_id`、`excerpt`；
- `AnalysisPoint.text` 和每个 `evidence_ids` item；
- `AnalysisContent.one_sentence_summary` 和每个 keyword；
- `AnalysisResult.provider`、`model`；
- `AnalysisCompleted.call.provider` 和非 `None` 的 `call.model`。

`description=""` 仍是 A-04 合法空描述；不要把它误改为必填。不能借修改全局
`ProviderCallMetadata` 破坏旧任务兼容性；可在 TASK-008A 新对象边界完成验证。

### P1-3：`ConfigError` 完整异常图脱敏

使用真实 secret-shaped YAML 合成哨兵触发 `load_settings` 失败。该值不得存在于：

- 异常文本、`repr`、Pydantic `errors()`；
- `__cause__`、`__context__` 及其递归异常图；
- traceback 对象；
- 任一项目 frame 的 `f_locals`，特别是 `load_settings.raw`；
- pytest failure/traceback 的可观察表示。

不得只做字符串替换后保留原始对象。修复必须在 raise 前释放、替换或隔离原始
mapping，使敏感值不再由异常图强引用；保留字段路径和安全错误分类。

### P1-4：tokenizer 本地只读与失败关闭

- 校验 A-16 固定资源的源文件、package resource、sdist 和 wheel 哈希一致。
- 在空 tiktoken cache、socket/HTTP 被拒绝的进程中，从包内资源使用 expected hash
  完成本地解析；不得发起网络。
- 资源缺失、单字节篡改、错误 hash、解析失败和打包遗漏必须在本地安全失败，且不得
  回退到网络/cache。若当前切片没有正式 tokenizer runtime，测试和冻结契约必须把
  这些条件明确留给 TASK-008，不能伪造 Provider 或计数实现。

### P1-5：OpenAI SDK 隔离导入

- 产品源码和 pytest 主进程均不得直接或间接 `import openai`。
- 依赖/版本验证用 `importlib.metadata`；SDK 导入验证只在全新独立子进程进行。
- 子进程必须通过绝对 `sys.executable`、无 shell 启动；不得复制 `os.environ`。
  `env` 只能是固定字面量：
  `PYTHONNOUSERSITE=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`。
- 用合成的 `OPENAI_*`、`AZURE_*`、代理变量和 `*_TOKEN`/`*_KEY`/`*_SECRET`/
  `*_PASSWORD` 哨兵证明它们不进入子进程；不得读取或打印真实父环境值。
- 子进程只做离线导入和安全元数据回传，不构造 client、不读取密钥、不发请求。
  A-17 的“导入完成后匿名管道传密钥”只在 ADR/契约测试中冻结；本任务不得实现
  Provider 或真实管道协议。

### P1-6：完成结果元数据一致

`AnalysisCompleted` 必须在构造和任何 copy 路径上强制：

- `result.provider == call.provider`
- `result.model == call.model`
- `call.model` 不得为 `None` 或纯空白

提供 provider mismatch、model mismatch、`None`、纯空白和一致正例；错误不得泄漏
payload、字幕、描述、密钥或绝对路径。

## TDD 与回归要求

先在 first review evidence 上以独立测试精确复现 6 组 RED，再做最小实现得到 GREEN。
不得删除、弱化、跳过或改写既有断言来掩盖失败。额外证明：

- `AnalysisPayload.model_dump()` 白名单不扩张；
- 所有新契约继续拒绝 `model_copy(update=...)`；
- Cloud 默认关闭、28k/30k、model/encoding/version 和错误脱敏既有行为不回归；
- 无 Provider、Prompt、SDK main-process import、Schema、state 或网络副作用。

## 必须运行的检查

固定资源下载完成后，以下全部离线：

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 82d1fd7c7f2f82e77df0518e63755bad0bf240f2...HEAD
```

还必须：

- 独立执行 P1-1 至 P1-6 探针并记录 RED/GREEN；
- 检查 `pyproject.toml` 直接依赖仍精确包含已批准范围，`uv.lock` 与 reviewed
  implementation blob 完全相同；
- 检查 sdist/wheel 同时包含 `migrations/001_initial.sql` 和固定 tokenizer 资源，
  解包后重新计算资源 SHA-256；
- 搜索完整产品 Diff，确认没有真实 key、token、用户数据、API 响应、cache、模型、
  媒体或未批准文件；
- 只清理本轮已忽略的 `dist/`；不得清理其他 Agent 文件、branch 或 worktree。

创建一个新的非 merge、非 amend commit，唯一父提交必须为 first review evidence。
只在 handoff 追加 Correction 1 的下载/哈希、六组 RED/GREEN、A-16/A-17 追溯、
检查、范围、复用、许可证待决、跳过项与风险。不得修改任务状态、启动 Reviewer、
merge、push 或清理 worktree。

## 回传格式

```text
Task: TASK-008A
Role: Codex Implementer (Correction 1)
Starting review evidence:
Correction commit:
Changed files:
A-16 resource URL/path/hash/package evidence:
A-17 isolated import evidence:
P1-1 through P1-6 closure evidence:
Checks:
Dependency/lock summary:
Diff review:
Skipped checks:
Remaining risks:
Decision needed:
Post-commit status:
```
