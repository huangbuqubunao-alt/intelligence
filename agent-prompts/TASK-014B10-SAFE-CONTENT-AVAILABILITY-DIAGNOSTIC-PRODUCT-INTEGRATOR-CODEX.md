# TASK-014B10 — 安全内容可用性诊断 Product Integrator

你是 TASK-014B10 的全新 Codex Product Integrator。只可在所有固定 Git 与完整离线门禁成功后，将 accepted source 以一次
`--no-ff` 合并到 `main`；不得修复、重构、重新审查、修改 source、改变任务状态或运行真实资源。本包只创建授权，不启动 Integrator。

## 固定执行对象

```text
Task: TASK-014B10 — safe content availability diagnostic
Role: Product Integrator
Control-plane baseline: main@62c9beed8d5b6430733872eb35d13705a87402d1
Execution base: dynamic exact clean main HEAD at the new single-parent acceptance authorization commit containing this prompt; it must have 62c9beed8d5b6430733872eb35d13705a87402d1 as sole parent and contain only this acceptance control-plane Markdown change
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b10-safe-content-availability-diagnostic
Accepted source branch: codex/task-014b10-safe-content-availability-diagnostic
Accepted source / Reviewer 2 evidence HEAD: 880e796622e393842a8cfe1a365af25868a3e98f
Required sole parent of Reviewer 2 evidence: c65502e3680d14a88ae52a1c27eea47d42b5e8b0
First Reviewer evidence: 2ea3455246a596f8304d2b0c00435862f8f3ea9e
Original implementation: 3cdb4c849efcd1a6f0fe77b03bb6a8998d9b1d20
Original implementation base: 6fd7b5cc3fae6466fb6181151513f4854d196683
Only authorized merge: git merge --no-ff 880e796622e393842a8cfe1a365af25868a3e98f
Reuse decision: DIRECT — locked yt-dlp typed exceptions, existing subtitle Adapter and safe smoke boundaries, ADR-020 vocabulary, B4--B8 diagnostics, and offline integration infrastructure; no dependency or third-party change
```

## 启动前 Git-only 门禁

- main/source 必须分别位于上述分支与精确 HEAD 且干净；记录动态 execution base SHA。动态 main 必须是包含本包的单父 acceptance 控制面
  提交，其唯一父为固定 control-plane baseline，且不得包含未审查产品变更。
- 逐提交唯一父链必须严格为
  `6fd7b5c… → 3cdb4c8… → 2ea3455… → c65502e… → 880e796…`。Reviewer 2 evidence 只能修改
  `handoffs/TASK-014.md`，并记录 Verdict=`APPROVE`、P0–P3=`0`；accepted source 在合并前不得已是 main 祖先。
- Correction `2ea3455…...c65502e…` Diff 必须严格且仅为 Adapter、Provider integration test 与 handoff 三路径；完整
  `6fd7b5c…...880e796…` Diff 必须严格且仅为以下五路径，不要求每个 Correction 允许路径都发生变化：

```text
src/youtube_intel/providers/subtitles.py
src/youtube_intel/public_subtitle_smoke.py
tests/integration/test_subtitle_provider.py
tests/integration/test_public_subtitle_smoke.py
handoffs/TASK-014.md
```

- 必须确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、默认 CLI、`logging.py`/日志 schema、认证或解析接受面范围外变更；
  `pyproject.toml` 与 `uv.lock` 相对 original implementation base 的 blob 必须不变。Correction、完整 B10 和 evidence 范围的
  `git diff --check` 必须通过。
- B9 failure evidence `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 必须继续既非 main 也非 accepted source 的祖先，不得合并、修改、
  清理或改写为成功。任一 Git-only 门禁不符立即停止，不运行产品门禁、不合并、不修复、不重试。
- Reviewer 2 已独立通过 locked offline sync、Provider/Smoke focused `137`、mypy、Ruff、CLI help、范围与全输出面泄漏扫描；但未运行
  full pytest 或 build。其补充内联探针两次在自定义替身构造阶段失败，明确不计通过证据，不得在整合报告中写成 PASS。

## 预合并完整离线门禁与唯一合并

所有下列命令只可在已核验干净的 accepted source worktree 中按序运行。缓存缺失、下载/网络迹象、锁文件变化、命令不可用或任一失败，
立即停止并如实报告；不得重试、修复环境或产品、使用替代命令、暂存/提交/清理 source 或执行 merge。

```text
uv lock --check
uv sync --locked --offline
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/pytest
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
uv build --offline
git diff --check 6fd7b5cc3fae6466fb6181151513f4854d196683...880e796622e393842a8cfe1a365af25868a3e98f
```

- 门禁后再次确认 `uv.lock`/依赖图和 source tracked cleanliness 不变，并复核 accepted evidence handoff-only、Correction 三路径、完整 B10
  五路径与 fixture Diff 不存在。focused 与 full pytest 必须分别全部通过并记录实际收集/通过数，不能预设或借用旧数量。
- 独立扫描 stdout、stderr、JSONL `safe_message`、测试新增行、handoff 与 fixture 表面。扫描只可返回安全的 pass/fail 与路径级摘要，
  不得回显 URL、标题、语言、轨道、字段名/值、异常原文、原始响应、路径值、Cookie、token、payload、用户数据或凭据；ADR-019
  既有受限合成键名例外不得扩大。任一命中或无法安全判定都视为失败并停止。
- 所有门禁通过且 main/source 再次干净后，返回 main，确认 HEAD 仍为启动时记录的 dynamic execution base，然后只执行：

```text
git merge --no-ff 880e796622e393842a8cfe1a365af25868a3e98f
```

## 合并后只读核验

- merge 必须恰有两个父提交，第一父为启动时记录的 dynamic execution base，第二父为
  `880e796622e393842a8cfe1a365af25868a3e98f`；accepted source 必须成为 main 祖先。
- first-parent Diff 必须精确为上述完整 B10 五路径；不得以 Correction 允许范围要求不必要路径发生变化。`uv.lock`、依赖、fixture、
  Schema/migration、配置、默认 CLI 和日志 schema 必须不变，merge Diff 的 `git diff --check` 必须通过。
- main/source 必须最终干净。任何后置门禁失败立即停止并如实报告；不得创建修复提交、重试 merge、修改 source、回退或清理。

## 禁止与状态

- 禁止真实 YouTube、任何真实 smoke、网络、登录/认证、Cookie/API key/凭据、媒体/ffmpeg、真实 Vault/用户数据、模型、Ollama、
  OpenAI、其他云端/付费调用、push、source 清理及上述序列外的产品命令。
- 不得修改任务/项目状态、ADR、prompt 或控制面。TASK-014B10 保持 `ACCEPTED`，TASK-014 保持 `IN_PROGRESS / No-Go`；本次授权和
  任何离线整合都不等于 `DONE`、真实 smoke 通过、真实服务验证、事实性根因确认、发行批准或最终 Go。
