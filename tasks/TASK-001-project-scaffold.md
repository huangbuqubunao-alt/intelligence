# TASK-001：工程脚手架与质量门禁

- Status: `IN_PROGRESS`
- Assignee: `Codex Implementer`
- Owner role: TL / 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-000
- Approval: `APPROVED` — 2026-07-14 产品负责人任务级授权

## 目标

建立可安装、可运行、可测试的最小 Python 3.12 工程，并把 PRD 约定的测试、Lint 和类型检查命令变成真实门禁。

## 范围

- 使用本机 Python 3.12 和 uv 创建项目元数据、`.python-version` 与 `uv.lock`。
- 建立 `youtube_intel` 包、最小 CLI `--help` 和一个离线 smoke test。
- 使用 `uv_build>=0.11.28,<0.12`；开发依赖只包含 `pytest>=9.1.1,<10`、`ruff>=0.15.21,<0.16`、`mypy>=2.3,<3` 及 uv 解析出的必要传递依赖。
- 配置并验证 pytest、Ruff 和 mypy；忽略构建产物、运行数据、日志、虚拟环境、缓存和本地密钥类文件。

## 范围外

- 不实现频道发现、数据库、字幕、模型或 Obsidian 逻辑。
- 不注册 launchd 服务。
- 不加入任何运行时依赖，不升级 uv，不安装 MLX Whisper 或下载模型。

## 验收标准

- [ ] 使用 Python 3.12 执行 `uv sync --locked` 和 `uv build` 均返回 0，且 `uv run python -m youtube_intel --help` 返回 0。
- [ ] `uv run python -m pytest`、`uv run ruff check .`、`uv run mypy src` 均返回 0，并至少运行一个真实 smoke test。
- [ ] `.gitignore` 覆盖 `data/` 运行产物、`logs/`、虚拟环境、缓存和本地密钥文件，同时不忽略示例配置或迁移文件。

## 验证

- [ ] `uv lock --check`
- [ ] `uv sync --locked`
- [ ] `uv build`
- [ ] `uv run python -m youtube_intel --help`
- [ ] `uv run python -m pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `git diff --check && git status --short`

## 预计触达文件

- `.python-version`
- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `src/youtube_intel/__init__.py`
- `src/youtube_intel/__main__.py`
- `tests/test_smoke.py`
- `handoffs/TASK-001.md`

`.gitignore` 作为本任务的配套小提交；完整安装和运维 README 由 `TASK-014` 负责，避免本任务扩成文档重写。

## 交付证据

- 依赖/工具链审批记录。
- 上述验证命令及退出码；`uv.lock` 的 Python、直接依赖和 build backend 版本摘要。
- Diff 中新增依赖的用途清单。

## 任务级批准记录

- Approver: 用户（产品负责人）
- Approved at: 2026-07-14
- Approval: `批准 TASK-001 推荐方案及上一条列出的依赖、版本范围、文件范围、uv 命令和网络下载权限。`
- 允许网络下载：上述直接依赖及其由 uv 锁定的必要传递依赖。
- 明确不授权：uv 升级、任何运行时依赖、MLX/模型、云调用、真实 Vault、launchd 或范围外文件。

## 分配记录

- Assigned at: 2026-07-14
- Base: `main@82871a2a0fa15c648e9a7d9f5ce7932544852534`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-001`
- Branch: `codex/task-001-project-scaffold`
- Implementer: Codex 独立会话
- Reviewer: Grok 独立会话，在实现 commit 后启动
- Parallel: `TASK-002` Read-only Preflight
