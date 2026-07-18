# TASK-006：本地 Whisper 转写

- Status: `IN_REVIEW`
- Assignee: `Codex`
- Owner role: 全新独立 Codex Reviewer（阶段 A）
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
