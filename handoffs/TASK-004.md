# TASK-004 交接报告

## 元数据

- Task: `TASK-004`
- Role: `Implementer`
- Agent/session: Grok Build (unique Implementer session)
- Base branch/commit: `main@dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-004`
- Branch: `grok/task-004-discovery-metadata`
- Head commit: (branch tip; see `git rev-parse HEAD` on `grok/task-004-discovery-metadata`)
- Started: 2026-07-15
- Reported: 2026-07-15

## 目标与范围

- 任务目标：实现频道 RSS 增量发现与 yt-dlp 元数据 Adapter；通过窄 Repository consumer Protocol/Fake 证明批次事务语义；完全离线验收。
- 允许修改：
  - `src/youtube_intel/discovery.py`
  - `src/youtube_intel/providers/youtube.py`
  - `tests/unit/test_discovery.py`
  - `tests/integration/test_discovery_adapter.py`
  - `tests/fixtures/youtube/**`
  - `pyproject.toml`
  - `uv.lock`
  - `handoffs/TASK-004.md`
- 实际修改：与允许范围一致；未新增 `providers/__init__.py`（PEP 420 namespace 包导入已验证）。
- 明确未做：
  - 未修改 `domain.py` / `state.py` / CLI / 字幕音频 / 公共任务状态 / ADR / 其他 worktree
  - 未读取 TASK-003 实现、未合并 main
  - 未运行真实 YouTube 冒烟；未使用 Cookie/账号/remote components/ffmpeg
  - 未下载媒体/字幕/缩略图

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1 固定夹具发现新视频、忽略已见、分类直播/结束/不可用 | PASS | `tests/unit/test_discovery.py` RSS/cursor 测试；`tests/integration/test_discovery_adapter.py` live/upcoming/ended/private/deleted/restricted |
| AC-2 重复发现稳定、无重复持久化、无错误推进游标 | PASS | `test_discover_and_save_all_or_nothing_and_idempotent`、`test_repeated_discovery_batch_does_not_duplicate_or_regress`、`test_rss_stable_results_for_same_fixture_and_cursor` |
| AC-3 超时/解析/不可用分码；响应正文不进日志/异常 | PASS | RSS 429/503/timeout/malformed/oversize；yt-dlp rate/timeout/parse/content maps；消息断言无 body/path/cookie |
| AC-4 元数据失败不回滚已提交候选/游标；语言摘要稳定 | PASS | `test_metadata_failure_does_not_rollback_discovery`；`test_available_languages_manual_then_auto_dedup_no_urls` |
| AC-5 yt-dlp 选项证明无下载/Cookie/remote components | PASS | `SAFE_YDL_OPTS` + `test_safe_ydl_opts_*` + integration 捕获 `last_opts` / `download=False` |

## ADR-004 可追溯性（D-01 … D-08）

| 决策 | 状态 | 证据 |
|---|---|---|
| D-01 发现批次提交点 | PASS | `SourceProvider.discover` 只返回 `DiscoveryBatch`；`DiscoveryService.discover_and_save` + `FakeDiscoveryRepository.save_discovery_batch` 全候选 DISCOVERED + next_cursor 同事务；失败整批回滚；元数据独立 |
| D-02 顺序/重复/游标 | PASS | Provider 顺序 + 批内去重；`published_at+video_id` 比较；同时间 video_id 平局；旧未知不回填；空批次只更新 `last_checked_at` |
| D-03 元数据失败与职责 | PASS | 单视频 `fetch`；`CONTENT_UNAVAILABLE` 标记不可用且不回滚发现；不全量伪造空 `VideoMetadata`；Adapter 不写 Job、不全局重试 |
| D-04 字幕清单归属 | PASS | 仅 `available_languages`（人工顺序 + 自动新增）；无 URL/格式/manual-auto 类型字段；未改 `domain.py` |
| D-05 Adapter 边界 | PASS | RSS=stdlib urllib/ET/datetime；yt-dlp Python API + `skip_download`/`noplaylist`/quiet/无写媒体；无 cookie/login/netrc/remote/ffmpeg |
| D-06 依赖与锁 | PASS | `yt-dlp[default,deno]>=2026.7.4,<2026.8`；`uv lock --check` / `uv sync --locked` 通过 |
| D-07 离线测试矩阵 | PASS | 单元+集成覆盖要求矩阵；真实网络未跑 |
| D-08 并行文件所有权 | PASS | 仅批准路径；未导入 TASK-003 Repository 类；窄 `DiscoveryRepository` Protocol + Fake |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | lock 与 pyproject 一致 |
| `uv sync --locked` | PASS | 30 packages |
| `uv run python -m pytest tests/unit/test_discovery.py` | PASS | 24 passed |
| `uv run python -m pytest tests/integration/test_discovery_adapter.py` | PASS | 4 passed |
| `uv run python -m pytest` | PASS | 75 passed（含 TASK-002 契约回归） |
| `uv run mypy src` | PASS | no issues in 6 source files |
| `uv run ruff check .` | PASS | All checks passed |
| `git diff --check` | PASS | 无空白错误 |
| yt-dlp 选项人工复核 | PASS | 见下节 |
| 错误文本人工复核 | PASS | 见下节 |
| Diff 范围人工复核 | PASS | 仅批准文件；无 `.venv`/缓存/密钥/真实响应 |

## Dependency lock summary

**Direct (approved):**

| Package | Spec | Locked |
|---|---|---|
| `yt-dlp[default,deno]` | `>=2026.7.4,<2026.8` | `yt-dlp==2026.7.4` |

**Extras / key transitive (locked):**

| Package | Version | Role / license note |
|---|---|---|
| `yt-dlp-ejs` | `0.8.0` | default extra；EJS challenge 组件（Unlicense AND MIT AND ISC） |
| `deno` | `2.9.2` | deno extra；JS runtime 分发（MIT） |
| `requests` | `2.34.2` | default 网络栈（Apache-2.0） |
| `urllib3` | `2.7.0` | requests 传递 |
| `certifi` | `2026.6.17` | default |
| `charset-normalizer` | `3.4.9` | requests 传递 |
| `idna` | `3.18` | requests 传递 |
| `mutagen` | `1.48.1` | default 媒体元数据依赖（GPL-2.0-or-later，yt-dlp default 传递，非本任务新增直接依赖） |
| `pycryptodomex` | `3.23.0` | default（BSD/Public Domain） |
| `brotli` | `1.2.0` | default |
| `websockets` | `16.1` | default |

既有直接依赖未升级：`pydantic==2.13.4`、`pyyaml==6.0.3`。

## yt-dlp option evidence

固定选项（`SAFE_YDL_OPTS` / `build_ydl_opts`）包含：

- `skip_download=True`、`noplaylist=True`、`quiet=True`、`no_warnings=True`
- `ignoreconfig=True`（不加载用户 CLI 配置）
- `writesubtitles=False`、`writeautomaticsub=False`、`writethumbnail=False`、`writeinfojson=False`、`writedescription=False`
- `usenetrc=False`、`cachedir=False`
- `socket_timeout` 来自配置超时

**明确不设置：** `cookiefile`、`cookiesfrombrowser`、`username`、`password`、`netrc_location`、`remote_components`、`ffmpeg_location`。

调用方式：`YoutubeDL(opts).extract_info(url, download=False)`（Python API，无 shell）。集成测试捕获全部 opts 与 `download=False`。

## Error/redaction evidence

- 对外错误统一为 `AdapterError.error: AppError`（安全 payload，无新 `ErrorCode`）。
- RSS：超时 → `TRANSIENT_NETWORK`；429 → `RATE_LIMITED`（可带 `retry_after_seconds`）；5xx/连接失败 → `PROVIDER_UNAVAILABLE`；非法 XML/超限 → `INVALID_RESPONSE`。消息不含响应正文、本机路径、Cookie。
- yt-dlp：超时/429/解析/私有/删除/地区限制分别映射；映射后消息为固定安全短语（如 `video content unavailable (private)`），不回传原始 provider 长文本。
- 单元/集成断言覆盖 `SECRET_BODY`、`/Users/`、`cookie`、原始 HTML/XML 片段不出现在 `AppError.message`。

## Reuse/license evidence

| 等级 | 来源 | 实际用法 |
|---|---|---|
| DIRECT | 官方 `yt-dlp` 2026.7.4 + `yt-dlp-ejs` 0.8.0 + `deno` 2.9.2 | Python API 元数据；锁文件固定；Adapter 隔离 |
| DIRECT | 标准库 `urllib.request` / `xml.etree.ElementTree` / `datetime` | RSS 发现 |
| REFERENCE | `imlewc/video-to-subtitle-summary-skill@2c794d74` | 借鉴无下载防御与语言排序测试思路；未复制 shell/ffmpeg/代理代码 |
| REFERENCE | `hailanlan0577/yt2md@8a845642` | 借鉴 URL/ID 与夹具稳定性思路；未复制依赖或 Vault 写入 |
| REJECT | `Xpos587/yt2md` | 未使用（TLS 禁用/页面正则） |
| REJECT | `ZeroPointRepo/youtube-skills` | 未使用（TranscriptAPI 远程账号/密钥） |
| 自有 | 游标语义、`DiscoveryRepository` Protocol、错误映射、批次 CAS、审计边界 | 本项目实现 |

离线 Fake：`FakeDiscoveryRepository` 证明 Adapter/Service 可替换为 TASK-003 SQLite 实现而不改变领域契约。

许可证：`yt-dlp` Unlicense；`yt-dlp-ejs` Unlicense AND MIT AND ISC；`deno` MIT；`requests` Apache-2.0。`mutagen` 为 yt-dlp default 传递的 GPL-2.0-or-later 依赖，属 D-06 已批准 extras 解析结果，非自行新增直接依赖。

## Diff 复核

- 修改文件：
  - `src/youtube_intel/discovery.py`（新）
  - `src/youtube_intel/providers/youtube.py`（新）
  - `tests/unit/test_discovery.py`（新）
  - `tests/integration/test_discovery_adapter.py`（新）
  - `tests/fixtures/youtube/*`（最小 RSS/info 夹具）
  - `pyproject.toml` / `uv.lock`
  - `handoffs/TASK-004.md`
- 是否存在任务范围外修改：否
- 是否存在生成文件或格式化噪声：否（`.venv`/`.pytest_cache` 未提交）
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：仅已批准 yt-dlp 依赖与锁；无 Schema/密钥/Vault/云调用

## 失败、跳过与风险

- 已解决失败：mypy（None callable / yt-dlp untyped / diagnostics 元组类型）；ruff import 排序与未使用变量。
- 跳过检查及原因：
  - 真实 YouTube `--limit 2` 冒烟：**NOT RUN**（任务包与 ADR-004 未授权）
  - 未请求 Cookie/账号/remote components/ffmpeg
- 剩余风险：
  - YouTube 页面/RSS 字段变化可能导致真实路径解析失败；离线夹具不能替代未来授权冒烟。
  - `mutagen` 作为 default 传递依赖的 GPL 义务需在分发场景由主控/发布任务再确认。
  - TASK-003 整合前，Repository 语义仅由 Fake 证明；组合契约测试在整合后进行。
  - `needs_auth`/部分 availability 枚举在真实站点上可能有更多变体，当前映射以固定夹具为准。
- `DECISION NEEDED`：`None`

## 预审修复（P1：公共 API 不得泄漏 yt-dlp 自由 dict）

### 原 P1

- `SAFE_YDL_OPTS` / `build_ydl_opts()` 在 `__all__` 中公开 `dict[str, Any]`。
- `map_info_dict_to_video_metadata` 及语言/状态 Mapping helpers 作为公开 API 暴露 `Mapping[str, Any]`。
- `YtDlpMetadataProvider` 公开 `last_opts: list[dict[str, Any]]` 与以 free-dict 为签名的 `ydl_factory` 类型别名。
- 违反 System Design §5.2 与 ADR-002 C-05：跨模块不得传递自由形状 `dict`。

### 封装方式

- `__all__ = ["YtDlpMetadataProvider"]`：跨模块公开导出仅此 Adapter 类。
- 选项表、选项构造、字幕语言摘要、live/availability/published 映射、info→`VideoMetadata` 全部改为私有：`_SAFE_YDL_OPTS`、`_build_ydl_opts`、`_summarize_available_languages`、`_map_*`、`_map_info_dict_to_video_metadata`。
- `YtDlpMetadataProvider` 公共注解：
  - `timeout_seconds: float`、`clock: Callable[[], datetime] | None`
  - 离线钩子 `ydl_factory: object | None`、`last_opts: object | None`（运行时校验；**不**标注 `dict[str, Any]` / `Mapping[str, Any]`）
  - 不再声明公开属性 `last_opts`；证据写入私有 `_opts_sink`
  - `fetch(video_id: str) -> VideoMetadata` 保持领域具名类型
- 为不改集成测试导入路径，保留残差名 `map_info_dict_to_video_metadata(info: object) -> VideoMetadata`：**不在** `__all__`，注解为 `object`（内部再校验 Mapping），不是跨模块契约。

### 回归测试

- `test_public_youtube_api_has_no_free_form_dict_annotations`：断言 `__all__`、构造/`fetch` 注解、禁止旧公开 helper 名、残差 helper 无 free-dict 注解。
- `test_safe_ydl_opts_have_no_download_cookie_remote_or_ffmpeg`：经私有 builder + Provider fake factory/`last_opts` sink 仍证明安全选项。

### 检查结果（修复后）

| 命令 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked` | PASS |
| `uv run python -m pytest tests/unit/test_discovery.py` | PASS |
| `uv run python -m pytest tests/integration/test_discovery_adapter.py` | PASS |
| `uv run python -m pytest` | PASS (76) |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

### Code evidence

- Prior head（首个实现）：`392edfb897003c1583b538667d10a2a89926a94b`
- Correction commit：见本分支新提交 `fix: hide yt-dlp raw mapping internals`（`git rev-parse HEAD` 在提交后）
- 修复仅触及：`src/youtube_intel/providers/youtube.py`、`tests/unit/test_discovery.py`、`handoffs/TASK-004.md`
- 行为/错误码/语言排序/依赖锁/未授权边界未改

### 修复后剩余风险（首轮，已被二次修复取代）

- 残差导入名 `map_info_dict_to_video_metadata` 与构造注入参数：见下方“二次预审修复”。
- 任务状态保持 `IN_PROGRESS`；Reviewer 尚未启动。

## 二次预审修复（P1 完整收口）

### 首轮未通过点

1. 非私有 `map_info_dict_to_video_metadata(info: object)` 仍邀请跨模块传入 yt-dlp 原始 payload（`__all__` 不是访问控制）。
2. 公开构造仍含 `ydl_factory` / `last_opts` / `clock`；写成 `object` 属于伪装，不是隔离。

### 私有化方式

- 删除非私有 `map_info_dict_to_video_metadata`；映射仅保留 `_map_info_dict_to_video_metadata` 等私有 helper。
- `YtDlpMetadataProvider.__init__(*, timeout_seconds: float = 30.0)` 仅领域配置参数。
- 默认 `_ydl_factory` / `_clock` / `_opts_sink=None` 为实例私有字段。
- 离线注入经私有 `_bind_test_hooks(provider, ydl_factory=..., clock=..., opts_sink=...)`（或等价私有属性赋值）；产品代码不得依赖。
- 可保留公开 `last_call: ProviderCallMetadata | None`（具名领域元数据，非 free dict）。

### 集成测试更新

- 不再从 `youtube.py` 导入任何非私有 mapping helper。
- 使用 `YtDlpMetadataProvider(timeout_seconds=...)` + `youtube_mod._bind_test_hooks(...)`。
- 稳定性映射改走 `youtube_mod._map_info_dict_to_video_metadata`。

### 回归测试

- `test_public_youtube_api_has_no_free_form_dict_surface`：
  - `__all__ == ["YtDlpMetadataProvider"]`
  - 不存在非私有 `map_*` / `build_*` / `SAFE_*` / residual mapper
  - 构造参数仅为 `timeout_seconds`
  - 无 free-dict 注解；无 `ydl_factory`/`last_opts`/`clock` 注入槽
- Provider fake 路径与安全 options 断言仍保留并增强。

### 检查结果（二次修复后）

| 命令 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked` | PASS |
| `uv run python -m pytest tests/unit/test_discovery.py` | PASS |
| `uv run python -m pytest tests/integration/test_discovery_adapter.py` | PASS |
| `uv run python -m pytest` | PASS |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `git diff --check` | PASS |

### Code evidence

- Prior head（首轮修复）：`10f5ffaaa3e8651a02e2f94c1736b8417acf3021`
- Correction-2 commit：见分支 tip（消息 `fix: make yt-dlp test hooks private`）
- 本轮仅改：`src/youtube_intel/providers/youtube.py`、`tests/unit/test_discovery.py`、`tests/integration/test_discovery_adapter.py`、`handoffs/TASK-004.md`
- 行为/错误码/语言排序/依赖锁/未授权边界未改

### 剩余风险

- 测试仍可触及私有 `_bind_test_hooks` / `_map_*`（Python 无真正封装）；属 Adapter 内部测试约定，非公共契约。
- YouTube 页面/RSS 漂移、mutagen GPL 传递、TASK-003 组合契约仍待后续。
- 任务状态保持 `IN_PROGRESS`；不启动 Reviewer。

## Reviewer REJECT 修复（Correction-3）

- Prior reviewed implementation head：`9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- Review evidence / required source head：`f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- Correction-3 commit：见分支 tip（消息 `fix: harden discovery adapter error boundaries`）
- 本轮仅改：`discovery.py`、`providers/youtube.py`、unit/integration tests、`handoffs/TASK-004.md`
- 任务状态保持 `IN_PROGRESS`；不启动 Reviewer、不合并 main

| Finding | 修复 | 回归 |
|---|---|---|
| P1 raw yt-dlp payload 绕过错误边界 | `_map_published_at` 捕获日期错误；`_coerce_age_limit` 非法值 → `AdapterError(INVALID_RESPONSE)`；`fetch`/`_map_info_dict_to_video_metadata` 统一封装，不泄漏 ValueError/TypeError/payload | `test_malformed_ytdlp_payload_is_safe_adapter_error` |
| P1 请求/响应 video_id 不一致 | 映射后强制 `metadata.video_id == requested_video_id`，否则 `INVALID_RESPONSE` 且 `AppError.video_id=请求ID`，不写 Repository | `test_response_video_id_must_match_request`；integration `test_provider_rejects_mismatched_and_http_errors_offline` |
| P1 RSS 不完整 entry 静默丢弃 | 缺 videoId/published/title 或无效时间戳 → 整批 `INVALID_RESPONSE` nonretryable；不推进 cursor | `test_incomplete_rss_entry_fails_without_advancing_cursor`（含后续修复后仍可发现较旧条目） |
| P1 yt-dlp HTTP 分类顺序错误 | 先解析 404→`CONTENT_UNAVAILABLE`、403/401→`PERMISSION_DENIED`、5xx→`PROVIDER_UNAVAILABLE`、429→`RATE_LIMITED`，再做宽文本匹配 | `test_ytdlp_http_status_classification_order`；integration 503 路径 |
| P2 RSS response 未关闭 | `_read_limited` 在 `finally` 中关闭（成功/timeout/OSError/类型/超限） | `test_rss_response_closed_on_read_timeout` |
| P2 needs_auth 标 PUBLIC | V1 无登录：`needs_auth` → `RESTRICTED` | `test_needs_auth_is_restricted_not_public` |
| P3 公开注解哨兵放过 Any | `_annotation_mentions_free_dict` 对 `Any`/`object`/Mapping 视为失败 | `test_public_youtube_api_has_no_free_form_dict_surface` |

### 检查结果（Correction-3）

| 命令 | 结果 |
|---|---|
| `uv lock --check` | PASS |
| `uv sync --locked` | PASS |
| `uv run python -m pytest tests/unit/test_discovery.py` | PASS |
| `uv run python -m pytest tests/integration/test_discovery_adapter.py` | PASS |
| `uv run python -m pytest` | PASS (83) |
| `uv run mypy src` | PASS |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS |
| `git diff --check` | PASS |

### 跳过与风险

- 真实 YouTube / Cookie / remote components / ffmpeg / 媒体字幕下载：未运行（未授权）
- 剩余风险：Provider 页面文案变化仍可能影响非 HTTP 文本分类；私有测试 hook 约定仍依赖 Python 命名隐私；TASK-003 组合契约待整合

## 实现者结论

- 建议状态：`IN_PROGRESS`（Reviewer REJECT 修复已提交；等待主控预核验后再开 Reviewer）
- 首个实现 Commit：`392edfb897003c1583b538667d10a2a89926a94b`
- Correction-1：`10f5ffaaa3e8651a02e2f94c1736b8417acf3021`
- Correction-2：`9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- Review REJECT evidence：`f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- Correction-3：见分支 tip（`fix: harden discovery adapter error boundaries`）
- 复现/验证说明：

```bash
cd /Users/hua/Documents/yia-worktrees/task-004
uv lock --check && uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
```

## Reviewer 结论

- Reviewer agent/session：Codex（全新独立 Reviewer 会话）
- Product base：`dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Reviewed implementation head：`9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- Review authorization baseline：`main@372a31eb53eed39faeba9df545c5e665c7a63ba1`
- Review evidence commit：`f34cbb09d628ebb256bf5f2895adfd10dbd61812`
- Verdict：`REJECT`（已由原 Implementer 在 Correction-3 修复；待主控预核验后重启 Reviewer）
- Decision needed：`None`；退回原 Grok Implementer 修复，不由 Reviewer 修改业务代码

### 开始门禁与范围

- `pwd`：PASS，`/Users/hua/Documents/yia-worktrees/task-004`
- branch：PASS，`grok/task-004-discovery-metadata`
- initial HEAD：PASS，`9db800fc9f4d01a5b6348c5cc8b567f83dc442aa`
- initial worktree：PASS，干净
- Git identity：PASS，`Mozhu <huangbuqubunao@gmail.com>`，`user.useConfigOnly=true`
- 父链：PASS，`dcc7d85... <- 392edfb... <- 10f5ffa... <- 9db800f...` 均为直接父子且可达
- main authorization：PASS，`main` 精确位于 `372a31eb53eed39faeba9df545c5e665c7a63ba1`
- 完整 Diff：PASS，恰好 17 个批准路径；无二进制、模式变化或范围外文件
- 三个实现提交的自身范围：PASS；首实现 17 个批准路径，Correction-1 仅 3 个批准文件，Correction-2 仅 4 个批准文件

### 独立复跑检查

| 命令 | 结果 |
|---|---|
| `uv lock --check` | PASS；Resolved 34 packages |
| `uv sync --locked` | PASS；Checked 30 packages |
| `uv run python -m pytest tests/unit/test_discovery.py` | PASS；25 passed |
| `uv run python -m pytest tests/integration/test_discovery_adapter.py` | PASS；4 passed |
| `uv run python -m pytest` | PASS；76 passed |
| `uv run mypy src` | PASS；6 source files，0 issues |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS；仅打印 CLI help |
| `git diff --check dcc7d85...9db800f...` | PASS |

附加 fixture 摘要命令首次对 intentionally-partial `info_private_partial.json` 的空 `subtitles` 调用 `jq keys`，因此该辅助命令 exit 1；随后直接读取该 5 行合成夹具并确认只有伪 ID、`private` availability 和伪 channel，无真实响应或敏感数据。这不是产品门禁失败，也未修改测试。

### 独立非写入探针

所有 Python 探针使用 `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python - <<'PY' ... PY`，不运行真实 `YoutubeDL`、不联网、不写仓库。

| 探针 | 预期 | 实际 |
|---|---|---|
| P-1 公开 surface/私有 hook：`inspect.signature`、`get_type_hints`、实际模块符号扫描和私有 Fake 路径 | `__all__` 仅 Provider；构造无 factory/callback/sink/raw/payload/clock；无非私有 raw mapper/builder/SAFE；公开注解无 `Any`/`object`/自由 `dict`；输出仅领域对象 | PASS；本模块定义的非私有符号仅 `YtDlpMetadataProvider`，构造仅 `timeout_seconds`，公开结果为 `VideoMetadata`/`ProviderCallMetadata` |
| P-2 离线安全 options：Fake 捕获 opts/`extract_info`；真实 `YoutubeDL`、文件写入、`subprocess.Popen/run` 设为调用即失败 | `skip_download=True`、`noplaylist=True`、`download=False`；无 Cookie/登录/netrc/remote components/ffmpeg/postprocessor/path；无媒体/字幕写入；raw mapping 不跨边界 | PASS；所有 required flags 符合，forbidden keys 为空，哨兵未触发，返回领域对象 |
| P-3 畸形 raw payload：非法日历日期、非数值 `age_limit` | 安全 `AdapterError` + `INVALID_RESPONSE` | **FAIL**；两例均从公开 `fetch()` 泄漏原始 `ValueError` |
| P-4 请求/响应视频 ID 不一致 | `AdapterError(INVALID_RESPONSE)`，不得写库 | **FAIL**；请求 `request1` 返回并存储 `other001`，Repository key 为 `other001` |
| P-5 RSS 不完整条目后续修复 | 首次应以 `INVALID_RESPONSE` 失败且不得推进游标 | **FAIL**；缺少 `videoId` 的条目被静默跳过，同批较新条目推进游标，修复后的 `vid_lost` 被永久过滤 |
| P-6 yt-dlp HTTP 分类：404/403/503 | 404=`CONTENT_UNAVAILABLE` nonretryable；403=`PERMISSION_DENIED` nonretryable；503=`PROVIDER_UNAVAILABLE` retryable | **FAIL**；404/403 均成 `PROVIDER_UNAVAILABLE` retryable；503 因含 `unavailable` 成 `CONTENT_UNAVAILABLE` nonretryable |
| P-7 RSS read timeout 资源关闭 | 映射 `TRANSIENT_NETWORK` 且 response 被关闭 | **FAIL**；错误码正确，但 `response.closed=False` |

### 验收矩阵

| 项目 | 结论 | Reviewer 证据 |
|---|---|---|
| AC-1 固定夹具发现/分类 | PASS | unit/integration 固定夹具覆盖正常发现、Shorts、live/upcoming/ended/private/deleted/restricted |
| AC-2 重复稳定、无重复/错误推进游标 | **FAIL** | 正常夹具幂等通过；P-5 证明非法但可解析的 RSS 条目被漏掉后仍推进游标并永久丢候选 |
| AC-3 错误分类与正文脱敏 | **FAIL** | 固定消息脱敏测试通过；P-3 原始异常越界，P-6 404/403/503 分类与 retryability 全部错误 |
| AC-4 元数据独立失败/语言摘要 | **FAIL** | 正常失败不回滚发现、语言排序均通过；但 P-4 证明单视频 Job 可把另一 `video_id` 的元数据写入仓库，破坏独立身份语义 |
| AC-5 yt-dlp 无下载/无登录/无 remote components | PASS | P-2 捕获 options 与 `download=False`，文件/subprocess/真实 YoutubeDL 哨兵未触发 |
| D-01 发现批次提交点 | PASS（有效 batch） | 窄 Repository Protocol + Fake 证明候选/cursor CAS 全有或全无；实际 SQLite 组合测试仍属整合后风险 |
| D-02 顺序、重复、游标规则 | PASS（有效 entry） | Provider 顺序、首个重复、稳定 `(published_at, video_id)` frontier、空 batch 保留字段均通过 |
| D-03 元数据失败与 Pipeline/Job 职责 | **FAIL** | P-3、P-4、P-6：错误未统一映射、返回 ID 未校验、HTTP 终态/重试语义错误 |
| D-04 字幕清单归属 | PASS | 只输出人工优先、自动补充的有序语言摘要；无轨道 URL/格式/类型公共字段 |
| D-05 RSS/yt-dlp Adapter 边界 | **FAIL** | Python API 与安全 options 通过；P-3/P-5/P-6 证明非法响应和错误边界不满足契约 |
| D-06 依赖与安装授权 | PASS | 直接依赖精确为 `yt-dlp[default,deno]>=2026.7.4,<2026.8`；锁 `2026.7.4`，无既有包升级 |
| D-07 离线测试矩阵 | **FAIL** | 现有 76 tests 全绿，但未捕获 P-3/P-4/P-5/P-6/P-7 的外部边界回归 |
| D-08 文件所有权/Repository 接口 | PASS | 仅批准路径；未改 `domain.py`/`state.py`/CLI/任务状态；未导入 TASK-003；Protocol 保持窄接口 |

### Findings（P0-P3）

- P0：无。
- **P1 — raw yt-dlp payload 可绕过统一错误边界。** `src/youtube_intel/providers/youtube.py:424-438` 在 provider try/except 之外映射 info；`_map_published_at` 的非法日期和 `_map_availability` 的非数值 `age_limit` 均可抛出原始 `ValueError`。P-3 已复现，违反 AC-3、D-03、D-05 和“外部数据视为不可信”的项目规则。
- **P1 — 请求 ID 与返回 ID 未校验，错误视频元数据会被写入仓库。** `src/youtube_intel/providers/youtube.py:339-438` 直接接受 payload `id`，`src/youtube_intel/discovery.py:329-340` 再按该返回 ID upsert。P-4 证明请求 `request1` 后成功存储 `other001`，破坏候选身份与独立 METADATA Job 语义。
- **P1 — RSS 不完整条目被静默丢弃且同批仍推进游标。** `src/youtube_intel/discovery.py:679-681` 对缺少 `videoId`/`published` 的 entry 返回 `None`；`459-471` 仍用其他条目推进 frontier。P-5 证明被修复的较旧条目随后永远不会被发现，违反 AC-2 与 D-05 的非法响应/不丢候选要求。
- **P1 — yt-dlp HTTP 错误分类顺序错误，终态和重试语义反转。** `src/youtube_intel/providers/youtube.py:471-583` 在 HTTP 状态判断前使用宽泛 `unavailable` 子串。P-6 证明 404/403 被盲目重试，503 反而直接终态，违反 AC-3、D-03 与 System Design §12。
- **P2 — RSS read 失败路径不关闭 response。** `src/youtube_intel/discovery.py:549-596` 仅在成功读取后关闭；timeout/OSError/类型错误/超限均先抛出。P-7 证明 read timeout 后 `closed=False`，长运行可能泄漏连接/文件描述符。
- **P2 — `needs_auth` 可被标为 `PUBLIC`。** 锁定 yt-dlp 的 `extractor/common.py` 将 `needs_auth` 定义为独立 availability condition；`src/youtube_intel/providers/youtube.py:133-150` 在存在 title 时却落到 `PUBLIC`。在禁止登录态的 V1 中该分类不安全。
- P3 — `tests/unit/test_discovery.py:501-523` 的 free-dict annotation helper 对 `Any` 返回 `False`；当前 surface 由 P-1 独立探针确认安全，但该回归哨兵本身仍可能漏掉未来公开 `Any`。

### Scope / red-line / reuse / license 复核

- 范围：PASS。`dcc7d85...9db800f...` 仅 17 个批准路径；`domain.py`、`state.py`、CLI、docs/tasks 状态和 main 均未修改。
- 公共 surface：PASS。yt-dlp 模块无非私有 raw mapper/builder/SAFE/test hook；`YtDlpMetadataProvider` 构造仅 `timeout_seconds`；领域输出为 `VideoMetadata`/`ProviderCallMetadata`。
- 安全 options：PASS。无 Cookie、浏览器 Cookie、用户名/密码、netrc、remote components、ffmpeg、postprocessor、媒体/字幕/缩略图/info JSON 写入；`skip_download` 与 `download=False` 双重保证。
- 真实数据/敏感信息：PASS。10 个 fixture 均为小型合成 JSON/XML；无媒体、字幕正文、真实响应缓存、Vault、密钥、Cookie 或本机私有路径。
- 依赖范围：PASS。新增包仅 `yt-dlp[default,deno]` 及 lock 解析的 15 个 marker/extra 传递包；无移除包、无既有版本升级。
- 锁定直接/关键传递：`yt-dlp==2026.7.4`、`yt-dlp-ejs==0.8.0`、`deno==2.9.2`、`requests==2.34.2`、`urllib3==2.7.0`、`mutagen==1.48.1` 等，与 D-06 一致。
- 本地 core metadata 许可证：`yt-dlp` Unlicense；`yt-dlp-ejs` Unlicense AND MIT AND ISC；Deno/Brotli/charset-normalizer MIT；Requests Apache-2.0；urllib3 MIT；certifi MPL-2.0；idna/websockets BSD-3-Clause；pycryptodomex BSD/Public Domain；mutagen GPL-2.0-or-later。
- 复用结论：PASS。实际为官方 yt-dlp Python API + 标准库 RSS；未复制 REFERENCE 项目代码，未引入已 REJECT 的 TranscriptAPI、TLS 禁用、直接 Vault 或付费代理路径。
- 许可证剩余风险：`mutagen` 是批准的 default extra 传递依赖，但 GPL-2.0-or-later 的分发义务仍需发布任务复核；本 Reviewer 不改变依赖。

### 跳过项与剩余风险

- 真实 YouTube 冒烟：`NOT RUN`（未授权）。
- Cookie/账号登录/浏览器会话、remote components、ffmpeg、媒体/字幕下载：`NOT RUN`（明确禁止，且 P-2 证明离线路径未触发）。
- 未读取、写入、检查、清理或等待 TASK-003；真实 SQLite 组合契约留待两个任务获批整合后验证。
- 即使修复上述 findings，YouTube RSS/页面字段漂移仍需未来单独授权的真实冒烟验证。
- 未解决 P0/P1：P0 无；P1 共 4 项，全部阻断合并。

## 主控验收

- Orchestrator：
- Verdict：
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：
