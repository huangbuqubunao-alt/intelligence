# TASK-004 Correction 6 — 第五次独立 Codex Reviewer

你是 TASK-004 的第五次独立 Codex Reviewer。你没有参与 correction 6 实现，也不得依赖 Implementer 的自报结论。你只审查固定 source head、独立复跑门禁和设计探针，并在 `handoffs/TASK-004.md` 追加 Reviewer 证据；不得修改业务代码、测试、依赖、锁文件、main 或任务状态。

## 固定授权与工作位置

- Main repository: `/Users/developer/Documents/youtubek agent`
- Source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Source branch: `grok/task-004-discovery-metadata`
- Reviewed implementation head: `7272528a3c5603087446251ee96ae4766fedeb96`
- Reviewed implementation parent: `d510794ffccf54948f967f010685aef1c0a02f3d`
- Full TASK-004 product Diff anchor: `58c79afc8ab9f74d98c8181a6565be5c9246e4a4`
- Git identity: `Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`
- Main review authorization: 用本文件在 main 的最近添加提交动态解析

只有提交本包的 Status Integrator 返回 `INTEGRATED` 后才能启动。先在任意目录执行：

```bash
main_repo='/Users/developer/Documents/youtubek agent'
review_authorization="$(git -C "$main_repo" log -1 --format=%H -- agent-prompts/TASK-004-REVIEWER-5-CODEX.md)"
test -n "$review_authorization"
test "$(git -C "$main_repo" rev-parse HEAD)" = "$review_authorization"
test "$(git -C "$main_repo" rev-parse "$review_authorization^")" = '091a591f56c9aec73d4e7d979635b866493326a9'
test -z "$(git -C "$main_repo" status --short)"
```

然后进入 source worktree 并确认：

```bash
cd '/Users/developer/Documents/yia-worktrees/task-004'
test "$(git branch --show-current)" = 'grok/task-004-discovery-metadata'
test "$(git rev-parse HEAD)" = '7272528a3c5603087446251ee96ae4766fedeb96'
test "$(git rev-parse HEAD^)" = 'd510794ffccf54948f967f010685aef1c0a02f3d'
test -z "$(git status --short)"
test "$(git config user.name)" = 'Mozhu'
test "$(git config user.email)" = 'maintainer@example.invalid'
test "$(git config --bool user.useConfigOnly)" = 'true'
```

任一门禁失败立即报告 `BLOCKED`。不得 stash、reset、rebase、merge、cherry-pick、清理或选择新 SHA；不得在 main/source 有其他写入者时继续。

## 必读与审查目标

按 `AGENTS.md` 顺序完整读取仓库协作规则、PROJECT_STATUS、PRD、SYSTEM_DESIGN、REUSE_REGISTER、TASK-004 任务卡、本包，以及：

- ADR-003 S-05 与 ADR-004 D-01、D-03、D-07、D-08
- `handoffs/TASK-004.md` 的第四次 Reviewer `REJECT` 与 Correction 6 Implementer 两节
- `src/youtube_intel/discovery.py`
- `src/youtube_intel/state.py` 中 frozen records 和四个 Repository 方法（只读）
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `tests/integration/test_state_store.py`

先审测试，再审实现，按 correctness、readability、architecture、security、performance 五轴检查。Correction 6 只允许关闭两个 P1，不得借机重构已通过的 RSS/yt-dlp、CAS、错误分类或 Provider Surface。

## 固定 Diff 与范围门禁

必须确认：

1. `d510794...7272528...` 精确只修改：
   - `src/youtube_intel/discovery.py`
   - `tests/unit/test_discovery.py`
   - `tests/integration/test_discovery_adapter.py`
   - `handoffs/TASK-004.md`
2. correction commit 是 `d510794...` 的单父直接后继，没有 amend/rebase/额外 merge。
3. `58c79af...7272528...` 完整产品差异仍精确为原批准 17 路径，且 `git diff --check` 为 0。
4. correction 没有修改 `state.py`、Schema/migration、`domain.py`、`providers/youtube.py`、fixtures、依赖、lock、main 或 TASK-005。
5. 没有 `Any`/宽 `object`/自由 mapping、`cast`、`type: ignore`、wrapper、猴子补丁或具体 SQLite 导入进入生产 consumer Protocol。

## 必跑检查

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
git diff --check 58c79afc8ab9f74d98c8181a6565be5c9246e4a4...7272528a3c5603087446251ee96ae4766fedeb96
git status --short
```

确认 sdist/wheel 都含 `youtube_intel/migrations/001_initial.sql`。`uv sync`/隔离构建若仅被 sandbox 网络限制阻断，可按既有任务授权原命令重跑；这不授权真实 YouTube。最终只允许存在被忽略的临时缓存，review evidence commit 前 source 必须 Git-clean。

## 独立探针 A：静态 Repository 可替代性

不要只相信现有 helper 或 Implementer probe。至少独立证明：

1. 上述精确 mypy probe 返回 0；`SQLiteStateRepository` 可赋给 `DiscoveryRepository` 并直接传给 `DiscoveryService`。
2. `get_channel_cursor`、`save_discovery_batch`、`upsert_video_metadata` 的真实 frozen 返回类型分别满足只读 view；`mark_video_unavailable` 仍为 `bool`。
3. `ChannelCursorView` / `VideoRecordView` 的字段是只读 property 语义，不允许 consumer 写回，不通过放宽类型伪装协变。
4. 运行时 `isinstance(initialized_repository, DiscoveryRepository) == True`，真实临时 SQLite Service 组合仍可执行。
5. `discovery.py` 不导入 `SQLiteStateRepository`/state concrete types，不新增重复 Repository 版本。

任一真实 assignment/argument/return conflict 都是 P1，必须 `REJECT`。

## 独立探针 B：纯空白版本零副作用

除重跑现有 unit test 外，设计一个临时、离线且不提交文件的独立 probe，覆盖至少 `" "`、`"   "`、`"\t"`、`"\n"`、`" \t\n "`，同时验证：

1. discovery 和 metadata 两条公开 Service 路径都返回安全 `AdapterError(AppError(CONFIG_INVALID))`；
2. Source/Metadata Provider call count 均为 0；
3. 真实临时 `SQLiteStateRepository` 无候选、cursor、metadata 或 availability 变化；
4. 不泄漏 `sqlite3.IntegrityError`、CHECK 文本、SQL、路径或 payload；
5. `pipeline_version="pipeline-v1"` 正常执行，naive UTC 与空字符串既有行为不倒退。

不要通过直接调用私有校验函数替代公开 Service 边界。

## 回归、验收与红线

重新核对：

- AC-1 至 AC-5；ADR-004 D-01 至 D-08。
- 真实 SQLite 原子 batch/cursor、稳定重跑、Service CAS、metadata/unavailable 与 Fake parity。
- correction 3/4 已通过的 malformed payload、video ID、RSS channel 完整性、HTTP 分类、response close、`needs_auth`、公开 Provider Surface 和安全 yt-dlp options。
- 无下载、无 Cookie/登录/`.netrc`、无 remote components、无 ffmpeg、无媒体/字幕写入。
- 复用仍为标准库 + 已锁定 yt-dlp；无依赖/许可证范围扩大。`mutagen` GPL 风险继续留 TASK-014。

真实 YouTube/字幕、Cookie/账号、remote components、ffmpeg、媒体下载、真实 Vault/密钥均不得运行。

## Verdict 与证据提交

Findings 必须按 P0/P1/P2/P3 给出文件/行号、复现和影响：

- 任一 P0/P1/P2、任一必跑检查失败、静态 probe 失败或纯空白出现副作用：`REJECT`。
- 只有两项 P1 独立关闭、全部必跑检查/AC/D 门禁通过、范围与红线无问题时：`APPROVE`。

只允许在 `handoffs/TASK-004.md` 追加第五次 Reviewer 结论并创建一个 review evidence commit：

```text
docs: record TASK-004 correction 6 independent review
```

要求该 commit 唯一父提交为 `7272528...`，且只修改 handoff。不得 amend、修改业务代码/测试、合并 main、更新任务状态或清理分支/worktree。

返回主控：

```text
Task: TASK-004
Role: Fifth Independent Codex Reviewer
Reviewed implementation head: 7272528a3c5603087446251ee96ae4766fedeb96
Review evidence commit:
Checks rerun:
Independent probe A — static Repository substitutability:
Independent probe B — whitespace zero side effects:
Regression/AC/D matrix:
Findings: P0/P1/P2/P3
Scope/red-line/reuse review:
Verdict: APPROVE | REJECT | BLOCKED
Skipped checks:
Remaining risks:
Decision needed: None | details
Post-commit status:
```
