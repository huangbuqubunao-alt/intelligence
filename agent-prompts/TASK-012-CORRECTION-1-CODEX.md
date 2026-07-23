# TASK-012 Correction 1 — Codex Implementer

你是原 TASK-012 Codex Implementer。只修复独立审查发现的 ADR-011 O-02 doctor 零副作用 P1；不得重构、合并、推送、修改任务状态或接触任何真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-012-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 控制面提交，且 main 中 TASK-012=`IN_PROGRESS`。
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-012` / `codex/task-012-cli-operations`。
- 起始 source HEAD：`9b5dec5d24e87ab942dff4268f7a95c35947d411`，唯一父为 implementation `7c83283eac83b01c88a7625b4a216790d14514b2`；worktree 必须干净。
- 分配 base：`8e322f362d2ff0972ee987b7c06c8453a9dce73d`；source 卡/状态为冻结快照，不得修改。

## 唯一允许修改

- `src/youtube_intel/cli.py`
- `src/youtube_intel/logging.py`
- `tests/integration/test_operations.py`
- `handoffs/TASK-012.md`

禁止 `__main__.py`、`pyproject.toml`、package resources、plist、operations 文档、依赖/锁、Schema/migration、state/domain/config、Provider、公共命令集、TASK-013/014 或 main 变更。不要在 source 运行会写 `.codebase-memory/` 的索引动作。

## P1 与完成标准

修复 `doctor` 路径：可以在内存产生 UUID4 `run_id` 与安全报告，但不得初始化或调用任何会创建/打开/写入 JSONL 或 `logs_dir` 的 logger。即使 `logs/` 和 Vault 路径不存在，也不得创建它们；不得创建 Job、调用 Provider/loopback/网络、读取密钥值或 Vault 内容。诊断只能在 pytest 临时 SQLite/项目路径中只读检查配置、SQLite/migration、Vault 路径边界和启用 Provider 配置。

新增回归：临时项目中 `logs/`、Vault 均不存在时，调用 doctor 后仍不存在；Fake Provider、credential resolver、Job/Repository 写入均为零。保留 O-01 的 in-memory run_id、其他命令 JSONL 安全化/退出码、静态 plist、archive 和零真实资源边界。

若现有冻结命令契约无法同时满足 O-01 与 O-02，停止并报告 `DECISION NEEDED`；不得自行扩大范围。

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
- `uv build --offline`，核验 sdist/wheel migration 和 root/package resource hashes
- `git diff --check 8e322f362d2ff0972ee987b7c06c8453a9dce73d...HEAD`

完成后追加 handoff，创建单父提交（父必须是 `9b5dec5...`），记录零副作用证据、复用、测试、风险和未授权路径；不得启动 Reviewer 或改状态。
