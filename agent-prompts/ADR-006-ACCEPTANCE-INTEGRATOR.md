# ADR-006 接受与 TASK-005 契约同步 — Status Integrator

你是 Status Integrator，只负责把主控已经准备好的 ADR-006 接受记录和关联控制面 Markdown 校验、暂存并提交到 main。不得修改准备内容，不得实现产品代码，不得运行产品测试/构建/依赖命令，不得创建 TASK-005 worktree，不得访问或等待正在审查的 TASK-004 source worktree。

## 固定基线

- Repository: `/Users/developer/Documents/youtubek agent`
- Branch: `main`
- Base HEAD: `5f8646645bbaad274c094777261deff4636521fc`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`

TASK-004 第四次独立 Reviewer 可能正在 `/Users/developer/Documents/yia-worktrees/task-004` 工作。本任务与其并行时只允许操作 main；不得读取、检查、写入、清理、等待或以任何方式访问该 source worktree。开始时 main 任一基线、分支、身份或洁净度范围不符，立即停止并报告 `BLOCKED`；不得 stash、reset、清理或选择新 SHA。

## 唯一允许提交的文件

初始 `git status --short` 必须精确显示以下 10 个由主控准备的 Markdown 文件，且暂存区为空：

- `agent-prompts/ADR-006-ACCEPTANCE-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-4-RESUME-CODEX.md`
- `docs/PRODUCT_DECISIONS.md`
- `docs/PROJECT_STATUS.md`
- `docs/REUSE_REGISTER.md`
- `docs/SYSTEM_DESIGN.md`
- `docs/decisions/ADR-006-subtitle-acquisition-contract.md`
- `docs/decisions/README.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

不允许任何其他已跟踪、未跟踪或暂存文件；全部必须为 Markdown。若范围不精确、存在 pre-existing staged 内容或检查期间发生并发变化，停止且不暂存、不提交。

## 只读内容核验

不得运行 uv、pytest、mypy、Ruff、build、数据库或网络命令。只用 main 的 Git 和文本检查确认：

1. ADR-006 与 decisions index 均为 `Accepted`，日期为 2026-07-15，T-01 至 T-15 内容未被删减或改写。
2. ADR 批准记录包含产品负责人原话，并明确：不新增 Schema/migration、不修改 `state.py`/`complete_stage`；真实 YouTube/字幕、Cookie、登录、remote components、ffmpeg、媒体下载、真实 Vault/密钥仍未授权。
3. `docs/PRODUCT_DECISIONS.md` 只新增 ADR-006 后续批准记录，不改变 DEC-01 至 DEC-10 已接受内容。
4. System Design 为 V1.3，引用 ADR-006，并同步 `TranscriptFetchResult` 判别联合、最小 `TranscriptArtifact` 扩展、选择/规范化/缓存/错误/Artifact 恢复边界；不得引入自由 `dict`、新 ErrorCode、Schema 或 Repository 语义。
5. Reuse Register 只把现有锁定 yt-dlp 与 Python 标准库登记为 TASK-005 `DIRECT`；不得新增依赖、修改版本或把外部端到端应用升级为运行时依赖。
6. TASK-005 在 task card、tasks index 与 project status 中仍统一为 `BLOCKED` / `UNASSIGNED`；ADR 审批已满足，但仍等待 TASK-004 `DONE`、正式 worktree/角色/文件范围和任务级命令授权。
7. 不存在 TASK-005 worktree、Implementer/Reviewer 包、实现 commit、依赖安装或网络授权；不得把 ADR Accepted 写成 TASK-005 `READY/IN_PROGRESS`。
8. TASK-004 仍为 `IN_REVIEW`，reviewed source 仍为 `9750df...`；本轮不得修改任何 TASK-004 文件或预写 Reviewer 结论。
9. ADR-006 的 T-13/T-14 明确拒绝 V1 manifest migration 与 job-neutral Artifact/Repository 改造；缓存命中使用现有 Artifact 验证与空 Artifact stage completion。
10. 第四次 Reviewer 的首次尝试只因 main 存在本轮未提交 Markdown 而在检查前 `BLOCKED`，source/handoff 均未修改；恢复包只替换 main 启动门禁，其余 Reviewer 要求和 source SHA 不变。

## Diff 与一致性门禁

依次运行：

```bash
git diff --check
git diff --name-status
git diff -- agent-prompts/ADR-006-ACCEPTANCE-INTEGRATOR.md agent-prompts/TASK-004-REVIEWER-4-RESUME-CODEX.md docs/PRODUCT_DECISIONS.md docs/PROJECT_STATUS.md docs/REUSE_REGISTER.md docs/SYSTEM_DESIGN.md docs/decisions/ADR-006-subtitle-acquisition-contract.md docs/decisions/README.md tasks/README.md tasks/TASK-005-subtitle-pipeline.md
```

人工确认状态、角色、审批原话、版本、禁令、尾随空白和 EOF 一致；准备文件 hash 在检查前后必须完全不变。TASK-005 卡中的通用 `<base>` 只属于未来分配模板，不是本执行包缺失 SHA。

## 暂存与提交

只有全部门禁通过后，精确暂存上述 9 文件。然后运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 10 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: accept ADR-006 subtitle acquisition contract
```

提交后验证：

- 新提交唯一父提交为 `5f8646645bbaad274c094777261deff4636521fc`；
- 新提交范围精确为上述 10 文件；
- main `git status --short` 无输出；
- ADR-006 为 Accepted，TASK-004 为 IN_REVIEW，TASK-005 为 BLOCKED/UNASSIGNED；
- Git author/committer 均为 `Mozhu <maintainer@example.invalid>`；
- 没有访问 TASK-004 source worktree，没有创建 TASK-005 worktree。
- 新提交是 `TASK-004-REVIEWER-4-RESUME-CODEX.md` 的最近添加提交，可由 Reviewer 动态解析为恢复授权。

不得运行 Reviewer、修改 source、创建分支/worktree、merge、push 或清理任何任务证据。

## 返回主控

```text
Task: ADR-006 acceptance sync
Role: Status Integrator
Base: main@5f8646645bbaad274c094777261deff4636521fc
Head commit:
Git identity:
Committed files:
Checks:
ADR-006 status/scope:
TASK-004 status:
TASK-005 status/gates:
Post-commit main status:
TASK-004 source accessed: No
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
