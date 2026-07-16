# TASK-005 交接报告

## 元数据

- Task: `TASK-005`
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-005`
- Branch: `codex/task-005-subtitle-pipeline`
- Head commit: 本交接文件所在实现提交；最终 SHA 见 Implementer 回传
- Started: `2026-07-16`
- Reported: `2026-07-16`

## 目标与范围

- 任务目标：离线完成字幕轨道重查、冻结顺序选择、JSON3/VTT/SRT 规范化、质量门禁、原始/规范文件写入、Artifact/Provider-call 缓存与崩溃恢复，并返回具名 `TranscriptFetchResult`。
- 允许修改：`domain.py`、`transcripts.py`、`providers/subtitles.py`、三组指定测试、`tests/fixtures/subtitles/**`、本 handoff。
- 实际修改：严格落在上述 8 个路径组。
- 明确未做：Whisper、评分、云分析、Obsidian、CLI/配置、真实网络、Cookie/登录/`.netrc`、remote components、ffmpeg/subprocess、媒体下载、Schema/migration、`state.py`/`complete_stage`、依赖或锁文件修改。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| AC-1 固定夹具覆盖人工/自动、多语言、空/损坏字幕 | PASS | `test_subtitle_policy.py` 与 `test_subtitle_provider.py` 覆盖人工全局优先、人工无效后自动回退、exact/base/variant、多格式、无轨道、无匹配、全部无效 |
| AC-2 同一输入不重复下载/规范化，原始/规范均有哈希和来源 | PASS | verified cache test 将网络和 `normalize_subtitle` 绑定为失败钩子，仍以空 Artifact completion 成功；两个 Artifact 均验证 SHA-256 |
| AC-3 具名 `transcription_required` 且与网络错误区分 | PASS | `NO_TRACKS`、`NO_MATCHING_LANGUAGE`、`ALL_CANDIDATES_INVALID` 返回判别联合；HTTP/timeout/权限/资源问题抛具名 `AppError` |
| AC-4 缓存命中验证 Artifact/文件并空 Artifact 推进 | PASS | 真实 `SQLiteStateRepository` 组合测试验证 `get_artifact_by_key`、文件 SHA-256、`complete_stage(artifacts=(), provider_call=None)` |
| AC-5 安全相对路径、原子写、恢复、脱敏 | PASS | DATA-relative `transcripts/<video_id>/<request_hash>/...`；同目录 tempfile、分块限流/哈希、flush/fsync、replace、父目录 fsync；缺失/篡改拒绝；DB 失败后文件恢复 |

## ADR-006 T-01 至 T-15 追踪

| 条款 | PASS/FAIL/BLOCKED | 实现/测试证据 |
|---|---|---|
| T-01 候选全局顺序 | PASS | `rank_subtitle_candidates`：人工/自动、配置语言、match rank、实际语言、格式、轨道名、Provider 位置 |
| T-02 语言匹配 | PASS | 大小写不敏感、`_`→`-`、exact/base/variant；Artifact 保留 Provider 实际语言 |
| T-03 格式与禁止项 | PASS | 只进入 JSON3/VTT/SRT 候选；临时 URL 只在内存；静态哨兵禁止 subprocess/ffmpeg；安全 options 禁止认证/媒体副作用 |
| T-04 具名结果联合 | PASS | `TranscriptReady | TranscriptionRequired`，固定 outcome/reason；真正错误继续为 8 个既有 `ErrorCode` |
| T-05 最小公共对象扩展 | PASS | 新枚举、结果类、严格 `TranscriptArtifact` 字段/来源规则/安全路径/SHA-256/具名 flags |
| T-06 确定性规范化 | PASS | strict UTF-8+BOM、LF、entity 单次、NFC、格式控制删除、cue 折叠、文件尾单 LF |
| T-07 语义与滚动字幕 | PASS | speaker/音乐音效保留；连续重复和词边界前缀仅按确定规则删除 |
| T-08 质量与资源阈值 | PASS | 5,000,000 bytes、1,000,000 code points、100,000 segments、20 chars、1% U+FFFD、80% 删除、10,000/1% 压缩比全部测试边界前后 |
| T-09 分层幂等键 | PASS | raw key 含视频/有序语言/选择/格式/Provider 版本/refresh；canonical key 含 raw hash/格式/规范/质量版本 |
| T-10 文件写入与恢复 | PASS | 两种既有 ArtifactKind、DATA/LONG_LIVED；原子写；文件先成功/DB 失败后第二 attempt 补索引；已索引缺失/篡改返回 LOCAL_RESOURCE |
| T-11 错误与重试 | PASS | 目录 401/403、正文 403/404、429 Retry-After、timeout/短读/5xx、危险 URL、权限/磁盘映射；Provider 不实现全局退避 |
| T-12 复用/依赖 | PASS | 直接使用锁定 yt-dlp Python API 和标准库；未新增/升级依赖，未改清单/锁 |
| T-13 不新增 manifest | PASS | metadata 以可逆 URL-safe token 编入 source path；版本/flags 编入稳定 key/path；计数从已验证 canonical 文件重算 |
| T-14 不修改 Repository | PASS | 首次当前 Job 两 Artifact + Provider call 原子完成；缓存命中真实空 Artifact completion；`state.py`/migration 无改动 |
| T-15 显式 refresh | PASS | 普通 verified cache 零网络；refresh generation 改变 request hash/path，重新枚举/读取，旧 Artifact 保留 |

## 脱敏 Artifact 示例

```text
TranscriptArtifact(
  video_id="video123",
  language="en",
  source_type=MANUAL_SUBTITLE,
  requested_language="en",
  source_format=JSON3,
  text_path="transcripts/video123/<raw-request-hash>/canonical.<canonical-hash>.s.txt",
  timed_text_path="transcripts/video123/<raw-request-hash>/source.<safe-metadata-token>.json3",
  source_content_hash="<sha256>",
  source_byte_count=111,
  content_hash="<sha256>",
  char_count=75,
  segment_count=1,
  normalization_version="subtitle-normalization-v1",
  provider="yt-dlp",
  model=None,
  quality_flags=(SPEAKER_LABELS_PRESENT,),
)
```

示例不含临时 URL、正文、绝对路径、Cookie、密钥或 Provider 原始 payload。

## 选择、规范化与质量矩阵

| 维度 | 覆盖 |
|---|---|
| 来源 | 人工全局优先；人工低语言偏好仍早于自动高偏好；人工全部无效后自动回退 |
| 语言 | exact、base、variant；大小写/下划线规范化；实际语言原值保留 |
| 稳定排序 | JSON3 > VTT > SRT；NFC/casefold 轨道名；Provider 原始位置 |
| 格式 | JSON3/VTT/SRT legal + malformed；BOM、非法 UTF-8、CRLF |
| 语义 | speaker、音乐/音效 marker、滚动字幕、连续重复 |
| 阈值 | T-08 每个边界值和第一无效值；marker-only 不计最低有效字符 |
| 失效 | normalizer/quality 版本只改变 canonical key；refresh 才改变 raw request path |

已知质量误判风险：V1 仅按连续完全重复和前一 cue 的词边界前缀去滚动；复杂交错滚动字幕、非标准 speaker 语法和非常规音效 marker 可能被保守保留，符合“不做模糊编辑距离/语义重写”的冻结取舍。

## 文件、SQLite 与恢复证据

- 首次成功：真实 SQLite 中 `subtitle_source`、`transcript_canonical` 两条记录与 Provider call、Job `SUCCEEDED`、Pipeline `TRANSCRIPT_READY` 在一个 `complete_stage` 事务提交。
- 缓存命中：先读两个 Artifact 记录，再验证 DATA 边界、文件存在、SHA-256、metadata token 和 canonical framing；随后 `artifacts=()`、`provider_call=None` 完成当前 Job。
- 文件先成功/DB 失败：注入 `stage.after_artifacts` 失败后 SQLite 回滚为 0 Artifact，确定性 source/canonical 文件保留；下一 attempt 只重新枚举目录，验证本地 raw/canonical，正文 opener 不再调用，再补齐索引并完成 Provider call/Job/Pipeline。
- DB 有记录但文件缺失或篡改：返回安全 `LOCAL_RESOURCE`，不联网修复，不推进 Job/Pipeline。
- SQLite 文件扫描不含 `api/timedtext`、字幕正文、Cookie、密钥或绝对路径。

## yt-dlp 安全证据

- `skip_download=True`，调用 `extract_info(..., download=False)`。
- `ignoreconfig=True`、`usenetrc=False`。
- `writesubtitles=False`、`writeautomaticsub=False`、`writethumbnail=False`、其他媒体/描述/info 写入关闭。
- options 不含 `cookiefile`、`cookiesfrombrowser`、username/password、`netrc_location`、remote components、ffmpeg、postprocessors。
- 仅打开经过 HTTPS/YouTube 或 Googlevideo host 校验的选中字幕 URL；响应分块限流、短读检查并在所有路径关闭。

## 复用与许可证

- `DIRECT`：`yt-dlp==2026.7.4` Python API，安装元数据 `License-Expression: Unlicense`；版本来自既有 `uv.lock`，未修改依赖。
- `DIRECT`：Python 标准库 `json/html/unicodedata/hashlib/pathlib/tempfile/os/re/urllib.request/base64`；项目自有选择、质量、Artifact、恢复和错误语义。
- `REFERENCE`：`imlewc/video-to-subtitle-summary-skill@2c794d74`（MIT）仅参考语言排序、清洗夹具和无下载测试思想；未复制、移植或实质改写其代码，因此无新增版权头/NOTICE。
- `DEFER`：`youtube-transcript-api`，yt-dlp 路径已由离线 Adapter/组合测试满足，无新增依赖依据。
- `REJECT`：subprocess/ffmpeg、Cookie/登录/`.netrc`、remote components、付费/远程 Transcript API、直接 Vault 写入和整套第三方应用。
- 已知传递许可证：锁中 `mutagen==1.48.1` 为 `GPL-2.0-or-later`，本任务未新增；继续由 TASK-014 分发许可证门禁跟踪。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv sync --locked` | PASS | 锁定 34 包；首次沙箱网络阻止，按授权下载锁中 build 包后成功 |
| `uv lock --check` | PASS | `Resolved 34 packages`，锁文件有效 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | `50 passed` |
| `uv run python -m pytest tests/unit/test_subtitle_policy.py` | PASS | `24 passed` |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py` | PASS | `31 passed` |
| `uv run python -m pytest` | PASS | `191 passed` |
| `uv run mypy src` | PASS | `Success: no issues found in 9 source files` |
| `env MYPYPATH=src uv run mypy -c '<SQLite wiring probe>'` | PASS | 真实 `SQLiteStateRepository` 静态满足 `TranscriptRepository` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常 |
| `uv build` | 环境阻止后替代 PASS | 精确命令因隔离 build 尝试联网被拒；未申请额外网络；`uv build --offline` 使用既有锁定缓存成功生成 sdist/wheel |
| sdist/wheel 内容检查 | PASS | 两者均包含 `migrations/001_initial.sql`、`transcripts.py`、`providers/subtitles.py` |
| `git diff --check` | PASS | 无空白错误；提交后再执行固定 base...HEAD 形式 |

## Diff 复核

- 修改文件：仅任务允许的 8 个路径组。
- 是否存在任务范围外修改：否；完整 status/路径枚举未见范围外文件。
- 是否存在生成文件或格式化噪声：否；build、pytest、mypy、Ruff 生成的忽略产物已清理，`.venv` 保留为已授权锁定环境且不提交。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否；`pyproject.toml`/`uv.lock` 基线 SHA-256 仍为 `49ca…fa9` / `81a3…c49`。
- 多轴自审：正确性、可读性、架构、安全和性能均复核；关闭了严格 VTT header、目录 404、响应打开后 timeout、危险 redirect、写前 DATA 边界和 discovery 异常耦合问题，无未解决 Critical/Important。

## 失败、跳过与风险

- 已解决失败：
  - 初次 `uv sync --locked` 因沙箱网络阻止 `uv-build`，按授权只下载锁中包后通过。
  - TDD RED：缺失新领域类型、`transcripts.py`、Adapter/Service；逐检查点实现后 GREEN。
  - 两个测试夹具参数相互影响导致边界测试误报；修正测试隔离后通过。
  - mypy 的私有 yt-dlp 返回值/HTTP header 类型与 Ruff import 顺序问题已按窄类型修复。
  - `mypy -c` 首次解析到未标记 `py.typed` 的已安装包；设置 `MYPYPATH=src` 后真实本地静态 wiring probe 通过。
  - 精确 `uv build` 因隔离环境尝试联网失败；遵守“build 不追加网络授权”，使用已缓存构建依赖的 `uv build --offline` 成功。
- 跳过检查及原因：真实 YouTube/字幕冒烟未运行，因为任务包明确未授权；其余任务级离线门禁均执行。
- 剩余风险：
  - 未获授权，未运行真实 YouTube/字幕冒烟；上游轨道 payload/临时 URL 漂移由 TASK-013 真实验收继续覆盖。
  - 未索引崩溃文件只能以确定性路径、严格解析、质量和重新计算 SHA-256 验证，无法与已消失的临时远端 URL 做字节身份对照；符合 ADR-003/T-10 的 at-most-once best effort，不声称严格 exactly-once。
  - 非标准 VTT/SRT 扩展和未列入 marker 词表的音效标签将保守保留或使候选无效，不做模糊修复。
- `DECISION NEEDED`：`None`

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：最终回传
- 复现/验证说明：默认测试完全离线；只使用固定 JSON/VTT/SRT、Fake yt-dlp/HTTP、临时 DATA 和临时 SQLite。

## Reviewer 结论

- Reviewer agent/session：由主控启动全新独立 Codex 会话
- 审查 commit：
- 重新运行的检查：
- Findings：
- Verdict：`APPROVE | REJECT`
- 未解决 P0/P1：

## 主控验收

- Orchestrator：
- Verdict：`ACCEPT | REJECT`
- 依据：
- 批准整合的 commit：

## 整合结果

- Integrator：
- 主线 commit：
- 整合后检查：
- 最终状态：`DONE | BLOCKED`
