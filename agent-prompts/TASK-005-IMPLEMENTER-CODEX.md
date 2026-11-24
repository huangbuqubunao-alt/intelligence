# TASK-005 字幕获取与规范化 — Codex Implementer

## 身份与目标

你是 `TASK-005` 的唯一 Codex Implementer。你负责完成一个可离线验收的字幕纵向切片：重新枚举人工/自动字幕轨道，按冻结策略选择候选，保存原始字幕并生成规范文本，执行质量门禁与幂等缓存/恢复，并返回具名 `TranscriptFetchResult`。你不承担 Reviewer、主控验收、main 整合、Whisper、评分或后续任务。

## 必读与冲突门禁

在 TASK-005 worktree 中按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md` 第 6、8、9、10、13、14、15 节
5. `docs/SYSTEM_DESIGN.md` 第 3、4、5、6、7、9、10、12、13、14、16、18 节
6. `docs/PRODUCT_DECISIONS.md` 的 ADR-006、DEC-01、DEC-02 与 DEC-07
7. `docs/REUSE_REGISTER.md` 的使用规则、TASK-005 直接复用与候选结论
8. `docs/decisions/ADR-002-config-domain-contracts.md`
9. `docs/decisions/ADR-003-sqlite-state-store-contract.md` 的 Artifact、Provider call 与 `complete_stage` 语义
10. `docs/decisions/ADR-004-discovery-ytdlp-contract.md` 的 D-04、D-05、D-08
11. `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
12. `docs/decisions/ADR-006-subtitle-acquisition-contract.md` 全文
13. `tasks/TASK-005-subtitle-pipeline.md`
14. `handoffs/TEMPLATE.md`
15. 主线任务包：`/Users/developer/Documents/youtubek agent/agent-prompts/TASK-005-IMPLEMENTER-CODEX.md`

如任一文档冲突，或实现必须修改 `state.py`、Schema/migration、`complete_stage`、依赖/锁文件、TASK-004 公共接口或任务范围外文件，立即停止并输出 `DECISION NEEDED`。不得在公共接口、跨模块契约或 Repository 兼容性上用 wrapper、monkey patch、`Any`、宽 `object`、自由 `dict`、`cast`/`type: ignore` 或重复 Repository 隐藏不兼容；Adapter 私有边界仍须显式验证 yt-dlp 原始 payload。

## 固定开工包

- Task：`TASK-005`
- Role：`Implementer`
- Agent：`Codex`
- Base：`main@b28f52d0e4950f78dba315d4afe211ea5f75b93c`
- Worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Branch：`codex/task-005-subtitle-pipeline`
- Reviewer：实现提交后由主控启动一个全新独立 Codex 会话；不得复用本 Implementer 对话
- Parallel now：TASK-006/007 只读 Scout；它不得读取本 worktree
- Waiting：TASK-006/007 写入实现及后续任务

基线隔离说明：本 worktree 从 `b28f52d...` 创建，本地公共任务卡可能仍显示 `BLOCKED/UNASSIGNED`；角色和授权随后只提交到 main 控制面。这是预期隔离，不是规格冲突。不得 pull、merge 或 cherry-pick 控制面提交。

## Reuse decision

- `DIRECT`：已锁定 `yt-dlp[default,deno]==2026.7.4` Python API，用于离线可替换的轨道枚举和选中字幕正文读取；Python 标准库 `json`、`html`、`unicodedata`、`hashlib`、`pathlib`、`tempfile`、`os`、`re`、`urllib.request` 负责解析、NFC、哈希、有限响应读取和原子文件操作。
- `ADAPT/REFERENCE`：`imlewc/video-to-subtitle-summary-skill@2c794d74` 仅参考语言排序、清洗夹具和无下载断言。若没有复制实质代码，明确记录“仅参考测试思想”；若发现必须复制，先停止并申请来源/许可证审批。
- `DEFER`：`youtube-transcript-api`；不得新增依赖，只有正式证据证明 yt-dlp 路径不足时才回主控申请。
- `REJECT`：subprocess/ffmpeg、Cookie/登录/`.netrc`、remote components、付费或远程 Transcript API、直接 Vault 写入以及整套第三方应用架构。
- 本项目自有：领域结果、选择/质量策略、Artifact/Provider-call 键、文件恢复、错误映射和 Pipeline 推进。

交接报告必须记录实际复用、固定版本、许可证、未复制外部代码的证据和所有拒绝/延期理由。

## 唯一允许提交的 8 个路径组

1. `src/youtube_intel/domain.py`
2. `src/youtube_intel/transcripts.py`
3. `src/youtube_intel/providers/subtitles.py`
4. `tests/unit/test_contracts.py`
5. `tests/unit/test_subtitle_policy.py`
6. `tests/integration/test_subtitle_provider.py`
7. `tests/fixtures/subtitles/**`
8. `handoffs/TASK-005.md`

不得新增 `providers/__init__.py`，不得修改 `src/youtube_intel/state.py`、`migrations/**`、`src/youtube_intel/discovery.py`、`src/youtube_intel/providers/youtube.py`、配置、CLI、任务/ADR、`pyproject.toml` 或 `uv.lock`。`.venv`、缓存、临时数据库、测试 DATA 和 `dist/` 可由命令生成但不得提交。

## 权限与红线

- 允许 `uv sync --locked`；如缓存缺失，只允许下载 `uv.lock` 中既有包。不得运行 `uv add`、升级或重锁依赖，不得改变 `pyproject.toml`/`uv.lock`。
- 允许任务卡列出的离线 pytest、mypy、Ruff、CLI help 和 build。只有 `uv sync --locked` 可在缓存缺失时下载 `uv.lock` 中已有包；`uv build` 不获得额外网络下载授权，若离线构建环境无法完成则保留证据并报告 `BLOCKED`。
- 所有 Provider、HTTP、yt-dlp 和文件路径测试必须使用固定夹具、私有测试钩子和临时目录；严禁真实 YouTube/字幕/RSS 请求。
- 严禁 Cookie、账号/浏览器登录、`.netrc`、remote components、ffmpeg、subprocess、媒体/音频/视频/缩略图下载、真实 Vault/密钥。
- 不实现 Whisper、评分、云分析、Obsidian、全局重试/退避、调度或清理用户数据。

## 实现检查点

### Checkpoint A：领域契约

先扩展 `domain.py` 并写失败测试：

- 新增 ADR-006 T-04/T-05 的 `SubtitleFormat`、`TranscriptQualityFlag`、`TranscriptionReason`、`TranscriptReady`、`TranscriptionRequired`、`TranscriptFetchResult`。
- `TranscriptArtifact` 增加并严格校验 `requested_language`、`source_format`、`source_content_hash`、`source_byte_count`、`normalization_version` 和具名 `quality_flags`；字幕与 Whisper 的可空规则必须一致。
- `TranscriptProvider.fetch` 返回具名判别联合；网络/权限/配置/资源/Provider 错误继续使用现有 `AppError`，不得新增 `ErrorCode`。
- 公共注解不得出现自由 `dict`、`Any`、宽 `object` 或未冻结字符串枚举；不得破坏 TASK-002/003/004 现有契约测试。

运行 `uv run python -m pytest tests/unit/test_contracts.py`，确认新契约与旧回归通过后再进入下一检查点。

### Checkpoint B：选择、规范化与质量

在 `transcripts.py` 实现纯策略/纯解析优先部分，并以 `test_subtitle_policy.py` 覆盖 ADR-006 T-01 至 T-09：

- 全局顺序：全部人工先于全部自动；配置语言顺序；exact/base/variant；规范化实际语言；JSON3/VTT/SRT；轨道名；Provider 原始位置。
- 语言比较大小写不敏感、`_` 等同 `-`，不新增 BCP-47 依赖；保留 Provider 实际语言。
- 严格 UTF-8（允许 BOM）、LF、HTML entity 单次解码、NFC；格式解析只允许 JSON3/VTT/SRT。
- 删除时间/样式控制信息，但保留 speaker 和音乐/音效语义；连续重复和滚动前缀只按 T-07 的确定性规则处理。
- 精确执行 T-08 的 byte/code-point/segment/最短内容/U+FFFD/重复删除率/压缩比阈值；无效候选继续下一项，全部无效才返回 `ALL_CANDIDATES_INVALID`。
- 原始与 canonical 幂等键按 T-09 分层并包含全部版本维度；普通缓存命中不联网，只有显式 refresh generation 重新枚举。

任何模糊格式、危险 URL、超限正文或非法 payload 必须 fail-closed，不得把原始 URL、正文、绝对路径或 Provider payload带入错误。

### Checkpoint C：Adapter、文件与 Repository 组合

在 `providers/subtitles.py` 和 `transcripts.py` 完成纵向组合，并以 `test_subtitle_provider.py` 使用 Fake 与真实临时 `SQLiteStateRepository` 验证 ADR-006 T-10 至 T-15：

- yt-dlp Python API 位于 Adapter 私有边界；安全选项必须证明 `skip_download=True`、`download=False`、`ignoreconfig=True`、`usenetrc=False`，且无 Cookie/登录/`.netrc`、remote components、ffmpeg、postprocessor 或媒体写入。
- 只读取选中字幕正文，严格 timeout/response size/短读/关闭 response；错误按 T-11 映射到既有 8 个 `ErrorCode`，Provider 不实现全局退避。
- 文件路径只能是安全 DATA-relative `transcripts/<video_id>/<request_hash>/...`；同目录临时写、边写边限流与 SHA-256、flush/fsync、原子替换、父目录 fsync。
- 首次成功用当前 Job 的两个 `ArtifactWrite` 和 Provider call 完成 `METADATA_READY -> TRANSCRIPT_READY`；缓存命中必须通过 `get_artifact_by_key` 和文件 SHA-256 验证，再调用现有 `complete_stage(artifacts=(), provider_call=None)`。
- 文件成功而 DB 失败时保留确定性文件供下一 attempt 验证补索引；DB 记录存在但文件缺失/哈希不符返回 `LOCAL_RESOURCE` 且 Pipeline 不推进。
- 必须有真实静态/运行时 Repository wiring 和故障注入证据；如现有 API 无法完成 T-13/T-14，立即 `DECISION NEEDED`，不得修改 TASK-003 或伪造成功。

## 必测矩阵

- 人工字幕优先、人工低语言优先于自动高语言、自动回退、exact/base/variant、多格式/多轨道稳定 tie-break。
- 无轨道、无匹配语言、全部候选无效三种具名 `TranscriptionRequired`。
- JSON3/VTT/SRT 合法与 malformed、BOM/非法 UTF-8、HTML/NFC、speaker/marker、滚动字幕、每个 T-08 边界值前后。
- 轨道目录 401/403、临时 URL 403/404、429 + Retry-After、timeout/短读/5xx、危险 URL、内容不可用和磁盘/路径错误。
- 响应始终关闭，正文受限；错误/日志/SQLite 无临时 URL、字幕正文、绝对路径、Cookie 或密钥。
- 原始/canonical request hash 稳定，refresh generation 变化；重复运行不重读远端、不重复规范化。
- 原子文件、文件后 DB 失败恢复、缺失/篡改缓存拒绝、两个 Artifact 首次成功、空 Artifact 缓存命中 completion、Pipeline/Job 原子性。
- public API/注解哨兵、未修改 state/schema/dependencies/lock、无媒体/ffmpeg/subprocess。

## 执行流程

1. 复述目标、三个检查点、8 个路径组、Reuse decision、权限和红线。
2. 核对当前目录、分支、HEAD、工作区、身份与 `user.useConfigOnly=true`；必须精确匹配开工包。
3. 运行 `uv sync --locked`，随后记录 `pyproject.toml` 与 `uv.lock` 基线哈希；结束时必须保持字节不变。
4. 测试驱动按 A → B → C 小步实现；同一失败连续出现两次后停止重复方法并保留证据。
5. 从 `handoffs/TEMPLATE.md` 创建 `handoffs/TASK-005.md`，写 T-01 至 T-15 追踪表、脱敏 Artifact 示例、选择/质量矩阵、文件/SQLite 恢复、复用/许可证、跳过项与风险。
6. 运行全部检查：

   ```bash
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/unit/test_contracts.py
   uv run python -m pytest tests/unit/test_subtitle_policy.py
   uv run python -m pytest tests/integration/test_subtitle_provider.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv run python -m youtube_intel --help
   uv build
   git diff --check b28f52d0e4950f78dba315d4afe211ea5f75b93c...HEAD
   ```

7. 检查 sdist/wheel 仍包含 `youtube_intel/migrations/001_initial.sql`；清理本轮被忽略的构建产物，但不得删除或重置受跟踪文件。
8. 完整复核 `b28f52d...HEAD`、未提交和未跟踪文件：范围必须精确落在 8 个路径组；`state.py`、migration、`complete_stage`、TASK-004、依赖/锁、真实配置/数据均无变化。
9. 全部通过后创建范围明确的 commit，建议：`feat: implement subtitle acquisition pipeline`。不得合并 main、改公共任务状态或启动 Reviewer。

## 最终回传

```text
Task: TASK-005
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + result summary
ADR-006 traceability: T-01 through T-15
Domain/result evidence:
Selection/normalization/quality evidence:
Artifact/cache/recovery evidence:
yt-dlp safety evidence:
Reuse/license evidence:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
