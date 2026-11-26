# TASK-005 字幕获取与规范化 — Product Integrator

## 身份与目标

你是 Codex Product Integrator。你只把已主控验收的 TASK-005 source evidence `d5268ef08b360e932b5dda9d0fb70d71b13587a4` 整合到 main，并在整合后独立重跑受影响的离线门禁。你不实现、重构、补测、重审、改任务状态或扩大任务范围。

仅当无冲突合并、所有门禁通过、first-parent Diff 精确属于 TASK-005 已批准范围时才创建 merge commit。若出现冲突、范围漂移、门禁失败或授权变化，立即停止并报告 `BLOCKED`；不得自行重新设计、修代码、改测试、改依赖、改 Schema 或覆盖失败。

## 固定对象与开工门禁

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch：`main`
- Execution base：动态执行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-005-INTEGRATOR.md`
- Authorization parent：`7ed6a3ea096e05a1861a4e56c1c9207ef5aaebd0`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Source head / accepted review evidence：`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Source head parent / Correction 3：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Task base：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Git identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

开始时 main 必须位于动态 execution base 且干净；source 必须位于固定 source head、分支正确且干净；TASK-005 必须为 `ACCEPTED`，fourth Reviewer verdict 必须为 `APPROVE`，且 P0/P1=0。任一条件不符立即 `BLOCKED`。不得 stash、reset、checkout、rebase、cherry-pick、pull、force 操作、修改 source 或清理任何分支/worktree。

整合期间你是 main 的唯一写入者；不得让 Status Integrator、Implementer、Reviewer 或其他任务写 main 或 task-005 source。

## 必读

完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PRD.md`
4. `docs/SYSTEM_DESIGN.md`
5. ADR-002、ADR-003、ADR-004、ADR-005、ADR-006
6. `docs/REUSE_REGISTER.md`
7. `tasks/TASK-005-subtitle-pipeline.md`
8. TASK-005 原 Implementer、四次 Reviewer、Correction 1/2/3 的全部任务包
9. source `handoffs/TASK-005.md` 的全部历史证据
10. 本 Integrator 包

不得以 Implementer 自报替代第四次 Reviewer evidence 或整合后重跑结果。

## 已验收证据与范围

- 第四次 Reviewer evidence `d5268ef...` 只修改 `handoffs/TASK-005.md`，父提交精确为 Correction 3。
- 第四次审查独立通过：lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容、固定 Diff、P1 A/B/C、Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15。
- 非阻断 P2：Service 职责/私有 test hook 聚合。不得在本轮修复、隐藏或宣称关闭。
- 完整 `b28f52d...d5268ef...` 产品范围只允许以下 11 个文件：
  - `handoffs/TASK-005.md`
  - `src/youtube_intel/domain.py`
  - `src/youtube_intel/providers/subtitles.py`
  - `src/youtube_intel/transcripts.py`
  - `tests/fixtures/subtitles/auto_zh.vtt`
  - `tests/fixtures/subtitles/info_tracks.json`
  - `tests/fixtures/subtitles/malformed.json3`
  - `tests/fixtures/subtitles/manual_en.json3`
  - `tests/integration/test_subtitle_provider.py`
  - `tests/unit/test_contracts.py`
  - `tests/unit/test_subtitle_policy.py`
- 禁止 `state.py`、migration、`complete_stage`、配置、CLI、`pyproject.toml`、`uv.lock`、真实网络/认证/媒体/Vault 操作。既有锁定包的 `uv sync --locked` 只允许缓存缺失时下载相同锁定包；不得重锁或改变清单。

## 整合步骤与检查

1. 独立确认 source 链、review evidence 单文件范围、Correction 3 四文件范围、完整 11 文件范围、`pyproject.toml`/`uv.lock` 相对 task base 字节不变、main/source 洁净、身份和 `ACCEPTED` 状态。
2. 在 main 执行无冲突的 staged merge：

```bash
git merge --no-ff --no-commit d5268ef08b360e932b5dda9d0fb70d71b13587a4
```

只允许该 source head 成为 merge 的第二父。发现冲突立即停止，报告冲突文件；不得解析冲突或创建 commit。

3. 合并暂存后，先验证：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached --name-only
git diff --name-only
```

cached 范围必须精确为上述 11 个文件，未暂存 Diff 必须为空。然后重跑：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest tests/unit/test_subtitle_policy.py
uv run python -m pytest tests/integration/test_subtitle_provider.py
uv run python -m pytest
uv run mypy src
env MYPYPATH=src uv run mypy -c 'from pathlib import Path
from youtube_intel.state import SQLiteStateRepository
from youtube_intel.transcripts import TranscriptRepository
repository: TranscriptRepository = SQLiteStateRepository(Path("state.sqlite3"))'
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

`uv sync --locked` 若仅被受限沙箱阻止访问既有锁定包，才可按现有任务级授权用相同原命令联网重跑；不得下载新依赖、运行真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体、真实 Vault/密钥路径。build 必须 offline，并验证 sdist/wheel 同时包含 migration SQL、`transcripts.py` 与 `providers/subtitles.py`；只清理本轮生成且被忽略的 `dist/`。

4. 全部通过后创建唯一 merge commit：

```text
merge: integrate TASK-005 subtitle pipeline
```

5. 提交后验证：

- merge parents 精确为 execution base 与 `d5268ef...`；
- `git diff <merge>^1 <merge> --name-only` 精确为 11 个允许文件；
- source evidence 是 merge commit 祖先；
- main/source 都干净；
- TASK-005 状态仍为 `ACCEPTED`，不得设为 DONE；
- 不 push，不清理 source 分支或 worktree。

## 回传格式

```text
Task: TASK-005
Role: Product Integrator
Execution base:
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
