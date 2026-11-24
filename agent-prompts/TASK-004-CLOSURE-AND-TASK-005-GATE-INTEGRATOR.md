# TASK-004 关闭与 TASK-005 门禁同步 — Status Integrator

你是 Status Integrator。你只校验、暂存并提交主控已经准备好的控制面 Markdown；不得修改准备内容、运行产品测试/构建/数据库/网络命令、合并分支、创建 worktree、启动 TASK-005、安装依赖、推送或清理任何分支/worktree。

## 固定基线

- main repository：`/Users/developer/Documents/youtubek agent`
- main branch / base HEAD：`main@dc3f097ce125bc8390b04d0913b5d00f44eae3e8`
- TASK-004 source worktree：`/Users/developer/Documents/yia-worktrees/task-004`
- source branch / retained head：`grok/task-004-discovery-metadata@d4d6d01ceba3b9524305bb41ece81b8783f3db4b`
- 合并证据：`dc3f097...` 的父提交必须依次精确为 `da469f54e05be39ede86648c4b5976c80b0bdec7` 与 `d4d6d01ceba3b9524305bb41ece81b8783f3db4b`

任一基线、分支、身份、父链、范围或洁净度不符，立即停止并报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、清理或选择其他 SHA。

## 唯一允许暂存/提交的文件

- `agent-prompts/TASK-004-CLOSURE-AND-TASK-005-GATE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `handoffs/TASK-004.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`
- `tasks/TASK-005-subtitle-pipeline.md`

开始时 main 的未提交内容必须精确为上述 6 个文件，暂存区为空；不得修改其字节内容。

## 必须校验

1. main 为 `main@dc3f097...`、工作区未提交内容只为上述 6 个准备文件、暂存区为空；`git config user.name` / `user.email` 精确为 `Mozhu` / `maintainer@example.invalid`，且 `user.useConfigOnly=true`。
2. `dc3f097...` 是双父 merge：第一父 `da469f54...`、第二父 `d4d6d01...`；第一父差异精确为 TASK-004 的 17 个已批准路径，`git diff --check dc3f097^1..dc3f097` 返回 0。
3. source 仍在指定 branch/head 且干净；不写入、不合并或清理 source。
4. `handoffs/TASK-004.md` 的主控验收、整合结果与 Git 证据一致：第五次 Reviewer `APPROVE`、无 P0/P1/P2/P3；整合后 lock/sync、state 30、unit 36、integration 10、全量 132、mypy/wiring、Ruff、CLI、build/migration 都为 PASS。不要重跑产品命令。
5. 所有控制面一致：TASK-004 为 `DONE`；TASK-005 为 `BLOCKED/UNASSIGNED`，其 TASK-003/004 依赖已满足但仍缺正式 worktree、角色、允许范围和离线命令的**任务级实施授权**。ADR-006 已接受不等于实施/网络授权。
6. 真实 YouTube/字幕、Cookie/登录、remote components、ffmpeg、媒体/字幕下载、真实 Vault/密钥继续未授权；不得在本轮解除。

执行 `git diff --check`、尾随空白/EOF 检查与完整 Diff 复核。比较准备文件哈希前后必须一致。

## 提交

仅在全部校验通过后，精确暂存上述 6 文件，运行 `git diff --cached --check`，并创建：

```text
docs: close TASK-004 after integrated checks
```

提交后确认：新提交唯一父提交为 `dc3f097...`；main `git status --short` 无输出；source 仍为 `d4d6d01...` 且干净；没有产品代码、依赖、锁文件或 TASK-005 实现被写入。

## 回传格式

```text
Task: TASK-004 closure / TASK-005 gate sync
Role: Status Integrator
Base: main@dc3f097ce125bc8390b04d0913b5d00f44eae3e8
Head commit:
Git identity:
Committed files:
Checks:
TASK-004 status/merge:
TASK-005 status:
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
