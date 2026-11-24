# TASK-001 Codex Implementer Task Packet

## 身份

你是 Codex，担任 `TASK-001` 的唯一 Implementer。只建立 Python 工程脚手架与质量门禁，不领取后续业务任务，不承担 Reviewer、主控验收或整合职责。

## 固定上下文

在任务 worktree 中按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md` 第 4、10、12、13、14、15 节
5. `docs/SYSTEM_DESIGN.md` 第 3、14、16、18 节
6. `docs/PRODUCT_DECISIONS.md` 的 DEC-02
7. `tasks/TASK-001-project-scaffold.md`
8. `handoffs/TEMPLATE.md`

如任一文件冲突，停止并输出 `DECISION NEEDED`，不得自行选择解释。

## 开工包

- Task: `TASK-001`
- Role: `Implementer`
- Agent: `Codex`
- Base: `main@82871a2a0fa15c648e9a7d9f5ce7932544852534`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-001`
- Branch: `codex/task-001-project-scaffold`
- Reviewer: Grok 独立会话；仅在实现 commit 后启动
- Parallel now: `TASK-002` Read-only Preflight，由其他只读会话执行
- Waiting: `TASK-002` 及后续写入型任务

## 允许范围

只允许提交以下文件：

- `.python-version`
- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `src/youtube_intel/__init__.py`
- `src/youtube_intel/__main__.py`
- `tests/test_smoke.py`
- `handoffs/TASK-001.md`

`.venv/`、`dist/`、测试/类型/Lint 缓存可以在验证时生成，但必须被 `.gitignore` 覆盖且不得提交。需要任何其他文件时先停止并请求主控批准。

## 已批准依赖与权限

- 使用已安装的 Python 3.12；`.python-version` 使用 `3.12`。
- 使用现有 uv；不得升级 uv。
- Build backend：`uv_build>=0.11.28,<0.12`。
- 开发依赖：`pytest>=9.1.1,<10`、`ruff>=0.15.21,<0.16`、`mypy>=2.3,<3`。
- 允许 uv 网络下载并锁定上述直接依赖及其必要传递依赖。
- `pyproject.toml` 不加入任何运行时依赖。
- 不安装 MLX Whisper、不下载模型、不调用云服务、不接触真实 Vault、不注册 launchd。

## 实现与验收要求

1. 开始前复述目标、三项验收标准、依赖和预计文件。
2. 运行 `pwd`、`git branch --show-current`、`git rev-parse HEAD` 和 `git status --short`；目录、分支、基线或干净状态不符立即停止。
3. 先建立能表达 CLI `--help` 预期的 smoke test，再实现最小包和 CLI；不实现任何业务命令或 Provider。
4. 使用 `src/` 布局和纯 Python 打包；配置只满足当前任务，不提前加入后续依赖或框架。
5. `.gitignore` 至少覆盖 `.venv/`、`dist/`、Python/pytest/mypy/Ruff 缓存、`data/`、`logs/` 和常见本地密钥文件，同时不得忽略示例配置或迁移文件。
6. 从 `handoffs/TEMPLATE.md` 创建 `handoffs/TASK-001.md`，填写实现证据、检查结果、Diff 复核、跳过项和风险。
7. 完整复核 `82871a2a0fa15c648e9a7d9f5ce7932544852534...HEAD` 和全部未提交文件；不得混入其他任务。
8. 所有检查通过后创建一个范围明确的 commit，建议消息：`chore: establish Python project scaffold`。
9. 不修改公共任务状态，不合并 `main`，不操作其他 worktree。

## 必须执行的检查

```bash
uv lock --check
uv sync --locked
uv build
uv run python -m youtube_intel --help
uv run python -m pytest
uv run ruff check .
uv run mypy src
git diff --check
git status --short
```

网络或沙箱阻止已授权下载时，可请求仅限上述依赖的执行批准。不得通过删除测试、跳过检查、放宽规则或换依赖来获得通过。

## 最终输出

```text
Task: TASK-001
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + exit/result summary
Dependency lock summary: Python, build backend, direct dev dependencies
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
