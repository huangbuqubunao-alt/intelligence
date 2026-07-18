# TASK-005A — Product Integrator

你是全新的 Codex Product Integrator。你只将已验收 TASK-005A source 合并进 `main`，
复跑整合后门禁，并提交一个明确的 merge commit。不得实现、修复或重构产品；出现任何
冲突、范围、测试、身份或状态不一致必须立即停止并报告 `BLOCKED`。

## 固定对象与启动门禁

- Main repository/worktree：`/Users/hua/Documents/youtubek agent`
- Main integration authorization：动态运行
  `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005A-INTEGRATOR.md`
- Required authorization parent / acceptance anchor：`ce8e76c7ba51fd8f53bf63ebcfc6cf53fcc30b9d`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005a`
- Source branch：`codex/task-005a-local-model-shared-contracts`
- Source head：`e726656ffcc96b3c61d12f649c5574dc927add62`
- Original implementation base：`82f45a1c04f9eba3264cd743b28bc339d79b34fc`
- Reviewer evidence：`e726656ffcc96b3c61d12f649c5574dc927add62`，Verdict=`APPROVE`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`

开始时 main 必须在动态 authorization commit、它是 Required authorization parent 的
唯一直接后继、main 干净且 TASK-005A=`ACCEPTED`；source 必须在 fixed head、分支正确且
干净。source 任务/状态文件的 `BLOCKED/UNASSIGNED` 是 assignment 前快照，不能阻塞或
被改写。任一 SHA、父链、身份、洁净度、范围或状态不符，立即 `BLOCKED`。不得 stash、
reset、checkout、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 已验收范围

original base...source head 必须精确为：

1. `config/settings.example.yaml`
2. `handoffs/TASK-005A.md`
3. `src/youtube_intel/config.py`
4. `src/youtube_intel/domain.py`
5. `src/youtube_intel/state.py`
6. `tests/integration/test_state_store.py`
7. `tests/unit/test_contracts.py`
8. `tests/unit/test_state_transitions.py`

`pyproject.toml`/`uv.lock`、migrations、Provider、`transcripts.py`、`discovery.py`、CLI、
任务/ADR 和 main 控制面都不得作为这次 merge 的 first-parent 产品范围。不得在合并中
修正任何代码、测试、任务状态或 docs；若需要，停止并交回主控。

真实模型/Ollama、ffmpeg、媒体、网络、YouTube/字幕、Cookie/登录、Vault/密钥及文件删除
仍未授权，绝不运行。仅已有锁定依赖的 `uv sync --locked` 缓存缺失包下载在用户先前
TASK-005A 授权内；不得重锁、加包或下载模型。

## 合并与验证

1. 只读确认 source 链：`82f45... -> 85cd... -> 3cec... -> 3a7d... -> e726...`，其中两份
   review evidence 都只改 handoff；确认完整 8 路径与 lockfile 无差异。
2. 在 main 执行非快进、未提交合并：

```bash
git merge --no-ff --no-commit e726656ffcc96b3c61d12f649c5574dc927add62
```

若发生冲突、额外文件、source 不可快进或 staged scope 不精确，立即停止；不得手工解冲突。
3. merge staging 必须通过 `git diff --cached --check`，且 `git diff --cached --name-status`
   精确为 8 个已验收路径。然后在 main 的 merge staging 上运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest tests/unit/test_state_transitions.py
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

验证 sdist/wheel 均包含 `youtube_intel/migrations/001_initial.sql`。不要删除、修改或
清理任何既有 ignored 文件；如本轮生成 `dist/`，只报告它，不得将其加入提交。
4. 全部通过后创建 merge commit：

```text
merge: integrate TASK-005A shared contracts
```

## 提交后门禁与报告

确认：

- merge commit 精确有两个父：第一父是动态 execution base，第二父是 fixed source head；
- source head 及 implementation/reviewer evidence 都成为 main 祖先；
- merge 的 first-parent Diff 精确为上述 8 路径，`git diff --check` 通过；
- lockfiles 相对 first parent 无差异；整合后的所有门禁成功；
- main/source `git status --short` 均无输出；source branch/worktree 仍保留；未 push；
- TASK-005A 仍为 `ACCEPTED`，不得改为 `DONE`；TASK-006/TASK-007 仍 BLOCKED。

```text
Task: TASK-005A
Role: Product Integrator
Acceptance/execution base:
Source head:
Merge commit:
Merge parents:
Pre-merge scope:
Checks:
Build/package evidence:
Post-merge task status:
Post-merge main/source status:
Git identity:
Unexpected files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
