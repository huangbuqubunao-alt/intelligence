# TASK-012：CLI、调度与日志

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: Medium
- Depends on: TASK-010
- Approval required: 加载/注册真实 launchd 服务前需用户明确授权

## 目标

提供稳定的手动运行、诊断、恢复和周报命令，生成可检索的结构化日志，并提供不会静默安装的 launchd 样例。

## 范围

- 实现 System Design 约定的 `check`、`process`、`retry`、`weekly`、`doctor` 命令语义和退出码。
- 为每次运行生成 `run_id`，日志包含阶段、视频、Job、耗时、错误码和安全化消息。
- 提供 launchd plist 模板、安装/卸载说明和路径占位符校验；不自动加载。

## 范围外

- 不开发 GUI 或 Web 管理页。
- 不在初始化时自动调用 `launchctl`。
- 不把字幕全文、模型原始响应或密钥写日志。

## 验收标准

- [ ] 每个命令有帮助文本、参数校验和确定退出码；错误配置在领取任务前失败。
- [ ] `doctor` 可检查配置、目录、SQLite、启用 Provider 和 Vault 边界，但不会执行昂贵处理或泄露密钥。
- [ ] 结构化日志可按 `run_id`/`video_id`/阶段关联；launchd 样例可通过静态校验且不会被测试加载到用户系统。

## 验证

- [ ] `python -m pytest tests/integration/test_operations.py`
- [ ] `python -m youtube_intel --help`
- [ ] `plutil -lint config/launchd/com.yia.agent.plist.example`
- [ ] `mypy src && ruff check .`

## 预计触达文件

- `src/youtube_intel/__main__.py`
- `src/youtube_intel/cli.py`
- `src/youtube_intel/logging.py`
- `config/launchd/com.yia.agent.plist.example`
- `tests/integration/test_operations.py`

## 交付证据

- 命令/退出码矩阵。
- 脱敏日志样例和无全文检查结果。
- 声明未加载真实 launchd 服务；如加载则附用户授权和回滚步骤。

## 2026-07-23 只读预检授权

- TASK-010 已 `DONE`，但本任务仍为 `BLOCKED/UNASSIGNED`。只授权独立 Scout 读取现有文档、CLI/
  Repository 接口和任务卡，冻结命令/退出码、`run_id`/结构化日志脱敏、doctor 零昂贵副作用、launchd
  样例静态校验和精确实施范围。
- 不创建 worktree、不运行产品命令、不修改代码/状态，不授权 `launchctl`、真实服务注册、网络、云端、
  凭据、Vault、用户内容、媒体或模型路径。预检结论须先形成 ADR 提案并由产品负责人批准。

## 2026-07-23 ADR-011 已接受

- 产品负责人已批准确定退出码、零副作用 doctor、UUID4 run_id/JSONL 脱敏、不自动日志删除，以及
  可选 daily/weekly 静态 launchd 示例；不得执行 `launchctl`。
- `weekly` CLI 依赖 TASK-011 已整合的周报服务，因此本任务保持 `BLOCKED`。后续正式范围可包括
  `__main__.py`、`cli.py`、`logging.py`、两个 static plist examples、安装说明、operations tests 与 handoff；
  仍禁止依赖/Schema/真实服务、网络、Vault、用户内容或凭据操作。
