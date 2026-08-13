# TASK-016B：Scoring Output Language Contract

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Base: `main@60551f2b8606e50ed8e4bd8d161ac5636a8a9266`
- Branch: `codex/task-016b-scoring-output-language`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016b-scoring-output-language`
- Dependencies: TASK-016A `DONE`、ADR-023 `Accepted`
- Reuse decision: `DIRECT` — 复用 Pydantic、现有 Ollama Adapter、一次 repair、SQLite
  Artifact/ProviderCall 与 Runtime provenance；Round 11 经用户明确批准固定
  `spacy==3.8.15` / `en_core_web_sm==3.8.0` 作为离线英文依存分析器；不修改 Schema。

## 用户价值

让本地快速评分的用户可见理由真正遵守 `general.output_language`：中文配置得到中文
理由，英文配置得到英文理由；切换语言时绝不复用另一语言的评分缓存。

## 完成标准

- `output_language` 进入 `ScoringInput`、Prompt、request identity、`ScoreResult`、
  结构化 Artifact 和 Runtime provenance。
- `zh-CN` 与 `en` request hash 不同，跨语言缓存 fail-closed。
- 明显整段错语种的 reason 触发现有一次 repair；修复后仍错误则不持久化为有效结果。
- 中文理由可包含英文技术名词；机器字段保持英文。
- 旧 Artifact 保留，但缺少语言身份时不能作为当前有效缓存恢复。
- 独立完成离线测试、类型检查、Lint、CLI、build、安全扫描与固定视频本地评分 smoke。

## 明确不做

- 不实现 TASK-016C 或任何 Deep Analysis、Knowledge Provider、Hybrid/Cloud Router、
  Video Note V2、Weekly V2、UI、migration 或 TASK-015 Remaining P2。
- 不调用 Cloud，不读取 Key，不写真实 Vault，不 merge/push/tag/release。
