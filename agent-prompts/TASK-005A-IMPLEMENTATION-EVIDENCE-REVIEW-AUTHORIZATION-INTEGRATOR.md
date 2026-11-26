# TASK-005A 实现证据与独立审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。你只核验并提交主控准备的实现证据、
`TASK-005A=IN_REVIEW` 控制面和独立 Reviewer 包；不得实现、审查或修改产品代码，
不得运行 `uv`、pytest、mypy、Ruff、build、数据库、模型、服务或任何网络/真实资源
命令，不得启动 Reviewer、合并、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@3ee490c19950482ecd014668ce510ba5c742b743`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Source implementation base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Source implementation head：`85cd5362460044773317a48cbaae58e55aa735af`
- Required identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须精确位于 Required main base、身份正确、暂存区为空；工作区必须恰有
下列 5 个准备 Markdown 文件且无其他 tracked、untracked 或 staged 内容。source 必须
位于固定 implementation head、分支正确且干净。任一条件不符立即报告 `BLOCKED`；
不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或自行选择 SHA。

source 从 assignment 前 base 创建，故 source 内 `tasks/TASK-005A-...` / Project Status
的旧 `BLOCKED/UNASSIGNED` 是历史快照；main 控制面的 `IN_REVIEW` 才是实时状态。不得
回填或改写 source 的任务状态文件。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-005A-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-005A-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-005A-local-model-shared-contracts.md`

## 必须核验的事实

1. source head 的唯一父提交精确为 implementation base，且不是 merge/amend/rebase
   产物；source worktree 干净。
2. `git diff --name-status <base>...<head>` 精确为：
   - `config/settings.example.yaml`
   - `handoffs/TASK-005A.md`
   - `src/youtube_intel/config.py`
   - `src/youtube_intel/domain.py`
   - `src/youtube_intel/state.py`
   - `tests/integration/test_state_store.py`
   - `tests/unit/test_contracts.py`
   - `tests/unit/test_state_transitions.py`
3. 对 source 完整 Diff 的 `git diff --check` 通过；`pyproject.toml` 与 `uv.lock` 相对
   base 无差异；无 migration、Provider、`transcripts.py`、`discovery.py`、CLI、任务/ADR
   或凭证/生成物改动。
4. main 控制面把 TASK-005A 设为 `IN_REVIEW`，source 固定为 `85cd536...`，Reviewer
   是全新独立 Codex 且尚未启动；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。
5. Implementer 自报 lock/sync、focused 52/10/34、全量 250、mypy、Ruff、CLI、offline
   build 和 package inclusion 通过；这仅是实现证据，绝不等同 Reviewer 结论。
6. TASK-006/TASK-007 继续 `BLOCKED/UNASSIGNED`；模型、Ollama、ffmpeg、真实网络/媒体、
   Cookie、登录、Vault/密钥与文件删除继续不授权。

## 执行与提交

记录 5 个准备文件 SHA-256，检查前后必须完全一致。运行以下只读 Git 门禁：

```bash
git diff --check
git diff --name-status
git diff
git -C "/Users/developer/Documents/yia-worktrees/task-005a" diff --check 82f45a1c04f9eba3264cd743b28bc339d79b34fc...85cd5362460044773317a48cbaae58e55aa735af
git -C "/Users/developer/Documents/yia-worktrees/task-005a" diff --name-status 82f45a1c04f9eba3264cd743b28bc339d79b34fc...85cd5362460044773317a48cbaae58e55aa735af
```

全部通过后，只暂存上述 5 个文件，运行 `git diff --cached --check` 和 cached scope
复核，创建单一非 merge commit：

```text
docs: authorize TASK-005A independent review
```

提交后确认唯一父为 Required main base、main/source 均干净、提交范围精确、并且：

```bash
git log -1 --format=%H -- agent-prompts/TASK-005A-REVIEWER-CODEX.md
```

解析为该新 commit。不得运行产品命令、写 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005A implementation evidence / review authorization sync
Role: Status Integrator
Base: main@3ee490c19950482ecd014668ce510ba5c742b743
Head commit:
Git identity:
Committed files:
Checks:
Source implementation/scope/status:
Reviewer authorization:
TASK-006/TASK-007 gates:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
