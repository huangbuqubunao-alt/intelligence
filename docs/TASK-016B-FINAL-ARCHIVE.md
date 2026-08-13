# TASK-016B Final Archive

## 1. Final Status

`TASK-016B — Scoring Output Language Contract`

**ACCEPTED WITH SCOPE BOUNDARY**

本归档记录 TASK-016B 已验收并整合的最终事实，不修改任务实现，也不构成 TASK-016C、
Cloud、Router、Weekly、公开分发或正式上线授权。

## 2. Merge Record

- Merge commit：`5272359144bd8c4f7d8680da201840f267239fac`
- Accepted source：`3e7564fbf69fa9b89699f60ce717a1cadafb8b19`
- Accepted code baseline：`08fbae17086c74757b5cf98bf8ad76613872a32c`
- First parent：`60551f2b8606e50ed8e4bd8d161ac5636a8a9266`
- Second parent：`3e7564fbf69fa9b89699f60ce717a1cadafb8b19`
- Merge method：`git merge --no-ff codex/task-016b-scoring-output-language`
- Conflict：none

Accepted source 包含代码基线、[ADR-024](decisions/ADR-024-scoring-language-validator-scope.md)
与完整 [TASK-016B handoff](../handoffs/TASK-016B.md)。完整开发历史被保留，未 squash、
rebase 或 cherry-pick。

## 3. Scope Boundary

Language Validator 负责：

- Unicode script mismatch detection；
- 保守的 natural-language structure validation；
- parser 缺失、失败或证据不足时 fail-closed；
- `INVALID` / `UNCERTAIN` 不能进入可信 `ScoreResult`、正式 scoring Artifact 或当前
  cache。

Language Validator 不负责：

- brand/entity recognition；
- company/product identification；
- entity truthfulness；
- entity stuffing detection；
- 一般内容质量或事实性判断。

该边界来自已证实的不可判定性：在单次 `casefold()` spaCy parse、无词汇实体知识的
约束下，`General Dynamics Corporation` 与 `useful AI models` 可产生同构的
`ADJ/amod + NOUN/compound -> NOUN/dobj` 结构。禁止品牌/实体词典、外部知识和语义模型
时，Language Validator 无法可靠地区分二者。

## 4. P1 Closure

### P1-1 — Language Validator scope

**CLOSED BY ACCEPTED SCOPE BOUNDARY.**

语言门禁继续检测 script mismatch、可信自然语言结构和不确定状态；品牌/entity-only
识别明确不属于 TASK-016B。不得把此 closure 表述为已解决所有 entity-only 或 entity
stuffing 风险。

### P1-2 — ScoreResult contract

**VERIFIED.**

`output_language` 是可信 domain invariant。进入 Runtime、Artifact 或 Cache 前必须
通过 schema validation 与语言 invariant；unchecked copy/construct 结果不能绕过可信
验证入口。

### P1-3 — Cache provenance

**VERIFIED.**

Repository-backed scoring cache recovery 校验 `request_hash`、provider、model、
`output_language`、`prompt_version` 与 `schema_version`。provenance mismatch 作为
cache miss 处理并重新计算，旧 Artifact 保留审计但不得冒充当前结果。

## 5. Dependency Record

- `spacy==3.8.15`
- `en_core_web_sm==3.8.0`
- 仅加载已安装的固定本地包；不得自动下载、调用 `spacy.cli.download`、使用网络
  fallback 或用户提供的远程模型地址。
- 模型缺失或加载失败统一产生 `UNCERTAIN`，保持 fail-closed。
- Local-only SBOM 与 NOTICE inventory 已完成：
  - [SBOM](SBOM.md)
  - [Third-Party NOTICE Inventory](THIRD_PARTY_NOTICES.md)

公开分发仍未获批准：模型来源归属、WordNet/OntoNotes 义务、发行包许可证文本装载与
release-owner sign-off 仍按 SBOM/NOTICE 中的发布门禁处理。

## 6. Validation Evidence

最终代码基线 `08fbae1…` 的 Round 15 已提交门禁证据：

| Gate | Result |
|---|---|
| Focused Domain/Ollama pytest | `169 passed` |
| Full pytest | `853 passed` |
| mypy | PASS，`27 source files` |
| Ruff | PASS |
| `uv lock --check` | PASS，`107 packages` |
| `uv sync --locked --offline` | PASS，`107 resolved / 84 checked`，无下载 |
| `uv build --offline` | PASS，sdist 与 wheel 成功 |
| `git diff --check` | PASS |

最近一次已提交的安全扫描证据来自 Round 13：

- `bash scripts/security_scan.sh`：`status=clean`；仅有既有非阻断 WARN。

Round 14/15 及 Scope Decision 没有新增依赖、配置、Cloud、Router、Weekly、Schema 或
migration 变更。Merge execution 仅执行 Git 整合与父链/洁净度检查，没有把未重跑的
产品门禁表述为合并后新证据。

## 7. Next Task Boundary

Content Quality、brand/entity quality、company/product recognition 与 entity stuffing
必须作为未来独立任务处理。该任务需要单独定义：

- 可使用的证据来源与依赖；
- 隐私、离线和许可证边界；
- 误报/漏报策略；
- `ScoreResult`、Artifact 与 Cache 的交互边界；
- 独立实现、Review、Acceptance 与 Integration 门禁。

本归档不创建或启动该任务，也不启动 TASK-016C。
