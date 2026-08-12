# TASK-016A：Intelligence Mode、配置与 Knowledge V2 契约基础

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Base: assignment prompt 动态冻结
- Branch: `codex/task-016a-intelligence-contract-foundation`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016a-intelligence-contract-foundation`
- Dependencies: ADR-023 `Accepted`、TASK-015 `DONE`
- Reuse decision: `DIRECT` — Pydantic、现有 Config/Domain 契约和 Provider-neutral
  Protocol；不新增依赖，不修改 Schema。
- Implementation: `codex/task-016a-intelligence-contract-foundation@210dd203e722eabf3453808f490f4afe52139183`
- Review 1 evidence: `6a564b18a3c91e4366c1b744733910dc5584854b` — `REJECT`，P1：Evidence 时间戳接受非有限值并在 JSON 序列化时破坏成对契约。
- Correction 1: `26a74cd508b28c9fd89e86af741414c8653f2721` — 非有限时间值 fail-closed，等待 Reviewer 2。
- Review 2 evidence: `2ea00258ec2b1843e268d4ed1ffef03bd6b0347d` — `REJECT`，P1：模型侧 Content 可自建 Evidence Registry，违反应用拥有的可信证据边界。

## 用户价值

先建立一个稳定的“分析结果语言”，使后续本地和云端模型输出完全可互换，并让模式、
语言、模型与版本成为可验证的产品配置，而不是散落在各服务中的隐含开关。

## 实现范围

仅允许：

- `config/settings.example.yaml`
- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `handoffs/TASK-016A.md`

## 完成标准

- 新增 `local-only | hybrid | cloud` 严格模式配置，安全默认不自动启用 Cloud。
- 新增独立 `local_analysis` 配置；未显式设置模型时可继承 scoring 配置，但解析后的
  model/digest 必须可作为后续 cache identity。
- 冻结 Provider-neutral `KnowledgeResult V2`、Evidence Registry reference、可信
  provenance 与 `WeeklyKnowledgeResult V2` 领域契约。
- 用户可见字段允许“无可靠机会”的空语义，但 summary、why-it-matters、core points
  和 Evidence 交叉引用必须 fail-closed。
- 配置与领域对象继续禁止 unchecked `model_copy(update=...)` 绕过校验。
- 旧 `cloud.enabled` 兼容映射明确、无歧义且不会自动扩大数据外发。

## 明确不做

- 不实现 Provider、Router、Prompt、Artifact 写入、Note/Weekly 模板或 Runtime wiring。
- 不调用 Ollama/OpenAI，不读取 Key，不访问网络或真实 Vault。
- 不修改 `pyproject.toml`、`uv.lock`、migration、state、CLI 或现有业务行为。
- 不启动 TASK-016B–H。

## 必须验证

```bash
uv lock --check
uv sync --locked --offline
uv run pytest tests/unit/test_contracts.py -q
uv run mypy src/youtube_intel/config.py src/youtube_intel/domain.py
uv run ruff check config/settings.example.yaml src/youtube_intel/config.py src/youtube_intel/domain.py tests/unit/test_contracts.py
uv run pytest -x -q
uv build --offline
git diff --check <BASE>...HEAD
```

实现结束只提交本任务 source，并建议进入 `IN_REVIEW`；不得修改任务状态或自行分配下一
任务。
