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

- Reviewer agent/session：`Codex`，2026-07-16 全新独立 Reviewer 会话
- 固定审查对象：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- 固定 base/parent：`b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Review evidence commit：本 Reviewer 节所在提交；SHA 由提交后回传

### 基线、授权与范围门禁

- main 动态 review authorization：
  `095380b7263aa3d04c7d133c1e17d8f4f2fea082`，其唯一父提交为
  `38f1caa1c957b4b305afbe0f87c2e082b1ffc929`；main 为 `main` 且干净。
- source 为 `codex/task-005-subtitle-pipeline`，HEAD 精确为固定实现 SHA，唯一父提交
  为固定 base，工作区开审时干净。
- Git 身份为 `Mozhu <huangbuqubunao@gmail.com>`，
  `user.useConfigOnly=true`。
- 相对 base 只有一个非 merge 实现提交；产品 Diff 精确为任务包规定的 11 个文件，
  没有 review commit、额外产品文件或未跟踪提交内容。
- `pyproject.toml` SHA-256 在 base/head 均为
  `49ca5e31c32d8dbadc3770901f227ed9dd95237a1ac1cb0b977019c5f13d1fa9`；
  `uv.lock` 均为
  `81a3fd81e51cac69ca4d072c481b63cc9a265b491eab9c65ea782963f85a9c49`。
- 未修改 `state.py`、migration、`complete_stage`、TASK-004 Adapter、配置、CLI、
  任务/ADR、依赖或锁文件；未发现 `.env`、凭证、Cookie、媒体、数据库、缓存或构建
  产物进入 Diff。

### 规定命令复跑

| 命令 | 结果 | Reviewer 证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 34 packages` |
| `uv sync --locked` | PASS | `Checked 30 packages`，无重锁或依赖变化 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | `50 passed` |
| `uv run python -m pytest tests/unit/test_subtitle_policy.py` | PASS | `24 passed` |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py` | PASS | `31 passed` |
| `uv run python -m pytest` | PASS | `191 passed` |
| `uv run mypy src` | PASS | 与另一个 mypy 探针并发的首次运行触发 mypy 2.3.0 internal error；无并发按原命令顺序复跑为 `Success: no issues found in 9 source files` |
| `env MYPYPATH=src uv run mypy -c '<SQLite wiring>'` | PASS | `SQLiteStateRepository` 静态满足 `TranscriptRepository` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常 |
| `uv build --offline` | PASS | 成功生成 sdist/wheel；随后只清理本轮 `dist/` |
| sdist/wheel 内容检查 | PASS | 均含 `migrations/001_initial.sql`、`transcripts.py`、`providers/subtitles.py` |
| `git diff --check b28f52d...98d1970...` | PASS | 无空白错误 |

规定门禁最终均有通过证据，但通过测试不能覆盖下述独立反例。

### 独立探针 A-F

#### A. 公共领域契约

- PASS：`TranscriptFetchResult` 精确为
  `TranscriptReady | TranscriptionRequired`，判别值分别为 `ready` 与
  `transcription_required`。
- PASS：`SubtitleFormat` 精确 3 个值；`TranscriptQualityFlag` 精确 3 个值；
  `TranscriptionReason` 精确 3 个值；`ErrorCode` 仍为既有 8 个值。
- PASS：公共导出和注解哨兵未发现自由 `dict`、`Any`、宽 `object` 或自由字符串枚举。
- PASS：字幕 Artifact 强制 `requested_language`、`source_format` 和
  `timed_text_path`；Whisper 强制 `requested_language=None`、
  `source_format=None`。SHA-256、DATA-relative 路径、非负计数和唯一 quality flags
  由领域校验拒绝非法输入。

#### B. 选择、解析与质量

- PASS：独立表驱动排序确认人工全局优先、配置语言顺序、exact/base/variant、
  JSON3/VTT/SRT 和稳定 tie-break；人工候选损坏后自动候选可成功回退。
- PASS：独立 JSON3/VTT/SRT 探针确认 BOM、CRLF、单次 HTML decode、NFC、单 speaker、
  marker 与固定滚动去重的基本路径。
- PASS：T-08 七组边界均接受边界值并拒绝第一个非法值；refresh 只改变 raw hash，
  normalization version 只改变 canonical hash。
- FAIL：合法多 speaker VTT
  `<v Alice>...</v> <v Bob>...</v>` 被规范化为单一 `Alice:` 前缀，`Bob:` 标签丢失。
- FAIL：合法 cue identifier `NOTEworthy-cue-id` 被 `startswith("NOTE")` 当作 NOTE
  控制块整段丢弃，最终以质量失败拒绝。两者均属于静默语义改写/内容丢失。

#### C. yt-dlp、HTTP 与安全边界

- PASS：独立捕获确认 `extract_info(..., download=False)`、`skip_download=True`、
  `ignoreconfig=True`、`usenetrc=False`，且无 Cookie/登录、remote components、
  ffmpeg、postprocessor 或媒体写入选项。
- PASS：HTTP、loopback、userinfo、非 443 端口、fragment、编码 hostname、IPv6
  loopback 和非 allowlist hostname 均在 opener 前以 `INVALID_RESPONSE` 拒绝；
  symlink DATA 逃逸以 `PERMISSION_DENIED` 拒绝且未写出界。
- FAIL：真实 `urllib` 使用的 `HTTPMessage` 不是 `Mapping`。声明
  `Content-Length: 100` 但只返回 5 bytes 的响应被当作成功读取，未映射
  `TRANSIENT_NETWORK` 短读。
- FAIL：只含 `ext="ttml"` 的目录 payload 被静默跳过并形成 0 tracks，而不是
  `INVALID_RESPONSE`；下游会误报 `NO_TRACKS`。
- FAIL：100,000 字符的 track name 和 100,024 字符的 URL 均被接受，目录的 track
  数量也无显式上限，不满足 Reviewer 包要求的 URL/track/payload 长度边界。
- FAIL：malformed JSON3 的 `JSONDecodeError.doc` 与非法 UTF-8 的
  `UnicodeDecodeError.object` 仍保留完整原始字幕字节；异常 cause/context 可泄漏正文。

#### D. Artifact、缓存与真实 SQLite 恢复

- PASS：独立临时 SQLite 首次成功写入两个 Artifact、Provider call，并原子推进 Job
  与 Pipeline。
- PASS：verified cache 命中在禁用网络枚举和令 `normalize_subtitle` 失败的条件下仍
  成功，以空 Artifact completion 推进新 Job。
- PASS：refresh generation 重新枚举/读取并生成新路径，旧文件仍存在。
- PASS：既有集成门禁确认缺失/篡改文件 fail-closed；独立 symlink 探针也未写出 DATA。
- FAIL：`complete_stage` 注入失败后 Provider call 保持 `PENDING`，默认租约仍有
  300 秒；按默认 base delay 2 秒进入下一 Job attempt 时，确定性文件虽已存在，仍返回
  retryable `PROVIDER_UNAVAILABLE`，无法立即补索引。
- FAIL：已有 `PENDING` Provider reservation 时，Service 先执行一次目录枚举，再检查
  reservation，产生重复远端 Provider call。
- FAIL：首次 `ALL_CANDIDATES_INVALID` 正确返回具名结果并把 Provider call 记为
  `FAILED_FINAL`；同一输入第二次却重新枚举并返回 retryable
  `PROVIDER_UNAVAILABLE`，不再是具名转写需求。
- FAIL：有效 raw Artifact 已索引但当前 canonical key 不存在时，Service 在零网络、
  零重新规范化之前直接返回 `LOCAL_RESOURCE: cached canonical transcript index is
  missing`。因此 normalization/quality version 变化不能仅失效 canonical 并从 raw
  重建。

#### E. 可读性、架构与规模

- `transcripts.py` 为 1,664 行、64 个定义；`SubtitleAcquisitionService` 563 行，
  `fetch` 284 行，`_load_cached` 163 行，`_atomic_write` 96 行。
- 同一模块同时承担排序、三种格式解析、语义规范化、质量策略、key/path 编码、文件
  原子写、缓存恢复、Provider reservation 和 Pipeline/Job 完成。上述 P1 状态组合与
  边界遗漏说明该聚合已显著增加证明难度。
- integration test 9 次调用私有 `_bind_test_hooks`，2 次修改 Repository 私有
  `_inject_failure`。测试同时包含真实 SQLite 外部行为证据，因此不是纯实现镜像，但
  Adapter 测试仍明显耦合私有生产 hook。
- 文件和正文读取均有 5 MB/4 MB 等硬上限，未发现无界全媒体读取；目录 track/name/URL
  本身仍无边界，见 P1-3。

#### F. 范围、复用与许可证

- PASS：直接运行依赖只复用既有 `yt-dlp==2026.7.4` 和标准库；未新增或升级依赖。
- PASS：本机安装元数据显示 yt-dlp `License-Expression: Unlicense`。
- PASS：未发现复制外部项目代码、版权头或未知来源片段；
  `imlewc/...@2c794d74` 仅作为测试思想 `REFERENCE` 记录。
- PASS：`youtube-transcript-api` 保持 `DEFER`；subprocess/ffmpeg、认证、真实网络、
  媒体、Vault 和密钥路径未进入实现。
- PASS：`mutagen==1.48.1` 仍为既有传递依赖，许可证为
  `GPL-2.0-or-later`；本任务未扩大风险，继续由 TASK-014 分发门禁处理。

### Acceptance matrix

| AC | 结论 | 独立 Reviewer 依据 |
|---|---|---|
| AC-1 固定夹具覆盖选择与损坏场景 | PASS | 规定测试与独立排序/回退探针通过 |
| AC-2 成功缓存不重复下载/规范化 | PASS | verified cache 在网络/normalizer 禁用时仍命中 |
| AC-3 具名转写需求与网络错误区分 | FAIL | `ALL_CANDIDATES_INVALID` 第二次变为 retryable `PROVIDER_UNAVAILABLE` |
| AC-4 校验缓存并空 Artifact completion | PASS | 真实 SQLite cache Job/Pipeline 原子推进 |
| AC-5 安全路径、原子恢复与脱敏 | FAIL | 快速恢复被 Provider 租约阻塞；exception cause 保留字幕正文；真实 headers 短读未识别 |

### ADR-006 T-01 至 T-15

| 条款 | 结论 | 依据 |
|---|---|---|
| T-01 | PASS | 人工/自动、语言、匹配、格式、名称、位置排序通过 |
| T-02 | PASS | exact/base/variant、大小写与 `_` 规范化通过 |
| T-03 | PASS with P1 in T-11 | 只生成三种允许候选且无媒体/认证副作用；不支持格式的错误分类见 T-11 |
| T-04 | FAIL | 重复 all-invalid 不再返回 `TranscriptionRequired` |
| T-05 | PASS | 具名联合、Artifact 字段、枚举与 8 个 ErrorCode 符合 |
| T-06 | FAIL | 合法 `NOTEworthy` cue ID 被误删 |
| T-07 | FAIL | 多 speaker 标签被合并并丢失 Bob 身份 |
| T-08 | PASS | 全部冻结阈值边界前后通过 |
| T-09 | FAIL | canonical version 失效不能从 verified raw 重建 |
| T-10 | FAIL | DB 失败后的下一快速 attempt 被遗留 Provider 租约阻塞 |
| T-11 | FAIL | 真实 `HTTPMessage` 短读被接受；不支持格式被误分类；payload 无长度边界 |
| T-12 | PASS | 仅既有 yt-dlp/标准库，无依赖变化 |
| T-13 | PASS | 未新增 manifest；source metadata/key/path 可逆且计数可重算 |
| T-14 | PASS for basic path | 首次与 cache completion 使用既有 Repository；未修改 `state.py`，但恢复状态机 P1 仍见 T-10 |
| T-15 | PASS | 普通 cache 零网络；refresh 新路径且保留旧 Artifact |

### 五轴审查

| 轴 | 结论 | 说明 |
|---|---|---|
| correctness | FAIL | parser 语义丢失、短读误分类、重复 all-invalid 结果漂移、canonical 失效失败 |
| readability | FAIL（P2） | 超大 Service/fetch 与跨层职责使状态组合难以审查 |
| architecture | FAIL | 外部枚举发生在 Provider reservation 之前；文件/DB 失败未同步释放调用状态 |
| security | FAIL | exception cause 泄漏正文；目录 payload/URL/name 无完整长度门禁 |
| performance | FAIL | unbounded track metadata 与并发/重复目录枚举可放大内存和网络成本 |

### Findings

#### P1-1：异常 cause/context 保留原始字幕正文

- 文件/行号：`src/youtube_intel/transcripts.py:382`、`:631`
- 可复现输入：带私有 marker 的 malformed JSON3；带同一 marker 的非法 UTF-8 bytes。
- 期望：`InvalidSubtitleCandidate` 及其 cause/context/traceback 不持有字幕正文。
- 实际：`JSONDecodeError.doc` 含完整 JSON3，`UnicodeDecodeError.object` 含完整原始
  bytes。
- 影响：任何记录 exception chain、traceback 或调试对象的路径都可能泄漏字幕正文，
  违反 ADR-006 和 Reviewer 安全门禁。

#### P1-2：VTT parser 静默丢失合法 speaker/cue 语义

- 文件/行号：`src/youtube_intel/transcripts.py:431`、`:469`
- 可复现输入：
  1. `<v Alice>...</v> <v Bob>...</v>`；
  2. cue identifier `NOTEworthy-cue-id` 后跟合法时间行与正文。
- 期望：两个 speaker label 均保留；合法 cue ID 不被当成 NOTE 控制块。
- 实际：输出只有 `Alice:`，`Bob:` 丢失；`NOTEworthy` 整块被忽略并最终质量失败。
- 影响：规范文本发生不可见语义重写或内容丢失，直接违反 T-06/T-07。

#### P1-3：Adapter 未完整执行短读、格式和 payload 长度 fail-closed

- 文件/行号：`src/youtube_intel/providers/subtitles.py:215`、`:316`、`:576`
- 可复现输入：
  1. `HTTPMessage(Content-Length=100)` + 5-byte body；
  2. 唯一轨道 `ext="ttml"`；
  3. 100,000 字符 name 与 100,024 字符 allowlist URL。
- 期望：短读为 retryable `TRANSIENT_NETWORK`；不支持格式为 nonretryable
  `INVALID_RESPONSE`；URL/track/payload 有显式长度边界。
- 实际：短读作为成功 body 返回；不支持格式静默变为 0 tracks；超长字段被接受。
- 影响：截断响应被误当坏字幕而非网络错误，Provider payload 可触发资源放大，错误语义
  不符合 T-11。

#### P1-4：Provider-call 状态机破坏幂等、并发与下一 attempt 恢复

- 文件/行号：`src/youtube_intel/transcripts.py:1389`、`:1414`、`:1570`、`:1618`
- 可复现输入：
  1. 预先存在未过期 `PENDING` reservation，再调用 `fetch`；
  2. `complete_stage` 在 Artifact 后注入失败，按默认 2 秒退避重试；
  3. 同一 all-invalid 输入连续调用两次。
- 期望：检查 reservation 后再联网；下一 attempt 使用确定性文件补索引；重复
  all-invalid 稳定返回具名结果且不误重试。
- 实际：每次先枚举目录；DB 失败后 reservation 保持 300 秒 `PENDING`，2 秒重试被
  `PROVIDER_UNAVAILABLE` 阻塞；第二次 all-invalid 也变成 retryable
  `PROVIDER_UNAVAILABLE`。
- 影响：并发重复调用、恢复延迟或耗尽 Job attempts、错误分类和 Pipeline 推进不稳定；
  违反 AC-3、T-04、T-10 及 D 轴门禁。

#### P1-5：canonical-only 版本失效不能从 verified raw 重建

- 文件/行号：`src/youtube_intel/transcripts.py:1141`
- 可复现输入：有效 raw Artifact/文件存在且哈希通过，但当前 normalization/quality
  版本对应的 canonical key 不存在。
- 期望：不重新下载 raw，使用 verified raw 重新规范化并写入新的 canonical key/path。
- 实际：在网络和 normalizer 前直接返回 nonretryable `LOCAL_RESOURCE`。
- 影响：任一规范化或质量版本升级都会使已有字幕无法继续，违反 T-09 分层失效契约。

#### P2-1：职责聚合和私有测试 hook 增加维护风险

- 文件/行号：`src/youtube_intel/transcripts.py:1073`、
  `src/youtube_intel/providers/subtitles.py:385`
- 实际：563 行 Service/284 行 `fetch` 同时编排缓存、Provider、文件和 Repository；
  Adapter 的离线测试 9 次依赖私有 `_bind_test_hooks`。
- 影响：状态组合难以局部证明，上述多个 P1 已落在跨职责边界。建议修复 P1 时至少把
  parsing/quality、artifact cache/file store、Provider reservation orchestration
  分成可独立验证的内部组件；该拆分建议本身为 P2，不单独决定 Verdict。

- P0：无
- P1：5 个，均未解决
- P2：1 个
- P3：无

### TASK-006 最终契约复核

TASK-006 可继续以 ADR-006 的公共形状设计，但不得在 TASK-005 修复并重新审查前整合：

- `TranscriptProvider.fetch(video: VideoMetadata, language_preferences: Sequence[str])`
  返回 `TranscriptReady | TranscriptionRequired`。
- `TranscriptReady`：`outcome="ready"`、`artifact`、`call`。
- `TranscriptionRequired`：`outcome="transcription_required"`、固定 `reason`、
  `call`、非负 `attempted_track_count`。
- `TranscriptArtifact` 精确字段：
  `video_id`、`language`、`source_type`、`requested_language`、`source_format`、
  `text_path`、`timed_text_path`、`source_content_hash`、`source_byte_count`、
  `content_hash`、`char_count`、`segment_count`、`normalization_version`、
  `provider`、`model`、`created_at`、`quality_flags`。
- manual/auto：`requested_language`、`source_format`、`timed_text_path` 必须非空；
  `source_format` 只允许 JSON3/VTT/SRT。
- Whisper：`requested_language=None`、`source_format=None`；`timed_text_path` 仍是公共
  可选安全 DATA-relative 路径，`text_path`、两个 SHA-256、字节/字符/segment 计数、
  `normalization_version`、provider/model 元数据仍存在。
- `quality_flags` 只允许三个冻结诊断枚举；失败质量不得进入 ready Artifact。
- Provider 调用元数据只位于结果的 `call`；Artifact 不包含临时 URL、artifact key 或
  绝对路径。
- 未修改 ADR-007；公共契约形状本身未发现需要新决策的冲突。

### Verdict、跳过项与剩余风险

- Verdict：`REJECT`
- 未解决 P0/P1：上述 5 个 P1。
- Skipped checks：未运行真实 YouTube/字幕、RSS、Cookie/登录/`.netrc`、remote
  components、ffmpeg、媒体、真实 Vault 或密钥路径；这些均明确未授权。规定离线门禁
  无跳过。
- Remaining risks：真实上游 yt-dlp payload/URL 漂移仍待 TASK-013；mutagen GPL 分发
  风险仍待 TASK-014；复杂非标准字幕的保守误判仍存在。当前首先必须由原 Implementer
  修复 P1 并生成新实现 commit。
- Scope/red-line/reuse review：PASS；REJECT 仅由实现正确性、安全、恢复和维护性问题
  触发，不是范围、依赖、许可证或变更行数自动触发。
- Decision needed：`None`；现有 ADR-006 已足以定义期望行为，退回原 Implementer 修复。

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
