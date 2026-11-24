# TASK-004 最终产品整合 — Codex Integrator

你是 TASK-004 的最终 Codex Integrator。你只把已经由第五次独立 Reviewer `APPROVE`、主控标记为 `ACCEPTED` 的固定 source head 合并到 main，并独立运行整合后门禁。不得顺便开发、修复、重构、改任务状态、启动 TASK-005、推送或清理分支/worktree。

## 固定 source 与动态执行基线

- Main repository: `/Users/developer/Documents/youtubek agent`
- Main branch: `main`
- Source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Source head / review evidence: `d4d6d01ceba3b9524305bb41ece81b8783f3db4b`
- Reviewed implementation head: `7272528a3c5603087446251ee96ae4766fedeb96`
- Review evidence parent: `7272528a3c5603087446251ee96ae4766fedeb96`
- Product Diff anchor: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`
- Git identity: `Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`

本包只有在 acceptance Status Integrator 返回 `INTEGRATED` 后才能执行。动态解析提交本包的执行基线：

```bash
main_repo='/Users/developer/Documents/youtubek agent'
execution_base="$(git -C "$main_repo" log -1 --format=%H -- agent-prompts/TASK-004-INTEGRATOR.md)"
test -n "$execution_base"
test "$(git -C "$main_repo" rev-parse HEAD)" = "$execution_base"
test "$(git -C "$main_repo" rev-parse "$execution_base^")" = '22dd5b5915d8c271274a06a2baa9865174bbad97'
test -z "$(git -C "$main_repo" status --short)"
```

任一门禁失败立即报告 `BLOCKED`；不得自行选择其他 SHA、stash、reset、rebase、cherry-pick、清理或修改准备内容。

## 必读与预合并证据

按 `AGENTS.md` 顺序完整读取协作规则、PROJECT_STATUS、PRD、SYSTEM_DESIGN、REUSE_REGISTER、TASK-004 卡、本包、ADR-003/004，以及 source `handoffs/TASK-004.md` 的 Correction 6 与第五次 Reviewer 结论。

在合并前确认：

1. main 当前为 `execution_base`、分支 `main`、工作区/暂存区干净、身份精确；TASK-004 为 `ACCEPTED`，TASK-005 仍为 `BLOCKED/UNASSIGNED`。
2. source 分支/HEAD/工作区干净；`d4d6d01...` 唯一父提交为 `7272528...`，review evidence commit 只修改 `handoffs/TASK-004.md`。
3. `7272528...` 唯一父提交为 `d510794...`，Correction 6 精确修改 `discovery.py`、两份 discovery 测试与 handoff 四个允许文件。
4. `58c79af...d4d6d01...` 完整产品差异精确为以下 17 个路径：
   - `handoffs/TASK-004.md`
   - `pyproject.toml`
   - `src/youtube_intel/discovery.py`
   - `src/youtube_intel/providers/youtube.py`
   - `tests/fixtures/youtube/info_ended.json`
   - `tests/fixtures/youtube/info_live.json`
   - `tests/fixtures/youtube/info_private_partial.json`
   - `tests/fixtures/youtube/info_public.json`
   - `tests/fixtures/youtube/info_restricted.json`
   - `tests/fixtures/youtube/info_shorts.json`
   - `tests/fixtures/youtube/info_title_update.json`
   - `tests/fixtures/youtube/info_upcoming.json`
   - `tests/fixtures/youtube/rss_sample.xml`
   - `tests/fixtures/youtube/rss_tiebreak.xml`
   - `tests/integration/test_discovery_adapter.py`
   - `tests/unit/test_discovery.py`
   - `uv.lock`
5. `git diff --check 58c79af...d4d6d01...` 返回 0；没有 `domain.py`、`state.py`、migration、CLI、TASK-005、真实配置/密钥、媒体或范围外文件。
6. 第五次 Reviewer 明确为 `APPROVE`：state 30、unit 36、integration 10、全量 132、mypy src、精确 wiring probe、Ruff、CLI、build/migration 全 PASS；AC-1 至 AC-5、D-01 至 D-08 全 PASS；P0/P1/P2/P3 均无。
7. 真实 YouTube/字幕、Cookie/登录、`.netrc`、remote components、ffmpeg、媒体下载、真实 Vault/密钥均未授权且不得运行。

任一父链、范围、Reviewer Verdict、状态或红线不符，停止且不 merge。

## 非提交合并与暂存门禁

在 main worktree 执行：

```bash
git merge --no-ff --no-commit d4d6d01ceba3b9524305bb41ece81b8783f3db4b
```

若冲突，保留现场并报告 `BLOCKED`；不得自行重设计或修改 source。无冲突时确认：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
git status --short
```

要求 staged scope 精确为上述 17 路径，`git diff --name-only` 无输出，`git status --short` 只显示这 17 个 staged 变更，没有未跟踪/未暂存意外文件。不得额外编辑、格式化或暂存控制面文件。

## 整合后产品门禁

在尚未创建 merge commit、但 staged tree 已是拟整合结果时运行：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
MYPYPATH=src uv run mypy -c '
from youtube_intel.discovery import DiscoveryRepository, DiscoveryService
from youtube_intel.domain import SourceProvider
from youtube_intel.state import SQLiteStateRepository

def wire(source: SourceProvider, repository: SQLiteStateRepository) -> DiscoveryService:
    checked: DiscoveryRepository = repository
    return DiscoveryService(source, checked)
'
uv run ruff check .
uv run python -m youtube_intel --help
uv build
```

确认 sdist/wheel 均含 `youtube_intel/migrations/001_initial.sql`。`uv sync` 或隔离构建若仅因 sandbox 网络限制失败，可按既有 TASK-004/构建授权原命令重跑；这不授权真实 YouTube。检查结束后只清理本轮被忽略的构建产物，Git staged tree 不得变化。

任何产品门禁失败都停止，不得通过修改代码/测试、跳过、xfail 或降级断言修复；报告命令与关键错误，由主控决定退回 source。

## Merge commit 与后置核验

所有门禁通过后创建 merge commit：

```text
merge: integrate TASK-004 discovery and metadata
```

提交后确认：

- merge commit 恰有两个父提交，依次为 `execution_base` 与 `d4d6d01...`；
- `d4d6d01...`、`7272528...` 均成为 main 祖先；
- merge 第一父差异精确为上述 17 路径；
- main `git status --short` 无输出；source 仍为 `d4d6d01...` 且干净；
- TASK-004 在 main 控制面仍为 `ACCEPTED`，不得在本轮改成 `DONE`；TASK-005 仍 `BLOCKED`；
- source branch/worktree 保留，不 push、不删除、不清理。

## 返回主控

```text
Task: TASK-004
Role: Integrator
Acceptance/execution base:
Source head: d4d6d01ceba3b9524305bb41ece81b8783f3db4b
Merge commit:
Merge parents:
Pre-merge scope:
Checks: command + result summary
Build/migration evidence:
Post-merge task status: ACCEPTED (not DONE)
Post-merge main/source status:
Git identity:
Unexpected files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
