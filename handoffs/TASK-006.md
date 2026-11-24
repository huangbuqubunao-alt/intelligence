# TASK-006 交接报告

## 元数据

- Task: `TASK-006`（阶段 A）
- Role: `Implementer`
- Agent/session: `Codex`
- Base branch/commit: `main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-006`
- Branch: `codex/task-006-local-transcription`
- Head commit: 待本报告与全部离线检查完成后创建
- Reported: `2026-07-19`

## 目标与范围

- 任务目标：实现完全离线、无模型的本地 Whisper Adapter 阶段 A：依赖锁定，以及可由
  Fake/合成 WAV 验证的策略、缓存、错误映射和音频清理行为。
- 允许修改：`transcription.py`、`providers/whisper.py`、两份 TASK-006 测试、
  `tests/fixtures/audio/**`、`pyproject.toml`、`uv.lock` 和本报告。
- 实际修改：新增纯 `TranscriptionPolicy`/缓存键/受限清理；新增只接受注入
  `WhisperExecutor` 的 `MlxWhisperAdapter`；新增离线测试与合成 WAV 夹具说明；锁定
  `mlx-whisper`。
- 明确未做：未改 `config.py`、`domain.py`、`state.py`、Schema/migration、任务状态或
  `main`；未实现媒体获取、真实模型加载、真实转写或实际的子进程管理。

## 复用、锁定与许可证证据

- `DIRECT`：`mlx-whisper>=0.4.3,<0.5`，实际锁定为 `0.4.3`。官方 PyPI 元数据声明
  MIT、`Requires-Python: >=3.8`，并列出 `mlx`、`numba`、`numpy`、`torch`、`tqdm`、
  `more-itertools`、`tiktoken`、`huggingface_hub`、`scipy`。
- `REFERENCE`：仅使用 MLX 官方 Whisper README 的 `mlx_whisper.transcribe` 说明。
  该说明明确 Hub 模型会自动下载，因此本阶段不导入或调用该函数；代码与测试均未复制
  第三方实现。
- 实际环境：`CPython 3.12.11`、`Darwin arm64`；`uv sync --locked` 成功安装
  `mlx==0.32.0`、`mlx-metal==0.32.0`、`numba==0.66.0`、`llvmlite==0.48.0`、
  `numpy==2.4.6`、`scipy==1.18.0`、`torch==2.13.0`、`tiktoken==0.13.0`、
  `huggingface-hub==1.24.0`、`more-itertools==11.1.0`、`tqdm==4.69.0`，及其锁定的
  次级依赖；这是 Python 3.12/arm64 的解析与安装兼容性证据，不是模型运行证据。
- 许可证复核：`mlx-whisper`/`mlx`/`mlx-metal` 为 MIT；`numba` BSD；`llvmlite`
  BSD-2-Clause + Apache-2.0 WITH LLVM-exception；`numpy` 为多许可证；`torch` 为
  Apache/BSD/MIT 组合；`huggingface-hub` Apache-2.0；`more-itertools` MIT；`tqdm`
  MPL-2.0 + MIT。`scipy` wheel 元数据还枚举 bundled OpenBLAS/LAPACK/GCC runtime 等
  许可证文本；任何捆绑分发前仍需 TASK-014 的完整许可证清单与分发决策。
- 模型风险：`mlx-community/whisper-large-v3-turbo` 未下载；ADR-007 已记录该转换仓库
  model card 没有许可证元数据，不能以 `mlx-whisper` 的 MIT 许可替代模型证据。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| 阶段 A 的短音频、资源/超时错误均可离线观察 | PASS | `test_whisper_provider.py` 用标准库生成确定性静音 PCM WAV，Fake executor 覆盖成功、超长、资源不足、超时、空/畸形响应；没有真实解码或推理。 |
| 同一音频/模型/参数命中缓存，变化时失效 | PASS | `test_transcription_policy.py` 断言确定性键绑定音频 SHA-256、模型、revision、参数策略；provider test 断言第二次调用不再执行 Fake。 |
| 成功、失败和超长清理/保留语义 | PASS | 成功路径只会删除已索引的 `DATA`/`AUDIO`/`EPHEMERAL_AUDIO` 且 SHA-256 匹配的文件，并 CAS 标记删除；哈希不匹配、索引冲突或不合格记录不删除。超长和 Fake 失败路径断言音频仍存在。清理诊断不会否定成功转写。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `uv lock --check` | PASS | 80 个锁定包可复现。 |
| `uv sync --locked` | PASS | 57 个环境包检查通过；无模型资源请求。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS | 6 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS | 6 passed。 |
| `uv run python -m pytest` | PASS | 最终全量复跑为 263 passed。 |
| `uv run mypy src` | PASS | `Success: no issues found in 11 source files`。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | 生成 sdist 与 wheel。 |
| migration 包含性 | PASS | sdist 和 wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |

## 夹具与刻意未运行的资源路径

- 夹具来源：测试以 Python 标准库 `wave` 在 `tmp_path` 生成 16 kHz、16-bit、单声道、
  160 静音帧的确定性 WAV；说明见 `tests/fixtures/audio/README.md`。未存储或下载真实
  媒体，未来自 YouTube 或任何媒体服务。
- 未运行：`mlx_whisper.transcribe`、任何模型/revision/权重下载或加载、Hugging Face
  请求、真实 WAV 解码/推理、ffmpeg 安装或调用、yt-dlp 媒体/YouTube 下载、Cookie/
  登录/`.netrc`、remote components、Vault/密钥、Ollama 以及真实资源/性能冒烟。
- 静态保护：适配器的 AST 测试确认它不导入 `mlx_whisper` 或 `subprocess`；实现中没有
  ffmpeg 调用。

## Diff 复核

- 修改文件：仅任务包允许的 8 类路径：两个产品模块、两份测试、夹具说明、
  `pyproject.toml`、`uv.lock` 和本报告。
- 是否存在任务范围外修改：否。
- 是否存在生成文件或格式化噪声：否；`dist/` 为忽略的本地构建输出，未纳入提交。
- 是否触及红线：仅任务包明确批准的直接依赖与锁文件；未触及 Schema、密钥、真实 Vault、
  云调用、调度配置或任务状态。

## 失败、跳过与风险

- 已解决失败：首次 `uv add` 被受限网络阻断；经用户批准的无代理 PyPI 访问后成功。
  一个夹具目录重复创建错误与一个 Ruff 导入排序错误均已修复；畸形 executor 返回值现被
  映射为 `INVALID_RESPONSE`。
- 跳过检查及原因：无。真实模型/媒体/ffmpeg/资源命令刻意未运行，因为阶段 A 未授权。
- 剩余风险：实际 MLX 模型加载、`multiprocessing` 超时终止、模型哈希/大小门禁、压缩音频
  与 ffmpeg、真实资源基线和模型许可证仍需后续逐项授权与验证。
- `DECISION NEEDED`：`None`。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：待最终全量复跑、Diff/secret 复核和提交后填写给主控。
- 复现/验证说明：从干净 worktree 执行本报告列出的 `uv sync --locked` 与检查命令；
  所有默认测试保持离线。

## Reviewer 结论

- Reviewer agent/session: 待主控分配独立 Codex Reviewer。
- 审查 commit: 待实现提交。
- 重新运行的检查: 待 Reviewer 填写。
- Findings: 待 Reviewer 填写。
- Verdict: 待 Reviewer 填写。
- 未解决 P0/P1: 待 Reviewer 填写。

## 主控验收

- Orchestrator: 待主控填写。
- Verdict: 待主控填写。
- 依据: 待主控填写。
- 批准整合的 commit: 待主控填写。

## 整合结果

- Integrator: 待主控分配。
- 主线 commit: 待整合。
- 整合后检查: 待整合。
- 最终状态: 待整合。

---

## 独立 Reviewer 审查证据（2026-07-19）

### 审查身份、授权与范围

- Reviewer：全新独立 Codex Reviewer；未参与该实现。
- 审查基线：`6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。
- 被审实现：`c6ff804569b376c347719296d80fbe1abf99057a`，分支
  `codex/task-006-local-transcription`，审查开始及全部产品检查前均为干净工作树。
- 动态授权：主仓库
  `git log -1 --format=%H -- agent-prompts/TASK-006-REVIEWER-CODEX.md` 解析为
  `92740a7c68c19657c5b0f70ce8655a6a72062a1d`。该提交的
  `docs/PROJECT_STATUS.md` 将此精确 source `c6ff804...` 标为 `IN_REVIEW`；未读取、
  运行、修改或报告 TASK-007 worktree。
- `git diff --check 6b4d59c...c6ff804...` 通过。完整范围恰为允许的 8 个路径：两份产品模块、
  两份 TASK-006 测试、音频夹具说明、`pyproject.toml`、`uv.lock` 和本 handoff。
- 红线/范围复核：未见 Schema/migration、`state.py`、密钥、Vault、Cookie/登录、真实网络、
  媒体、ffmpeg、模型加载或任务状态改动；`dist/` 仅为 ignored 的离线构建产物。

### 重新运行的必需检查

| 命令 | 独立结果 |
|---|---|
| `uv lock --check` | PASS — `Resolved 80 packages`。 |
| `uv sync --locked` | PASS — `Checked 57 packages`；未触发模型或媒体资源。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS — 6 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS — 6 passed。 |
| `uv run python -m pytest` | PASS — 263 passed。 |
| `uv run mypy src` | PASS — 11 source files 无问题。 |
| `uv run ruff check .` | PASS。 |
| `uv run python -m youtube_intel --help` | PASS。 |
| `uv build --offline` | PASS — 生成 sdist/wheel；两者均含 `youtube_intel/migrations/001_initial.sql`，与源文件 SHA-256 同为 `10bd726f...2693006`。 |

### 独立探针

#### A. 依赖、导入与离线边界

- `pyproject.toml` 的唯一新增直接依赖为
  `mlx-whisper>=0.4.3,<0.5`；锁定版本为 `0.4.3`。本地安装元数据复核为 MIT、
  `Requires-Python >=3.8`，其 `Requires-Dist` 与锁定闭包一致：MLX/MLX Metal、
  numba/llvmlite/numpy、scipy、torch（及平台 marker 的 CUDA 条目）、tiktoken/regex、
  Hugging Face Hub/httpx 及其必要传递依赖、more-itertools、tqdm。没有第二个新增直接依赖。
- AST/静态探针确认 `providers/whisper.py` 不导入 `mlx_whisper`、`subprocess`、
  `urllib`、`requests`、`http`、`socket` 或 `huggingface_hub`；Adapter 只能调用必需注入的
  `WhisperExecutor`。未导入或调用真实 `mlx_whisper.transcribe`，未调用 ffmpeg、模型下载或网络 API。
- `tests/fixtures/audio/` 只有 `README.md`；测试以标准库 `wave` 在临时目录生成确定性静音
  PCM WAV。没有可再分发现实媒体或下载夹具。

#### B. 缓存、策略与错误完整性

- 临时离线 Fake-executor 探针先验证完全相同请求命中缓存，再分别改变音频 SHA-256、模型、
  revision、参数策略版本；共 5 次 executor 调用，只有完全相同的请求复用。超时、资源错误、
  `ValueError`、未知错误及畸形返回分别映射为安全的
  `LOCAL_RESOURCE`、`LOCAL_RESOURCE`、`INVALID_RESPONSE`、`PROVIDER_UNAVAILABLE`、
  `INVALID_RESPONSE`，消息不含临时绝对路径或 `SECRET` 文本。
- 超长策略在 executor 之前短路；失败或畸形返回不写入缓存，随后成功调用和第二次缓存命中均通过。
- 这些探针没有导入模型包模块或调用真实模型。

#### C. 真实 SQLite 与 DATA 根清理探针

- 临时目录中以真实 `SQLiteStateRepository` 初始化 migration、写入 discovery/video/artifact，
  再调用 `cleanup_successful_audio`。正常已登记的 `DATA` / `AUDIO` /
  `EPHEMERAL_AUDIO` 且哈希匹配的记录得到 `DELETED`：文件消失、SQLite `deleted_at` 已设置。
- 错误 kind、retention、storage root 和文件哈希不匹配均被拒绝并保留音频；符号链接逃逸被拒绝，
  根外目标和链接均保留（当前诊断值为 `MISSING`）。清理失败不会删除已创建的 transcript marker。
- **失败反例（阻断）**：伪造/缺失 Artifact id 和已由另一方标记删除的陈旧 Artifact snapshot 均返回
  `INDEX_CONFLICT`，但对应音频文件已经被删除。这与“只删除已登记、哈希匹配且 CAS 成功的
  Artifact；拒绝 missing/stale CAS”的要求不符。

### 验收矩阵与阶段诚实性

| 项目 | 结果 | 证据 |
|---|---|---|
| 阶段 A 离线短音频、策略/资源/超时错误 | PASS | Fake 与合成 WAV 的定向及独立探针均通过。 |
| 缓存命中及模型/revision/参数/音频变化失效 | PASS | 定向测试和独立 5 维变化探针通过。 |
| 成功、失败、超长音频保留/清理语义 | FAIL | 成功、普通失败和超长路径通过；missing/stale CAS 会删除音频，见 P1。 |
| 无隐藏真实模型、进程、ffmpeg 或媒体主张 | PASS | Adapter 为注入 executor 边界；资源/模型/ffmpeg/媒体门禁仍明确 deferred。 |

### Findings（P0–P3）

- P0：无。
- **P1-1 — CAS 失败仍删除文件，且不验证 Artifact 当前已登记。**
  `src/youtube_intel/transcription.py:216-222` 在调用
  `repository.mark_artifact_deleted(...)` 前已经执行 `resolved.unlink()`。因此 caller 传入
  不存在的 `artifact_id` 或从并发更新前取得的 snapshot 时，真正的 SQLite CAS 返回 `False`，
  函数返回 `INDEX_CONFLICT`，但已删除 DATA 文件。现有回归测试甚至在
  `tests/unit/test_transcription_policy.py:199-207` 将这种 index conflict 后文件不存在作为预期。
  这会制造未标记的物理删除，违反 ADR-007 L-14、System Design §10 及本轮 C 探针的
  missing/stale-CAS 约束；必须在后续修复中以可验证的登记/并发协议关闭，不能把失败当作成功。
- P2-1 — 清理哈希验证对合法大音频一次性读取全部内容。`src/youtube_intel/transcription.py:210`
  使用 `resolved.read_bytes()`；策略允许最多 2,000,000,000 bytes（第 77 行），且此路径不捕获
  `MemoryError`。应改为分块 SHA-256，以维持本地资源边界；此项不改变 P1 阻断结论。
- P3：无。

### 复用、许可证、秘密与未运行路径

- 复用结论：`mlx-whisper` 为已授权范围内的 `DIRECT`；本审查独立复核直接包元数据和完整锁定依赖闭包。
  传递的 Hub/httpx 能力来自包依赖，未被 Phase A 代码导入或调用。模型转换仓库许可证风险仍按
  ADR-007/TASK-014 延后，因本轮没有下载模型。
- Secret 扫描：对完整 base...source Diff 以私钥、AWS、GitHub 和典型 API key 模式扫描，无命中。
- 刻意未运行且仍未获授权：`mlx_whisper.transcribe`、模型/权重/Hugging Face 下载或加载、ffmpeg、
  任何媒体/YouTube 请求、Cookie/登录、remote components、Vault/凭据、真实资源和性能冒烟、
  multiprocessing 实际终止。

### Reviewer 结论

- Verdict: **REJECT**。
- 未解决 P0/P1：P1-1。
- 原因：P1-1 使成功清理不再以真实 Artifact CAS 成功为前提，且缺失或陈旧索引会丢失文件；
  因此 Phase A AC 的音频保留/恢复项未满足。其余规定的离线检查、范围、依赖、许可证、夹具、
  Phase A 资源边界和缓存/错误探针均通过。
- 建议：退回原 Implementer，在不扩展 Schema、真实资源或任务范围的前提下提出可验证的
  Artifact 登记与 CAS/文件删除恢复协议，并加入真实 SQLite 的 missing/stale-CAS 回归；随后由新的
  独立 Reviewer 重跑全部门禁。

---

## Correction 1 — P1 cleanup preflight closure（2026-07-19）

### 范围与复用

- Correction parent：`f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`（review evidence）；本报告
  随本次 correction commit 一并提交。
- 精确四文件范围：`src/youtube_intel/transcription.py`、
  `tests/unit/test_transcription_policy.py`、
  `tests/integration/test_whisper_provider.py`、本报告。
- 未修改：`state.py`、Schema/migration、依赖/锁文件、Provider surface、任务状态或 `main`；
  未运行模型、ffmpeg、媒体、网络、凭据、Vault 或非测试临时文件删除。
- `DIRECT`：复用既有 `SQLiteStateRepository.get_artifact_by_key()` 和
  `mark_artifact_deleted()` 的公开语义，以及 Python 标准库 `hashlib`/`pathlib`；未新增依赖或
  外部代码。哈希改为 1 MiB 分块读取，避免对允许的大音频整读入内存。

### P1 closure

- `cleanup_successful_audio()` 现在在任何 `unlink()` 前读取当前 Artifact，并验证精确
  `artifact_id`、`artifact_key`、content hash、`AUDIO`、`DATA`、DATA-relative path、
  `EPHEMERAL_AUDIO` 与 `deleted_at is None`。缺失、已删除、未知 ID 或任一索引快照不一致均返回
  无路径/内容的 `INDEX_CONFLICT`，并保留音频字节。
- 随后才验证受控 DATA-root 路径、拒绝符号链接或逃逸、流式计算文件 SHA-256；失败保留字节并只返回
  枚举诊断。成功时仍严格遵循既有设计：先受控删除文件，再调用未修改的 index-only
  `mark_artifact_deleted()`。
- 临时真实 SQLite regressions 证明：未知 ID 与已删除的陈旧 snapshot 都保留音频；有效记录才会删除
  并写入 `deleted_at`；错误 kind/retention/root/hash、缺失/已删除记录、符号链接/路径逃逸都不删除。
  最终 CAS race 也有覆盖，诊断不包含临时路径或内容。

### 残余 at-most-once window

- 预检读取成功到文件已删除、再到最终 CAS 的窗口无法在不新增 reservation/lock/Schema 或改变
  `state.py` 契约的条件下消除。若并发方在预检后改变索引，文件已删除时最终 CAS 仍可能返回 `False`；
  函数返回非成功的 `INDEX_CONFLICT`，不报告索引成功、不重试也不声称 exactly-once。
- 因此该清理是已文档化的 at-most-once best effort：P1 的 missing/stale-before-unlink 数据丢失已关闭，
  但 post-unlink CAS 竞争不能回滚物理删除，留待任何未来已批准的跨资源协调设计。

### Correction checks

| 命令/检查 | 结果 | 关键证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 80 packages`。 |
| `uv sync --locked` | PASS | `Checked 57 packages`；未触发模型或媒体资源。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS | 10 passed；预检与路径安全回归。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS | 9 passed；真实 SQLite unknown/stale/success/race 回归。 |
| `uv run python -m pytest` | PASS | 270 passed。 |
| `uv run mypy src` | PASS | 11 source files 无问题。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist/wheel 构建成功。 |
| migration package inclusion | PASS | sdist 与 wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |
| `git diff --check` | PASS | 无空白错误；最终提交前复跑。 |

### Implementer correction conclusion

- 建议状态：`IN_REVIEW`
- Correction commit SHA：待全部最终范围/敏感信息/Diff 复核完成后创建。
- `DECISION NEEDED`：None。残余 CAS 窗口已按本节显式记录，未以未获批准的 reservation、lock、Schema 或
  `state.py` 变更掩盖。

---

## Correction 1 — 第二次独立 Codex Reviewer 审查证据（2026-07-19）

### 授权、身份与范围

- Reviewer：全新独立 Codex Reviewer；未参与实现或第一轮审查。
- 动态授权：主仓库对
  `agent-prompts/TASK-006-REVIEWER-2-CODEX.md` 的最新提交为
  `7fd56716eac58a7878c5e64f99d811f0c5cfdc3e`；其 prompt blob
  `4f7d1933a62012d710001854defe8def0628ead5` 与被读取的授权文件一致。
  主控授权记录已将 TASK-006 Correction 1 置为 `IN_REVIEW`。
- 审查范围：完整 `6b4d59c882ccdcbd0e5a6069a6661e0672921a80...17afcd349827b36e5ba18fb0eab443c1ae5fb53f`；
  被审 source 为干净的 `codex/task-006-local-transcription`，HEAD 精确为
  `17afcd349827b36e5ba18fb0eab443c1ae5fb53f`，唯一父提交为
  `f1c15ed6eb854a4a8ed2299bbbf89e1cb6266426`。
- Correction-only Diff 精确为本报告、`src/youtube_intel/transcription.py`、
  `tests/unit/test_transcription_policy.py` 与
  `tests/integration/test_whisper_provider.py`。未改 lockfile、依赖、Schema/migration、
  `state.py`、任务状态、`main` 或 Provider surface。

### 独立重新运行的检查

| 命令/检查 | 结果 | 关键证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 80 packages`。 |
| `uv sync --locked --offline` | PASS | `Resolved 80 packages`，`Checked 57 packages`；没有 cache miss 或网络请求。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS | 10 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS | 9 passed。 |
| `uv run python -m pytest` | PASS | 270 passed。 |
| `uv run mypy src` | PASS | 11 个 source files 无问题。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | 成功生成 sdist 与 wheel。 |
| migration package inclusion | PASS | sdist 与 wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |
| `git diff --check 6b4d59c...17afcd...` | PASS | 无空白错误。 |

### 独立临时 SQLite / DATA-root 探针

- 使用临时真实 `SQLiteStateRepository`、临时 DATA 根和合成字节。未知、缺失、已删除、
  以及 current Artifact 的 kind/retention/root/path/hash 不匹配均返回
  `INDEX_CONFLICT` 且音频保留；调用方提供 `../` 路径也在 preflight 返回
  `INDEX_CONFLICT` 并保留音频。
- 当前、匹配的 `DATA` / `AUDIO` / `EPHEMERAL_AUDIO` Artifact 能删除音频并写入
  `deleted_at`。模拟 final CAS race 时文件已删除但结果为非成功
  `INDEX_CONFLICT`；未引入 reservation、Schema 或 exactly-once 声明。
- 文件字节哈希被篡改时得到 `HASH_MISMATCH` 且保留音频。SQLite 自身拒绝把 `../...`
  作为 Artifact relative path 持久化。
- **反例：** 当前 Artifact 的音频文件被替换为符号链接时，函数在
  `src/youtube_intel/transcription.py:235-236` 返回 `PATH_OUTSIDE_DATA`，而不是本轮
  授权要求的安全 `INDEX_CONFLICT`；链接和根外目标都保留。单元测试也在
  `tests/unit/test_transcription_policy.py:303` 固化了错误枚举。

### Fake-only、缓存、资源与错误边界探针

- 静态 AST 检查确认 `providers/whisper.py` 不导入 `mlx_whisper`、`subprocess`、
  `urllib`、`socket` 或 `huggingface_hub`；仅注入 Fake executor，未加载模型、调用
  ffmpeg 或访问网络/媒体。
- 相同音频/模型/revision/参数策略只执行 Fake 一次；更改模型产生不同 cache key 并再次
  执行。超长纯策略在 executor 前短路，Fake timeout 映射为可重试的
  `LOCAL_RESOURCE`，错误消息不含临时绝对路径或合成的 secret 文本。

### AC 与 ADR-007 矩阵

| 项目 | 结果 | 证据 |
|---|---|---|
| AC：离线短音频、资源/超时观察 | PASS | Fake/合成 WAV 定向测试与独立探针。 |
| AC：音频、模型/revision/参数缓存身份 | PASS | 10/9 focused tests 与独立 cache-key 探针。 |
| AC：成功、失败、超长的音频保留/清理 | FAIL | 文件保留安全性通过，但符号链接拒绝的结果码违反本轮显式 `INDEX_CONFLICT` 合约。 |
| ADR-007 L-10/L-11 | PASS | 锁定依赖已离线安装；没有模型 import、加载或下载。 |
| ADR-007 L-12 | PASS | 无 yt-dlp 媒体下载、ffmpeg、Cookie、remote component 或网络路径。 |
| ADR-007 L-13/L-15 | PASS | duration/resource 仍是纯策略并在 executor 前执行；未改状态机或真实资源逻辑。 |
| ADR-007 L-14 | FAIL | preflight、哈希、DATA 边界和 post-delete CAS 均通过；但 symlink 拒绝未返回规定的 `INDEX_CONFLICT`。 |

### 五轴审查、复用与红线

- Correctness：除下列 P1 外，预检、流式 SHA-256、有效删除与 post-delete CAS race
  均符合 Correction 1 目标。
- Readability：具名 enum 和小型协议使控制流可读；无无关重构或死代码发现。
- Architecture：继续复用既有 `get_artifact_by_key` / `mark_artifact_deleted`，没有绕过
  Repository、添加 reservation 或修改 Schema。
- Security：路径、根边界、哈希与错误脱敏均保留；P1 是安全拒绝的公共诊断契约不一致，
  不是物理删除逃逸。
- Performance：SHA-256 为 1 MiB 流式读取；未发现无界集合、N+1 或模型热路径。
- Reuse：Correction 仅 `DIRECT` 复用既有 SQLite Artifact API 与 Python 标准库；没有新增
  依赖或外部代码。完整 Diff 的凭据格式扫描未发现密钥；匹配到的 `task-006-local-...`
  只是分支文本。
- Scope/red-line：完整范围为任务批准的 8 个路径，Correction 为批准的 4 个路径；无
  lockfile correction、Schema、密钥、Vault、任务状态或生产配置变更。

### 刻意跳过的未授权路径

- 未运行或访问：`mlx_whisper.transcribe`、模型/权重下载或加载、Hugging Face、ffmpeg、
  YouTube/媒体、Cookie/登录、remote components、Vault/credentials、真实资源/性能冒烟、
  multiprocessing 终止。所有临时数据均在测试临时目录中创建。

### Findings（P0–P3）与结论

- P0：无。
- **P1-1 — 符号链接/路径逃逸的拒绝枚举违反当前审查授权。**
  `src/youtube_intel/transcription.py:228-246` 对符号链接、绝对/逃逸路径返回
  `PATH_OUTSIDE_DATA`；`tests/unit/test_transcription_policy.py:286-307` 明确将其作为
  预期。本轮授权要求这些情况“each return safe `INDEX_CONFLICT` and retain audio”。独立
  SQLite/DATA-root 探针复现：`symlink-escape: PATH_OUTSIDE_DATA; safety=True`。虽然文件
  与根外目标都保留，调用方不能依赖指定的统一 conflict 语义；修复应只调整该安全拒绝
  结果及其离线回归，不应触及 CAS、Schema、reservation 或真实资源路径。
- P2：无。
- P3：无。
- Verdict：**REJECT**。
- 未解决 P0/P1：P1-1。
- `DECISION NEEDED`：None；这是明确授权/测试契约的不一致，不需要扩展范围或新增批准。

---

## Correction 2 — safe conflict for cleanup path escapes（2026-07-19）

### 授权、范围与复用

- 授权提交已核验为 `5cb2a0d3ce5bc9f883e83e4861fc528a92a1f884`；开始时工作树干净，
  `47599db196b1b9440de3ae57ec3547935f64b1dc` 的唯一父提交为
  `17afcd349827b36e5ba18fb0eab443c1ae5fb53f`。主控 TASK-006 状态为
  `IN_PROGRESS`，Assignee 为 Codex；本次没有修改任务状态、`main`、Reviewer、merge 或 push。
- 精确修改范围为 `src/youtube_intel/transcription.py`、
  `tests/unit/test_transcription_policy.py`、
  `tests/integration/test_whisper_provider.py` 和本报告。未修改 Provider、`state.py`、
  Schema/migration、依赖/锁文件、配置或凭据。
- `DIRECT` 复用既有 `AudioDeletionRepository`/SQLite Artifact API 与 Python 标准库
  `pathlib`；没有新增依赖、reservation、Schema 或 exactly-once 语义。

### P1 closure

- `cleanup_successful_audio()` 对绝对路径、含 `..` 的相对路径、末端符号链接及解析后逃出
  DATA 根的路径，现均返回无路径/内容的可重试 `INDEX_CONFLICT`。这些分支在哈希或 `unlink()`
  前返回，因而保留链接、目标和根外合成音频。
- 未改变未知/缺失 Artifact、哈希不匹配、kind/retention/root 资格、有效删除或最终 CAS race 的
  原有路径。保留 `PATH_OUTSIDE_DATA` 枚举以避免无关的公共契约删除；本任务指定的全部清理逃逸
  预检均不再返回它。
- 单元 RED 先确认旧实现的符号链接、`../` 与绝对路径都返回
  `PATH_OUTSIDE_DATA`；GREEN 后统一为 `INDEX_CONFLICT`，且没有调用 index 删除。SQLite 的
  Artifact 写入 API 会拒绝不安全 relative path，故该两类受控索引快照测试不绕过或篡改真实
  SQLite；另有临时真实 SQLite/DATA 根回归覆盖已登记音频替换为符号链接，确认链接、外部合成目标
  和 `deleted_at` 全部保留。

### Correction checks

| 命令/检查 | 结果 | 关键证据 |
|---|---|---|
| `uv lock --check` | PASS | `Resolved 80 packages`。 |
| `uv sync --locked --offline` | PASS | `Resolved 80 packages`，`Checked 57 packages`。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS | 11 passed；先 RED 后覆盖符号链接、`..` 与绝对逃逸。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS | 10 passed；临时真实 SQLite/DATA 符号链接保留回归。 |
| `uv run python -m pytest` | PASS | 272 passed。 |
| `uv run mypy src` | PASS | 11 source files 无问题。 |
| `uv run ruff check .` | PASS | `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS | CLI 帮助正常输出。 |
| `uv build --offline` | PASS | sdist/wheel 构建成功。 |
| migration package inclusion | PASS | sdist 与 wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |
| `git diff --check 47599db...HEAD` | PASS | 单一 correction commit 创建后无空白错误。 |

### 未运行的未授权路径

- 未下载或加载模型/权重，未调用 `mlx_whisper`、ffmpeg、媒体/YouTube、网络、Cookie、remote
  components、Vault 或 credentials；未运行真实转录。
- 所有新音频、SQLite 数据库、DATA 根、符号链接和删除尝试都在 pytest 临时目录中；没有删除真实
  资源。未尝试 reservation、migration、依赖/锁变更或其它任务范围。

---

## Correction 2 — 第三次独立 Codex Reviewer 审查证据（2026-07-19）

### 授权、身份与范围

- Reviewer：全新独立 Codex Reviewer；未参与实现或前两次审查。
- 主仓库授权提交：`3eeeac58a5662c4098b1d483f70c9b94fca23699`（`TASK-006-REVIEWER-3-CODEX.md`）；
  主控任务状态为 `IN_REVIEW`。
- 被审 source：`51b308828a6f2c433a9b4e92fb4a24e042f55d77`，唯一父提交
  `47599db196b1b9440de3ae57ec3547935f64b1dc`；审查开始时工作树干净。
- 全量 `6b4d59c...51b308...` Diff 为八个授权路径。Correction 2 相对 `47599db...` 仅改本报告、
  `transcription.py` 和两份测试；`pyproject.toml`/`uv.lock` 无 correction 差异。没有 Schema、
  migration、`state.py`、任务状态、配置、凭据、真实资源、merge、push 或 source clean 操作。

### 离线门禁与包检查

| 命令 | 独立结果 |
|---|---|
| `uv lock --check` | PASS — Resolved 80 packages。 |
| `uv sync --locked --offline` | PASS — Resolved 80，Checked 57 packages。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS — 11 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS — 10 passed。 |
| `uv run python -m pytest` | PASS — 272 passed。 |
| `uv run mypy src` | PASS — 11 source files 无问题。 |
| `uv run ruff check .` | PASS。 |
| `uv run python -m youtube_intel --help` | PASS。 |
| `uv build --offline` | PASS — 生成 sdist/wheel。 |
| migration 包产物检查 | PASS — sdist 和 wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |
| `git diff --check 6b4d59c...51b308...` | PASS。 |

### 独立探针

- **缓存身份反例（FAIL）**：共享 Fake-only cache 的 `language_hint="en"` 与 `"fr"` 两次请求，
  结果为 `{'calls': ['en'], 'first_text': 'text-en', 'second_text': 'text-en',
  'second_cache_hit': True}`。没有模型、音频解码或文件读取；`language_hint` 未进入缓存键。
- **真实临时 SQLite/DATA-root 矩阵**：unknown、missing、已删除/stale、索引 hash 不匹配、绝对与
  `..` 路径、末端符号链接及中间目录符号链接 DATA-root escape 均为 `INDEX_CONFLICT`，文件/链接/
  根外合成目标均保留，诊断不含路径。匹配 `AUDIO`/`DATA`/`EPHEMERAL_AUDIO` 的成功路径为 `DELETED`
  并写入 `deleted_at`。
- **最终 CAS race**：真实 SQLite wrapper 在 unlink 后先完成既有 CAS、再返回 `False`；结果
  `{'result': 'INDEX_CONFLICT', 'file_removed': True, 'index_marked': True}`，符合已授权的
  at-most-once 窗口，未引入 reservation、Schema 或 exactly-once 声明。
- **错误 Artifact 枚举反例（FAIL）**：错误 kind、retention、storage root 的传入 Artifact 均保留
  文件，但分别返回 `INELIGIBLE_ARTIFACT`；当前审查包要求这些安全拒绝统一为可重试
  `INDEX_CONFLICT`。
- 静态检查确认没有 `mlx_whisper`、`subprocess`、网络客户端或 ffmpeg 调用；安装元数据为
  `mlx-whisper==0.4.3`、MIT、`Requires-Python: >=3.8`。完整 Diff 的常见私钥/AWS/GitHub/OpenAI
  key 模式扫描无命中。

### AC / ADR-007 与五轴审查

| 项目 | 结果 | 证据 |
|---|---|---|
| AC：离线 Fake/合成 WAV、资源与超时 | PASS | 规定 focused tests 和静态边界通过。 |
| AC：音频、实现/模型与参数的缓存身份 | FAIL | 不同 `language_hint` 命中旧语言的缓存文本。 |
| AC：成功、失败、超长的安全清理 | FAIL | 路径与 CAS 通过；kind/root/retention 的强制拒绝枚举不符。 |
| ADR-007 L-10/L-11 | FAIL | 无模型加载/下载；但 L-10 `language_hint` 未进入缓存身份。 |
| ADR-007 L-12 | PASS | 无媒体、ffmpeg、Cookie、remote component 或网络路径。 |
| ADR-007 L-13/L-15（阶段 A） | PASS | 纯策略在 Fake executor 前拒绝；未改状态机或真实资源逻辑。 |
| ADR-007 L-14 | FAIL | 当前审查包指定的错误 Artifact 安全枚举不符合。 |

- Correctness：两项 P1 如下；Correction 2 的路径逃逸和最终 CAS 语义未退化。
- Readability：cleanup 预检顺序清楚，1 MiB 分块 SHA-256 避免整文件读取；未见无关重构或死代码。
- Architecture：复用冻结的 Repository read/post-delete CAS，未增加 reservation、Schema 或 wrapper；
  但可变 decode 参数未被缓存边界隔离。
- Security/privacy：路径脱敏与零物理逃逸通过；P1-2 破坏明确的可重试 fail-closed 枚举契约。
- Performance/resources：没有 N+1、无界循环或模型热路径；P1-1 可能错误省略所需转写。
- Scope/red lines/reuse/licensing：范围正确，Correction 未改依赖/锁、Schema、密钥或生产配置；
  仅直接复用既有 SQLite Artifact API、Python 标准库和已授权 `mlx-whisper`。模型许可证与真实
  兼容性继续 deferred。

### 刻意跳过的未授权路径

- 未下载、导入或加载 Whisper 模型/权重，未调用 `mlx_whisper.transcribe`、ffmpeg、媒体/YouTube、
  网络、Cookie、remote components、Vault/credentials、真实资源/性能冒烟或 multiprocessing 终止。
- 所有探针只使用系统临时目录的合成字节、SQLite、DATA 根和测试文件；未删除真实文件。

### Findings（P0–P3）与结论

- P0：无。
- **P1-1 — `language_hint` 不在缓存身份中，可返回错误语言的旧转写。**
  `src/youtube_intel/providers/whisper.py:54-85` 允许 `language_hint` 变化，而 147-152 行调用的
  `src/youtube_intel/transcription.py:106-129` 缓存键未包含它。独立 Fake probe 已复现 `fr` 请求
  命中 `en` 文本。必须将实际语言提示纳入稳定键，或禁止该参数可变并补回归测试。
- **P1-2 — 错误 kind/root/retention 的 Artifact 未返回强制的 `INDEX_CONFLICT`。**
  `src/youtube_intel/transcription.py:214-220` 返回 `INELIGIBLE_ARTIFACT`，且
  `tests/unit/test_transcription_policy.py:224-237` 固化这一行为。当前审查包要求 wrong-kind、
  wrong-retention、wrong-root 与 unknown/missing/stale/hash mismatch 一样返回可重试
  `INDEX_CONFLICT`；真实 SQLite probe 已复现三种不符枚举。修复并覆盖实际 Repository 路径后再审。
- P2：无。
- P3：无。
- Verdict：**REJECT**。
- 未解决 P0/P1：P1-1、P1-2。
- `DECISION NEEDED`：None。P1-1 位于 `providers/whisper.py`；若后续 correction 保持本轮四文件
  范围，主控须先明确扩展范围。

---

## Correction 3 — P1 closure（2026-07-20）

### 授权、范围与复用

- 主仓库授权已核验为 `aee73330d864fa0806a999bce8168cd8ec403dc3`；开始时 source
  worktree 干净，分支为 `codex/task-006-local-transcription`，起点
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7` 的唯一父提交为
  `51b308828a6f2c433a9b4e92fb4a24e042f55d77`，主控 TASK-006 状态为 `IN_PROGRESS`。
- 本 correction 仅修改批准的五个路径：`transcription.py`、唯一的
  `providers/whisper.py` cache-key call site、两份指定测试和本报告；未改 `state.py`、
  Artifact API、Schema/migration、依赖/锁文件、配置、任务状态、`main` 或凭据。
- `DIRECT` 复用已有 `WhisperDecodePolicy`、`TranscriptionCache`、SQLite Artifact API 与
  Python 标准库；没有新增依赖、外部代码、reservation、claim 或 exactly-once 机制。

### P1 closure 与回归

- `build_transcription_cache_key()` 现在要求关键字参数 `language_hint: str | None`，并把
  已验证的 `WhisperDecodePolicy.language_hint` 纳入稳定 JSON 哈希。唯一 Adapter call site
  直接传入该已有值；没有新增 Adapter 参数、改变 executor 调用或改变 language-hint 验证。
- 先 RED：四项 focused regression 均按预期失败，分别暴露缺失的关键字参数、`en`/`zh`
  cache collision，以及 wrong kind/root/retention 仍返回 `INELIGIBLE_ARTIFACT`。
  GREEN 后，synthetic WAV + shared Fake cache 验证不同 hint 各执行一次、cache key 不同；
  相同 `en` hint 仍命中既有缓存。unit cache-key 回归同时验证 `None` 保持确定性且不同于
  非空 hint。
- cleanup 的既有最前置资格检查顺序和后续 index/hash/path/unlink/CAS 顺序均未改变；wrong
  kind、non-DATA root、wrong retention 和已删除传入 record 统一返回可重试、无路径的
  `INDEX_CONFLICT`。`INELIGIBLE_ARTIFACT` enum 保留，避免无关 Artifact API 变更。
- 临时真实 SQLite/DATA-root 回归使用合成音频和外部临时目标，验证三类 ineligible request
  都保留 DATA 文件、外部目标和 index `deleted_at`，结果不泄露任一路径。既有 unknown、
  missing、deleted/stale、hash mismatch、path/symlink escape、成功删除及 final CAS race
  tests 仍全部通过。

### 离线检查与包内容

| 命令/检查 | 结果 |
|---|---|
| `uv lock --check` | PASS — Resolved 80 packages。 |
| `uv sync --locked --offline` | PASS — Resolved 80，Checked 57 packages。 |
| focused RED then GREEN | PASS — 4 项 P1 regressions 先失败后 4 passed。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS — 11 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS — 12 passed。 |
| `uv run python -m pytest` | PASS — 274 passed。 |
| `uv run mypy src` | PASS — 11 source files 无问题。 |
| `uv run ruff check .` | PASS。 |
| `uv run python -m youtube_intel --help` | PASS。 |
| `uv build --offline` | PASS — sdist 和 wheel 均构建成功。 |
| migration 包内容 | PASS — sdist/wheel 均含 `youtube_intel/migrations/001_initial.sql`。 |

### 刻意跳过与剩余风险

- 未下载、导入或加载 Whisper 模型/权重，未调用 `mlx_whisper`、ffmpeg、媒体/YouTube、网络、
  Cookie、remote components、Vault 或 credentials；未运行真实转录。所有新建音频、SQLite、
  DATA 根和外部目标均在 pytest 临时目录中。
- 保留既有 at-most-once 限制：unlink 成功后最终 `mark_artifact_deleted()` CAS 可能竞争失败，
  因而仍返回 `INDEX_CONFLICT` 且文件已删除；本 correction 未引入 reservation 或严格
  exactly-once 声明。

---

## Correction 3 — 第四次独立 Codex Reviewer 审查证据（2026-07-20）

### 审查身份、授权与范围

- Reviewer：全新独立 Codex Reviewer；未实现 TASK-006，也未参与前三次审查。
- 固定基线为 `6b4d59c882ccdcbd0e5a6069a6661e0672921a80`。审查 source 是
  `codex/task-006-local-transcription@548338978b8656db0c650be276f847850af940a1`；唯一父提交精确为
  `66f0b31023c290d76e2c14bea72d1cc103cc27c7`。审查开始及写入本节前，source worktree 均干净。
- 主仓动态授权：`git -C '/Users/developer/Documents/youtubek agent' log -1 --format=%H --
  agent-prompts/TASK-006-REVIEWER-4-CODEX.md` 解析为
  `3a6d0c38b0869622581e4f763371147c6c30d2d9`。该提交中的 `docs/PROJECT_STATUS.md` 明确将此精确
  source 列为第四次独立审查，TASK-006 状态为 `IN_REVIEW`。
- 完整 `6b4d59c...5483389...` 范围精确为 8 个初始批准路径：本报告、`pyproject.toml`、`uv.lock`、
  两个产品模块、两个既有测试和合成音频 README。Correction 3 相对其唯一父提交精确为 5 个授权
  路径：本报告、`transcription.py`、两份既有测试以及 `providers/whisper.py`。
- Provider correction-only Diff 只有一行：既有 `build_transcription_cache_key()` 调用点传入
  `language_hint=self._decode_policy.language_hint`。没有新增公共 Adapter 方法参数、策略规范化、
  executor 行为、Repository/Schema/state、依赖或锁文件改动。`pyproject.toml` 与 `uv.lock` 相对
  Correction 3 父提交的 Diff 为零。

### 必需离线复跑与包检查

| 命令/检查 | 独立结果 |
|---|---|
| `uv lock --check` | PASS — `Resolved 80 packages`。 |
| `uv sync --locked --offline` | PASS — `Resolved 80 packages`，`Checked 57 packages`；没有 cache miss 或下载。 |
| `uv run python -m pytest tests/unit/test_transcription_policy.py` | PASS — 11 passed。 |
| `uv run python -m pytest tests/integration/test_whisper_provider.py` | PASS — 12 passed。 |
| `uv run python -m pytest` | PASS — 274 passed。 |
| `uv run mypy src` | PASS — 11 source files 无问题。 |
| `uv run ruff check .` | PASS — `All checks passed!`。 |
| `uv run python -m youtube_intel --help` | PASS — CLI 帮助正常输出。 |
| `uv build --offline` | PASS — 生成 `youtube_intel-0.1.0.tar.gz` 与 `youtube_intel-0.1.0-py3-none-any.whl`。 |
| 生成包人工检查 | PASS — `tar -tzf` 与 `unzip -l` 均列出 `youtube_intel/migrations/001_initial.sql`。 |
| `git diff --check 6b4d59c...5483389...` | PASS — 无空白错误。 |

所有 uv 命令严格离线；执行环境需要读取既有 uv cache，未触发网络下载或依赖解析写入。

### 独立探针

#### 1. 语言提示缓存身份与 hard-to-omit API

- 在系统临时目录以合成字节和共享 `InMemoryTranscriptionCache` 构造三个 Fake-only Adapter：
  `language_hint=None`、`"en"` 与 `"zh"`。三次首次请求均 miss，产生三个不同 key 和对应
  `synthetic-none` / `synthetic-en` / `synthetic-zh` 结果；各自第二次请求均 hit。Fake executor 调用
  精确为 `[None, "en", "zh"]`，没有跨 hint 复用结果。
- 直接调用 `build_transcription_cache_key()` 再次证明 `None`、`"en"`、`"zh"` 三个 stable JSON
  hash 全异；相同 `"en"` 输入重复计算得到相同 key。
- `inspect.signature()` 证明 `language_hint` 是无 default 的 `KEYWORD_ONLY` 参数；源码确认其位于
  `sort_keys=True`、紧凑 deterministic JSON body 中。`MlxWhisperAdapter.__init__` 与 `.transcribe`
  的公开参数面未出现新的 `language_hint` 参数。
- 复核原有策略语义：默认值仍为 `None`；空串与纯空白字符串仍抛出 `ValueError`；非空的
  `" en "` 仍原样保留，未引入无授权的规范化。executor 接收既有、冻结的
  `WhisperDecodePolicy` 对象。

#### 2. Provider 离线与边界探针

- AST/import 探针确认 `providers/whisper.py` 不导入 `mlx_whisper`、`subprocess`、`urllib`、`http`、
  `requests`、`socket` 或 `huggingface_hub`，源码也不含 ffmpeg 路径。该 Adapter 只能使用注入的
  Fake executor；没有模型加载/下载、媒体读取、网络、子进程或 ffmpeg 行为。
- 复查 focused integration tests 与源码：资源/时长决策在 executor 前拒绝；Fake `TimeoutError`、
  `MemoryError`/`OSError`、`ValueError` 和未知异常仍映射为既有安全错误；空或畸形响应仍为
  `INVALID_RESPONSE`，错误消息不披露临时绝对路径或 Fake 文本。

#### 3. 统一清理结果与回归矩阵

- 临时真实 `SQLiteStateRepository` + 临时 DATA 根验证：wrong kind、non-DATA root、wrong retention
  和 already-deleted input 都在物理删除前返回无路径的 `INDEX_CONFLICT`。已登记 DATA 音频、外部
  合成目标和 index `deleted_at` 均保持不变。
- 真实 SQLite 分别验证 unknown、missing、stale、hash mismatch、末端 symlink、合法删除和最终
  post-unlink CAS race。unknown/stale 为 `INDEX_CONFLICT` 且保留音频；missing 为 `MISSING`；
  hash mismatch 为 `HASH_MISMATCH`；symlink 保留链接和根外目标；合法路径为 `DELETED` 并写入
  `deleted_at`；race 在已 unlink 且真实 inner CAS 已写入时返回 `INDEX_CONFLICT`，保留已批准的
  at-most-once 语义。
- Fake repository 补足 SQLite 拒绝持久化的恶意索引快照：绝对路径、`..` 逃逸和中间目录 symlink
  DATA-root escape 都为 `INDEX_CONFLICT`，不调用 delete CAS，且外部合成文件保持存在。
- 该矩阵同时复核顺序仍是：资格/read-register 验证 → 相对路径与 DATA 边界 → 流式 1 MiB SHA-256
  验证 → unlink → 既有 index-only CAS；未引入 reservation、Schema、claim 或 exactly-once 主张。

### AC / ADR-007 边界矩阵

| 项目 | 结果 | 独立证据 |
|---|---|---|
| 阶段 A：离线短音频、资源与 timeout 可观察 | PASS | 合成字节/Fake executor、focused tests 和全量 suite；没有解码或推理。 |
| 阶段 A：音频/模型/revision/参数/语言提示缓存身份 | PASS | 三 hint shared-cache probe、required keyword-only API probe、focused 11/12 tests。 |
| 阶段 A：成功、失败、超长的音频保留/清理 | PASS | Fake + 临时真实 SQLite 矩阵、hash/path/root/CAS 反例及有效删除。 |
| L-01 / L-02 | PASS | 共享契约基线已存在；本 correction 只在已批准 Phase A Adapter/策略范围内，未改共享契约、Schema 或迁移。 |
| L-03 至 L-09 | N/A，未回归 | 评分/Ollama 契约不在 TASK-006 范围，完整与 correction Diff 均未触及。 |
| L-10 | PASS | 已锁定依赖未在 correction 改动；冻结 `language_hint` 已加入唯一缓存身份且无自由 kwargs。 |
| L-11 | PASS | 无模型 import、加载或下载；运行时无隐式联网路径。 |
| L-12 | PASS | 无 yt-dlp 媒体、Cookie、remote components、ffmpeg 或网络访问。 |
| L-13 | PASS | 时长/资源仍是纯策略，executor 前拒绝，未改变 Pipeline 状态。 |
| L-14 | PASS | 只对 DATA 下已登记、hash 匹配的音频执行；所有不安全/不合格预检统一 fail closed。 |
| L-15 | PASS（阶段 A） | 未运行真实模型或 multiprocessing；所有真实资源阶段继续独立门禁。 |

### 五轴审查

- Correctness：Correction 3 关闭了前轮两个 P1。独立 key/API/shared-cache probe 阻止跨语言误命中；
  real/Fake cleanup matrix 证明错 kind/root/retention 与 stale/escape 均在删除前 fail closed。最终
  CAS 窗口按冻结 at-most-once 语义仍被诚实报告。
- Readability：缓存键通过具名 keyword-only 维度和稳定 JSON 显示其身份；清理分支顺序明确，测试名
  覆盖每类安全边界。没有死代码、兼容 shim 或无关重构。
- Architecture：仅在唯一 Provider cache-key call site 衔接既有 `WhisperDecodePolicy`；继续使用
  `get_artifact_by_key` 和 post-delete `mark_artifact_deleted`，没有让 Adapter 拥有 Repository、
  状态、模型或文件系统外部语义。
- Security / privacy：语言参数、Artifact register、根边界和哈希均在边界验证；错误返回为枚举而不
  披露路径或内容。完整 Diff 的 private-key、AWS、GitHub、OpenAI 与 Slack-token 模式扫描无命中。
- Performance / resources：缓存键为常数大小 JSON/SHA-256；清理哈希为 1 MiB 流式读取；没有 N+1、
  无界集合、模型热路径或新增同步网络操作。

### 范围、红线、复用与许可证复核

- Scope：完整 8 路径和 correction-only 5 路径均精确符合授权；`providers/whisper.py` 确认只有
  一行授权调用点变更。没有改变 `state.py`、Schema/migration、task status、main、source history、
  配置、生产依赖或 lockfile（Correction 3）。
- Red lines：未删除/跳过/弱化测试；未触及 `.env`、credentials、真实 Vault、付费服务、真实媒体、
  模型或系统工具；未 merge、push、reset 或 clean。审查仅写入本报告。
- Reuse：Correction 3 为 `DIRECT` 复用已有 `WhisperDecodePolicy`、transcription cache、SQLite
  Artifact API 和 Python 标准库；未复制外部代码或引入新依赖。初始 TASK-006 的
  `mlx-whisper==0.4.3`/MIT、其传递依赖与模型许可证仍按既有登记维持：模型未下载，转换模型
  license 风险继续 deferred 至后续获批资源/许可证工作。

### 刻意跳过的未授权路径

- 未下载、导入、加载或调用任何 Whisper 模型/权重；未调用 `mlx_whisper.transcribe`、ffmpeg、
  multiprocessing 终止、媒体/YouTube、网络、Cookie/登录、remote components、Vault 或凭据。
- 未运行真实转录、真实资源/性能冒烟或任何非 TASK-006 工作树命令。独立探针只使用系统临时目录的
  合成字节、SQLite、DATA 根、symlink 和外部临时目标；没有读取或删除真实文件。

### Findings（P0–P3）与结论

- P0：无。
- P1：无。
- P2：无。
- P3：无。
- 未解决 P0/P1：无。
- `DECISION NEEDED`：None。
- Verdict：**APPROVE**。

---

## 主控关闭记录（2026-07-20）

- Product Integrator execution base：
  `7d18ecffc61fc0def974ce07ee9dc1ceeb4bf305`。
- Accepted source/review evidence：
  `f00209c8018a9e728d9f6509f0ae70067fa33676`。
- Merge commit：`fd9a07462a0596e1c5d4c67c200c3a7f2561fea1`，双父依次为
  `7d18ecffc61fc0def974ce07ee9dc1ceeb4bf305` 与
  `f00209c8018a9e728d9f6509f0ae70067fa33676`。
- 合并前、暂存态与 first-parent Diff 均精确为批准的八个路径；直接依赖仍仅新增
  `mlx-whisper>=0.4.3,<0.5`，锁定 `0.4.3`。
- 整合后 lock check、locked offline sync、focused `11/12`、全量 `305`、mypy（13
  source files）、Ruff、CLI、offline build 与 sdist/wheel migration inclusion 全 PASS。
- main 与 retained source worktree 均干净；source branch/head 原样保留。TASK-006 已由主控
  关闭为 `DONE`。
- 未运行模型下载/加载、真实转写、ffmpeg、网络、媒体、Vault 或凭据操作。保留
  post-unlink/final-CAS 的 at-most-once 风险，不声称 exactly-once。
