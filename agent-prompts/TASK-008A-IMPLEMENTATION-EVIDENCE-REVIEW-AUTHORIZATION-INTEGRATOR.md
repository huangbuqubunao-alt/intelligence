# TASK-008A 实现证据与独立审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。你只核验并提交主控准备的 TASK-008A 实现证据、
`IN_REVIEW` 状态和独立 Reviewer 包；不得实现或审查产品代码，不得运行 `uv`、
pytest、mypy、Ruff、build、Python import、数据库或网络命令，不得启动 Reviewer、
合并、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@112a79a1bed8f02eba6f75ec7247f398b104ac75`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Source implementation base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Source implementation head：`382251298af7fcbfadba66c1902af6de0a425179`
- Required identity：`Mozhu <maintainer@example.invalid>`；
  `user.useConfigOnly=true`

开始时 main 必须精确位于 Required main base，身份正确，暂存区为空；工作区必须
恰有下列 5 个准备 Markdown 文件且无其他 tracked、untracked 或 staged 内容。source
必须位于固定 implementation head、分支正确且干净。任一条件不符立即报告
`BLOCKED`；不得 stash、reset、restore、checkout、merge、rebase、cherry-pick、
pull、清理或自行选择其他 SHA。

source 从 assignment 前 base 创建，因此 source 内任务卡/Project Status 的
`READY/UNASSIGNED` 历史快照不代表实时状态；main 的 `IN_REVIEW` 才是实时控制面。
不得回填或修改 source 中的控制面文件。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-008A-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008A-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`

## 必须核验的事实

1. source head 的唯一父提交精确为 implementation base，且不是 merge commit；
   source worktree 干净。
2. `git diff --name-status <base>...<head>` 精确为：
   - `config/settings.example.yaml`
   - `handoffs/TASK-008A.md`
   - `pyproject.toml`
   - `src/youtube_intel/config.py`
   - `src/youtube_intel/domain.py`
   - `tests/unit/test_contracts.py`
   - `uv.lock`
3. source 完整 Diff 的 `git diff --check` 通过；相对 base 无 Provider、
   `analysis.py`、Prompt、Schema/migration、`state.py`、`complete_stage`、CLI、
   task/ADR、真实数据、凭据或生成物改动。
4. `pyproject.toml` 只新增直接范围 `openai>=2.46.0,<2.47` 和
   `tiktoken>=0.13.0,<0.14`；锁文件记录实现者声明的 2.46.0/0.13.0 与必要传递依赖，
   不得出现未经批准的其他直接依赖或既有直接依赖升级。
5. main 把 TASK-008A 设为 `IN_REVIEW`，固定 source 为 `3822512...`，Reviewer
   为全新独立 Codex 且尚未启动；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。
6. Implementer 自报 contracts `66 passed`、全量 `318 passed`、mypy、Ruff、CLI、
   lock/sync、offline build 和 package inclusion 通过。这只构成待审查证据，不等同
   Reviewer 结论。
7. TASK-009A、TASK-008、TASK-009 继续 `BLOCKED/UNASSIGNED`。真实 OpenAI/API、
   密钥/环境变量值、付费调用、云端 token-count、真实 Vault/用户内容、YouTube、
   媒体和模型路径继续未授权。

## 执行与提交

记录 5 个准备文件的 SHA-256；所有检查前后必须完全一致。只运行以下只读 Git 门禁：

```bash
git branch --show-current
git rev-parse HEAD
git status --porcelain=v1
git diff --check
git diff --name-status
git diff
git -C "/Users/developer/Documents/yia-worktrees/task-008a" branch --show-current
git -C "/Users/developer/Documents/yia-worktrees/task-008a" rev-parse HEAD
git -C "/Users/developer/Documents/yia-worktrees/task-008a" rev-parse HEAD^
git -C "/Users/developer/Documents/yia-worktrees/task-008a" status --porcelain=v1
git -C "/Users/developer/Documents/yia-worktrees/task-008a" diff --check 82d1fd7c7f2f82e77df0518e63755bad0bf240f2...382251298af7fcbfadba66c1902af6de0a425179
git -C "/Users/developer/Documents/yia-worktrees/task-008a" diff --name-status 82d1fd7c7f2f82e77df0518e63755bad0bf240f2...382251298af7fcbfadba66c1902af6de0a425179
```

全部通过后，只暂存上述 5 个文件，运行 `git diff --cached --check`、完整 cached
Diff 与精确 scope 复核，创建单一非 merge commit：

```text
docs: authorize TASK-008A independent review
```

提交后确认：

- 唯一父提交为 Required main base；
- 提交范围精确为上述 5 个文件；
- main/source 均干净，source HEAD 未变化；
- `git log -1 --format=%H -- agent-prompts/TASK-008A-REVIEWER-CODEX.md`
  解析为该新 commit。

不得修改任何准备内容，不得运行产品命令、写 source、启动 Worker、merge、push 或
清理。

## 回传格式

```text
Task: TASK-008A implementation evidence / review authorization sync
Role: Status Integrator
Base: main@112a79a1bed8f02eba6f75ec7247f398b104ac75
Head commit:
Git identity:
Committed files:
Checks:
Source implementation/scope/status:
Reviewer authorization:
TASK-009A/TASK-008/TASK-009 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
