# TASK-014B8 — 受限键名级字幕目录诊断 Product Integrator

你是 TASK-014B8 的全新 Codex Product Integrator。只可在所有预合并 Git/离线门禁成功后，将固定 accepted source 以一次
`--no-ff` 合并到 `main`；不得修复、重构、重新审查、修改 source 或改变任务状态。

## 固定执行条件

```text
Task: TASK-014B8 — restricted directory keyname diagnostic
Role: Product Integrator
Control-plane baseline: main@a3a905db8bfef0326a2625eac76e199b8b01f2f3
Execution main: dynamic clean main at the single-parent acceptance authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b8-restricted-directory-keyname-diagnostic
Accepted source branch: codex/task-014b8-restricted-directory-keyname-diagnostic
Accepted source HEAD: 96dee64ec7ab172d036e8472ffc3f65efa0cb6c4
Required sole parent of Reviewer evidence: 2334374f66497546108d12be541ab137b4a8981a
Required sole parent of implementation: 43f2c748c43215facb231f76a0c93ac45d350657
Only authorized merge: git merge --no-ff 96dee64ec7ab172d036e8472ffc3f65efa0cb6c4
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017/ADR-018 diagnostics, ADR-019, and offline integration tests; no dependency or third-party change
```

- 开始前 main/source 必须干净；动态 main 必须是包含本包的单父授权提交、从控制面基线后仅有本次控制面 Markdown 变更且无未审查产品变更。
  source 分支、HEAD、两层父链、Reviewer evidence 仅改 handoff、Verdict=`APPROVE`/P0--P3=`0`、锁文件不变及完整五路径范围必须全部匹配；任一不符立即停止。
- Reviewer 已通过 focused `119`、mypy、Ruff、CLI help、范围和 stdout/stderr/JSONL/test/handoff 泄漏检查，但未运行 build 或全量 pytest；
  未运行项不是通过证据，必须先由本角色成功完成下列离线门禁。

## 预合并离线门禁与唯一合并

所有下列命令仅可在 accepted source worktree、已核验 source 干净时按序运行；不得修改、暂存、提交或清理 source。缓存缺失、任何
下载/网络迹象、锁文件变化或任一检查失败，立即停止并保留证据；**不得合并、修复或重试**。

```text
uv sync --locked --offline
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/pytest
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
uv build --offline
git diff --check
```

- 在合并前完成静态范围与 stdout/stderr/JSONL/test/handoff 泄漏扫描：完整 `43f2c748…...96dee64…` Diff 必须严格且仅为
  `src/youtube_intel/providers/subtitles.py`、`src/youtube_intel/public_subtitle_smoke.py`、
  `tests/integration/test_subtitle_provider.py`、`tests/integration/test_public_subtitle_smoke.py`、`handoffs/TASK-014.md`。
  除 ADR-019 明确授权的合成、规范键名外，扫描不得记录或输出字段名/值、URL、正文、标题、语言、轨道、路径、原始异常、Cookie、token、
  payload、用户数据或凭据；不得放宽解析接受面。所有门禁通过后再次确认 source 干净，才可返回 `main` 执行唯一授权命令：

```text
git merge --no-ff 96dee64ec7ab172d036e8472ffc3f65efa0cb6c4
```

- 合并后只核验 merge 双父顺序、accepted source 为 main 祖先、first-parent Diff 严格为同一完整五路径、锁/依赖未变、范围与泄漏扫描，及
  main/source 洁净度。任一后置门禁失败均停止并保留证据；不得在整合中修复、重试或改变 source。

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、认证、媒体/ffmpeg、Cookie/API key/凭据、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、push、source 清理和任何额外产品命令。
- 不得修改任务/状态/ADR/prompt；TASK-014B8 保持 `ACCEPTED`，TASK-014 保持 `IN_PROGRESS / No-Go`。本次离线整合不等于
  `DONE`、真实 B-1 成功、真实服务验证或发行批准。
