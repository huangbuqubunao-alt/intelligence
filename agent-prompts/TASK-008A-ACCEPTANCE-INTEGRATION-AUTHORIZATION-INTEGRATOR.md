# TASK-008A 验收与最终整合授权同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-008A 验收控制面和
Product Integrator 包；不得实现、审查或修改产品 source，不得运行 `uv`、pytest、
mypy、Ruff、build、import、数据库、网络或真实资源命令，不得启动 Worker、merge、
push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@aa134f43af57e6f6bdc7455b56c59ac97ee342e7`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Correction source：`d95745fd04b115369a9fd70362cd735d1eb70917`
- Reviewer 2 evidence：`7a8239f3da02fa204b63702677fae5f669fb99c0`
- Original task base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；
  `user.useConfigOnly=true`

开始时 main 必须在 Required main base、身份正确且暂存区为空；工作区必须恰有下列
5 个准备 Markdown 文件且没有其他修改/未跟踪路径。source 必须位于 Reviewer 2
evidence、分支正确且干净。任一条件不符立即 `BLOCKED`；不得 stash、reset、checkout、
merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-008A-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008A-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`

## 必须核验

1. Reviewer 2 evidence 的唯一父提交为 Correction source，evidence Diff 只修改
   `handoffs/TASK-008A.md`；source worktree 干净。
2. Correction Diff 精确为 5 个授权路径；original base...review evidence 完整产品
   范围精确为 8 个路径，`pyproject.toml`/`uv.lock` blob 与初始 implementation 一致。
3. Reviewer Verdict=`APPROVE`，P0/P1/P2/P3 均无；contracts `72 passed`、全量
   `324 passed`、mypy、Ruff、CLI、locked offline sync/build、migration/BPE package
   hash、Diff 和 A-F 探针均 PASS。不得以 Implementer 自报替代该独立 evidence。
4. 审查明确关闭 6 个先前 P1：hash 表示、语义空白、完整 ConfigError 脱敏图、固定
   BPE 本地只读/无网络回退、SDK 白名单子进程隔离导入、AnalysisCompleted 元数据一致。
5. main 控制面将 TASK-008A 设为 `ACCEPTED`，记录 source/review SHA、A-16/A-17 和
   无 P0–P3；不得写 merge SHA 或 `DONE`。Product Integrator 仅获后续执行授权，尚未
   启动。
6. Product Integrator 包固定 source、non-fast-forward merge、整合后全部离线门禁、
   8 路径 first-parent Diff、BPE/migration archive checks、source worktree 保留和
   `ACCEPTED`（非 `DONE`）状态。
7. TASK-009A、TASK-008、TASK-009 继续 `BLOCKED/UNASSIGNED`。真实 OpenAI/API、
   密钥、付费、token-count、Vault/用户内容、媒体、模型、所有网络和 BPE 许可证结论
   均不因验收而扩展；BPE NOTICE/许可证仍由 TASK-014 决定。

## 执行与提交

记录 5 个准备文件 SHA-256，完整检查前后必须一致。检查 main/source branch、HEAD、
identity、clean/index、父链、两种 source 范围、BPE source hash、prepared LF/EOF/
whitespace、`git diff --check`、cached Diff/精确 scope 和敏感字面量。只暂存上述 5 个
文件，创建单一非 merge commit：

```text
docs: accept and authorize TASK-008A integration
```

提交后确认唯一父为 Required main base、main/source 均干净，且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-008A-INTEGRATOR.md
```

解析为新 commit。不得运行产品命令、写 source、启动 Integrator、merge、push 或清理。

## 回传格式

```text
Task: TASK-008A acceptance / final integration authorization sync
Role: Status Integrator
Base: main@aa134f43af57e6f6bdc7455b56c59ac97ee342e7
Head commit:
Git identity:
Committed files:
Checks:
Review/source/status:
Integrator authorization:
TASK-009A/TASK-008/TASK-009 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
