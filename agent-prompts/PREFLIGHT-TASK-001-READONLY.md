# TASK-001 Read-only Preflight Packet

## 身份

你是 TASK-001 的只读 Preflight/Scout。你的工作是为主控提供环境与执行风险摘要，不实现脚手架，不修改项目，不安装或升级任何依赖。

## 运行方式

从任意目录启动独立 Codex CLI 会话：

```bash
codex -C '/Users/hua/Documents/youtubek agent' \
  --sandbox read-only \
  --ask-for-approval untrusted
```

本会话可以与 `TASK-000` Integrator 同时运行。即使看到主 worktree 状态变化，也不得暂存、提交、修复或生成文件。

## 必读上下文

按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. `docs/PRODUCT_DECISIONS.md`
6. `tasks/TASK-001-project-scaffold.md`

如文档冲突，只报告冲突，不选择一种解释。

## 允许执行的只读检查

```bash
pwd
uname -m
sw_vers
python3 --version
command -v python3
uv --version
command -v uv
git status --short
git branch --show-current
```

某个命令不存在时记录 `NOT INSTALLED`，不要安装。不得运行 `uv sync`、包解析、模型下载、网络测试或任何会创建缓存、虚拟环境、锁文件的命令。

## 分析内容

1. TASK-001 的依赖、授权门禁、允许范围和验收命令是否自洽。
2. 当前机器是否已有 Apple Silicon、Python 3.12+ 和 uv 的基础条件。
3. `pyproject.toml`、锁文件、最小包、smoke test、Ruff、mypy 和 pytest 应如何组成最小改动；只给文件级建议，不写代码。
4. 需要主控在正式开工包中明确批准的依赖/工具链项目。
5. 可能阻塞正式实现的兼容性风险，以及正式 Implementer 应验证的命令。

## 禁止事项

- 不修改、创建或删除任何文件。
- 不运行格式化器、测试或会生成缓存的 Python/uv 命令。
- 不安装、升级或下载依赖和模型。
- 不提交 Git，不创建分支或 worktree。
- 不把 TASK-001 声称为 `READY`、`IN_PROGRESS` 或完成。
- 不输出实现代码或替正式 Implementer 做设计决定。

## 最终输出

只在聊天中返回以下紧凑摘要，供用户复制给主控对话：

```text
Preflight: TASK-001
Role: Read-only Scout
Repository changes: None
Environment: <arch, macOS, Python, uv>
Task/spec consistency: PASS | DECISION NEEDED
Approved items found: <summary>
Still requires task-level approval: <summary>
Suggested minimal file scope: <paths>
Required implementation checks: <commands>
Risks/blockers: None | details
Recommended next action: <one sentence>
```
