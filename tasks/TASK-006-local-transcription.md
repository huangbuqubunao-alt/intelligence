# TASK-006：本地 Whisper 转写

- Status: `DONE`
- Assignee: `Codex`
- Owner role: 已整合并关闭；merge `fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`
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

### Correction 2 实现证据与第三次独立审查

- Correction source：`51b308828a6f2c433a9b4e92fb4a24e042f55d77`，唯一父提交为第二轮 review
  evidence `47599db196b1b9440de3ae57ec3547935f64b1dc`；source worktree 干净。Correction 精确
  修改 `transcription.py`、`tests/unit/test_transcription_policy.py`、
  `tests/integration/test_whisper_provider.py` 和 handoff；完整产品范围仍为批准的八路径，
  `state.py`、Schema/migration、依赖和锁文件未改变。
- Implementer 自报：绝对路径、相对 `..` 路径、DATA-root escape 与符号链接现在均安全、可重试地
  返回 `INDEX_CONFLICT`，不删除文件或根外目标；新增路径逃逸单测与临时真实 SQLite/DATA
  符号链接回归。locked offline sync、focused `11/10`、全量 `272`、mypy、Ruff、CLI、offline
  build、migration package inclusion 和固定 Diff 检查均 PASS；这些仅构成待独立复跑证据。
- 第三次 Reviewer 必须是全新独立 Codex 会话，只能在 source handoff 写入并创建以 `51b308...` 为
  唯一父提交的 evidence commit。必须复跑全部离线门禁，并以真实临时 SQLite/DATA 根证明所有路径
  逃逸统一为 `INDEX_CONFLICT`、零物理删除，同时不退化既有 Artifact/CAS/retention 语义；不得访问
  TASK-007、改业务代码、任务状态或 main。

## 第三次独立审查拒绝与 Correction 3

- Evidence：`66f0b31023c290d76e2c14bea72d1cc103cc27c7`，唯一父提交为 `51b308...`，且仅修改
  handoff。Verdict=`REJECT`，P1=2；规定离线门禁均通过。
- P1-1：`language_hint` 未纳入转写缓存身份；不同语言请求会错误复用旧转写。
- P1-2：错误 kind/root/retention Artifact 的清理前置条件返回 `INELIGIBLE_ARTIFACT`，违反本任务
  已冻结的统一、可重试 `INDEX_CONFLICT` 语义。

### Correction 3 的冻结边界

- 起点必须为 `66f0b310...`，Correction commit 以它为唯一父提交。只允许 `transcription.py`、
  `providers/whisper.py`、`tests/unit/test_transcription_policy.py`、
  `tests/integration/test_whisper_provider.py` 与 handoff；不得改 `state.py`、Schema/migration、
  依赖/锁、任务状态或 main。
- 缓存身份必须将已验证/规范化的 `language_hint` 作为请求语义的一部分；相同请求保持原行为，不同
  language hint 不得复用旧 Artifact 或缓存结果。错误 kind/root/retention Artifact 以及现有未知、
  缺失、陈旧、hash 不匹配和路径逃逸拒绝必须安全、可重试地返回 `INDEX_CONFLICT`，保留文件并不泄露
  路径。有效删除和 final CAS 竞态不得退化；不得引入 reservation 或 exactly-once 声明。
- 以临时真实 SQLite/DATA 根和合成音频补充缓存身份与 cleanup RED/GREEN 回归；真实模型、ffmpeg、
  媒体、网络、Vault/凭据与文件删除仍不授权。完成后由全新独立 Codex Reviewer 重审；Implementer
  不得改状态、合并或启动 Reviewer，也不得访问 TASK-007。

### Correction 3 缓存身份传递范围修正

- Implementer 在写入前确认 `language_hint` 由 `WhisperDecodePolicy` 持有，而缓存键在
  `transcription.py` 构造、唯一生产调用点位于 `providers/whisper.py`；原四文件范围无法形成
  端到端缓存隔离，因此按主控决定停止是正确的。
- 批准将原始 TASK-006 范围内的 `providers/whisper.py` 重新加入本轮最小范围。该文件只允许在
  `MlxWhisperAdapter` 的既有缓存键调用点传入 `self._decode_policy.language_hint`；不得修改
  executor 调用、模型/资源路径、错误映射、下载行为或公共 Adapter 方法签名。
- `build_transcription_cache_key()` 新增无默认值的 keyword-only
  `language_hint: str | None`，强制每个调用方明确选择缓存语义；使用现有已验证值，不新增
  normalization，也不改变 `None`/空白校验。该修正不授权其他 Provider 改动、依赖/锁文件、Schema、
  `state.py`、真实模型、ffmpeg、媒体、网络、Vault 或凭据操作。

### Correction 3 实现证据与第四次独立审查授权

- Correction source：`548338978b8656db0c650be276f847850af940a1`，唯一父提交为第三次
  review evidence `66f0b31023c290d76e2c14bea72d1cc103cc27c7`；source worktree 干净。
- Correction 精确修改 `transcription.py`、`providers/whisper.py` 的既有缓存键调用点、两份
  转写测试和 handoff 五个允许路径。相对 `66f0b310...`，`state.py`、Schema/migration、domain/
  config、依赖和锁文件未变；完整产品范围仍为原批准的八类路径。
- Implementer 自报 `language_hint` 已成为 required keyword-only 缓存维度，相同提示保持 cache
  hit、不同提示隔离；错误 kind/root/retention Artifact 统一为 `INDEX_CONFLICT`，删除/CAS 顺序
  不变。focused `11/12`、全量 `274`、mypy、Ruff、CLI、locked offline sync、offline build 和
  migration package inclusion 均 PASS；这些不构成独立验收。
- 第四次 Reviewer 必须为全新独立 Codex 会话，只能追加 source handoff 并创建以
  `548338978...` 为唯一父提交的 evidence commit。必须独立验证缓存键 API 强制性、共享缓存
  `None/en/zh` 隔离、Provider 单调用点、Fake/真实临时 SQLite cleanup 矩阵、AC/ADR 与五轴审查；
  不得改产品代码、状态、main，或访问 TASK-007。

### 第四次独立审查通过与最终整合授权

- Reviewer evidence：`f00209c8018a9e728d9f6509f0ae70067fa33676`，唯一父提交为
  Correction 3 `548338978b8656db0c650be276f847850af940a1`，且只修改
  `handoffs/TASK-006.md`；source worktree 已干净。
- Verdict=`APPROVE`，P0/P1/P2/P3 均无。独立 Reviewer 复跑 focused `11/12`、全量
  `274`、mypy、Ruff、CLI、locked offline sync、offline build、migration package
  inclusion 与固定 Diff 均 PASS；缓存键必填 API、共享缓存 `None/en/zh` 隔离、Provider
  唯一调用点及 Fake/真实临时 SQLite cleanup 矩阵也全部通过。
- 主控验收通过，TASK-006 进入 `ACCEPTED`。Codex Product Integrator 只可按
  `agent-prompts/TASK-006-INTEGRATOR.md` 把固定 source `f00209c...` 非快进整合到 main，
  不得作整合期修复、改为 `DONE`、访问 TASK-007 source、推送或清理 worktree。
- 接受并保留 preflight 成功后、unlink 与最终 CAS 之间的 at-most-once cleanup 风险；不声称
  exactly-once。真实 Whisper 模型下载/加载、ffmpeg、真实转写、媒体/YouTube、网络、Cookie/
  登录、Vault、凭据与真实文件删除继续未授权。

### 最终整合与关闭

- Codex Product Integrator 已从执行基线
  `7d18ecffc61fc0def974ce07ee9dc1ceeb4bf305` 非快进整合 accepted source
  `f00209c8018a9e728d9f6509f0ae70067fa33676`；merge commit 为
  `fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`，双父顺序正确。
- merge 的 staged 和 first-parent 差异均精确为本任务批准的八个路径；唯一新增直接依赖仍为
  `mlx-whisper>=0.4.3,<0.5`，锁定 `0.4.3`，其余新增锁记录属于必要传递依赖树。
- 整合后 `uv lock --check`、`uv sync --locked --offline`、focused `11/12`、全量
  `305`、mypy（13 source files）、Ruff、CLI、offline build 与 sdist/wheel migration
  inclusion 全部 PASS。main 与 retained source worktree 均干净，source 分支/HEAD 保留。
- TASK-006 正式关闭为 `DONE`。真实 Whisper 模型兼容性、资源表现和转换模型许可证继续等待
  后续单独授权；既有 post-unlink/final-CAS at-most-once 风险继续保留。

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
