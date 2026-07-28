# TASK-014B7：字幕目录安全来源与结构指纹

- Status: `ACCEPTED`
- Assignee: `Codex Product Integrator（已授权，尚未启动）`
- Reviewer: `Correction 2 独立 Codex Reviewer（APPROVE，P0--P3=0）`
- 依赖：TASK-014B3 `DONE`、TASK-014B4 `DONE`、TASK-014B5 `DONE`、TASK-014B6 `DONE`、ADR-018 `Accepted`
- 实施基线：`main@5b7dcca2ba9bd9e52e254a8944e584542838e24b`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint`
- Branch：`codex/task-014b7-safe-directory-origin-fingerprint`
- accepted source：`6a7f4ce444b3f93aa1388f45e7a5619eb802a317`（Reviewer evidence，唯一父
  `4d4366f6a6403403a0d9bed65fbbf862a362eede`；后者唯一父 `069e62e…`）
- Reuse decision：`DIRECT` — 既有锁定 subtitle Adapter、ADR-015 `directory_diagnostic`、B4 directory-only、B5 安全摘要、
  ADR-017 B6 结构诊断、JsonlLogger 与离线 fixture/integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

未合并的 B-1 B6 evidence `17bfe9062677f3b3117df4dd192848d27690541c` 仅作只读失败 evidence；不得合并、重写、重跑或写成通过。
实现 ADR-018 的有限、无值来源与结构指纹，使目录 `INVALID_RESPONSE` 的既有安全摘要可在不保存响应内容且不放宽解析的前提下增加
可审计边界信息。

## 冻结契约

- 保留 ADR-017 `directory_diagnostic` 的原语义和七个固定值。
- 仅在目录阶段最终为 `INVALID_RESPONSE` 时，安全摘要/既有 JSONL `safe_message` 可附加 ADR-018 词表中的可选
  `directory_origin` 与 `directory_fingerprint`；不得在成功、非目录阶段、非 `INVALID_RESPONSE` 或正文读取中输出。
- 只允许 ADR-018 的固定无值标签；禁止字段名、字段值、URL、字幕正文、标题、语言、轨道名、路径、原始异常、Cookie、token、payload、
  用户数据或凭据形状。
- 默认与 directory-only 的读取计数、退出码、CLI 边界、临时根、ID 上限、无重试、零业务记录和 fail-closed 行为保持不变；不得扩大
  目录解析接受面、增加兼容规则或真实资源权限。
- TASK-014 始终为 `IN_PROGRESS / No-Go`；B7 离线实现不构成真实 B-1 成功、真实服务验证或发行批准。真实验证必须等待独立审查后另行授权。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/fixtures/subtitles/` 下一个新增的脱敏指纹 fixture
4. `tests/integration/test_subtitle_provider.py`
5. `tests/integration/test_public_subtitle_smoke.py`
6. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任何其他路径。

## 独立 Reviewer 控制面

- 完整产品 Diff `5b7dcca2ba9bd9e52e254a8944e584542838e24b...8d06197557de4ce92c2752f4a8ef74582a0efdca` 必须严格且仅为上述六路径；
  脱敏 fixture 固定为 `tests/fixtures/subtitles/directory_origin_fingerprint.json`。
- Reviewer 只能追加 source `handoffs/TASK-014.md` 的审查 evidence，且 evidence 必须以 `8d061975…` 为唯一父提交；不得修改业务代码、
  测试、ADR、任务/状态控制面或任何其他 source 路径。
- 审查 ADR-018 的四个 `directory_origin`、六个 `directory_fingerprint` 固定无值标签、B6 `directory_diagnostic` 不变、仅目录
  `INVALID_RESPONSE` 且 enumerate=`1`/read=`0` 时的出口，以及正文 `INVALID_RESPONSE` 不输出 origin/fingerprint。独立验证
  stdout/stderr/JSONL/fixture 无泄漏、解析接受面与 default/directory-only/CLI/fail-closed 边界不退化。

## P1 Correction 1 控制面

- 原 Reviewer 发现 P1 后停止，未创建 Reviewer evidence commit；不得伪造或引用不存在的 Reviewer SHA。
- P1：`tests/fixtures/subtitles/directory_origin_fingerprint.json` 明文含目录响应字段名、字段值、语言值及 URL，违反 ADR-018 的
  无值/无泄漏边界。用户已明确批准删除该唯一不合规 fixture。
- Correction 1 的唯一允许范围：

  1. 删除 `tests/fixtures/subtitles/directory_origin_fingerprint.json`
  2. `tests/integration/test_subtitle_provider.py`
  3. `tests/integration/test_public_subtitle_smoke.py`
  4. `handoffs/TASK-014.md`

- Correction 必须以无字段名、字段值或 URL 的内存测试替身替代 fixture，并保持或增强 ADR-018 四个 origin、六个 fingerprint、
  B6 code 不变、输出限制及 stdout/stderr/JSONL 无泄漏断言。不得修改任何生产代码、依赖、锁文件、Schema、CLI、`logging.py`、
  解析接受面或真实资源权限。
- Correction Implementer source commit 必须以 `8d061975…` 为唯一父提交；完成后必须由全新独立 Reviewer 审查。

## Correction 1 独立 Reviewer 控制面

- Correction 1 source `069e62e…` 的唯一父为 `8d061975…`，且 Diff 严格为 fixture 删除、两份 integration test 与 handoff。
  完整 B7 Diff `5b7dcca…...069e62e…` 是原六路径允许范围的五路径子集；不合规 fixture 必须在 source HEAD 中不存在，且不得在其他路径重现。
- 新 Reviewer 只能追加 source `handoffs/TASK-014.md` 的审查 evidence，且 evidence 必须以 `069e62e…` 为唯一父提交。
- 复审无值内存 Mapping 替身覆盖 ADR-018 四个 origin、六个 fingerprint、B6 diagnostic、目录/正文出口和 stdout/stderr/JSONL
  泄漏断言；确认没有字段名、字段值、URL、语言、轨道名、原始响应、Cookie、token、payload 或用户数据进入 fixture、测试或输出，
  且生产代码、依赖、CLI、`logging.py`、解析接受面和所有 fail-closed 边界未被改动。

## P1 Correction 2 控制面

- 两位 Reviewer 都在发现 P1 后停止，均未创建 evidence commit；不得伪造或引用任何 Reviewer SHA。
- P1：fixture 已删除，但测试源码仍内嵌受限字段值、URL 和身份值，违反 ADR-018 的无值/无泄漏边界。
- Correction 2 的唯一允许范围：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `tests/integration/test_subtitle_provider.py`
  3. `tests/integration/test_public_subtitle_smoke.py`
  4. `handoffs/TASK-014.md`

- 仅允许最小内部拆分：原始目录结构检查继续封装在 Adapter 内；供测试使用的“结构状态 → 固定安全分类”内部接口只接受无值
  枚举/类型状态。测试不得含字段名、字段值、URL、语言、轨道名、身份值、原始响应、Cookie、token、payload 或用户数据。
- 不得改变解析接受面、CLI、`logging.py`、依赖、锁文件、Schema、读取计数、退出码、默认/directory-only 行为、临时根、ID 上限、
  无重试、零业务记录、fail-closed 边界或真实资源权限。已删除 fixture 不得恢复、替代或在任何路径重现。
- Correction 2 Implementer commit 必须以 `069e62e…` 为唯一父提交；完成后必须由全新独立 Reviewer 审查。

## Correction 2 Reviewer 范围对齐与独立审查

- 上次 Reviewer 授权未创建提交；两位更早的 Reviewer 也均在发现 P1 后停止，未创建 evidence commit。不得伪造或引用任何
  Reviewer evidence SHA。
- Correction 2 source `4d4366f…` 的唯一父为 `069e62e…`。精确实际 Diff 严格且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `tests/integration/test_subtitle_provider.py`
  3. `handoffs/TASK-014.md`

- `tests/integration/test_public_subtitle_smoke.py` 是初始授权上限内但无需改动的文件；未修改是最小范围的正确结果，不得为了迎合文档
  制造无关改动。完整 B7 Diff `5b7dcca…...4d4366f…` 仍必须是原六路径允许范围的五路径子集，已删除 fixture 不得恢复或在任何路径重现。
- 新 Reviewer 只能追加 source `handoffs/TASK-014.md` 的审查 evidence，且该 evidence 必须以 `4d4366f…` 为唯一父提交。必须审查
  私有无值状态接口、固定 origin/fingerprint、B6 diagnostic、无敏感材料、以及解析/CLI/计数/退出码/default/directory-only、无重试、
  零业务记录和 fail-closed 边界未退化。

## Correction 2 验收与 Product Integrator 控制面

- Reviewer evidence/accepted source `6a7f4ce…` 的唯一父为 `4d4366f…`，且只修改 `handoffs/TASK-014.md`；Verdict=`APPROVE`，
  P0--P3 均为 `0`。source 已核验干净。完整 B7 Diff `5b7dcca…...6a7f4ce…` 是原六路径允许范围的五路径子集，已删除 fixture 不得重现。
- Reviewer 因 source 中不存在 `.venv`，未运行 pytest、mypy、Ruff 或 CLI help；这不是已通过证据，必须由 Product Integrator 在合并前
  成功完成授权的离线环境同步和完整验证后才能合并。
- Product Integrator 只可对固定 accepted source 执行 `git merge --no-ff 6a7f4ce…`。缓存缺失、`uv sync --locked --offline`、Provider/Smoke
  pytest、mypy、Ruff、CLI help、build、范围或泄漏扫描任一失败均立即停止、不合并；禁止修复代码、改变任务状态、push 或清理 source。
- TASK-014B7 的 `ACCEPTED` 不等于 `DONE`、真实 B-1 成功、真实服务验证或发行批准；TASK-014 始终为 `IN_PROGRESS / No-Go`。

## 验收与离线检查

- 离线 Fake 覆盖 ADR-018 的完整 `directory_origin` 与 `directory_fingerprint` 固定词表、unknown/省略边界、B6 code 不变、
  stdout/JSONL 安全出口及无泄漏。
- 回归默认一次正文读取、directory-only `1/1/0`、退出码、临时根、ID 上限、无重试、零业务记录、CLI 拒绝与 fail-closed 解析边界。
- Implementer 仅可先运行一次：

```text
uv sync --locked --offline
```

缓存缺失、锁文件变化、任何下载/网络迹象或失败立即停止。仅在已有离线 `.venv` 可用时，才可按序运行：

```text
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、合并、source 清理、测试/检查外的产品命令和 `.codebase-memory` 工件。
- 完成时只创建一个包含允许路径的 Implementer commit，追加 handoff，报告 SHA 与实际检查；不得修改任务/状态/ADR/prompt，不得自行
  `ACCEPTED`、`DONE`、合并、push 或启动 Reviewer。
