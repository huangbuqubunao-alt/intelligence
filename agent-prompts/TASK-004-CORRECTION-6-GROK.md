# TASK-004 Correction 6 — Grok Implementer

你是 TASK-004 原 Grok Implementer。你只负责关闭第四次独立 Codex Reviewer 在 correction 5/5A 上确认的两个 P1：真实 SQLite Repository 的静态 Protocol 可替代性，以及纯空白 `pipeline_version` 的应用边界零副作用校验。Reviewer 已通过的运行时 Repository 组合、CAS、RSS/yt-dlp 安全行为和无下载边界不得重做、重构或扩大。

## 固定位置与起点

- Main repository: `/Users/hua/Documents/youtubek agent`
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- 开始时 source HEAD 必须精确为第四次 review evidence `d510794ffccf54948f967f010685aef1c0a02f3d`
- 该 evidence 的唯一父提交必须为 reviewed implementation `9750df2503a1aee135fdfbcca9f1706bcc9bd8de`
- evidence commit 必须只修改 `handoffs/TASK-004.md`
- source worktree 必须干净
- Git identity 必须为 `Mozhu <huangbuqubunao@gmail.com>`，且 `user.useConfigOnly=true`

本包只有在 Status Integrator 已把它提交到 main 并返回 `INTEGRATED` 后才能执行。不要猜同步 SHA，使用：

```bash
control_sync_head="$(git -C '/Users/hua/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-004-CORRECTION-6-GROK.md)"
test -n "$control_sync_head"
test "$(git -C '/Users/hua/Documents/youtubek agent' rev-parse HEAD)" = "$control_sync_head"
test "$(git -C '/Users/hua/Documents/youtubek agent' rev-parse "$control_sync_head^")" = '6c24f4341f98cad961fa3d442d49e5982a0d97cf'
test -z "$(git -C '/Users/hua/Documents/youtubek agent' status --short)"
```

该 main 控制面提交只记录 Reviewer `REJECT`、Correction 6 和任务状态，不包含需要同步到 source 的产品依赖。**不得 merge、rebase、reset、cherry-pick 或 amend main/control commit。** source 直接从 `d510794...` 创建新的 correction commit。

任一分支、HEAD、父链、身份、洁净度或控制面范围不符，立即停止并报告 `BLOCKED`；不得自行选用其他 SHA、stash、清理或改写历史。

## 必读与证据

按 `AGENTS.md` 的既定顺序完整阅读仓库说明、规格、复用登记、TASK-004 任务卡和本包，然后读取：

- `handoffs/TASK-004.md` 的“第四位独立 Reviewer 结论（Correction 5/5A 恢复审查）”
- `src/youtube_intel/discovery.py` 中 `ChannelCursorView`、`VideoRecordView`、`DiscoveryRepository`、`DiscoveryService`
- `src/youtube_intel/state.py` 中 frozen `ChannelCursorRecord`、`VideoRecord` 和四个 Repository 方法；**只读，不得修改**
- `tests/integration/test_discovery_adapter.py`
- `tests/unit/test_discovery.py`

第四次 Reviewer 的 evidence 已确认：131 tests、`mypy src`、Ruff、CLI、build、migration 包含性、运行时 Protocol、真实 SQLite 原子性/CAS、Fake parity 和 correction 3/4 安全回归均通过；但以下两个 P1 阻断验收。

## P1-1：真实 Repository 的静态 Protocol 可替代性

当前 `ChannelCursorView` / `VideoRecordView` 用可变 Protocol attribute 声明只读字段。TASK-003 的 frozen dataclass records 在运行时满足 Protocol，但 mypy 不允许其作为这些可变属性返回类型的协变实现，因此真实 wiring 仍失败。

完成标准：

1. `SQLiteStateRepository` 在不修改 `state.py` 的前提下，既保持 `isinstance(repository, DiscoveryRepository) == True`，又能被 mypy 直接赋给 `DiscoveryRepository` 并传入 `DiscoveryService`。
2. 最小推荐修复是把最小 view 的只读字段表达为只读 `@property` Protocol 成员，使 frozen records 结构化满足；允许等价的严格类型方案，但不得改变 TASK-003 的冻结记录或 Repository 方法。
3. 禁止 `Any`、宽 `object`、自由 `dict`/`Mapping`、`cast()`、`# type: ignore`、stub 欺骗、重复 SQLite wrapper、运行时猴子补丁或生产代码导入具体 `SQLiteStateRepository`。
4. `DiscoveryRepository` 的四个具名方法、关键字参数和领域返回语义保持与 TASK-003 唯一版本一致。
5. 在 `tests/integration/test_discovery_adapter.py` 保留运行时真实 Repository 组合断言，并加入可由独立 mypy probe 验证的真实静态 wiring；不得只写一个未进入任何 mypy 命令的注释/helper 就声称通过。

必须运行并保存以下独立静态组合 probe；它不得创建数据库或访问网络：

```bash
MYPYPATH=src uv run mypy -c '
from youtube_intel.discovery import DiscoveryRepository, DiscoveryService
from youtube_intel.domain import SourceProvider
from youtube_intel.state import SQLiteStateRepository

def wire(source: SourceProvider, repository: SQLiteStateRepository) -> DiscoveryService:
    checked: DiscoveryRepository = repository
    return DiscoveryService(source, checked)
'
```

该命令必须无 `arg-type`、assignment、return covariance 或其他错误。Reviewer 会独立复跑同一 probe。

## P1-2：纯空白 pipeline version 零副作用

当前 `discover_and_save()` 与 `fetch_and_store_metadata()` 只用 truthiness 检查；`"   "` 会先调用 Source/Metadata Provider，再泄漏 SQLite `IntegrityError`。

完成标准：

1. 在任何 Source、Metadata Provider 或 Repository 调用之前，把纯空白 `pipeline_version` 与空字符串同样拒绝为安全 `AdapterError(AppError(CONFIG_INVALID))`。
2. 至少覆盖 `" "`、`"   "`、`"\t"`、`"\n"` 和混合空白；不得依赖 SQLite CHECK 才失败。
3. discovery 与 metadata 两条 Service 路径均证明 Provider call count 为 0、Repository 状态不变、无 `sqlite3.IntegrityError`/约束文本/原始 payload 逸出。
4. 有效非空版本、naive UTC 既有行为、Service CAS、metadata/unavailable、RSS/yt-dlp 安全回归不得倒退。

## 允许修改范围

Correction 6 commit 最多只允许修改：

- `src/youtube_intel/discovery.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `handoffs/TASK-004.md`

若某个测试文件无需修改，不得为了凑范围触碰。禁止修改 `state.py`、migration、Schema、`domain.py`、`providers/youtube.py`、fixtures、`pyproject.toml`、`uv.lock`、main 控制面、TASK-003/TASK-005 或其他文件。

Reuse decision 仍为 `DIRECT`：现有 Python Protocol/dataclass、标准库 SQLite/RSS 和已锁定 yt-dlp；本轮不新增/升级依赖，不复制外部代码。

## 必须运行的离线检查

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
git diff --check
git diff --check 58c79afc8ab9f74d98c8181a6565be5c9246e4a4...HEAD
git status --short
```

`uv build` 后确认 sdist/wheel 均包含 `youtube_intel/migrations/001_initial.sql`，并在提交前清理仅被忽略的本轮构建产物，使 worktree 最终干净。网络若只因 sandbox 阻断 `uv sync --locked` 或隔离构建，可按既有授权原命令重跑；不授权真实 YouTube。

继续禁止真实 YouTube/字幕、Cookie/登录、`.netrc`、remote components、ffmpeg、媒体/字幕下载、真实 Vault/密钥。

## 提交与返回

先做 red/green 证据：证明当前静态 probe 与纯空白测试会失败，再做最小修复；不得删除、跳过、xfail 或弱化既有测试。若同一失败重复两次，停止并保留证据。

提交前复核：

- `d510794...HEAD` 的 correction 差异只属于上述四个允许文件；
- `58c79af...HEAD` 的完整 TASK-004 产品范围仍为原批准 17 路径；
- 没有 state/migration/domain/provider/dependency/lock/control-plane 变化；
- 没有缓存、数据库、构建产物、真实响应、Cookie、密钥、媒体或字幕进入 Git；
- TASK-004 保持 `IN_PROGRESS`，不合并 main、不设为 `ACCEPTED/DONE`。

创建一个新的 correction commit，不得 amend `d510794...` 或任何历史提交。更新 handoff，记录两个 P1 的 red/green 证据、精确静态 probe、所有命令、Diff、跳过项、复用和风险。

返回主控：

```text
Task: TASK-004
Role: Implementer (review-fix / correction 6)
Branch/worktree:
Starting review evidence: d510794ffccf54948f967f010685aef1c0a02f3d
Correction code evidence commit:
Final branch head:
Changed files:
P1-1 static Protocol evidence:
P1-2 whitespace boundary evidence:
Checks:
Build/migration evidence:
Diff review:
Skipped checks: real YouTube/Cookie/remote/ffmpeg/media only
Remaining risks:
Decision needed: None | details
Post-commit status:
```

若修复只能通过修改 `state.py`/Schema/依赖、放宽公共类型、增加 wrapper 或扩大文件范围实现，立即报告 `DECISION NEEDED`，不得越界。
