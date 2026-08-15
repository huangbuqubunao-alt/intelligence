# TASK-016C Phase E — Trusted Scoring Finalizer

## 状态

`READY / AUTHORIZED`。本任务的 implementation source 必须从
`codex/task-016c-phase-e-finalizer@<Phase-E-control-plane-commit>` 开始，且该提交必须是
Phase D `2c11faf41e17c3b823a39bfd1018c5c876b236c5` 的 descendant。

## 目标

在无 I/O 的纯内存边界实现 canonical scoring identity、runtime-owned
`TrustedScoringContext`、Finalizer-only `TrustedScoreResult` 与 `TrustedScoringFinalizer`。所有输入在
Finalizer 重新验证；任一 mismatch fail-closed。

## 允许范围

- `src/youtube_intel/scoring.py`：仅抽取复用现有 canonicalization 的
  `build_scoring_request_identity()`；既有 `build_scoring_input()` 与 `_provider_request()` 必须共同使用它，
  request hash 不得变化；
- `src/youtube_intel/quality.py`：opaque capability、wrapper 与 Finalizer；
- `src/youtube_intel/runtime.py`：从已验证 `AppConfig` 的 composition point 私有铸造/保存 context；
- `src/youtube_intel/domain.py`：仅为 Finalizer 输入重建与公开业务字段兼容所需的最小契约；
- `tests/unit/test_task016c_finalizer.py`、`tests/unit/test_scoring.py`、
  `tests/integration/test_runtime_composition.py`（及确有必要的现有 TASK-016C 测试）；
- `handoffs/TASK-016C.md`。

## 不可协商边界

- 不修改 `providers/ollama.py`、`state.py`、DB、migration、Artifact、cache、ProviderCall persistence、
  filesystem protocol、primary/repair orchestration、Judge budget 或 Phase F–K；
- 不改 TASK-016B Language Validator、依赖、`pyproject.toml` 或 `uv.lock`；
- 不调用网络、真实 Ollama、模型下载、cloud、真实 Vault 或凭据；
- `QualityProvenanceAuthority` / `QualityPassAttestation` 的 Phase D 语义不改；
- Finalizer 前后均不得创建 Artifact、cache entry、ProviderCall SUCCESS、response artifact ID 或文件。

## TDD 验收

1. RED：identity extraction 与现有 hash bit-for-bit 等值；模型、prompt/schema、temperature、
   max output tokens、max description chars、normalized input 任一改动改变或拒绝 identity；
2. RED：Mapping/JSON/subclass/proxy/copy/deepcopy/pickle 不能伪造 `TrustedScoringContext`；
   `RuntimeOperations` 是唯一合法 minting path；
3. RED：裸 `ScoreResult` 的 constructor/model_validate/model_construct/JSON restore 不能进入 trusted
   pipeline；只有 Finalizer 返回 `TrustedScoreResult`；
4. RED：候选、input、quality result、operation、attestation、authority 或 context 任一篡改均拒绝；
5. GREEN：合法 PASS 经过真实 revalidation chain 产出 wrapper，且业务字段与 candidate 保持兼容；
6. 证明 Finalizer 无 DB/cache/Artifact/ProviderCall/filesystem/network side effect。

## 必须门禁

`uv lock --check --offline`、`uv sync --locked --offline`、focused tests、`uv run pytest -x -q`、
`uv run mypy src`、`uv run ruff check .`、`uv build --offline`、`git diff --check`。

## 提交与审查

先记录可复现 RED，再以一个 implementation commit 完成最小 GREEN。提交不得 squash/rebase/amend，
不得合并到 main。完成后只追加 handoff，停止，等待新会话/不同实现者的独立 Reviewer。

Reuse decision：`DIRECT` — 复用现有 Pydantic revalidation、canonical JSON/SHA-256、
`build_provider_request_hash` 与 Phase D authority primitive；不新增依赖。
