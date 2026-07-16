# TASK-006/007 预检与 ADR-007 提案同步 — Status Integrator

你是一个全新的 Codex Status Integrator。你只负责校验、暂存并提交主控已准备的
TASK-006/TASK-007 只读预检结果、ADR-007 `Proposed` 文档与关联控制面 Markdown。
不得修改准备内容，不得批准 ADR，不得实现产品代码，不得创建共享任务或 worktree，
不得安装依赖/模型/系统工具，不得运行产品测试/构建/数据库/网络命令。

## 固定基线与并行隔离

- Main repository：`/Users/hua/Documents/youtubek agent`
- Branch / base：`main@b335b12358bbbc9dada1abfafc5a2fe9a68494be`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- TASK-005 live worktree：`/Users/hua/Documents/yia-worktrees/task-005`

TASK-005 Codex Implementer 可能正在 live worktree 写入。本任务只允许操作 main；
严禁读取、检查、等待、清理、写入或以任何方式访问 task-005 worktree。开始时 main
基线、分支、身份或准备范围不符，立即报告 `BLOCKED`；不得 stash、reset、checkout、
merge、rebase、cherry-pick、清理或自行选择新 SHA。

## 唯一允许提交的 9 个 Markdown 文件

- `agent-prompts/TASK-006-007-PREFLIGHT-ADR-PROPOSAL-INTEGRATOR.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/REUSE_REGISTER.md`
- `docs/decisions/ADR-007-local-model-pipeline-contracts.md`
- `docs/decisions/README.md`
- `tasks/README.md`
- `tasks/TASK-006-local-transcription.md`
- `tasks/TASK-007-local-scoring.md`

初始 `git status --short` 必须精确为上述 9 个文件，暂存区为空；不得存在其他已跟踪、
未跟踪或 staged 内容。全部准备文件 hash 在检查前后必须保持一致。

## 只读内容门禁

只允许 Git 与文本检查，确认：

1. ADR-007 状态为 `Proposed`，日期 2026-07-16，完整包含 L-01 至 L-15；不得出现
   Accepted、批准记录或实施授权。
2. TASK-006/TASK-007 仍统一为 `BLOCKED/UNASSIGNED`，共同等待 TASK-005 `DONE`、
   ADR-007 批准和未来 `TASK-005A` 共享契约切片；不得创建该任务卡或写为 READY。
3. 当前唯一活动写入任务仍是 TASK-005；不得改变其状态、角色、base、worktree、
   允许范围或授权。
4. 预检来源是只读 Scout，Observed main 为 `b335b123...`，Repository changes=None；
   不得把 Scout 建议表述成批准事实。
5. Reuse Register 只登记官方核验事实与 `DIRECT-PENDING/DEFER`：
   - `mlx-whisper>=0.4.3,<0.5`；
   - Whisper 模型固定 revision/hash/体积，但转换仓库无 license metadata；
   - Ollama `>=0.32.1,<0.33` 与 `qwen3:8b` digest/体积/Apache-2.0 上游；
   - ffmpeg 8.1.2/Homebrew GPL 风险；
   不得把任何安装、下载或真实调用写成已授权。
6. TASK-006/TASK-007 验证命令统一使用 `uv run`；真实模型、Ollama、ffmpeg 和真实
   YouTube 冒烟必须继续是独立门禁。
7. Roadmap 只增加共享契约切片前置要求，不改已完成任务或既有产品范围。
8. 真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、模型
   下载、Ollama 安装/拉取、真实 Vault/密钥仍未授权。
9. 本轮不得修改 `docs/SYSTEM_DESIGN.md` 或 `docs/PRODUCT_DECISIONS.md`；只有用户
   批准 ADR-007 后才能同步 Accepted 设计与创建共享任务。
10. 所有当前与未来角色均使用 Codex；历史 Grok 证据保留，不属于角色冲突。

## Diff 与提交

运行并人工复核：

```bash
git diff --check
git diff --name-status
git diff
```

确认尾随空白、EOF、状态、角色、SHA、版本、digest、禁令和 9 文件范围。只有全部
通过后精确暂存上述 9 文件，然后运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 9 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: propose local model pipeline contracts
```

提交后确认：

- 新提交唯一父提交为 `b335b12358bbbc9dada1abfafc5a2fe9a68494be`；
- 提交范围精确为 9 个指定 Markdown 文件；
- main `git status --short` 无输出；
- TASK-005 状态/角色未变化，TASK-006/TASK-007 仍为 BLOCKED/UNASSIGNED；
- ADR-007 仍为 Proposed；
- 没有访问 TASK-005 live worktree，没有创建 worktree/branch/task card；
- 没有运行 uv、测试、构建、数据库、安装、下载、模型或网络命令；
- 未 push、merge 或清理任何历史证据。

## 回传格式

```text
Task: TASK-006/007 preflight + ADR-007 proposal sync
Role: Status Integrator
Base: main@b335b12358bbbc9dada1abfafc5a2fe9a68494be
Head commit:
Git identity:
Committed files:
Checks:
ADR-007 status/scope:
TASK-005 status:
TASK-006/TASK-007 status/gates:
TASK-005 worktree accessed: No
Post-commit main status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
