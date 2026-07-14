# TASK-001 Grok Reviewer Task Packet

## 身份

你是 Grok，担任 `TASK-001` 的独立 Reviewer。实现者为 Codex。只审查工程脚手架、依赖锁定、测试和证据，不修改业务代码、工具链配置或测试；只可补充 `handoffs/TASK-001.md` 的 Reviewer 部分。

## 固定上下文

按顺序完整读取：

1. `/Users/hua/Documents/youtubek agent/AGENTS.md`
2. `/Users/hua/Documents/youtubek agent/docs/COLLABORATION.md`
3. `/Users/hua/Documents/youtubek agent/docs/PROJECT_STATUS.md`
4. `/Users/hua/Documents/youtubek agent/docs/PRD.md` 第 4、10、12、13、14、15 节
5. `/Users/hua/Documents/youtubek agent/docs/SYSTEM_DESIGN.md` 第 3、14、16、18 节
6. `/Users/hua/Documents/youtubek agent/docs/PRODUCT_DECISIONS.md` 的 DEC-02
7. `/Users/hua/Documents/youtubek agent/tasks/TASK-001-project-scaffold.md`
8. 本任务包
9. Worktree 中的 `handoffs/TASK-001.md`

公共状态以主仓库中的文件为准。实现分支从较早基线创建，所以其中任务卡的 `READY/UNASSIGNED` 是历史快照，不是冲突，也不得由 Reviewer 修改。

## 审查对象

- Task: `TASK-001`
- Role: `Reviewer`
- Agent: `Grok`
- Implementer: `Codex`
- Control baseline before review packet: `main@d86de14f171ff5efb82eee22fdbf1550673b4f92`
- Diff base: `82871a2a0fa15c648e9a7d9f5ce7932544852534`
- Reviewed implementation commit: `00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c`
- Branch: `codex/task-001-project-scaffold`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-001`
- Allowed Reviewer write: `handoffs/TASK-001.md` 的 Reviewer 部分
- Forbidden: 修改其他文件、修复实现、rebase/reset/merge、切换分支、更新公共任务状态、安装白名单外依赖

开始前确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git rev-list --count 82871a2a0fa15c648e9a7d9f5ce7932544852534..00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c
```

目录、分支、HEAD、干净状态不符，或实现区间不是恰好 1 个 commit 时立即停止。

## 必查范围

完整审查 `82871a2a0fa15c648e9a7d9f5ce7932544852534..00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c`，应恰好只有：

- `.python-version`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `src/youtube_intel/__init__.py`
- `src/youtube_intel/__main__.py`
- `tests/test_smoke.py`
- `handoffs/TASK-001.md`

重点核对：

1. Python 3.12、`uv_build>=0.11.28,<0.12` 和三个开发依赖范围与审批完全一致。
2. `project.dependencies` 为空，锁文件没有未经批准的直接依赖；传递依赖能追溯到 pytest、Ruff 或 mypy。
3. wheel/sdist 确实包含 `youtube_intel` 包和 `__main__.py`，而不是“构建成功但空包”。
4. smoke test 验证真实模块 CLI 行为，不是恒真断言，也未降低 Ruff/mypy/pytest 门禁。
5. `.gitignore` 命中运行产物、缓存和本地密钥，同时不忽略 `.env.example`、`.env.sample`、示例配置和迁移；特别判断未锚定的 `data/`、`logs/` 是否会不合理地忽略未来测试夹具，并按实际影响分级。
6. Diff、锁文件、构建元数据和交接报告不含密钥、真实 Vault 路径、模型/云调用或范围外业务实现。
7. 交接报告中的命令、版本和风险与可复现结果一致。

## 必须重新运行

```bash
git diff --name-status 82871a2a0fa15c648e9a7d9f5ce7932544852534..00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c
git diff --check 82871a2a0fa15c648e9a7d9f5ce7932544852534..00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c
uv lock --check
uv sync --locked
uv build -v
uv run python -m youtube_intel --help
uv run python -m pytest
uv run ruff check .
uv run mypy src
git status --short
```

另外人工检查构建归档内容和 `.gitignore` 正反例。网络或缓存权限阻止已批准命令时，只可请求与 TASK-001 已批准依赖相同的最小权限，不得换依赖或跳过检查。

## 结论与证据写入

按 P0/P1/P2/P3 列出 findings，并提供文件和行号。P0/P1 必须 `REJECT`；P2 是否阻塞需说明对当前验收或后续任务的具体影响；P3 为可选建议。

完成审查后，只补充 `handoffs/TASK-001.md` 的 Reviewer 部分，包括：

- Reviewer agent/session
- 审查 commit `00c7b2fc94ff3aa96a81a5dc5e1a2be4b549430c`
- 重新运行的命令与结果
- Findings
- `APPROVE` 或 `REJECT`
- 未解决 P0/P1 和剩余风险

只暂存该交接文件，运行 `git diff --cached --check`，然后提交：

```text
docs: record task 001 review
```

若出现任何其他已修改/暂存文件，停止，不清理、不覆盖，也不创建 commit。

## 最终输出

```text
Task: TASK-001
Role: Reviewer
Reviewed implementation commit:
Review evidence commit:
Checks rerun:
Findings: P0/P1/P2/P3 with file references
Acceptance matrix:
Scope/red-line review:
Verdict: APPROVE | REJECT
Remaining risks:
Decision needed: None | details
Post-commit status:
```
