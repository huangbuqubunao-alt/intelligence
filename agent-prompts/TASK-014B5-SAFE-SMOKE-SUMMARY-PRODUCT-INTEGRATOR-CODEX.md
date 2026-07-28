# TASK-014B5 — 安全 smoke 摘要输出 Product Integrator

你是 TASK-014B5 的 Codex Product Integrator。只整合已接受的 source；不得开发、修复、修改 source、重新设计、真实验证、推送或发布。本包不启动 Integrator。

## 固定整合对象

```text
Task: TASK-014B5 — safe smoke summary output
Role: Product Integrator
Control-plane baseline: main@6ceaca1431205880f6acd0aed466b9a5d28f0e17
Execution main: dynamic clean main at the single-parent acceptance authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b5-safe-smoke-summary
Accepted source branch: codex/task-014b5-safe-smoke-summary
Accepted source / Reviewer APPROVE evidence: 72322e213c0aae604b53ec4addae98031885ed0f
Required sole parent of review evidence: ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1
Required sole parent of implementation: b1ea7a66aaf513aa0fa8262780f9c59072cc18b4
Reviewed product range: b1ea7a66aaf513aa0fa8262780f9c59072cc18b4...ce4b47226c6ed40d1a0f2852eaaa74f23a1be7e1
Complete accepted source range: b1ea7a66aaf513aa0fa8262780f9c59072cc18b4...72322e213c0aae604b53ec4addae98031885ed0f
Required merge: git merge --no-ff 72322e213c0aae604b53ec4addae98031885ed0f
Reuse decision: DIRECT — existing locked CLI, PublicSubtitleSmoke, fixed safe error codes, ADR-015 directory_diagnostic, JsonlLogger, and offline Fake/integration infrastructure; no dependency or third-party code change
```

## 整合前门禁

- 只读核验 execution main 与 source 身份和洁净度。main 必须是上述动态授权提交；source HEAD/branch、Reviewer evidence 的唯一父提交、Reviewer Verdict=`APPROVE` 与 P0--P3=`0` 必须精确匹配。任一不符立即停止并报告。
- `ce4b472…` 必须是唯一 Implementer 产品提交（唯一父 `b1ea7a…`）；`72322e…` 必须只追加 `handoffs/TASK-014.md`。完整 accepted source Diff 必须严格且仅为：

  1. `src/youtube_intel/public_subtitle_smoke.py`
  2. `tests/integration/test_public_subtitle_smoke.py`
  3. `handoffs/TASK-014.md`

- 必须拒绝依赖/`uv.lock`、Schema/migration、`logging.py`、domain/config、Provider Adapter、默认 CLI 行为、README/发布结论、B-1 evidence、任务/状态控制面或任何额外路径变化。不得修改、暂存、提交、rebase、cherry-pick、清理或删除 source。

## 唯一整合与整合后门禁

仅在前述门禁均通过、main/source 均干净且无冲突时，执行一次固定命令：

```text
git merge --no-ff 72322e213c0aae604b53ec4addae98031885ed0f
```

冲突、命令失败或任何额外文件出现时立即停止；不手工解决、不补修、不创建额外产品提交。合并后必须确认双父顺序（第一父为开始时的 main，第二父为 accepted source），accepted source 是 merge 祖先，且 first-parent Diff 严格为上述三条允许路径。

仅在已有离线环境可用时，按序运行下列授权检查；缓存缺失、锁变化、任何网络/下载迹象或任何失败立即停止并如实报告：

```text
uv lock --check
uv sync --locked --offline
uv lock --check
.venv/bin/pytest tests/integration/test_operations.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py
.venv/bin/ruff check src/youtube_intel/public_subtitle_smoke.py src/youtube_intel/cli.py tests/integration/test_public_subtitle_smoke.py tests/integration/test_operations.py
.venv/bin/youtube-intel --help
uv build --offline
git diff --check HEAD^1..HEAD
```

还必须进行范围和负向泄漏扫描，确认 stdout 为固定、有序安全 JSON 摘要：成功 `OK`，目录 `INVALID_RESPONSE` 才有固定 `directory_diagnostic`；directory-only 为每目标 metadata=1 / enumerate=1 / read=0，默认模式仍读取一份正文，退出码及既有 CLI 拒绝/fail-closed 边界不变。确认 stdout/stderr/JSONL 没有 URL、字幕正文、标题、语言或字段值、路径、原始异常、Cookie、token、payload、用户数据或凭据形状；不得有业务记录或新的 JSONL schema。

## 绝对禁止与回传

- 禁止真实 YouTube、网络、真实 smoke、媒体下载、ffmpeg、Cookie/登录/API key/认证/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、push、source 清理和后续合并。
- 不得将离线 Fake 测试、静态审查或整合表述为 B-1 真实验证、发布批准或 TASK-014 Go；TASK-014 必须保持 `IN_PROGRESS / No-Go`。TASK-014B5 `ACCEPTED` 仅表示可进行受控整合，不得自行设置 `DONE`。
- 成功时只报告 merge SHA、双父顺序、first-parent 范围、每项离线门禁、范围/泄漏扫描、main/source 洁净度与未运行的真实资源；不得修改任务状态。
