# TASK-016A Implementer — Intelligence Contract Foundation

任务状态：`IN_PROGRESS / Codex`。本包只授权 TASK-016A，不授权连续启动后续任务。

完整读取并严格执行：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md`
5. `docs/SYSTEM_DESIGN.md`
6. `docs/REUSE_REGISTER.md`
7. `docs/decisions/ADR-023-local-hybrid-cloud-intelligence.md`
8. `tasks/TASK-016-intelligence-output.md`
9. `tasks/TASK-016A-intelligence-contract-foundation.md`

## 动态授权对象

本 prompt 最近一次控制面提交即为授权提交：

```bash
AUTH=$(git -C '/Users/hua/Documents/youtubek agent' log -1 --format=%H -- \
  agent-prompts/TASK-016A-INTELLIGENCE-CONTRACT-FOUNDATION-IMPLEMENTER-CODEX.md)
```

开始时必须确认 source HEAD 等于 `$AUTH`、分支为
`codex/task-016a-intelligence-contract-foundation`、worktree 为
`/Users/hua/Documents/yia-worktrees/task-016a-intelligence-contract-foundation`，且除
明确登记的本地未跟踪项外没有 tracked staged/unstaged 修改。若不一致立即停止。

## 目标

只实现模式、配置与 Provider-neutral Knowledge V2 契约。此任务不提供用户功能，不得
提前实现 Local Provider、Router、Prompt、Renderer、Weekly synthesis 或 Runtime wiring。

## 唯一允许修改路径

- `config/settings.example.yaml`
- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `handoffs/TASK-016A.md`

## 强制边界

- 不新增/升级依赖，不修改 `pyproject.toml`、`uv.lock`。
- 不修改 migration/Schema/state/CLI/runtime/provider/templates。
- 不访问网络、Ollama、模型、OpenAI、Key、真实 Vault 或用户数据。
- 不删除、跳过或弱化测试。
- 先写契约测试，再做最小实现；出现规格冲突输出 `DECISION NEEDED`。
- 只创建一个单父 Implementer commit；不 merge、rebase、push、tag 或分配下一任务。

## 契约重点

- 模式是 `local-only | hybrid | cloud`，新配置安全默认不得自动启用 Cloud。
- `local_analysis` 与 `local_scoring` 可配置不同模型；继承必须解析成可信具体身份。
- Local/Cloud 使用相同 `KnowledgeResult V2`。
- Provider/model/mode/language/prompt/schema/sampling/request hash provenance 由可信应用边界
  注入并进行交叉验证。
- Evidence 只引用已登记 ID；无可靠机会允许空列表，但 summary、why-it-matters、core
  points 与 Evidence 关系必须有效。
- Weekly 使用独立但 Provider-neutral 的 V2 synthesis result。
- 保持现有对象的 update-bypass 防护。

## 检查

严格运行任务卡命令，额外确认最终 Diff 只有五条允许路径、lockfile 无变化、工作树干净。
在 `handoffs/TASK-016A.md` 记录实际契约、Reuse、检查、跳过项和风险，并回报 commit SHA。
