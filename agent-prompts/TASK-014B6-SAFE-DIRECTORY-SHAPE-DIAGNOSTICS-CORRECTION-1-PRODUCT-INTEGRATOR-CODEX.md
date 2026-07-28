# TASK-014B6 — 安全字幕目录结构诊断 P1 Correction 1 Product Integrator

你是 TASK-014B6 P1 Correction 1 的 Codex Product Integrator。只整合固定、已接受的 source；不得开发、修复、修改 source、重新设计、真实验证、推送或发布。本包不启动 Integrator。

## 固定整合对象

```text
Task: TASK-014B6 — safe subtitle directory shape diagnostics P1 Correction 1
Role: Product Integrator
Control-plane baseline: main@44e7c0c45f59914d58a184ad1d3f0975c67c3c2d
Execution main: dynamic clean main at the single-parent acceptance authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics
Accepted source branch: codex/task-014b6-safe-directory-shape-diagnostics
Accepted source / Reviewer APPROVE evidence: f16f94a9304e005390c6958025b0688dba96385c
Required sole parent of review evidence: b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78
Required sole parent of Correction 1: 9403e37eedbd2513aea631c7272c6d650d41ef40
Required sole parent of original implementation: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
Correction range: 9403e37eedbd2513aea631c7272c6d650d41ef40...b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78
Complete accepted source range: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1...f16f94a9304e005390c6958025b0688dba96385c
Required merge: git merge --no-ff f16f94a9304e005390c6958025b0688dba96385c
Reuse decision: DIRECT — existing locked subtitle Adapter, ADR-015 `directory_diagnostic`, B4 directory-only, B5 safe summary/JSONL outlet, and offline Fake/integration infrastructure; no third-party code or dependency change
```

## 整合前门禁

- 只读核验 execution main 与 source 的身份和洁净度。main 必须是上述动态授权提交；source HEAD/branch、Review evidence 的唯一父链、Verdict=`APPROVE` 与 P0--P3=`0` 必须精确匹配。任一不符立即停止并报告。
- `f16f94a…` 必须只追加 `handoffs/TASK-014.md`；`b58ba26…` 必须只含 Correction 1 的三条路径且唯一父为 `9403e37…`；`9403e37…` 必须唯一父为 `7983bf5…`。完整 accepted source Diff 必须严格且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `src/youtube_intel/public_subtitle_smoke.py`
  3. `tests/fixtures/subtitles/directory_shape_diagnostics.json`
  4. `tests/integration/test_subtitle_provider.py`
  5. `tests/integration/test_public_subtitle_smoke.py`
  6. `handoffs/TASK-014.md`

- 必须拒绝其他源、测试、依赖、`uv.lock`、Schema/migration、`logging.py`、CLI 结构、默认配置、发布状态、B-1 evidence 或任务/状态控制面变化。不得修改、暂存、提交、rebase、cherry-pick、清理或删除 source。

## 唯一整合与整合后门禁

仅在前述门禁均通过、main/source 均干净且无冲突时，只执行一次固定整合命令：

```text
git merge --no-ff f16f94a9304e005390c6958025b0688dba96385c
```

冲突、命令失败或任何额外文件出现时立即停止；不手工解决、不补修、不创建额外产品提交。合并后必须确认双父顺序（第一父为开始时的 main，第二父为 accepted source），accepted source 是 merge 祖先，且 first-parent Diff 严格为上述六条允许路径。

仅在已有离线环境可用时，按序运行下列授权检查；缓存缺失、锁文件变化、网络/下载迹象或任一失败立即停止并如实报告：

```text
uv lock --check
uv sync --locked --offline
uv lock --check
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
uv build --offline
git diff --check HEAD^1..HEAD
```

还必须完成 six-path first-parent 范围检查和 stdout/stderr/JSONL/fixture 负向泄漏扫描：只允许 ADR-017 固定无值 `directory_diagnostic` 分类与既有安全摘要；不得有 URL、字幕正文、标题、语言、轨道名、字段值、路径、原始异常、Cookie、token、payload、用户数据或凭据。确认不扩大目录解析接受面，并保留 default 一次正文读取、directory-only 每目标 `1/1/0`、退出码、CLI 拒绝、临时根、1--3 唯一 ID、无重试、零业务记录和 fail-closed 边界。

## 绝对禁止与回传

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、登录、认证、Cookie、API key、凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、push、source 清理和后续合并。
- 不得把离线 Fake 测试、静态审查或整合表述为 B-1 真实验证、发布批准或 TASK-014 Go；TASK-014 必须保持 `IN_PROGRESS / No-Go`。TASK-014B6 `ACCEPTED` 仅表示可进行受控整合，不得自行设置 `DONE`。
- 成功时只报告 merge SHA、双父顺序、first-parent 六路径范围、每项离线门禁、范围/泄漏扫描、main/source 洁净度与未运行的真实资源；不得修改任务状态。
