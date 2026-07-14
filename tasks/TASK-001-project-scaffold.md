# TASK-001：工程脚手架与质量门禁

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: TL / 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-000
- Approval required: 依赖、包管理器、锁文件和工具链配置

## 目标

建立可安装、可运行、可测试的最小 Python 3.12 工程，并把 PRD 约定的测试、Lint 和类型检查命令变成真实门禁。

## 范围

- 在获得明确依赖审批后创建项目元数据和锁定方式。
- 建立 `youtube_intel` 包、最小 CLI `--help` 和一个离线 smoke test。
- 配置并验证 pytest、Ruff 和 mypy；忽略运行数据、日志、虚拟环境和密钥类文件。

## 范围外

- 不实现频道发现、数据库、字幕、模型或 Obsidian 逻辑。
- 不注册 launchd 服务。
- 不加入任何未审批的生产依赖。

## 验收标准

- [ ] 新环境按任务证据中批准的命令可完成安装，`python -m youtube_intel --help` 返回 0。
- [ ] `python -m pytest`、`ruff check .`、`mypy src` 均返回 0，并至少运行一个真实 smoke test。
- [ ] `.gitignore` 覆盖 `data/` 运行产物、`logs/`、虚拟环境、缓存和本地密钥文件，同时不忽略示例配置或迁移文件。

## 验证

- [ ] `python -m youtube_intel --help`
- [ ] `python -m pytest`
- [ ] `ruff check .`
- [ ] `mypy src`
- [ ] `git diff --check && git status --short`

## 预计触达文件

- `pyproject.toml`
- 锁文件（具体名称由 TASK-000 决定）
- `src/youtube_intel/__init__.py`
- `src/youtube_intel/__main__.py`
- `tests/test_smoke.py`

`.gitignore` 作为本任务的配套小提交；完整安装和运维 README 由 `TASK-014` 负责，避免本任务扩成文档重写。

## 交付证据

- 依赖/工具链审批记录。
- 五项验证命令及退出码。
- Diff 中新增依赖的用途清单。
