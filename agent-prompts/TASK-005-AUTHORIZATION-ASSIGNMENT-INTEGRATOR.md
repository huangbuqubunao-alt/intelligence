# TASK-005 授权、worktree 与分配同步 — Worktree / Status Integrator

> 状态说明：本包首次执行已成功创建 TASK-005 worktree/branch，但因主控同时完成“全 Codex”角色修正而触发准备文件哈希门禁，未暂存或提交。不得再次执行本包；后续只执行 `TASK-005-ASSIGNMENT-RESUME-INTEGRATOR.md`，保留既有 worktree/branch。

你是 Worktree / Status Integrator。你只执行本包明确授权的 worktree 创建，以及校验、暂存、提交主控准备的控制面 Markdown。不得修改准备内容或产品代码，不得运行产品测试、构建、数据库或真实产品网络命令，不得启动 Implementer/Reviewer，不得安装或升级依赖、推送、合并、rebase、reset、stash 或清理任何分支/worktree。

## 固定授权与基线

- main repository：`/Users/developer/Documents/youtubek agent`
- main branch / worktree base：`main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- 新 worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- 新 branch：`codex/task-005-subtitle-pipeline`
- Implementer：Codex；Reviewer：完成后才启动的全新独立 Codex 会话
- 用户已授权：仅 TASK-005 的 8 个产品路径、现有锁定依赖的 `uv sync --locked`（缓存缺失时仅包下载）与离线验证/构建；真实 YouTube/字幕、认证、remote components、ffmpeg、媒体下载、真实 Vault/密钥继续未授权

任一基线、身份、worktree/branch 既有状态或洁净度不符，立即报告 `BLOCKED`。不得选择其他 SHA 或自行处理冲突。

## 唯一允许提交的控制面文件

- `agent-prompts/TASK-005-AUTHORIZATION-ASSIGNMENT-INTEGRATOR.md`
- `agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`
- `agent-prompts/PREFLIGHT-TASK-006-007-READONLY.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

开始时 main 的未提交内容必须精确为上述 7 个准备文件，暂存区为空；不得修改其字节内容。

## 必须执行的门禁与唯一写入动作

1. 确认 main HEAD 精确为 `b28f52d...`、main 干净（除上述 7 个准备文件）、身份为 `Mozhu <maintainer@example.invalid>` 且 `user.useConfigOnly=true`。
2. 确认 `/Users/developer/Documents/yia-worktrees/task-005` 不存在，`codex/task-005-subtitle-pipeline` 不存在；既有 TASK-001 至 TASK-004 worktree 不读取、不修改、不清理。
3. 仅在前两项通过后执行：

    git worktree add /Users/developer/Documents/yia-worktrees/task-005 -b codex/task-005-subtitle-pipeline b28f52d0e4950f78dba315d4afe211ea5f75b93c

4. 核验新 worktree 分支、HEAD 精确为 `b28f52d...`、工作区干净；不得在其中写产品文件或运行 `uv`。
5. 核验 7 个控制面文件一致：TASK-005 为 `IN_PROGRESS`、Codex 为唯一 Implementer、全新独立 Codex Reviewer 等待 source commit；允许范围精确为 8 个路径；无新依赖/Schema/Repository 或真实网络授权。
6. `PREFLIGHT-TASK-006-007-READONLY.md` 只允许在本次同步提交完成后的干净 main 上只读执行，禁止读取 TASK-005 live worktree、安装依赖、运行产品测试或提前实现；TASK-006/007 保持 `BLOCKED/UNASSIGNED`。
7. `git diff --check`、尾随空白/EOF、完整 Diff、准备文件哈希前后和 cached Diff 检查均通过。

## 提交

仅在全部门禁通过后，精确暂存上述 7 文件并创建提交：`docs: assign TASK-005 subtitle pipeline`。

提交后确认：main 新提交唯一父为 `b28f52d...`；main 与 task-005 worktree 均干净；task-005 HEAD 仍为 `b28f52d...`；没有产品代码、依赖、锁文件或任务状态外文件被写入。

## 回传格式

    Task: TASK-005 authorization / assignment sync
    Role: Worktree / Status Integrator
    Base: main@b28f52d0e4950f78dba315d4afe211ea5f75b93c
    Head commit:
    Worktree/branch/base:
    Git identity:
    Committed files:
    Checks:
    TASK-005 status/roles:
    Post-commit status:
    Verdict: INTEGRATED | BLOCKED
    Remaining risks:
