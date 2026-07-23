# TASK-011 / TASK-012 — Read-only Scout

你是全新的 Codex Read-only Scout。只评估 TASK-011 周报与 TASK-012 CLI/调度/日志的实施前提和 ADR 缺口；不得修改、暂存、提交、创建 worktree/branch、安装依赖、运行产品命令或访问真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-011-012-PREFLIGHT-SCOUT.md` 必须解析为本 preflight 控制面提交。
- 仅在 main `/Users/hua/Documents/youtubek agent` 做只读核验。当前 baseline、identity、工作树和 index 都必须干净。
- TASK-010 已 `DONE`；TASK-011/TASK-012 仍是 `BLOCKED/UNASSIGNED`。不得把它们设为 READY/IN_PROGRESS，也不得创建 source worktree。

## 必读材料

按仓库 `AGENTS.md` 顺序读取协作、状态、PRD、System Design、Reuse Register、TASK-011/TASK-012 卡和本 prompt。再只读定位现有 Repository、Artifact、KnowledgeSink、CLI 和模板接口；优先用已配置的 codebase-memory graph，只读查询。不得运行会写 `.codebase-memory/` 工件的 index 操作。

## 只读预检范围

### TASK-011 周报

报告以下决策缺口：ISO 周/时区/跨年/空周/并列排序定义；数据来源、周报唯一键与可重复 upsert；趋势/关键词只能复用既有 Analysis 还是需要新增策略；模板/双链与临时 pytest Vault I/O 的最小安全边界；无新依赖或 Schema 的可行性、建议文件范围、离线门禁、复用/许可证决策。

### TASK-012 CLI、调度与日志

报告以下决策缺口：`check`、`process`、`retry`、`weekly`、`doctor` 的参数/退出码/失败层级与零昂贵副作用；`run_id`、结构化日志脱敏/保留边界；launchd 模板、静态 `plutil -lint`、安装说明边界；无新依赖或 Schema 的可行性、建议文件范围、离线门禁、复用/许可证决策。

## 绝对禁止

- 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、真实 OpenAI/Ollama/Whisper、token-count、Vault、用户笔记、媒体、ffmpeg、`launchctl`、密钥或凭据命令。
- 不读取、修改、等待或清理任何 source worktree；不创建任务、ADR 或 prompt 文件。

## 回传格式

```text
Preflight: TASK-011 / TASK-012
Observed main: <SHA>
Git state: clean | BLOCKED
TASK-011: <required ADR/approvals, recommended scope, exact resource boundary>
TASK-012: <required ADR/approvals, recommended scope, exact resource boundary>
Reuse/license: <DIRECT/ADAPT/REFERENCE/REJECT>
Recommended next control-plane action: <ADR proposal sync / no action>
Commands run: read-only Git/document/graph only
Decision needed: <explicit product decisions>
```
