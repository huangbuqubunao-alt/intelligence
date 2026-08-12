# TASK-016A — Intelligence Contract Foundation 独立 Reviewer

你是 TASK-016A 的全新独立 Reviewer。只审查固定 source 的契约实现，不得依赖 Implementer
自报，不得修复、重构或扩大 TASK-016A；Reviewer 唯一允许写入是向 source
`handoffs/TASK-016A.md` 追加审查证据并创建一个 handoff-only commit。

## 固定审查对象

```text
Task: TASK-016A — Intelligence Mode、配置与 Knowledge V2 契约基础
Role: Independent Reviewer
Control-plane baseline: main@36969c5c5f7af75a2cf2255b63f742c12cf4fb0c
Execution main: dynamic single-parent authorization commit containing this prompt and synchronized status documents
Reviewed worktree: /Users/hua/Documents/yia-worktrees/task-016a-intelligence-contract-foundation
Reviewed branch: codex/task-016a-intelligence-contract-foundation
Reviewed implementation HEAD: 210dd203e722eabf3453808f490f4afe52139183
Required sole parent: 36969c5c5f7af75a2cf2255b63f742c12cf4fb0c
Review range: 36969c5c5f7af75a2cf2255b63f742c12cf4fb0c...210dd203e722eabf3453808f490f4afe52139183
Allowed product paths: config/settings.example.yaml; src/youtube_intel/config.py; src/youtube_intel/domain.py; tests/unit/test_contracts.py; handoffs/TASK-016A.md
Reuse: DIRECT — locked Pydantic and existing typed Config/Domain contracts; no dependency or Schema change
```

## Git-only preflight

完整阅读仓库协作资料、ADR-023、TASK-016/TASK-016A、Implementer handoff 与本包。核验
dynamic main 授权链、固定 source branch/HEAD/唯一父、source tracked/untracked 洁净度、
五路径完整范围、`uv.lock`/`pyproject.toml`/migration/state/runtime/provider/templates 未变，
并运行 `git diff --check`。任一身份、范围或洁净度不符，立即停止且不得写 source。

## 独立审查重点

1. 配置严格接受 `local-only | hybrid | cloud`；新安装与旧 Cloud OFF 安全默认 Local-only，
   旧 `cloud.enabled=true` 明确映射 Hybrid，显式冲突 fail-closed，不会静默扩大外发。
2. `local_analysis` 可与 scoring 使用不同模型；继承后 model/base URL/digest 都是具体、经过
   验证的可信身份；Named override 仍重新验证而非绕过。
3. `KnowledgeResult V2` 对 Local/Cloud 完全 Provider-neutral；provider/model/requested/
   executed mode/language/prompt/schema/sampling/privacy/hashes/fallback provenance 交叉验证。
4. summary、why-it-matters、core points 都引用已登记 Evidence ID；无可靠机会的机会/行动
   列表允许为空；Evidence Registry ID 唯一，timestamp 仅在 `timed-subtitle` 可信 basis 下
   成对出现，不允许模型伪造半截或非字幕时间。
5. `WeeklyKnowledgeResult V2` 是独立 Provider-neutral synthesis 契约，结论必须带 video/
   evidence source references，routing/model provenance fail-closed。
6. Config 与新 Knowledge 契约禁止 unchecked `model_copy(update=...)`；旧 Analysis V1、
   Scoring、Weekly V1 与所有现有行为不退化。审查正确性、架构、可读性、安全/隐私和性能。

若静态确认 P0/P1，立即停止后续产品命令，只记录已得证据和 `REJECT`。否则独立运行：

```text
uv lock --check
uv sync --locked --offline
uv run pytest tests/unit/test_contracts.py -q
uv run mypy src/youtube_intel/config.py src/youtube_intel/domain.py
uv run ruff check .
uv run pytest -x -q
uv build --offline
git diff --check 36969c5c5f7af75a2cf2255b63f742c12cf4fb0c...210dd203e722eabf3453808f490f4afe52139183
```

另外用 YAML safe loader 独立核验 example config。任务卡中把 YAML 传给 Ruff 的命令会被
Ruff 当 Python 解析；不得把该工具/文件类型不匹配写成产品缺陷，但必须确认 Python 全仓
Ruff 与 YAML 解析分别通过。不得运行网络、Ollama、OpenAI、Key、真实 Vault 或用户数据。

## 交付

以 P0/P1/P2/P3 记录发现并给出 `APPROVE` 或 `REJECT`。唯一可写 source 路径为
`handoffs/TASK-016A.md`，只可追加 Reviewer evidence；唯一 Reviewer commit 必须以
`210dd203e722eabf3453808f490f4afe52139183` 为唯一父，且 handoff-only。提交前后核验
父链、精确范围、`git diff --check` 与洁净度。禁止 merge、push、source 清理、任务状态
修改或启动 TASK-016B–H。
