# TASK-005 实现证据与独立审查授权同步 — Status Integrator

你是一个全新的 Codex Status Integrator。你只负责校验并提交主控已准备的 TASK-005
实现证据、`IN_REVIEW` 状态和独立 Codex Reviewer 包。不得修改准备内容、产品代码或
source，不得运行产品测试/构建/uv/数据库/网络命令，不得启动 Reviewer、批准实现或
合并 source。

## 固定基线与 source

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@38f1caa1c957b4b305afbe0f87c2e082b1ffc929`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Expected source HEAD：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- Expected source parent：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`

开始时任一 main/source 基线、分支、身份、父链、洁净度或范围不符，立即停止并报告
`BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理
或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-005-REVIEWER-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为上述 5 个文件，暂存区为空；不得存在其他
tracked、untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读证据门禁

不得运行 uv、pytest、mypy、Ruff、build、数据库或真实网络。只用 Git 与文本检查：

1. source branch/HEAD/parent/worktree 精确匹配且干净；实现为一个非 merge commit，
   author/committer 均为已验证身份。
2. `base...source` 精确为 11 个获批文件，全部属于任务卡的 8 个路径组；不得存在
   `state.py`、migration、discovery/youtube Adapter、配置、CLI、任务/ADR、
   `pyproject.toml`、`uv.lock` 或其他范围外文件。
3. `git diff --check base...source` 返回 0；`pyproject.toml`/`uv.lock` 相对 base
   无变化；source handoff 已填写 Implementer 证据，Reviewer 部分为空。
4. 当前控制面统一为 TASK-005=`IN_REVIEW`，source SHA=`98d197...`；Reviewer 是
   全新独立 Codex 会话，尚未启动，不得预写 Verdict。
5. Reviewer 包固定 base/source、11 文件、完整离线命令、AC-1 至 AC-5、ADR-006
   T-01 至 T-15、五轴审查和独立探针 A-F；只允许最终修改 source handoff。
6. Reviewer 必须特别审查 4,384 行变更和 1,664 行 `transcripts.py` 的职责/复杂度，
   但不得仅按行数自动拒绝，也不得只凭 191 tests 自动批准。
7. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
   真实 Vault/密钥继续未授权；Reviewer 默认检查完全离线。
8. TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`；ADR-007 仍为 `Proposed`，
   TASK-005A 尚不存在。本轮不得批准 ADR-007 或启动后续任务。
9. 所有新角色使用 Codex；历史 Grok 证据不修改。
10. 本轮仅记录 Implementer 自报检查与主控静态范围核验，不得写成 Reviewer 已独立
    复跑或实现已 `ACCEPTED`。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

人工确认状态、角色、SHA、范围、禁令、尾随空白和 EOF；文件 hash 前后不变。全部
通过后精确暂存 5 个文件，再运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-005 subtitle review
```

提交后确认：

- 新提交唯一父提交为 `38f1caa1c957b4b305afbe0f87c2e082b1ffc929`；
- 提交范围精确为上述 5 个 Markdown 文件；
- main 和 source worktree 均干净，source HEAD 未变化；
- 新提交可由 `git log -1 -- agent-prompts/TASK-005-REVIEWER-CODEX.md` 动态解析为
  review authorization；
- TASK-005=`IN_REVIEW`，未写为 `APPROVED/ACCEPTED/DONE`；
- ADR-007=`Proposed`，TASK-006/TASK-007=`BLOCKED/UNASSIGNED`；
- 未运行或启动 Reviewer、产品检查、安装、网络、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 implementation evidence / review authorization sync
Role: Status Integrator
Base: main@38f1caa1c957b4b305afbe0f87c2e082b1ffc929
Head commit:
Git identity:
Committed files:
Checks:
TASK-005 source/scope/status:
Reviewer authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
