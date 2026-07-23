# TASK-012 — Codex Implementer

你是 TASK-012 的唯一 Codex Implementer。实现 ADR-011 的离线 CLI、结构化日志与静态 launchd 样例；只修改固定范围，不合并、推送、改 main 任务状态或访问真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-012-IMPLEMENTER-CODEX.md` 必须解析为本分配控制面提交，且 main 中 TASK-012=`IN_PROGRESS`、Assignee=`Codex`。
- Worktree/branch/base：`/Users/hua/Documents/yia-worktrees/task-012` /
  `codex/task-012-cli-operations` / `8e322f362d2ff0972ee987b7c06c8453a9dce73d`；worktree 必须干净。
- Source 卡/状态为分配 base 冻结快照；不得写回 source 任务卡。TASK-011 已整合，`weekly` 可调用其既有服务。

## 唯一允许修改

- `src/youtube_intel/__main__.py`
- `src/youtube_intel/cli.py`
- `src/youtube_intel/logging.py`
- `pyproject.toml`（仅 package-data / sdist/wheel 包含配置）
- `config/launchd/com.yia.agent.daily.plist.example`
- `config/launchd/com.yia.agent.weekly.plist.example`
- `docs/operations.md`
- `tests/integration/test_operations.py`
- `handoffs/TASK-012.md`

`pyproject.toml` 只允许最小 package-data / sdist/wheel 包含配置，让两个 plist examples 与 `docs/operations.md` 进入两个归档；不得改 `[project].dependencies`、任何依赖版本、build backend、工具链或 `uv.lock`。仍禁止 Schema/migration、state、domain/config、Provider、模板、任务状态、真实 Vault/用户内容、网络、模型、凭据、`launchctl` 或任何测试目录外文件写入。不得运行会创建 `.codebase-memory/` 的索引动作。

## 目标与完成标准

- 以 `argparse` 提供 `check`、`process`、`retry`、`weekly`、`doctor`，参数、帮助与退出码严格遵守 ADR-011 O-01：成功 `0`、已执行项目失败/部分失败 `1`、用法/配置/前置条件 `2`、本地资源/持久化不可用 `3`；不得将部分失败伪装成功。
- 每个命令生成 UUID4 `run_id`；JSONL 必填 `timestamp`、`level`、`event`、`run_id`、`stage`、`safe_message`，可选 `video_id`、`job_id`、`error_code`、`duration_ms`。所有异常/配置值都安全化，绝不记录密钥、字幕、原始模型响应、绝对路径、用户笔记或 traceback。
- `doctor` 只验证配置结构、项目内路径、SQLite 可打开/迁移一致性、Vault 路径边界和启用 Provider 配置；零 Job、零处理、零 Provider/loopback/网络调用、零密钥值读取、零 Vault 内容读取。可在 pytest 临时数据库/目录验证。
- 只提供 daily 与 weekly 的静态 plist 样例及安装/卸载说明：明确占位符、互斥选择、WorkingDirectory、stdout/stderr 日志重定向、禁止自动改写/安装。仅运行 `plutil -lint`，绝不调用 `launchctl`。
- 日志只记录 30 天保留策略，不自动删除日志或其他文件。

## 复用与离线边界

- `DIRECT`：Python 标准库 `argparse`、`json`、`logging`、`uuid`、`datetime`、`pathlib`、`sqlite3`；不得新加 CLI/调度/日志依赖。
- 测试只能使用 pytest 临时 SQLite、临时日志目录和最小 fake service；不得访问真实 Vault、用户笔记、网络、Provider、模型、凭据、外部文件或 launchd 服务。

## 强制验证

- `uv lock --check`
- `uv sync --locked`
- `uv run python -m pytest tests/integration/test_operations.py`
- `uv run python -m pytest`
- `uv run mypy src`
- `uv run ruff check .`
- `uv run python -m youtube_intel --help`
- `plutil -lint config/launchd/com.yia.agent.daily.plist.example`
- `plutil -lint config/launchd/com.yia.agent.weekly.plist.example`
- `uv build --offline`，核验 sdist/wheel 含 migration SQL、两个 plist examples 与 `docs/operations.md`
- `git diff --check 8e322f362d2ff0972ee987b7c06c8453a9dce73d...HEAD`

先保留现有未提交实现，仅补最小 `pyproject.toml` 配置并验证归档内容；不得重置、清理或拆分当前实现。完成后追加 handoff，创建单父提交（父必须为 `8e322f362d2ff0972ee987b7c06c8453a9dce73d`），记录命令/退出码、JSONL 脱敏、doctor 零副作用、plist 静态证据、归档包含性、复用、测试与未授权路径；不得启动 Reviewer 或改状态。
