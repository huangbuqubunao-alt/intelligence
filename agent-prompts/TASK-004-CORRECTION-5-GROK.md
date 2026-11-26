# TASK-004 Correction 5 — Grok Implementer

你是 TASK-004 原 Grok Implementer。你只负责关闭主控在第三次独立审查后发现的 SQLite Repository 组合契约 P1。第三次 Reviewer 对 correction 4 的 `APPROVE` 仍有效；本轮不得重做、重构或扩大已通过的 yt-dlp/RSS 行为。

## 固定位置与起点

- Main repository: `/Users/developer/Documents/youtubek agent`
- Source worktree: `/Users/developer/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- 开始时 source HEAD 必须精确为 review evidence `1883367d313623c42d9d3624b16307ca8d502709`
- 该 evidence 的唯一父提交必须为 correction 4 `54c0ab201388cba35e481d7a511f21575946ad14`
- source worktree 必须干净
- Git identity 必须为 `Mozhu <maintainer@example.invalid>`，且 `user.useConfigOnly=true`

本包只有在 Status Integrator 已把它提交到 main 并返回 `INTEGRATED` 后才能执行。不要猜同步 SHA。用下面的 Git 历史查询取得**添加本包的确定提交**：

```bash
control_sync_head="$(git -C '/Users/developer/Documents/youtubek agent' log -1 --format=%H -- agent-prompts/TASK-004-CORRECTION-5-GROK.md)"
test -n "$control_sync_head"
printf '%s\n' "$control_sync_head"
```

把命令输出记为 `control_sync_head`。开始前必须确认：

1. main 当前 HEAD 与 `control_sync_head` 完全相同；
2. `control_sync_head` 是 `b966e8aa056e2d922641d75ecdd4824bea5aaeb8` 的单父后继；
3. 该控制面提交只修改任务包列出的 Markdown 文件；
4. source 和 main 均无未提交内容。

任一条件不满足立即停止，报告 `BLOCKED`；不得自行挑选另一个 main SHA。

## 先同步已完成依赖

TASK-004 原分支从 TASK-003 并行启动前的 `dcc7d85...` 创建，因此本轮必须先把包含已完成 TASK-003 的 `control_sync_head` 合入 source 分支，才能编写和运行真实组合测试。

在 source worktree 执行一次普通非快进 merge：

```bash
git merge --no-ff "$control_sync_head" -m "chore: sync TASK-003 for discovery repository contract"
```

禁止 rebase、reset、cherry-pick、amend、强制移动分支或向 main 合并。若 merge 出现冲突，保持证据并停止，不得自行解决控制面冲突。

merge 成功后，记录 merge commit SHA，并确认 main 的 `src/youtube_intel/state.py`、migration 和 TASK-003 测试已经成为 source 分支祖先；此同步 merge 不算 correction 代码提交。

## 必读与目标

按仓库 `AGENTS.md` 的顺序完整阅读相关文档，重点复核：

- `docs/decisions/ADR-003-sqlite-state-store-contract.md` S-05
- `docs/decisions/ADR-004-discovery-ytdlp-contract.md` D-01、D-03、D-08
- `src/youtube_intel/state.py` 中 `ChannelCursorRecord`、`VideoRecord` 和 `SQLiteStateRepository` 的四个具名方法
- `src/youtube_intel/discovery.py` 中 `DiscoveryRepository`、`FakeDiscoveryRepository` 与 `DiscoveryService`
- `tests/integration/test_state_store.py`
- `tests/integration/test_discovery_adapter.py`

完成标准是：真实 `SQLiteStateRepository` 能作为 `DiscoveryRepository` 传给 `DiscoveryService`，不靠 `Any`/宽 `object`/自由 `dict`/运行时猴子补丁，也不要求生产 `discovery.py` 导入具体 SQLite 类。

主控已确认当前不兼容证据：

```text
runtime_protocol_match=False
missing methods required by TASK-004: get_cursor, upsert_metadata, mark_unavailable
SQLite methods: get_channel_cursor, save_discovery_batch,
                upsert_video_metadata, mark_video_unavailable
save_discovery_batch additionally requires expected_revision,
pipeline_version and UTC now
```

## 冻结设计边界

遵循 One-Version Rule：TASK-003 已验收的 Repository 具名 API 是唯一版本。本轮调整 TASK-004 consumer Protocol/Service/Fake 与之对齐，不在两边维持一套同义但不同名的接口。

必须满足：

1. `DiscoveryRepository` 使用与 `SQLiteStateRepository` 一致的四个具名方法和关键字参数：
   - `get_channel_cursor`
   - `save_discovery_batch`
   - `upsert_video_metadata`
   - `mark_video_unavailable`
2. 新频道把 persisted cursor 视为 `None`、revision `0`；已有频道从只读、具名 cursor view 取得 `DiscoveryCursor` 与 revision。不得把 SQLite record 或内部自由结构泄漏到 Provider。
3. `DiscoveryService` 在应用边界显式获得并传递 `pipeline_version` 与有时区 UTC `now`。可选择清晰的 typed method 参数或具名 typed context，但不得硬编码、使用本机隐式时间或公开无界 callback/object 测试钩子。
4. `save_discovery_batch` 必须把 expected cursor、expected revision、pipeline version 和 now 完整传入真实 Repository，保留候选 + cursor 的单事务 CAS。
5. 元数据成功调用 `upsert_video_metadata`；内容不可用调用 `mark_video_unavailable` 后仍保留现有安全错误语义。Job 失败诊断继续属于后续编排层，不得扩入 state 或伪造新的持久化字段。
6. `DiscoveryRepository` 的公共输入/输出只能是批准领域对象、基础标量或最小只读 Protocol view。不得使用 `Any`、宽 `object`、自由 `dict`/`Mapping`、具体 SQLite 类型或重复的 SQLite wrapper 隐藏签名不兼容。
7. `isinstance(initialized_sqlite_repository, DiscoveryRepository)` 必须为 `True`；mypy 必须能把实际 `SQLiteStateRepository` 传给 `DiscoveryService`。
8. 不改变 correction 4 已通过的 RSS 完整性、HTTP/error 分类、age_limit 请求身份、响应关闭、安全 yt-dlp options、公开 Provider Surface 或无下载边界。

## 允许修改范围

同步 merge 会引入 main 已提交内容；**correction 代码提交**只允许修改：

- `src/youtube_intel/discovery.py`
- `tests/unit/test_discovery.py`
- `tests/integration/test_discovery_adapter.py`
- `handoffs/TASK-004.md`

若某个测试无需修改，不必为了凑范围触碰它。禁止修改：

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/**`
- `src/youtube_intel/domain.py`
- `src/youtube_intel/providers/youtube.py`
- `pyproject.toml`
- `uv.lock`
- 任务状态、main 控制面、TASK-003/TASK-005 文件

不得新增或升级依赖，不得运行真实 YouTube、Cookie/登录、remote components、ffmpeg、媒体/字幕下载、真实 Vault 或密钥路径。

## 强制组合测试

在 `tests/integration/test_discovery_adapter.py` 使用 `tmp_path` 初始化真实 `SQLiteStateRepository`，并至少证明：

1. `DiscoveryRepository` 的运行时结构检查通过，且静态类型检查接受真实 Repository。
2. 空数据库的离线固定 DiscoveryBatch 通过 `DiscoveryService` 原子写入全部候选和 cursor；cursor revision、`pipeline_version`、UTC 审计时间正确。
3. 第二次稳定运行不重复创建视频、不倒退 Pipeline；expected cursor/revision 冲突时候选与 cursor 均不产生部分提交。
4. 离线元数据成功后真实视频记录更新；现有 Pipeline 不因 metadata upsert 倒退。
5. `CONTENT_UNAVAILABLE` 路径用真实 Repository 更新非 PUBLIC availability，同时保持安全 `AppError` 行为，不把原始响应或自由 payload 写入 SQLite。

测试只能使用 Fake Source/Metadata Provider 和临时 SQLite 文件，不得访问网络。不要通过 `skip`、`xfail`、条件导入或降级断言绕过组合测试。

## 必须运行的检查

在 source worktree 运行并记录：

```bash
uv lock --check
uv sync --locked
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build
git diff --check "$control_sync_head"...HEAD
git status --short
```

`uv build` 还必须确认 sdist/wheel 都包含 `youtube_intel/migrations/001_initial.sql`。网络若只因 sandbox 阻断 `uv sync --locked` 或隔离构建，可按已有 yt-dlp/构建授权原命令重跑；这不授权真实 YouTube。

## 自审与提交

提交前检查：

- `control_sync_head...HEAD` 的产品差异仍只包含 TASK-004 原 17 个路径加本轮允许修改，不包含 state/migration/domain 或控制面倒写；
- correction 代码提交精确属于本轮四个允许文件；
- 无 cache、`.venv`、`dist/`、数据库、真实响应、Cookie、密钥、媒体或字幕进入 Git；
- Git 作者/提交者身份正确；
- TASK-004 仍为 `IN_PROGRESS`，没有合并 main、没有设为 `ACCEPTED/DONE`。

不要 amend `1883367d...` 或 Reviewer evidence。同步 merge 后创建范围明确的 correction commit；更新 `handoffs/TASK-004.md`，记录接口映射、组合测试、命令结果、复用/许可证、跳过项和风险。

## 返回主控

```text
Task: TASK-004
Role: Implementer (repository compatibility / correction 5)
Branch/worktree:
Original review evidence head: 1883367d313623c42d9d3624b16307ca8d502709
Control sync head:
Source sync merge commit:
Correction code evidence commit:
Final branch head:
Changed files in correction commit:
Repository compatibility matrix:
Real SQLite combination evidence:
Checks: command + result summary
Build/migration inclusion evidence:
Diff review:
Skipped checks: real YouTube/Cookie/remote/ffmpeg/media only
Remaining risks:
Decision needed: None | details
Post-commit status:
```

若同步 merge 冲突、接口只能靠修改 `state.py`/Schema/依赖解决、组合测试无法离线成立或同一失败重复两次，立即停止并保留证据，不得扩大范围。
