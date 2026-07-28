# TASK-014B6：安全字幕目录结构诊断

- Status: `DONE`
- Assignee: `Closure Status Integrator（已收口）`
- Reviewer: `范围修正独立 Codex Reviewer — APPROVE（P0--P3=0）`
- 依赖：TASK-014B3 `DONE`、TASK-014B4 `DONE`、TASK-014B5 `DONE`、ADR-017 `Accepted`
- 实施基线：`main@7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics`
- Branch：`codex/task-014b6-safe-directory-shape-diagnostics`
- accepted source / Reviewer evidence：`f16f94a9304e005390c6958025b0688dba96385c`（唯一父
  `b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78`；后者唯一父 `9403e37…`，再后者唯一父 `7983bf5…`）
- Reuse decision：`DIRECT` — 既有锁定的 subtitle Adapter、ADR-015 `directory_diagnostic`、B4 directory-only、B5 安全摘要、JsonlLogger 与离线 fixture/integration 基础设施；不新增第三方代码或依赖。

## 背景与目标

未合并的 B-1 auditable evidence `c7a3f403c910ab8e50e74f08b1c5ead057a5e4fa` 仅作为只读失败 evidence；不得合并、重写、重跑或写成通过。
实现 ADR-017 的有限、固定、无值目录结构 code，使目录 `INVALID_RESPONSE` 可经既有安全摘要/JSONL 审计，而不保存响应内容或放宽解析。

## 冻结契约

- 仅为目录 `INVALID_RESPONSE` 产生 ADR-017 的固定 code：缺失、非对象、非列表、空列表、不支持条目形状、提取器目录错误或未知。
- 禁止字段值、URL、字幕正文、标题、语言、轨道名称、路径、原始异常、Cookie、token、payload、用户数据或凭据形状。
- 默认和 directory-only 的读取/退出码/临时根/ID 上限/无重试/零业务记录/fail-closed 边界保持不变；不得因此扩大目录解析接受面。
- 兼容修复必须等待独立审查和新的真实授权。TASK-014 始终为 `IN_PROGRESS / No-Go`；B6 离线完成不构成 B-1 成功、真实服务验证或发布批准。

## 最大允许实现范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/fixtures/subtitles/` 下一个新增的脱敏结构 fixture
4. `tests/integration/test_subtitle_provider.py`
5. `tests/integration/test_public_subtitle_smoke.py`
6. `handoffs/TASK-014.md`

不得修改依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任何其他路径。

## P1 Correction 1 控制面

- 原 Implementer source `9403e37eedbd2513aea631c7272c6d650d41ef40`（唯一父 `7983bf5…`）保持干净。原 Reviewer 发现 P1 后停止，
  没有 Reviewer evidence commit；不得伪造或引用不存在的 Reviewer SHA。
- P1：未知目录 `INVALID_RESPONSE` 的 fallback 输出为旧 B3 code `directory_unknown_invalid_response`，但 ADR-017
  的精确固定词表要求 `directory_shape_unknown`。
- Correction 1 的唯一允许路径：

  1. `src/youtube_intel/public_subtitle_smoke.py`
  2. `tests/integration/test_public_subtitle_smoke.py`
  3. `handoffs/TASK-014.md`

- Correction 1 `b58ba26…` 的唯一父为 `9403e37…`，且严格为上述三条路径；完整 B6 Diff `7983bf5…...b58ba26…` 严格为上述六路径。
  `public_subtitle_smoke.py` 仅将有限、无值 Adapter 分类传递到既有安全摘要；不得据此增加输出面、其他路径或放宽解析。
  上一 Reviewer 因完整范围少列此路径而停止，未写 evidence commit；其 prompt 已被全新范围修正 Reviewer prompt 取代。
  范围修正独立 Reviewer 仅追加了 source `handoffs/TASK-014.md` 的 evidence `f16f94a…`，其唯一父为 `b58ba26…`；
  Verdict=`APPROVE`，P0--P3 均为 `0`。
- 复审必须精确验证未知目录 `INVALID_RESPONSE` 仅输出 `directory_shape_unknown`，旧
  `directory_unknown_invalid_response` 不再从 stdout/JSONL 输出；其余 ADR-017 固定分类、unknown fallback、无泄漏、
  解析接受面与 default/directory-only/CLI/fail-closed 边界不得退化。

## Correction 1 验收与受控整合

- TASK-014B6 现为 `ACCEPTED`，只表示上述固定离线 source 可由 Product Integrator 受控整合；不是 `DONE`，也不代表
  B-1 真实验证、真实服务通过、发行批准或 TASK-014 Go。
- Integrator 只能在动态、干净、单父 acceptance authorization main 上，对固定 accepted source 执行一次
  `git merge --no-ff f16f94a9304e005390c6958025b0688dba96385c`。不得修改、暂存、提交、rebase、cherry-pick、清理或删除 source。
- 整合后必须运行离线 Provider/Smoke 测试、mypy、Ruff、CLI help、离线 build、六路径 first-parent 范围和
  stdout/stderr/JSONL/fixture 泄漏扫描；任何失败、网络/下载迹象、锁变化、冲突或范围外路径均立即停止，如实保留证据，
  不在整合中修复代码。

## Closure

- Product Integrator 已以 merge commit `f402400aea0e943ce5e46bf1bba59fcef1e1d376` 整合；父提交顺序为
  `dac394bd7f6a43d484ad713814db7f614a755e36`、`f16f94a9304e005390c6958025b0688dba96385c`。accepted source 是 merge 祖先，
  source worktree 保持干净并保留；first-parent Diff 严格为本任务六条批准路径。
- 既有离线整合证据均通过：lock/sync、Provider/Smoke `104 passed`、mypy、Ruff、CLI help、离线 build、范围检查及
  stdout/stderr/JSONL/fixture 泄漏扫描。TASK-014B6 现为 `DONE`；这不代表 B-1 真实成功、真实服务验证通过、发行批准或 TASK-014 Go。

## 验收与离线检查

- Correction 1 回归未知目录 `INVALID_RESPONSE` 的 stdout/JSONL 只输出 `directory_shape_unknown`，不含旧 B3 fallback 或任何
  动态值；默认一次正文读取、directory-only 1/1/0、退出码、临时根、ID 上限、无重试、零业务记录、CLI 拒绝和 fail-closed 边界不变。
- Correction 1 Implementer 仅可先运行一次 `uv sync --locked --offline`；缓存缺失、下载/网络迹象、锁文件变化或失败立即停止。
- 仅在已有离线 `.venv` 可用时，允许按任务实际范围运行：

```text
.venv/bin/pytest tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
git diff --check
```

## 红线与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、合并、source 清理和任何额外产品命令。
- 完成时只提交 Correction 1 三条允许路径的一个 Implementer commit，追加 `handoffs/TASK-014.md` 并报告 SHA；不得自行 `ACCEPTED`、`DONE`、
  合并、push 或启动真实验证。
