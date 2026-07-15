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

### 修复后剩余风险

- 残差导入名 `map_info_dict_to_video_metadata` 仍可被模块内 import（非 `__all__`）；后续清理集成测试导入后可完全删除。
- 构造参数名 `ydl_factory` / `last_opts` 仍为离线钩子入口，类型已去 free-dict，但运行时仍接受 sink/callable。
- 任务状态保持 `IN_PROGRESS`；Reviewer 尚未启动。

## 实现者结论

- 建议状态：`IN_PROGRESS`（预审修复已提交；不自行启动 Reviewer / 不改公共任务状态）
- 首个实现 Commit：`392edfb897003c1583b538667d10a2a89926a94b`
- Correction Commit：见分支 tip（消息 `fix: hide yt-dlp raw mapping internals`）
- 复现/验证说明：

```bash
cd /Users/hua/Documents/yia-worktrees/task-004
uv lock --check && uv sync --locked
uv run python -m pytest tests/unit/test_discovery.py
uv run python -m pytest tests/integration/test_discovery_adapter.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
```

## Reviewer 结论

- Reviewer agent/session：尚未启动（主控预审修复核对通过后再启动）
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：
- 未解决 P0/P1：

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
