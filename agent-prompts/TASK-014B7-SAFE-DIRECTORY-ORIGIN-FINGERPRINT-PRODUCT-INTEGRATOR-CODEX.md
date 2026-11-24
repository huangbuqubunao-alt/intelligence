# TASK-014B7 — 字幕目录安全来源与结构指纹 Product Integrator

你是 TASK-014B7 P1 Correction 2 的 Codex Product Integrator。只可在所有预合并 Git/离线门禁通过后，将固定 accepted source 以一次
`--no-ff` 合并到 `main`；不得修复代码、修改 source 或改变任务状态。

## 固定执行条件

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint
Role: Product Integrator
Control-plane baseline: main@a14bf1b2405bb90eea175c8da2ec4763eec64a69
Execution main: dynamic clean main at the single-parent acceptance authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Accepted source worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Accepted source branch: codex/task-014b7-safe-directory-origin-fingerprint
Accepted source HEAD: 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
Required sole parent of Reviewer evidence: 4d4366f6a6403403a0d9bed65fbbf862a362eede
Required sole parent of Correction 2: 069e62ececada5152871fb7c626e64c146a270ad
Required architecture base: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Only authorized merge: git merge --no-ff 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017, ADR-018, and offline integration tests; no dependency or third-party change
```

- 开始前 main/source 必须干净；source 分支、HEAD、三重父链、Reviewer evidence 仅改 handoff、Verdict=`APPROVE`/P0--P3=`0`、
  Correction 2 精确三路径、完整 B7 五路径子集及 fixture 删除/无重现均必须匹配。任一不符立即停止。
- Reviewer 因 source 中没有 `.venv` 未运行 pytest、mypy、Ruff 或 CLI help；这不是通过证据。必须先获得本包规定的全套离线通过证据。

## 预合并离线门禁与唯一合并

所有以下命令仅可在 accepted source worktree、已核验 source 干净时按序运行；不得修改、暂存、提交或清理 source。缓存缺失、任何
下载/网络迹象、锁文件变化或任一命令失败，立即停止并保留证据；**不得合并**。

```text
uv sync --locked --offline
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
.venv/bin/python -m build --no-isolation
git diff --check
```

- 同时执行静态范围与 stdout/stderr/JSONL/fixture 泄漏扫描：确认完整 B7 Diff 严格为
  `handoffs/TASK-014.md`、`src/youtube_intel/providers/subtitles.py`、`src/youtube_intel/public_subtitle_smoke.py`、
  `tests/integration/test_subtitle_provider.py`、`tests/integration/test_public_subtitle_smoke.py`；fixture 在 source 中不存在且未在其他路径
  重现。泄漏扫描不得记录或输出字段名、字段值、URL、正文、标题、语言、轨道名、身份值、路径、原始异常、Cookie、token、payload 或用户数据。
- 仅在上述全部通过且 source 仍干净后，返回 `main` 执行唯一授权命令：

```text
git merge --no-ff 6a7f4ce444b3f93aa1388f45e7a5619eb802a317
```

- 合并后仅核验 merge 双亲顺序、accepted source 祖先、first-parent Diff 严格为完整 B7 五路径子集、范围和泄漏扫描、锁/依赖未变与
  main/source 洁净度。若任一后置门禁失败，停止并保留证据；不得在整合中修复代码。

## 绝对禁止与交付

- 禁止真实 YouTube、网络、真实 smoke、媒体/ffmpeg、认证、Cookie、API key、凭据、真实 Vault、用户数据、模型、Ollama、
  OpenAI、付费调用、push、source 清理和任何额外产品命令。
- 不得修改任务/状态/ADR/prompt；TASK-014B7 保持 `ACCEPTED`，TASK-014 保持 `IN_PROGRESS / No-Go`。一次离线整合不等于
  `DONE`、真实 B-1 成功、真实服务验证或发行批准。
