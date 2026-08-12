# TASK-015：正式 Runtime Composition 与 Local-First Smoke

- Status: `DONE`
- Assignee: `Codex Lead Maintainer`
- Base: `main@41ed7ee55afe5f8cb44ca20931c776257d15805f`
- Branch: `codex/task-015-runtime-composition`
- Dependencies: TASK-013 `DONE`、TASK-014 离线能力已整合、ADR-022 `Accepted`
- Reuse decision: `DIRECT` — 既有 SQLite Repository、Pipeline、yt-dlp/RSS、字幕、
  Ollama、cloud policy、Obsidian、weekly、标准库与已锁定依赖；不新增依赖。

## Closure

- Accepted source：`workbuddy/task-015-p1-fix@429bf45daacaaeb5474faca6d27b11616e448aae`
- Merge：`451766f9b1772eed9d36587d7956328ee7c2f7ff`
- Maintainer Review：APPROVE；整合后 675 tests、mypy、Ruff、CLI、安全扫描与备份恢复
  门禁通过。
- Remaining P2 保留为独立后续项，不并入 TASK-016。

## 目标

让未注入测试 `Operations` 的正式 `uv run youtube-intel` 能执行配置、doctor、check、
process、笔记与 weekly，并在缺少真实本地资源时给出明确、安全、可操作的先决条件。

## 完成标准

- 有独立 production composition root；CLI 默认使用它。
- 首次业务命令幂等初始化 DATA/logs/SQLite/受管测试 Vault 子目录。
- doctor 保持只读并输出逐项诊断。
- check 真实持久化频道发现；process 使用现有 Job/Pipeline 和真实服务；weekly 使用持久数据。
- 新增不注入 Fake Operations 的 production composition regression。
- full pytest、mypy、Ruff、安全扫描、备份恢复、offline build、Diff check 通过。
- 仅在 `/Users/hua/Documents/YouTube-Intel-Test-Vault` 做真实 smoke；Cloud=false。
- 大模型下载、真实用户 Vault、凭据或付费服务须另行授权。
- 真实 E2E 未跑通时不得设为 `DONE` 或宣称 `LOCAL PRODUCT DEMO READY`。

## 最大实现范围

- `src/youtube_intel/cli.py`
- `src/youtube_intel/operations.py`
- `src/youtube_intel/runtime.py`
- `src/youtube_intel/discovery.py`
- `src/youtube_intel/state.py`
- 必要的既有 pipeline/transcript/reporting/note application service 最小接口
- 真实 Smoke 证明需要的 yt-dlp/Ollama 边界兼容与安全日志收口
- package 内固定 scoring prompt
- `tests/integration/test_runtime_composition.py`
- 与上述边界相关的最小回归测试
- 本任务 ADR、任务卡、索引、状态与 handoff

禁止依赖/锁文件、Schema/migration、真实 Vault、云端、模型下载和无关重构。
