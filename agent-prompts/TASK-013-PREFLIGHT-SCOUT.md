# TASK-013 — Read-only acceptance preflight Scout

你是全新的 Codex Read-only Scout。你的目标是把 TASK-013 的端到端验收转化为一份面向产品负责人的“验收覆盖与授权缺口”报告：说明哪些用户价值可用离线固定夹具证明、哪些情形仍需要明确授权。不得修改仓库、创建 worktree/branch、运行测试或访问真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-PREFLIGHT-SCOUT.md` 必须解析为本 preflight 控制面提交。
- 只在 main `/Users/developer/Documents/youtubek agent` 做只读核验；开始时 main、index 和 identity 必须干净。
- 当前基线 TASK-012 已 `DONE`；TASK-013 仍是 `BLOCKED/UNASSIGNED`。本包不构成实现、依赖、worktree、Reviewer 或真实冒烟授权。

## 必读材料

按 `AGENTS.md` 顺序阅读协作、项目状态、PRD、系统设计、复用登记、TASK-013 卡和本 prompt。重点完整核对 `docs/PRD.md` 第 10 节、TASK-013 的五个固定场景以及现有测试/夹具/恢复证据。代码定位优先使用已有的只读 graph 查询；不得运行会创建 `.codebase-memory/` 工件的索引。

## 只读预检范围

1. **用户可见验收地图**：逐条列出 PRD 第 10 节 1–8 的预期用户价值、现有离线证据、缺失证据和建议验收方式。
2. **五个固定场景**：人工字幕、自动字幕、无字幕/Whisper、低分、高分。判断每个场景能否完全离线、其输出（视频笔记、周报、跳过/失败提示）及重复运行的幂等证据。
3. **故障恢复**：检查字幕、转写、评分、云分析和笔记写入的失败注入与恢复证据；明确尚缺的端到端连接或人工核验。
4. **隐私与边界**：确认离线验收不得读取真实密钥、调用真实 Provider、访问真实 Vault 或用户笔记；提出最小临时目录/固定夹具边界。
5. **最小后续方案**：提出一个不涉及真实资源的实现/验收范围、所需检查和报告结构；另列一个可选、必须由产品负责人另行批准的最小真实冒烟包（若需要）。不要自行决定或授权真实冒烟。
6. **复用与许可证**：只评估已批准的标准库、锁定依赖和既有测试基础设施；记录 DIRECT/ADAPT/REFERENCE/REJECT/DEFER，不新增候选依赖。

## 绝对禁止

- 不运行 `uv`、`pytest`、`mypy`、`ruff`、build、imports、数据库、网络、模型、token-count、真实或临时 Vault 文件 I/O、媒体、ffmpeg、launchctl、密钥/凭据命令。
- 不读取、修改、等待或清理任何 source worktree；不创建任务、ADR、prompt、夹具、验收报告或提交。
- 不把“当前已有单元/集成测试”表述为端到端验收已经通过；必须区分已证实、待连接验证和需授权的真实验证。

## 回传格式

```text
Preflight: TASK-013
Observed main: <SHA>
Git state: clean | BLOCKED
Product acceptance map: <PRD 10.1–10.8 table or concise mapping>
Offline five-scenario readiness: <ready / partial / missing, with user-visible outcome>
Failure and recovery readiness: <covered / missing>
Privacy/resource boundary: <what stays offline; each separate approval needed>
Recommended offline acceptance scope: <exact paths, checks, report contents>
Optional real-smoke package: <minimal scenarios and explicit authorization required | not recommended>
Reuse/license: <DIRECT/ADAPT/REFERENCE/REJECT/DEFER>
Recommended next control-plane action: <ADR/assignment proposal / no action>
Commands run: read-only Git/document/graph only
Decision needed: <explicit product decisions, or None>
```
