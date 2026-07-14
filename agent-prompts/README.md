# Agent Task Packets

本目录存放由主控对话按最新已验收基线生成的角色提示词。

## 原则

- 提示词按任务即时生成，不为未来全部任务一次性预生成。
- 一份任务包绑定：Task ID、角色、Agent、基线 commit、worktree、分支、范围和检查命令。
- 未替换占位符、基线已过期或任务不是 `READY/IN_PROGRESS` 时不得执行。
- Implementer、Reviewer、QA、Integrator 使用不同任务包和不同对话。
- Reviewer 不修改业务代码；修复退回原 Implementer。
- 所有任务包都必须服从根目录 `AGENTS.md`，不能扩大任务权限。

只读 `PREFLIGHT-*.md` 是例外的准备包：可在任务尚未 `READY` 时运行，但只能检查环境、规格、测试方案和风险，在聊天中返回摘要；不得写仓库、安装依赖、创建 commit 或视为任务已开工。

## 文件命名

```text
TASK-001-IMPLEMENTER-CODEX.md
TASK-001-REVIEWER-GROK.md
TASK-013-QA-CODEX.md
TASK-014-INTEGRATOR-GROK.md
PREFLIGHT-TASK-001-READONLY.md
```

Agent 名只表示本轮分配，不表示永久角色。下一张任务可以交换 Codex/Grok 的实现与审查位置。

## 生成时机

1. 主控确认任务依赖已 `DONE`。
2. 主控确认任务级红线审批。
3. 主控记录最新 base commit。
4. 主控选择 Implementer 与不同模型的 Reviewer。
5. 主控从 `agent-prompts/templates/` 生成任务专用文件。
6. Worker 只把该任务专用文件作为开工提示词，不直接使用模板。

## 模板

- `templates/IMPLEMENTER.md`
- `templates/REVIEWER.md`
- `templates/QA.md`
- `templates/INTEGRATOR.md`
- `ORCHESTRATOR-BOOTSTRAP.md`：主控对话轮换时使用。
