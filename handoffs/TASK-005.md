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

## Implementer Correction 1

- Implementer/session：原 TASK-005 Codex Implementer，2026-07-16 修正会话
- 修正起点：Reviewer evidence
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- 被修正实现：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- 修正提交：本节所在提交；SHA 由提交后回传
- 范围：仅关闭 Reviewer 的 P1-1 至 P1-5，并在原文件内完成 P2 要求的具名 helper
  提取；未承担重新 Review、main 整合或任务状态修改

### RED 与 GREEN 证据

先只加入 Reviewer 反例、未改生产代码：

| 分片 | RED 命令与结果 | 关键失败 |
|---|---|---|
| P1-1/P1-2 | `uv run python -m pytest tests/unit/test_subtitle_policy.py -q` → `4 failed, 26 passed` | JSON3/UTF-8 异常链保留 payload；多 voice 丢失 Bob；`NOTEworthy` cue 被删除 |
| P1-3/P1-4/P1-5 与嵌套 P1-1 | `uv run python -m pytest tests/integration/test_subtitle_provider.py -q` → `20 failed, 30 passed` | 真实 `HTTPMessage` 短读与目录边界失守；Provider 状态在枚举后检查；租约不释放；all-invalid 漂移；canonical 缺失直接 `LOCAL_RESOURCE` |

实现后：

| 分片 | GREEN 证据 |
|---|---|
| P1-1 异常链脱敏 | malformed JSON3、非法 UTF-8、unindexed recovered raw → Service 三条路径均验证 message、cause、context、格式化 traceback 和底层 `doc`/`object` 不含 marker、raw bytes、临时 URL 或绝对路径 |
| P1-2 VTT 语义 | 多 voice、单 voice、无 voice、NOTE block、`NOTEworthy-cue-id` 全部通过；正文顺序不变 |
| P1-3 Adapter fail-closed | 真实 `HTTPMessage` 大小写、短读、非法/重复/负数/超限 Content-Length；unsupported-only/mixed/结构非法；512 tracks、name 1000、language 128、ext 32、URL 8192 的边界与 +1 全部通过 |
| P1-4 Provider 状态与恢复 | active PENDING、not-due FAILED_RETRYABLE、重复 all-invalid、两个真实 SQLite Service 竞争、stage failure 后 2 秒重试全部通过 |
| P1-5 canonical-only 失效 | verified raw 本地重建、零枚举、零正文 opener、旧 raw/canonical 保留、新 key/path/Job 可追踪、重复命中不重新规范化全部通过；追加 raw 缺失/篡改/provider metadata 反例时先为 `1 failed, 2 passed`，修正 metadata 验证后为 `3 passed` |

最终 focused 结果：

- `tests/unit/test_subtitle_policy.py`：`30 passed`
- `tests/integration/test_subtitle_provider.py`：`53 passed`

### Provider-call 状态矩阵

| 既有状态 | 目录枚举 | 正文读取 | 结果/动作 |
|---|---:|---:|---|
| 无记录、无 raw cache | 允许；用于区分 no tracks/no match | 仅 ranked candidate 且 reservation acquired 后允许 | 首次正常流程 |
| active `PENDING` | 0 | 0 | retryable `PROVIDER_UNAVAILABLE` |
| not-due `FAILED_RETRYABLE` | 0 | 0 | retryable `PROVIDER_UNAVAILABLE` |
| expired `PENDING` / due `FAILED_RETRYABLE` | 状态到期后允许；正文前仍须取得 reservation | 若确定性 source 文件存在则为 0 | 验证文件并补索引 |
| `SUCCEEDED` | 0 | 0 | 只走 verified raw/canonical cache；当前 canonical 缺失则从 raw 重建 |
| 本任务记录的 all-invalid `FAILED_FINAL` | 0 | 0 | 稳定 `ALL_CANDIDATES_INVALID`，`attempted_track_count=0`，call 只由安全 record、当前 Adapter 版本和稳定时间构造 |
| reservation 未取得 | 不再新增调用 | 0 | 按 record 状态返回 cache、负结果或安全 Provider 错误 |

`complete_stage` 失败时，原始 stage persistence 异常不被替换；Service 在抛出
retryable `LOCAL_RESOURCE` 前调用现有
`fail_provider_call(retryable=True, available_at=now)`，清空 owner/lease。故默认
300 秒 Provider lease 不再阻塞默认 2 秒 Job backoff 后的下一 attempt。失败记录本身
失败时仍保留并抛出原始 stage persistence 错误。

### verified raw → canonical 重建

- raw Artifact 必须通过 video、kind、DATA root、deleted 状态、raw producer version、
  当前 Adapter provider、空 model、`transcripts/<video>/<raw hash>/` 父路径、
  metadata token、格式扩展名、文件大小和 SHA-256 全部验证。
- 当前 normalization/quality version 的 canonical key 不存在时，不访问 Adapter；
  对 verified raw 执行当前 parser、normalizer 和 quality policy。
- 只写当前 deterministic canonical 文件和当前 Job 的
  `TRANSCRIPT_CANONICAL` Artifact；`provider_call=None` 完成阶段。
- 原 raw Artifact 的 `job_id`、key、path 和 provider metadata 不修改、不重绑定；
  旧 raw、旧 canonical Artifact 与文件均保留。
- 新 canonical 允许属于当前 Job，不再错误要求与历史 raw Artifact 同一 Job；
  provider/source 绑定仍验证一致。
- raw 缺失、篡改、路径/metadata/producer 不一致或当前 policy 下无效，继续
  nonretryable `LOCAL_RESOURCE` fail-closed。
- Provider/selection/format/refresh 仍进入 raw request hash；normalization/quality
  version 只进入 canonical request hash。

### P2 局部可读性处理

- `transcripts.py`：提取 `_is_vtt_control_block`、`_parse_vtt_block`、
  `_preserve_vtt_voice_spans`、`_normalize_recovered_raw`、
  `_preflight_provider_call`、`_existing_provider_outcome`、
  `_recorded_all_invalid_result` 和 `_rebuild_canonical_from_raw`。
- `providers/subtitles.py`：提取 `_MappedDirectory`、统一目录字段/数量验证和
  `_content_length`。
- `SubtitleAcquisitionService.fetch` 从 Reviewer 记录的 284 行降为 280 行；没有新增
  产品模块、公开测试 hook、wrapper、`cast`、`type: ignore` 或宽 Repository shim。
- `TranscriptRepository` 只增加现有
  `SQLiteStateRepository.get_provider_call(request_hash)` 的窄具名只读方法；
  `state.py`、Schema/migration 和 `complete_stage` 均未修改。

### 修正后完整检查

| 命令 | 结果 |
|---|---|
| `uv lock --check` | PASS：`Resolved 34 packages` |
| `uv sync --locked` | PASS：`Checked 30 packages`，无依赖或锁变化 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS：`50 passed` |
| `uv run python -m pytest tests/unit/test_subtitle_policy.py` | PASS：`30 passed` |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py` | PASS：`53 passed` |
| `uv run python -m pytest` | PASS：`219 passed` |
| `uv run mypy src` | PASS：9 source files |
| `env MYPYPATH=src uv run mypy -c '<SQLite wiring>'` | PASS：`SQLiteStateRepository` 静态满足扩展后的 `TranscriptRepository` |
| `uv run ruff check .` | PASS |
| `uv run python -m youtube_intel --help` | PASS |
| `uv build --offline` | PASS：生成 sdist/wheel |
| sdist/wheel 内容 | PASS：均含 `migrations/001_initial.sql`、`transcripts.py`、`providers/subtitles.py`；随后只清理本轮 `dist/` |
| `git diff --check`（提交前等价工作区检查） | PASS |

提交后仍按修正包精确执行
`git diff --check 515c34894bb138115a4658d962fb5ef0aa7d9d80...HEAD`，结果随最终回传。

### Diff、依赖、复用与红线复核

- Correction 工作区 Diff 仅为：
  `src/youtube_intel/transcripts.py`、
  `src/youtube_intel/providers/subtitles.py`、
  `tests/unit/test_subtitle_policy.py`、
  `tests/integration/test_subtitle_provider.py` 和本 handoff；均属于允许的 6 个路径组。
- 完整 `b28f52d...HEAD` 产品范围仍精确属于原批准的 8 个路径组、11 个文件。
- `pyproject.toml` SHA-256 仍为
  `49ca5e31c32d8dbadc3770901f227ed9dd95237a1ac1cb0b977019c5f13d1fa9`；
  `uv.lock` 仍为
  `81a3fd81e51cac69ca4d072c481b63cc9a265b491eab9c65ea782963f85a9c49`。
- 未修改 `domain.py`、`tests/unit/test_contracts.py`、`state.py`、migration、配置、
  CLI、discovery/youtube Adapter、任务/ADR、依赖或锁文件。
- 复用决策不变：直接复用既有 `yt-dlp==2026.7.4` 与标准库；外部 MIT 项目仍只参考
  测试思想，未复制代码；`youtube-transcript-api` 继续 DEFER；subprocess/ffmpeg、
  auth、remote component、媒体、Vault 继续 REJECT。
- 未运行真实 YouTube/字幕、RSS、Cookie/登录/`.netrc`、remote components、
  ffmpeg、媒体、真实 Vault 或密钥路径；这些均未授权且本修正不需要。
- Remaining risks：真实上游 yt-dlp payload 漂移仍待 TASK-013；复杂非标准字幕仍采取
  保守 fail-closed；既有 mutagen GPL 分发门禁仍待 TASK-014。本修正未扩大这些风险。
- Decision needed：`None`。

## 第二次独立 Reviewer 结论

- Reviewer agent/session：`Codex`，2026-07-17 全新独立第二次 Reviewer 会话
- 固定审查对象：
  `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
- Correction parent：
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Implementation base：
  `b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Review evidence commit：本节所在提交；SHA 由提交后回传

### 授权、父链与范围门禁

- main 动态 review authorization 为
  `a3954bf782430678fa5e0040084bf0d907a52d05`，其唯一父提交为
  `4df3ff13732e98665732e2ba7bfc8b90c4c141aa`；开审时 main 位于该提交、
  分支为 `main` 且干净。
- source 开审时位于
  `codex/task-005-subtitle-pipeline@55156f9f53a610ccbf9c8806f19f19f2c16bb1cf`
  且干净；Git 身份为 `Mozhu <huangbuqubunao@gmail.com>`，
  `user.useConfigOnly=true`。
- 父链逐项通过：
  - `98d19700818bcae14efc412aaaaeb6eed97a1535` 唯一父提交为
    `b28f52d0e4950f78dba315d4afe211ea5f75b93c`；
  - `515c34894bb138115a4658d962fb5ef0aa7d9d80` 唯一父提交为
    `98d19700818bcae14efc412aaaaeb6eed97a1535`，且只修改本 handoff；
  - `55156f9f53a610ccbf9c8806f19f19f2c16bb1cf` 唯一父提交为
    `515c34894bb138115a4658d962fb5ef0aa7d9d80`，不是 amend/rebase/merge。
- Correction Diff 精确为 5 个文件：
  `handoffs/TASK-005.md`、
  `src/youtube_intel/providers/subtitles.py`、
  `src/youtube_intel/transcripts.py`、
  `tests/integration/test_subtitle_provider.py`、
  `tests/unit/test_subtitle_policy.py`。
- 完整 `base...Correction` Diff 精确为原批准的 11 个文件，仍只属于 8 个路径组。
- Correction 未修改 `domain.py`、contracts test、`state.py`、migration、配置、CLI、
  discovery/youtube Adapter、`pyproject.toml` 或 `uv.lock`。
  `pyproject.toml`/`uv.lock` 相对 base 的 SHA-256 分别保持
  `49ca5e31c32d8dbadc3770901f227ed9dd95237a1ac1cb0b977019c5f13d1fa9` /
  `81a3fd81e51cac69ca4d072c481b63cc9a265b491eab9c65ea782963f85a9c49`。
- 未发现真实数据、凭证、Cookie、媒体、数据库、cache 或构建产物进入提交。
  Correction 的 `1,489` 行规模和 `219` tests 均未被单独用作 Verdict 依据。

### 规定命令独立复跑

| 命令 | 结果 | 第二次 Reviewer 证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 34 packages` |
| `uv sync --locked` | PASS | `Checked 30 packages`，无重锁或依赖变化 |
| `uv run python -m pytest tests/unit/test_contracts.py` | PASS | `50 passed` |
| `uv run python -m pytest tests/unit/test_subtitle_policy.py` | PASS | `30 passed` |
| `uv run python -m pytest tests/integration/test_subtitle_provider.py` | PASS | `53 passed` |
| `uv run python -m pytest` | PASS | `219 passed` |
| `uv run mypy src` | PASS | `Success: no issues found in 9 source files` |
| `env MYPYPATH=src uv run mypy -c '<SQLite wiring>'` | PASS | `SQLiteStateRepository` 静态满足 `TranscriptRepository` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run python -m youtube_intel --help` | PASS | CLI help 正常 |
| `uv build --offline` | PASS | 成功生成 sdist/wheel |
| sdist/wheel 内容检查 | PASS | 均含 `migrations/001_initial.sql`、`transcripts.py`、`providers/subtitles.py` |
| `git diff --check b28f52d...55156f9...` | PASS | 无空白错误 |

构建前确认 `dist/` 不存在；内容核验后只清理本轮 ignored `dist/`。未清理其他
`.pytest_cache`、`.mypy_cache` 或 `__pycache__`。

### P1 closure probes R1-R5

以下独立探针均以 `uv run python - <<'PY'` 在 source worktree 直接运行，只使用
独立 marker、Fake transport、受控时钟、`TemporaryDirectory` 和真实临时
`SQLiteStateRepository`；没有修改产品代码或测试。

#### R1：异常链与正文脱敏 — FAIL

- PASS：malformed JSON3 与非法 UTF-8 在 `normalize_subtitle` 边界产生的
  `InvalidSubtitleCandidate` 均为 `__cause__ is None`、
  `__context__ is None`，message/args/traceback 不含独立 marker。
- PASS：带独立 marker 的损坏人工候选可继续回退到合法自动候选；只持久化合法候选，
  marker 未进入 DATA 文件或 SQLite。
- PASS：unindexed recovered raw 的现有修复路径把解析失败转换为安全
  `LOCAL_RESOURCE`。
- FAIL：真实 `YtDlpSubtitleAdapter` 的目录错误通过 Service 外层抛出时，
  `TranscriptError.__context__` 仍为原始 `DownloadError`。独立输入同时含 marker、
  临时字幕 URL 和绝对路径，三者均可从异常图读取。
- FAIL：把已索引 canonical 文件替换为含 marker 的非法 UTF-8，并同步其 DB hash 后，
  Service 返回安全 message，但 `TranscriptError.__context__` 仍为
  `UnicodeDecodeError`，其 `.object` 保留 canonical 原始 bytes。
- 结论：Correction 只关闭了 parser/recovered-raw 的局部异常链，没有满足“Service
  外层、所有 cause/context、临时 URL、绝对路径和正文均脱敏”的 R1。

#### R2：VTT speaker/cue 语义 — PASS

- 单 voice、多 voice、无 voice、voice 位于嵌套 `<c>/<b>/<i>` 样式内均保留 speaker
  身份和正文顺序。
- `NOTE`、`NOTE text`、`NOTE\ttext` 控制块均被忽略；
  `NOTEworthy-cue-id`、`NOTES-cue-id` 等合法 cue ID 保留。
- cue ID、时间行、正文、speaker 与 `[Music]`/`[Applause]` marker 的组合顺序和
  `SPEAKER_LABELS_PRESENT`/`NON_SPEECH_MARKERS_PRESENT` flags 均正确。

#### R3：Adapter fail-closed — PASS

- 使用真实 `http.client.HTTPMessage` 独立覆盖 Content-Length 大小写、缺失、合法、
  短读、负数、非数字、多个相同值、多个冲突值和超过正文上限。
- 短读为 retryable `TRANSIENT_NETWORK`；非法/重复 header 为 nonretryable
  `INVALID_RESPONSE`；header/实际正文超限为无效候选 `RESOURCE_LIMIT`。
- 轨道数 `512/513`、name `1000/1001`、language `128/129`、ext `32/33`、
  URL `8192/8193` 边界全部符合；language/ext/URL/name 非字符串均 fail-closed。
- unsupported-only 为 nonretryable `INVALID_RESPONSE`；支持/不支持混合只保留支持
  格式，但不支持项结构非法时整个目录拒绝。
- 危险初始 URL 和危险 redirect 均在正文读取前拒绝；所有成功/失败 response 均关闭，
  header/body marker 未进入短读异常图。

#### R4：Provider-call 幂等、竞态与快速恢复 — FAIL

- PASS：无记录时允许目录枚举，并在正文读取前已持有 `PENDING` reservation。
- PASS：active `PENDING`、not-due `FAILED_RETRYABLE` 均为零目录枚举、零正文读取；
  Job 保持 `RUNNING/attempt_count=1`，Pipeline 保持 `METADATA_READY`。
- PASS：`SUCCEEDED` verified cache 为零网络、零重新规范化，并以空 Artifact
  completion 完成当前 Job。
- PASS：本任务记录的 all-invalid `FAILED_FINAL` 重复调用稳定返回
  `ALL_CANDIDATES_INVALID`，零目录/正文调用；三个 `complete_stage` 故障注入点均把
  reservation 释放为 due `FAILED_RETRYABLE`。
- PASS：默认 2 秒 Job backoff 后可验证已存在文件、零正文读取补索引并完成，不等待
  300 秒 lease；release 记录自身失败不覆盖原 stage `LOCAL_RESOURCE`。
- FAIL：非 all-invalid `FAILED_FINAL` 状态漂移。首次 `read_track` 返回
  nonretryable `PERMISSION_DENIED`，Provider record 也正确保存
  `PERMISSION_DENIED`；相同 request 第二次却被重映射为 nonretryable
  `PROVIDER_UNAVAILABLE`。
- FAIL：reservation 取得后的原子文件写入若发生 `PermissionError`，Service 直接抛出
  `PERMISSION_DENIED`，但 Provider call 仍为 active `PENDING`、owner/300 秒 lease
  未释放。
- FAIL：两个 Service 在“均尚未看到 Provider record”的真实 barrier 竞态中都执行
  目录枚举；结果为 `enum_total=2`、`read_total=1`。正文读取被去重，但失败方并非
  “无副作用”，仍产生额外远端目录调用。

#### R5：verified raw → canonical-only 重建 — FAIL

- PASS：verified raw 在 normalization/quality version 变化时零枚举、零正文 opener
  重建；旧 raw/旧 canonical 保留，raw record 字节不变，只新增当前 Job canonical
  Artifact；第二次运行命中当前 canonical 且不重新规范化。
- PASS：raw kind、storage root、deleted_at、producer、provider、model、父路径、
  缺失、篡改、非法 token、format extension 不一致均零网络返回
  nonretryable `LOCAL_RESOURCE`；当前 policy 注入质量失败也返回
  `LOCAL_RESOURCE`。
- FAIL：raw 文件为越界 symlink 时返回 `PERMISSION_DENIED`，而本轮 R5 冻结要求该类
  已索引本地缓存失效统一安全返回 `LOCAL_RESOURCE`。
- FAIL：把 raw 文件移动到同一 request 目录下、使用结构合法但
  `requested_language="fr"` 的 metadata token 并同步 Artifact path 后，以当前
  `("en",)` 请求重建仍成功；返回 Artifact 静默变为 `requested_language="fr"`，
  当前 Job/Pipeline 被推进。
- FAIL：ordinary canonical cache 记录的 `model` 被篡改为非空值后仍被当作 verified
  cache 命中；返回 Artifact 取 raw 的 `model=None`，掩盖 canonical 索引不一致并推进
  当前 Job/Pipeline。

### Regression A-F

| 组 | 结论 | 独立依据 |
|---|---|---|
| A 公共领域契约 | PASS | 判别联合、三个枚举、Artifact 字段/可空规则、8 个 ErrorCode、真实 Repository wiring 均未回归 |
| B 选择、解析与质量 | PASS | 人工/自动、语言 exact/base/variant、三格式、T-08 边界、R2 VTT 语义与候选回退通过 |
| C yt-dlp/HTTP/安全 | FAIL | R3 HTTP/URL bounds 通过，但 R1 真实 Adapter/Service exception graph 仍泄漏 URL、绝对路径和正文 bytes |
| D Artifact/cache/SQLite 恢复 | FAIL | R4 非 all-invalid 终态漂移、文件写失败遗留 reservation、真实竞态重复枚举；R5 metadata/cache 验证不完整 |
| E 可读性/架构/规模 | P2 concern | 模块与 Service 继续过大，新增测试仍大量依赖私有 hook；具体 P1 已在跨职责状态边界复现 |
| F 范围/复用/许可证 | PASS | 仅既有 yt-dlp/标准库，无依赖、Schema、认证、真实网络、媒体或 Vault 扩张 |

### Acceptance matrix

| AC | 结论 | 第二次 Reviewer 依据 |
|---|---|---|
| AC-1 固定夹具覆盖人工/自动、多语言、空/损坏字幕 | PASS | focused tests 与独立排序、回退、R2 通过 |
| AC-2 同一成功输入不重复下载/规范化 | PASS | SUCCEEDED verified cache 与 rebuilt canonical 第二次命中均零网络/零规范化 |
| AC-3 具名转写需求与网络错误区分 | PASS | no tracks/no match/all-invalid 联合稳定；真正错误继续为 `AppError` |
| AC-4 验证 Artifact/cache 并空 Artifact completion | FAIL | raw metadata token 与 canonical model 不一致仍被接受并推进 |
| AC-5 安全路径、原子恢复与脱敏 | FAIL | exception graph 泄漏；文件写失败遗留 reservation；raw symlink 错误分类不符 |

### ADR-006 T-01 至 T-15

| 条款 | 结论 | 依据 |
|---|---|---|
| T-01 | PASS | 人工/自动、语言、匹配、格式、名称、位置全局排序通过 |
| T-02 | PASS | 大小写、`_`/`-`、exact/base/variant 与实际语言保留通过 |
| T-03 | PASS | 只允许 JSON3/VTT/SRT，无媒体、认证、ffmpeg、remote components |
| T-04 | PASS | 具名联合与三种 `TranscriptionReason` 稳定；真实失败仍使用 `AppError` |
| T-05 | PASS | 公共对象、SHA、路径、计数、flags 和可空规则未回归 |
| T-06 | PASS | deterministic decode/LF/entity/NFC 与 NOTE/cue 控制语义通过 |
| T-07 | PASS | 多 speaker、marker、重复与滚动前缀语义通过 |
| T-08 | PASS | 全部冻结资源/质量阈值边界通过 |
| T-09 | PASS | raw/canonical 分层 key 与 canonical-only 版本重建正向路径通过 |
| T-10 | FAIL | 已索引 raw symlink 分类不符；文件写失败遗留 Provider reservation，恢复不完整 |
| T-11 | FAIL | 非 all-invalid `FAILED_FINAL` 重复调用错误码漂移；异常链仍泄漏 Provider/正文原始对象 |
| T-12 | PASS | 只复用既有 yt-dlp/标准库，无依赖或锁变化 |
| T-13 | FAIL | metadata token 未与当前 request 语言约束绑定，不能证明无歧义恢复 |
| T-14 | PASS | 未修改 `state.py`/migration/`complete_stage`；首次与普通 cache completion 的既有 Repository 路径成立 |
| T-15 | PASS | 普通成功 cache 零网络；refresh generation 仍生成新路径并保留旧 Artifact |

### 五轴审查

| 轴 | 结论 | 说明 |
|---|---|---|
| correctness | FAIL | R4 终态错误码漂移；R5 token/model 不一致被接受并推进 |
| readability | P2 concern | `transcripts.py` 1,988 行、Service 829 行、`fetch` 282 行，状态证明仍困难 |
| architecture | FAIL | true race 仍可重复目录 Provider 调用；文件错误未与 Provider reservation 生命周期统一 |
| security | FAIL | Adapter 与 canonical decode 的原异常对象仍可从 `__context__` 读取敏感内容 |
| performance | FAIL/P2 | true race 放大远端目录调用；name `runs` 和空 language bucket 数量仍无独立上限 |

### Findings

#### P1-1：真实 Adapter/Service 与 canonical cache 的异常图仍保留敏感原始对象

- 文件/行号：
  `src/youtube_intel/providers/subtitles.py:564-585`、
  `src/youtube_intel/providers/subtitles.py:634-688`、
  `src/youtube_intel/transcripts.py:1579-1587`
- 可复现输入：
  1. `DownloadError` message 含独立 marker、临时字幕 URL 和绝对路径，经真实
     `YtDlpSubtitleAdapter.enumerate_tracks` 与 `SubtitleAcquisitionService.fetch`
     外抛；
  2. canonical 文件为含 marker 的非法 UTF-8，DB hash 同步为该文件的真实 SHA-256。
- 期望：新 `TranscriptError` 的 message/args/属性、`__cause__`、`__context__` 和
  完整异常图均不持有 marker、正文、临时 URL 或绝对路径。
- 实际：场景 1 的外层 `__context__` 为原始 `DownloadError`；场景 2 的
  `__context__` 为 `UnicodeDecodeError`，其 `.object` 为 canonical 原始 bytes。
- 影响：任何记录或检查异常图的日志/调试路径仍可泄漏字幕正文和 Provider 敏感信息，
  R1 未关闭。

#### P1-2：Provider-call 状态仍会漂移、遗留 lease，并在真实竞态重复远端枚举

- 文件/行号：
  `src/youtube_intel/transcripts.py:1228-1273`、
  `src/youtube_intel/transcripts.py:1724-1758`、
  `src/youtube_intel/transcripts.py:1829-1844`
- 可复现输入：
  1. 首次正文读取返回 nonretryable `PERMISSION_DENIED`，随后重复同一 request；
  2. reservation 取得后 `NamedTemporaryFile` 抛 `PermissionError`；
  3. 两个真实 SQLite Service 以 barrier 同时通过“无 Provider record”预检。
- 期望：重复终态保持原错误语义；任何 reservation 后失败均安全释放；竞争失败方零
  Provider/文件/DB 副作用。
- 实际：
  1. record 保存 `PERMISSION_DENIED`，第二次却返回 `PROVIDER_UNAVAILABLE`；
  2. 文件失败后 record 仍为 active `PENDING` 且保留 owner/300 秒 lease；
  3. 两个 Service 均执行目录枚举，只有正文读取被去重。
- 影响：错误分类漂移、默认 2 秒 Job retry 被 lease 阻塞、额外远端调用以及 attempts
  耗尽风险，R4 未关闭。

#### P1-3：verified raw/canonical 元数据验证仍不足以 fail-closed

- 文件/行号：
  `src/youtube_intel/transcripts.py:795-848`、
  `src/youtube_intel/transcripts.py:1460-1539`、
  `src/youtube_intel/transcripts.py:1595-1613`
- 可复现输入：
  1. raw path 使用结构合法但 `requested_language="fr"` 的 metadata token，当前请求为
     `("en",)`，文件/hash/provider/producer 均有效；
  2. raw 文件为指向 DATA 外部的 symlink；
  3. ordinary canonical Artifact 的 `model` 被改为非空不一致值。
- 期望：三者均零网络返回 nonretryable `LOCAL_RESOURCE`，Job/Pipeline 不推进。
- 实际：场景 1 和 3 被当作 verified cache，返回的 provenance 被重写/掩盖并推进；
  场景 2 返回 `PERMISSION_DENIED` 而非本轮冻结的 `LOCAL_RESOURCE`。
- 影响：本地索引与 metadata token 不能被证明与当前 request/canonical provenance
  一致，R5 和 AC-4 未关闭。

#### P2-1：职责聚合和私有测试耦合风险仍然存在

- 文件/行号：
  `src/youtube_intel/transcripts.py:1131-1959`、
  `src/youtube_intel/providers/subtitles.py:513-765`、
  `tests/integration/test_subtitle_provider.py:123-1705`
- 实际：`transcripts.py` 增至 1,988 行、76 个定义；
  `SubtitleAcquisitionService` 为 829 行，`fetch` 282 行，`_load_cached` 170 行，
  `_rebuild_canonical_from_raw` 139 行。integration tests 有 15 次
  `_bind_test_hooks`，并直接使用 `_SourceMetadata`、`_source_relative_path` 与
  Repository `_inject_failure`。
- 影响：Correction 提取了具名 helper，但未实质分离 Provider 状态、文件/cache 与
  stage 编排；新增 P1 仍集中出现在这些职责交界。该维护性问题本身为 P2，不因行数
  自动决定 Verdict。

#### P2-2：目录嵌套 metadata 仍有剩余资源放大面

- 文件/行号：
  `src/youtube_intel/providers/subtitles.py:273-306`、
  `src/youtube_intel/providers/subtitles.py:337-412`
- 实际：track 总数有 512 上限，但 name `runs` 会先累积全部片段再检查最终 1,000
  code points；包含空 entry list 的 language bucket 数量也没有独立上限。
- 影响：畸形但字段长度合法的 yt-dlp payload 仍可放大 CPU/临时列表内存。未在当前
  固定边界探针中形成错误接受或越界写，登记为 P2 性能/安全加固风险。

- P0：无
- P1：3 个，均未解决
- P2：2 个
- P3：无

### 范围、红线、复用与许可证

- PASS：只直接复用既有 `yt-dlp==2026.7.4` 与 Python 标准库；没有新依赖、升级或
  lock 变化。
- PASS：`imlewc/video-to-subtitle-summary-skill@2c794d74` 仍仅为测试思想
  `REFERENCE`，未发现复制代码；`youtube-transcript-api` 继续 `DEFER`。
- PASS：未修改 Schema、migration、`state.py`、配置、CLI、TASK-004 公共接口或任务
  状态；未运行 subprocess/ffmpeg、Cookie/登录/`.netrc`、remote components、媒体、
  真实 Vault/密钥。
- PASS：既有 `mutagen==1.48.1` 的 `GPL-2.0-or-later` 分发风险未被本任务扩大，继续
  由 TASK-014 跟踪。

### Verdict、跳过项与剩余风险

- Verdict：`REJECT`
- 未解决 P0/P1：上述 3 个 P1；R1、R4、R5 不能被独立证明关闭。
- Skipped checks：规定离线门禁无跳过。真实 YouTube/字幕、RSS、Cookie/登录/
  `.netrc`、remote components、ffmpeg、媒体、真实 Vault 或密钥路径未运行，因为
  明确未授权。
- Remaining risks：
  - 上述 P2 职责聚合、私有 hook 和嵌套 metadata 资源放大；
  - 真实上游 yt-dlp payload/URL 漂移仍待 TASK-013；
  - `mutagen` GPL 分发风险仍待 TASK-014；
  - 复杂非标准字幕继续采用保守 fail-closed，可能存在非阻断误判。
- Decision needed：`None`。ADR-006 与本 Reviewer 包已足以定义期望；应退回原
  Implementer 修复，不需要新 ADR，也不得由 Reviewer 自行修代码。

### TASK-006 最终公共契约复核

- 公共契约形状相对第一次 Reviewer 未回归：
  `TranscriptProvider.fetch(video, language_preferences)` 返回
  `TranscriptReady | TranscriptionRequired`。
- `TranscriptArtifact` 精确字段仍为：
  `video_id`、`language`、`source_type`、`requested_language`、`source_format`、
  `text_path`、`timed_text_path`、`source_content_hash`、`source_byte_count`、
  `content_hash`、`char_count`、`segment_count`、`normalization_version`、
  `provider`、`model`、`created_at`、`quality_flags`。
- manual/auto 仍要求 `requested_language`、`source_format`、`timed_text_path`
  非空；Whisper 仍要求 `requested_language=None`、`source_format=None`，
  `timed_text_path` 可空，其他 hash/count/version/provider/model 字段继续存在。
- 三个 `TranscriptQualityFlag` 和三个 `TranscriptionReason` 的冻结集合未变化，
  Provider call metadata 仍只位于结果 `call`。
- 结论：TASK-006 的最终公共类型契约仍成立，不需要修改 ADR-007；但 TASK-005 因本次
  `REJECT` 尚未关闭，TASK-006/007 继续保持 blocked，不得据此启动写入实现。

## Implementer Correction 2

- Implementer：Codex
- Source commit：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- 授权父提交：`a3954bf782430678fa5e0040084bf0d907a52d05`
- 目标：关闭 Reviewer 2 的三个 P1，同时保持 ADR-006、TASK-006 公共契约、
  TASK-003 Repository/Schema 和现有依赖不变。

### RED 证据

先只修改测试并运行 Reviewer 2 三组反例：

```text
uv run python -m pytest tests/integration/test_subtitle_provider.py -q \
  -k 'adapter_directory_error_is_redacted or invalid_utf8_canonical_cache_is_redacted \
  or raw_metadata_requested_language or indexed_cache_symlink \
  or canonical_model_mismatch or no_tracks_and_no_matching_language \
  or non_all_invalid_final or two_real_sqlite \
  or permission_error_during_atomic_write'
```

- 实际：`11 failed, 49 deselected`。
- P1-1 RED：
  - `DownloadError` 中的 marker、临时 URL、绝对路径仍可从外层异常图读取；
  - canonical 非法 UTF-8 的 `UnicodeDecodeError.object` 仍保留原 bytes；
  - 原子写 `PermissionError` 的绝对路径仍在 `__context__`。
- P1-2 RED：
  - no tracks/no match 后无 `provider_calls` 终态；
  - non-all-invalid `FAILED_FINAL(PERMISSION_DENIED)` 重放为
    `PROVIDER_UNAVAILABLE`；
  - barrier 强制两个真实 SQLite Service 同时完成无记录预检时无法证明只有一个
    目录枚举；
  - 原子写失败后 reservation 未进入释放后的稳定终态。
- P1-3 RED：
  - 当前偏好 `("en",)` 接受 `requested_language="fr"` token 并重建；
  - raw/canonical 越界 symlink 返回 `PERMISSION_DENIED`；
  - canonical 非空 model、provider/producer/path/quality 不一致未完整 fail-closed。

### P1-1：完整异常图脱敏

- 代码：
  - `src/youtube_intel/providers/subtitles.py:120` 的
    `_safe_boundary_error` 只复制 `ErrorCode`、retryable、retry-after、stage 所需
    的固定安全诊断；
  - `enumerate_tracks`（`:569`）和 `read_track`（`:655`）捕获底层异常后先退出活动
    `except`，再抛新 `TranscriptError`；
  - `src/youtube_intel/transcripts.py:762` 的 `_copy_app_error` 只复制结构化安全字段；
  - cache metadata/quality/UTF-8 decode、Repository 包装、文件读写和 reservation
    包装均改为在活动 `except` 外抛安全异常。
- 测试：
  - `tests/unit/test_subtitle_policy.py:398,415`；
  - `tests/integration/test_subtitle_provider.py:1021,1056,1298,2180`。
- GREEN：
  - 递归检查每个异常节点的 message、args、`vars()`、`__cause__`、`__context__`
    和格式化 traceback；
  - marker、字幕 bytes、临时 URL、绝对路径均不存在；
  - Adapter/Service 仍保留原 `ErrorCode`、retryable、`TRANSCRIPT` stage 和 video ID。

### P1-2：pre-enumeration reservation、终态重放和失败释放

- `src/youtube_intel/transcripts.py:1842` 在任何目录枚举或正文读取前，用既有
  `provider_calls` CAS 取得默认 300 秒 reservation。
- `:1932` 的 `_fetch_reserved` 只允许 reservation owner 执行目录、正文与文件写入；
  `fetch`（`:2140`）在统一安全边界记录所有 Provider、解析、文件和 stage 提交失败，
  再在活动 `except` 外重抛。
- `:1337` 只把本任务精确记录的 no-tracks、no-match、all-invalid 终态映射回相应
  `TranscriptionRequired`；`:1383` 对其他 `FAILED_FINAL` 验证合法
  `ErrorCode`/安全消息后精确重放，不再泛化为 `PROVIDER_UNAVAILABLE`。
- `:1894` 为 no tracks/no match/all-invalid 写入 nonretryable 终态并清除 owner/lease；
  retryable 错误按原 retry-after 写 `available_at`。失败状态持久化异常不覆盖原始业务
  结果或错误。
- 测试矩阵：
  - no tracks/no match 首次与重复：`:1815`；
  - all-invalid 首次/重复：`:1857,1891`；
  - non-all-invalid 精确重放：`:1926`；
  - 两个真实 SQLite Service 双阶段 barrier 竞争：`:2059`；
  - stage failure、默认 2 秒 Job retry、文件恢复：`:2108`；
  - 原子写 Permission failure 释放：`:2180`；
  - SUCCEEDED verified cache、canonical rebuild 和第二次稳定命中沿用既有测试。
- GREEN：
  - 双 Service `enum_total=1`、`body_total=1`，竞争失败方零文件写入；
  - owner reservation 的 `lease_until == NOW + 300s`；
  - 文件 Permission failure 为 `FAILED_FINAL(PERMISSION_DENIED)`，owner/lease 为
    `NULL`；
  - stage failure 为 `FAILED_RETRYABLE`，owner/lease 清除，2 秒 Job retry 后从已写
    raw 文件恢复且不重复正文读取。

### P1-3：raw/canonical provenance 与 cache 分类

- `src/youtube_intel/transcripts.py:904` 校验 metadata token 的
  `requested_language` 必须是当前有序偏好中第一个实际匹配项，并保持 actual language
  的 track 不变量。
- `_load_cached`（`:1638`）验证 raw 的 key、video、kind、root、deleted、producer、
  provider、空 model、request-hash parent、token canonical encoding、当前语言选择、
  SHA 与真实路径边界。
- canonical 验证自身的 key lookup、video、kind、root、deleted、provider、model、
  producer、request hash/path、SHA、UTF-8 framing 与 quality token/内容语义；
  返回值使用已验证的 canonical provider/model，不再用 raw 字段掩盖不一致。
- `_resolve_data_path`（`:1024`）和 `_read_verified_file`（`:1066`）区分：
  - 已索引 cache 缺失、篡改、不可读、symlink/realpath 越界：
    nonretryable `LOCAL_RESOURCE`；
  - 新写入目标的 DATA 边界或权限失败：`PERMISSION_DENIED`。
- 测试矩阵：
  - valid raw → 新 canonical 与第二次稳定命中沿用 `:1192`；
  - raw missing/tampered/provider/model/producer/path/format：`:1369`；
  - 当前语言/token 不一致：`:1473`；
  - raw/canonical symlink：`:1551`；
  - canonical model/provider/producer/path/quality：`:1616`；
  - ordinary canonical missing/tampered 与 Job/Pipeline 不推进沿用 `:1701`。
- GREEN：上述无效 cache 均零网络、nonretryable `LOCAL_RESOURCE`，Job 保持
  `RUNNING`，Pipeline 保持 `METADATA_READY`。

### P2、架构与公共契约

- P2-1 有改善但未声称关闭：
  - 新增窄私有 helper 分离安全异常转换、provenance、终态映射和 reservation owner
    编排；
  - `fetch` 只保留验证、preflight/cache、CAS 和 owner 安全边界；
  - integration tests 仍依赖私有 `_bind_test_hooks`、`_SourceMetadata` 和
    Repository failure injection，职责聚合仍交第三次 Reviewer 判断。
- P2-2 未修改：name `runs` 与空 language bucket 的嵌套 metadata 资源放大仍登记为
  P2；本轮未新增公共模块、依赖或未冻结阈值。
- 未修改 `domain.py`、`state.py`、migration、配置、CLI、discovery、任务文件、
  ADR、依赖清单或锁文件；TASK-006 的 `TranscriptProvider` /
  `TranscriptArtifact` 公共形状不变。

### 验证

```text
uv lock --check
  PASS — Resolved 34 packages
uv sync --locked
  PASS — Checked 30 packages
uv run python -m pytest tests/unit/test_contracts.py
  PASS — 50 passed
uv run python -m pytest tests/unit/test_subtitle_policy.py
  PASS — 30 passed
uv run python -m pytest tests/integration/test_subtitle_provider.py
  PASS — 68 passed
uv run python -m pytest
  PASS — 234 passed
uv run mypy src
  PASS — 9 source files
env MYPYPATH=src uv run mypy -c '<TranscriptRepository wiring>'
  PASS — 1 source file
uv run ruff check .
  PASS
uv run python -m youtube_intel --help
  PASS
uv build --offline
  PASS — sdist + wheel
```

- sdist/wheel 均包含：
  `migrations/001_initial.sql`、`youtube_intel/transcripts.py`、
  `youtube_intel/providers/subtitles.py`；检查后仅清理本轮生成且被忽略的 `dist/`。
- `pyproject.toml` SHA-256：
  `49ca5e31c32d8dbadc3770901f227ed9dd95237a1ac1cb0b977019c5f13d1fa9`，
  与 source commit 相同。
- `uv.lock` SHA-256：
  `81a3fd81e51cac69ca4d072c481b63cc9a265b491eab9c65ea782963f85a9c49`，
  与 source commit 相同。
- Correction 2 只修改允许的 5 个文件：
  `transcripts.py`、`providers/subtitles.py`、两个 subtitle tests 和本 handoff。
- 未运行真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、
  媒体、真实 Vault/密钥；未产生 source 内数据库、cache、媒体或构建产物。

### 复用、许可证、剩余风险

- 继续只复用既有 `yt-dlp==2026.7.4` 与 Python 标准库；无新增/升级依赖，无复制
  外部代码。
- `imlewc/video-to-subtitle-summary-skill@2c794d74` 继续仅为测试思想
  `REFERENCE`；`youtube-transcript-api` 继续 `DEFER`。
- `mutagen==1.48.1` 的 `GPL-2.0-or-later` 分发风险未扩大，继续由 TASK-014 跟踪。
- 剩余风险：上述两个 P2、真实上游 yt-dlp payload/URL 漂移（TASK-013）、复杂非标准
  字幕的保守 fail-closed 误判；无剩余已知 P0/P1。
- Skipped checks：规定离线门禁无跳过；仅按明确禁令跳过真实外部网络/认证/媒体/Vault。
- Decision needed：`None`。

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
