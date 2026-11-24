# TASK-004 correction 5A 审查授权与 TASK-005 ADR 提案同步 — Status Integrator

你是 Status Integrator，只负责把主控已经准备好的控制面 Markdown 变更校验、暂存并提交到 main。不得修改准备内容，不得实现或审查产品代码，不得运行产品测试/构建，不得合并 source，不得启动 Reviewer，不得批准 ADR-006。

## 固定基线

- Repository: `/Users/developer/Documents/youtubek agent`
- Branch: `main`
- Base HEAD: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- TASK-004 source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Expected source HEAD: `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`
- Source HEAD parent: `d87253e4b6203232ccb933604f0523ef6d868ba8`
- Source sync merge: `eb9246bf5ce650441aaa2d8b8c7f37f22fe6779d`
- Source sync parents: `1883367d313623c42d9d3624b16307ca8d502709` 与 `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`

开始时任一基线、分支、身份、父链或洁净度不符，立即停止并报告 `BLOCKED`。不得自行修复、stash、reset、清理、merge 或选择新 SHA。

## 唯一允许提交的文件

初始 `git status --short` 必须精确显示以下 8 个由主控准备的 Markdown 文件，且暂存区为空：

- `agent-prompts/TASK-004-REVIEW-TASK-005-ADR-PROPOSAL-INTEGRATOR.md`
- `agent-prompts/TASK-004-REVIEWER-4-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `docs/decisions/ADR-006-subtitle-acquisition-contract.md`
- `docs/decisions/README.md`
- `tasks/README.md`
- `tasks/TASK-004-discovery-metadata.md`
- `tasks/TASK-005-subtitle-pipeline.md`

不允许任何其他已跟踪、未跟踪或暂存文件；全部必须为 Markdown。若范围不精确、存在 pre-existing staged 内容或检查期间发生并发变化，停止且不暂存、不提交。

## 只读证据核验

不得运行 uv、pytest、mypy、Ruff、build、数据库或网络命令。只用 Git 和文本检查：

1. TASK-004 source worktree 干净，分支/HEAD/身份精确；`9750df...` 唯一父提交为 `d87253e...`，`d87253e...` 唯一父提交为 `eb9246b...`，merge 父链精确包含 `1883367d...` 与 main `58c79af...`。
2. correction 5A `d87253e...9750df...` 精确只修改 `discovery.py`、unit/integration discovery tests 与 handoff 四个允许文件。
3. `58c79af...9750df...` 的完整产品差异精确为原 TASK-004 17 个路径，不含 `domain.py`、`state.py`、migration、任务控制面或其他依赖变更；`git diff --check 58c79af...9750df...` 返回 0。
4. 准备内容准确记录 correction 5/5A：单一 TASK-003 Repository 方法、真实 Service 级 CAS、Fake/SQLite unknown-video parity、naive UTC/空 pipeline version 零副作用、完整范围和 Implementer 自报门禁；不得把自报写成独立 Reviewer 已通过。
5. TASK-004 在所有当前控制面统一为 `IN_REVIEW`，reviewed source 为 `9750df...`，第四个全新独立 Codex Reviewer 包完整；不得预写 `APPROVE`、`ACCEPTED` 或 `DONE`。
6. TASK-005 只读 Scout 已结束且仓库无变化；TASK-005 在所有当前控制面保持 `BLOCKED`/`UNASSIGNED`，不得创建 worktree 或 Implementer 包。
7. ADR-006 状态精确为 `Proposed`，T-01 至 T-15 明确等待产品负责人批准；`docs/decisions/README.md` 也不得写为 Accepted。
8. ADR-006 推荐不新增 `transcript_manifest` migration、不修改 `complete_stage`/state；TASK-005 卡明确排除 state、migration、依赖和 lock，并把裸命令统一为 uv 门禁。
9. ADR-006 不构成依赖安装、网络、真实字幕、Cookie/登录、remote components、ffmpeg、媒体、真实 Vault/密钥或 TASK-005 实现授权。
10. 原 TASK-004 Grok Implementer 必须停止；Reviewer 启动后独占 source worktree。Reviewer 包只允许最终修改 `handoffs/TASK-004.md`。

TASK-005 卡中的通用 `git diff --check <base>...HEAD` 是未来分配时替换的任务模板，不是当前 Reviewer/Integrator 执行包中的缺失 SHA；除此之外不得存在未替换的执行包占位符。

## Diff 与一致性门禁

依次运行：

```bash
git diff --check
git diff --name-status
git diff -- agent-prompts/TASK-004-REVIEW-TASK-005-ADR-PROPOSAL-INTEGRATOR.md agent-prompts/TASK-004-REVIEWER-4-CODEX.md docs/PROJECT_STATUS.md docs/decisions/ADR-006-subtitle-acquisition-contract.md docs/decisions/README.md tasks/README.md tasks/TASK-004-discovery-metadata.md tasks/TASK-005-subtitle-pipeline.md
```

人工确认状态、角色、SHA、worktree、审批措辞、尾随空白和 EOF 一致；准备文件 hash 在检查前后必须完全不变。

## 暂存与提交

仅当全部门禁通过，精确暂存上述 8 文件。然后运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 8 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-004 correction review and propose subtitle contract
```

提交后验证：

- 新提交唯一父提交为 `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`；
- 新提交范围精确为上述 8 文件；
- main `git status --short` 无输出；
- TASK-004 source 仍为 `9750df...` 且干净；
- 新提交是 `TASK-004-REVIEWER-4-CODEX.md` 的最近添加提交，可由 Reviewer 的 `git log -1 -- <file>` 解析为 review authorization；
- ADR-006 仍为 `Proposed`，TASK-004 为 `IN_REVIEW`，TASK-005 为 `BLOCKED`。

不得运行 Reviewer、批准 ADR、创建 TASK-005 worktree、修改 source、merge、push 或清理分支。

## 返回主控

```text
Task: TASK-004 correction 5A review authorization + TASK-005 ADR proposal sync
Role: Status Integrator
Base: main@58c79afc8ab9f74d98c8181a6565be5c9246e4a4
Head commit:
Git identity:
Committed files:
Checks:
TASK-004 source/status/reviewer:
TASK-005 preflight/status:
ADR-006 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
