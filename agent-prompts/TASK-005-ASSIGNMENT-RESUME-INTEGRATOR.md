# TASK-005 分配同步续执行 — Worktree / Status Integrator

你是 Worktree / Status Integrator。首次分配执行已安全创建 TASK-005 worktree/branch，但控制面因主控同步把所有当前角色改为 Codex而触发文件哈希变化，未暂存或提交。本轮只接受既有 worktree，核验并提交最终控制面；不得重新创建、删除、移动或清理 worktree/branch，不得修改准备内容或产品代码，不得运行 `uv`、产品测试、构建、数据库或网络命令，不得启动任何 Worker。

## 固定恢复状态

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch / base HEAD：`main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Existing worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Existing branch：`codex/task-005-subtitle-pipeline`
- Required worktree HEAD：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Implementer：Codex
- Reviewer：实现提交后启动的全新独立 Codex 会话；不得复用 Implementer
- Parallel Scout：另一个全新 Codex 只读会话

任一 main/worktree 基线、分支、身份、洁净度或准备范围不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、worktree remove/add、branch delete/create、清理或选择其他 SHA。

## 唯一允许暂存/提交的 8 个控制面文件

- `agent-prompts/TASK-005-AUTHORIZATION-ASSIGNMENT-INTEGRATOR.md`
- `agent-prompts/TASK-005-ASSIGNMENT-RESUME-INTEGRATOR.md`
- `agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`
- `agent-prompts/PREFLIGHT-TASK-006-007-READONLY.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

开始时 main 的未提交内容必须精确为上述 8 个文件，暂存区为空；不得修改其字节内容。原分配包顶部必须明确写为“首次创建成功、后续由本续执行包处理”，不得再次运行创建动作。

## 必须校验

1. main 为 `main@b28f52d...`，分支 `main`；身份精确为 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。
2. 既有 task-005 worktree/branch/HEAD 精确匹配且工作区干净；只读核验，不创建、不写入、不运行 `uv`。
3. 当前 8 文件全部一致：TASK-005=`IN_PROGRESS`；Codex 为唯一 Implementer；Reviewer 是全新独立 Codex 会话；TASK-006/007 Scout 也是独立 Codex 只读会话。
4. 当前 TASK-005 分配内容中不得仍有 Grok Reviewer/Scout。`tasks/README.md` 和 `docs/PROJECT_STATUS.md` 的历史 TASK-001 至 TASK-004 Grok 审计记录必须保留，不属于冲突。
5. 产品范围仍精确为 Implementer 包列出的 8 个路径组；不新增/升级依赖，不改 `state.py`、Schema/migration、`complete_stage`、`pyproject.toml` 或 `uv.lock`。
6. 只有 `uv sync --locked` 可在缓存缺失时下载现有锁定包；其他检查/构建离线。真实 YouTube/字幕、Cookie/登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥继续未授权。
7. `PREFLIGHT-TASK-006-007-READONLY.md` 禁止读取 task-005 live worktree、写仓库、安装/下载、运行产品命令或提前实现；TASK-006/007 保持 `BLOCKED/UNASSIGNED`。
8. `git diff --check`、尾随空白、EOF、完整 Diff、准备文件哈希前后和 `git diff --cached --check` 均通过；检查期间再发生任何字节变化立即停止。

## 暂存与提交

仅在全部门禁通过后，精确暂存上述 8 个文件并创建：

```text
docs: assign TASK-005 subtitle pipeline
```

提交后确认：

- 新提交唯一父提交为 `b28f52d...`，提交范围精确为上述 8 个文件；
- main `git status --short` 无输出；
- task-005 worktree 仍为 `codex/task-005-subtitle-pipeline@b28f52d...` 且干净；
- 没有产品代码、依赖、锁文件或其他任务状态被写入；
- 不启动 Implementer、Reviewer 或 Scout，等待用户分别在独立 Codex 终端执行任务包。

## 回传格式

```text
Task: TASK-005 assignment resume sync
Role: Worktree / Status Integrator
Base: main@b28f52d0e4950f78dba315d4afe211ea5f75b93c
Head commit:
Existing worktree/branch/base:
Git identity:
Committed files:
Checks:
TASK-005 status/roles:
TASK-006/007 preflight status:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
