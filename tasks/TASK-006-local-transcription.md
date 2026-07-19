# TASK-006：本地 Whisper 转写

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Owner role: 原 Codex Implementer（Correction 2；安全拒绝枚举修复）
- Size: M
- Risk: High
- Depends on: TASK-005A
- Approval required: 阶段 A 已获 `mlx-whisper` 包/传递依赖、锁文件与离线实现授权；模型、
  ffmpeg、媒体、资源实测和真实冒烟仍须逐项另批

## 2026-07-16 只读预检

- Scout observed main：`b335b12358bbbc9dada1abfafc5a2fe9a68494be`
- Repository changes：None
- 结论：`DECISION NEEDED`
- ADR-007 L-01 至 L-15 已于 2026-07-17 接受；本任务仍为 `BLOCKED/UNASSIGNED`，
  不得创建 worktree 或安装/下载。
- 共享 config/domain/state 变更必须先由 TASK-005A 整合为 `DONE`，不能与 TASK-007
  分支重复实现；之后仍须获得 `mlx-whisper` 解析/锁定/安装、模型、ffmpeg、媒体和
  本机冒烟的独立任务级授权。

## 2026-07-19 阶段 A 分配与边界

- Main control-plane base：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。worktree：
  `/Users/hua/Documents/yia-worktrees/task-006`；branch：
  `codex/task-006-local-transcription`；Implementer：Codex；完成后由全新独立 Codex
  Reviewer 审查。
- 允许 `mlx-whisper>=0.4.3,<0.5`、uv 解析出的必要传递依赖、网络包下载、
  `pyproject.toml`/`uv.lock` 修改，以及 `uv add`、`uv lock`、`uv sync --locked` 与本卡
  离线验证/构建命令。Implementer 必须记录实际解析版本、许可证和 Python 3.12/arm64
  兼容性；若解析需要白名单外直接依赖或不兼容，立即停止并报告。
- 本轮只实现可由 Fake/受控夹具验证的 Adapter、策略、缓存、超时/资源错误与清理语义。
  允许一个可再分发或确定性生成的短 WAV 测试夹具；不得下载模型或音频，且不得执行真实
  转写。
- 继续禁止：任何 Whisper 权重/模型下载或加载、`ffmpeg` 安装/调用、媒体或 YouTube
  下载、Cookie/登录/`.netrc`、remote components、真实 Vault/密钥、真实资源或模型冒烟。
  不新增 Schema/migration，不修改共享 `config.py`、`domain.py`、`state.py`。
- 允许范围严格为本卡“预计触达文件”列出的 `transcription.py`、`providers/whisper.py`、
  两份测试、`tests/fixtures/audio/**`、`pyproject.toml`、`uv.lock` 和
  `handoffs/TASK-006.md`。不得改任务状态或 main。

## 实现证据与独立审查授权

- Source：`codex/task-006-local-transcription@c6ff804569b376c347719296d80fbe1abf99057a`；
  唯一父提交为共同 base `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`，worktree 已干净。
- base...source 精确包含本卡允许的 8 类路径：`transcription.py`、`providers/whisper.py`、
  两份测试、`tests/fixtures/audio/README.md`、`pyproject.toml`、`uv.lock` 和 handoff；
  `git diff --check` 通过。直接依赖精确新增 `mlx-whisper>=0.4.3,<0.5`，实际锁定
  `0.4.3`，无其他新增直接依赖。
- Implementer 自报 focused `6+6`、全量 `263`、mypy、Ruff、CLI、locked sync、offline
  build 和 migration packaging 全部通过；这些只构成待复跑证据，不构成验收。
- Reviewer：必须为全新独立 Codex 会话，仅可在 source worktree 的
  `handoffs/TASK-006.md` 追加审查并创建一个以 `c6ff804...` 为唯一父提交的 evidence
  commit。不得改业务代码、测试、依赖、锁文件、任务状态或 main。审查包由动态 main
  commit 解析；`TASK-007` 正在并行写入，Reviewer 不得读取、检查或操作其 worktree。

## 第一轮独立审查拒绝与 Correction 1

- Reviewer evidence：`f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`，唯一父提交为实现
  `c6ff804569b376c347719296d80fbe1abf99057a`，且只修改 source handoff。Verdict：
  `REJECT`；P1 位于 `transcription.py` 的音频清理路径：它在调用 SQLite
  `mark_artifact_deleted()` CAS 前删除文件。真实 SQLite 探针证明未知 Artifact id 或陈旧
  CAS 会返回 `INDEX_CONFLICT`，但文件已不可恢复地删除。
- 产品负责人已批准最小 Correction：保留现有 Repository “文件已删除后才 index-only
  confirmation”的冻结契约和 `state.py`/Schema 边界。删除前必须用现有 Repository 读取
  Artifact 并验证 id/key/hash、`AUDIO`/`EPHEMERAL_AUDIO`、DATA 根、未删除状态和受控
  路径；任一预检不符时不得删除，并安全返回 `INDEX_CONFLICT`。仅预检成功后才能删除，
  然后调用既有 post-delete CAS 确认。
- 该设计明确保留“预检与 post-delete CAS 之间”的 at-most-once cleanup 并发窗口：若最终
  CAS 失败，必须返回安全诊断而不是伪报 index 成功；不得改为提前标记删除、不得宣称严格
  exactly-once。消除该窗口需要新的 deletion reservation 契约/Schema，超出本任务授权。
- Correction 1 只能修改 `src/youtube_intel/transcription.py`、
  `tests/unit/test_transcription_policy.py`、`tests/integration/test_whisper_provider.py` 和
  `handoffs/TASK-006.md`。不得改依赖/锁、`state.py`、migration、公共任务状态或 main；
  TASK-007 Reviewer 正在独立审查，Correction Implementer 不得读取或操作其 worktree。

### Correction 1 实现证据与独立审查排队

- Correction source：`17afcd349827b36e5ba18fb0eab443c1ae5fb53f`，唯一父提交为第一轮 review
  evidence `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`；source worktree 干净。Correction
  精确修改 `transcription.py`、`tests/unit/test_transcription_policy.py`、
  `tests/integration/test_whisper_provider.py` 和 handoff，`state.py`、Schema/migration、依赖和
  锁文件未改变。
- Implementer 自报：删除前读取和核验当前 Artifact 索引；未知/缺失/已删除/不匹配时保留音频并返回
  `INDEX_CONFLICT`；真实 SQLite 覆盖成功确认、最终 CAS 竞态、kind/retention/root/hash、符号链接
  与路径逃逸安全诊断。lock/sync、focused `10/9`、全量 `270`、mypy、Ruff、CLI、offline build
  和 migration package inclusion 全 PASS；这些只构成待独立复跑证据。
- 独立 Reviewer 必须是全新 Codex 会话，只能在 source handoff 写入并创建以 `17afcd...` 为唯一
  父提交的 evidence commit。为遵守单 Reviewer WIP 限制，必须等待正在执行的 TASK-007 Reviewer
  结束后再启动；不得改业务代码、任务状态、main 或访问 TASK-007 worktree。

## 第二次独立审查拒绝与 Correction 2

- Evidence：`47599db196b1b9440de3ae57ec3547935f64b1dc`，唯一父提交为 `17afcd...`，且仅修改
  handoff。Verdict=`REJECT`，P1=1；规定离线门禁均通过。
- P1：符号链接/路径逃逸预检正确保留音频与根外目标，却返回 `PATH_OUTSIDE_DATA`；本轮授权要求
  一切未知/缺失/错误索引/路径逃逸拒绝均使用安全、可重试的 `INDEX_CONFLICT`。

### Correction 2 的冻结边界

- 起点必须为 `47599db...`，Correction commit 以它为唯一父提交。只允许 `transcription.py`、
  `tests/unit/test_transcription_policy.py`、`tests/integration/test_whisper_provider.py` 与 handoff；
  不得改 Provider、`state.py`、Schema/migration、依赖/锁、任务状态或 main。
- 仅将符号链接、绝对路径、相对路径逃逸与 root escape 的清理 preflight 统一映射为安全、可重试的
  `INDEX_CONFLICT`，保持文件/目标不删除、错误内容不泄漏路径。未知/缺失/哈希/错误 kind/retention/
  root、有效删除和 final CAS 竞态的现有语义不得退化；不得引入 reservation 或 exactly-once 声明。
- 以临时真实 SQLite/DATA 根与合成文件补充 RED/GREEN 回归；真实模型、ffmpeg、媒体、网络、Vault/
  凭据和文件删除仍不授权。完成后由全新独立 Codex Reviewer 重审，Implementer 不得改状态、合并或启动 Reviewer。

## 目标

在无有效字幕时下载受控音频并在 Apple Silicon 本地完成转写，产出与字幕路径相同的 TranscriptArtifact 契约。

## 范围

- 按 `DEC-03` 实现 Whisper Adapter；时长纯策略由本任务测试，Pipeline 跳过与
  `--force` 状态审计归 TASK-010。
- 音频下载、转写参数、超时、资源错误和清理均可观察。
- 缓存键包含音频哈希、实现/模型和参数版本，模型升级不会误用旧结果。

## 范围外

- 不使用未批准的云端转写服务。
- 不对已有有效字幕的视频下载音频。
- 不静默下载超出长度或资源策略的视频。
- 不在运行时隐式下载包、模型或系统工具。
- 不在本任务新增 Schema/migration；过期清理使用共享契约并由 TASK-012 执行。

## 验收标准

- [ ] 短音频夹具可在支持环境完成转写；不支持/资源不足时返回明确错误而非崩溃或无限等待。
- [ ] 相同音频和模型参数重复运行命中缓存；模型/参数变化时生成新的可追踪产物。
- [ ] 成功、失败和超长三条路径遵循已审批的音频保留策略，清理失败不丢失已完成转写。

## 验证

- [ ] `uv lock --check`
- [ ] `uv run python -m pytest tests/unit/test_transcription_policy.py`
- [ ] `uv run python -m pytest tests/integration/test_whisper_provider.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build`
- [ ] `git diff --check`
- [ ] 受控本机冒烟：记录短音频时长、模型、耗时、峰值资源的可用指标和退出码。

## 预计触达文件

- `src/youtube_intel/transcription.py`
- `src/youtube_intel/providers/whisper.py`
- `tests/unit/test_transcription_policy.py`
- `tests/integration/test_whisper_provider.py`
- `tests/fixtures/audio/` 下一个短且可再分发的夹具
- `pyproject.toml`、`uv.lock`（仅在任务级依赖授权后）
- `handoffs/TASK-006.md`

共享 `config.py`、`domain.py`、`state.py`、示例配置和既有契约/状态测试不属于
TASK-006 分支；它们必须由 TASK-005A 先行完成。真实媒体、模型、ffmpeg 冒烟
不得进入默认离线检查。

## 交付证据

- 依赖和实现选择审批记录。
- 自动测试与本机冒烟结果。
- 性能/资源基线和未解决风险。
- 音频夹具来源、再分发许可证、模型 revision/hash、ffmpeg 构建与许可证证据。
