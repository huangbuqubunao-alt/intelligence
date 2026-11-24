# TASK-014B11 — 安全字幕目录契约状态诊断 Product Integrator

你是 TASK-014B11 的全新 Codex Product Integrator。只可在全部固定 Git 与完整离线门禁成功后，
将 accepted source 以一次 `--no-ff` 合并到 `main`；不得修复、重构、重新审查、修改 source、
改变任务状态或访问真实资源。本包只创建授权，不启动 Integrator。

## 固定执行对象

```text
Task: TASK-014B11 — safe subtitle directory contract-state diagnostics
Role: Product Integrator
Control-plane baseline: main@95fa9e41d34086434ef10a425bc418a782f43196
Execution base: dynamic exact clean main HEAD at the new single-parent acceptance authorization commit containing this prompt; it must have 95fa9e41d34086434ef10a425bc418a782f43196 as sole parent and contain only the synchronized acceptance control-plane Markdown change
Accepted source worktree: /Users/developer/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Accepted source branch: codex/task-014b11-safe-directory-contract-diagnostics
Accepted source / Reviewer 2 evidence HEAD: f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Required sole parent of Reviewer 2 evidence: ed250baf752182adbc4d98f5271d34995865d192
Coverage-only Correction 1: ed250baf752182adbc4d98f5271d34995865d192
First Reviewer evidence: 4aebc01360fa9684fe6b052f266a00ecc2de57dc
Original implementation: f22e0dbfa8222280d4b97c3cd7f1e7cf37e7cf50
Original implementation base: 80aff83fc033a8bd2950108cad2e34feea5d396f
Only authorized merge: git merge --no-ff f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Reuse decision: DIRECT — existing locked yt-dlp Adapter, B4 directory-only, B5 safe stdout/JSONL schema, ADR-017--ADR-021 fixed diagnostics, and offline integration infrastructure; no dependency or third-party change
```

## 启动前 Git-only 门禁

- main/source 必须分别位于上述分支与精确 HEAD 且干净；记录动态 execution base SHA。动态 main
  必须是包含本包的单父 acceptance 控制面提交，唯一父为固定 control-plane baseline，且不得
  包含未审查产品变更。
- 逐提交唯一父链必须严格为
  `80aff83… → f22e0db… → 4aebc01… → ed250ba… → f57b21c…`。Reviewer 2 evidence
  必须只向 `handoffs/TASK-014.md` 追加证据，并记录 Verdict=`APPROVE`、P0--P3=`0`；accepted
  source 在合并前不得已是 main 祖先。
- Correction `4aebc01…...ed250ba…` Diff 必须精确且仅为两份 integration tests 与 handoff
  三路径；它是 coverage-only 补证，三个生产链节点在产品源码未改时首次通过，没有有效产品 RED，
  不得登记为产品 bug 修复。两个产品 source blob 相对首轮 implementation 必须不变。
- 完整 `80aff83…...f57b21c…` Diff 必须精确且仅为以下五路径：

```text
src/youtube_intel/providers/subtitles.py
src/youtube_intel/public_subtitle_smoke.py
tests/integration/test_subtitle_provider.py
tests/integration/test_public_subtitle_smoke.py
handoffs/TASK-014.md
```

- 必须确认无 fixture、依赖、`uv.lock`、Schema/migration、配置、认证、默认 CLI、`logging.py`/
  日志 schema 或解析接受面范围外变更；`pyproject.toml` 与 `uv.lock` 相对 original implementation
  base 的 blob 必须不变。Correction、完整 B11 和 Reviewer evidence 范围的 `git diff --check`
  必须通过。
- 只读真实 evidence `51d9749943270cb75c2b166e77bce0a5f663d92c` 与 B9 failure evidence
  `bd770ef9d212ebe75689b8f33145bf2556fe93c2` 必须继续既非 main 也非 accepted source 的祖先，
  不得合并、修改、清理或改写为成功。
- Reviewer 2 已独立通过 locked offline sync、三个生产链节点 `3 passed`、Provider/Smoke focused
  `149 passed`、mypy、Ruff、CLI help、范围/Diff 与全输出面泄漏扫描；未运行 full pytest 或 build。
  任一 Git-only 门禁不符立即停止，不运行产品门禁、不合并、不修复、不重试。

## 预合并完整离线门禁与唯一合并

所有下列命令只可在已核验干净的 accepted source worktree 中按序运行。缓存缺失、下载/网络迹象、
锁文件变化、命令不可用或任一失败，立即停止并如实报告；不得重试、修复环境或产品、换命令、
暂存/提交/清理 source 或执行 merge。

```text
uv lock --check
uv sync --locked --offline
.venv/bin/pytest tests/integration/test_subtitle_provider.py::test_ytdlp_adapter_maps_contract_mismatch_to_frozen_no_value_state tests/integration/test_public_subtitle_smoke.py::test_directory_only_emits_frozen_directory_contract_state_matrix tests/integration/test_public_subtitle_smoke.py::test_production_contract_state_is_omitted_without_directory_only_gate
.venv/bin/pytest tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/pytest
.venv/bin/mypy src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py
.venv/bin/ruff check src/youtube_intel/providers/subtitles.py src/youtube_intel/public_subtitle_smoke.py tests/integration/test_subtitle_provider.py tests/integration/test_public_subtitle_smoke.py
.venv/bin/youtube-intel --help
uv build --offline
git diff --check 4aebc01360fa9684fe6b052f266a00ecc2de57dc...ed250baf752182adbc4d98f5271d34995865d192
git diff --check 80aff83fc033a8bd2950108cad2e34feea5d396f...f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
git diff --check ed250baf752182adbc4d98f5271d34995865d192...f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
```

- 三个生产链节点、focused 与 full pytest 必须分别全部通过并记录实际收集/通过数，不得预设或
  借用 Implementer/Reviewer 数量。门禁后再次确认 `uv.lock`/依赖图和 source tracked/untracked
  洁净度不变，并复核 Reviewer handoff-only、Correction 三路径、完整 B11 五路径、产品 blob
  未变和 fixture Diff 不存在。
- 独立扫描 stdout、stderr、JSONL `safe_message`、测试新增行、handoff 与 fixture 表面。扫描只可
  返回安全的 pass/fail 与路径级摘要，不得回显任意外部 key、视频 ID 值、URL、标题、语言、轨道、
  字段值、异常原文、原始响应、路径值、Cookie、token、payload、用户数据或凭据；ADR-019 既有
  受限合成键名例外不得扩大。任一命中或无法安全判定都视为失败并停止。
- 所有门禁通过且 main/source 再次干净后，返回 main，确认 HEAD 仍为启动时记录的 dynamic
  execution base，然后只执行：

```text
git merge --no-ff f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
```

## 合并后只读核验

- merge 必须恰有两个父提交，第一父为启动时记录的 dynamic execution base，第二父为
  `f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d`；accepted source 必须成为 main 祖先。
- first-parent Diff 必须精确为上述完整 B11 五路径。`uv.lock`、依赖、fixture、Schema/migration、
  配置、认证、默认 CLI、`logging.py`/日志 schema 必须不变，merge Diff 的 `git diff --check`
  必须通过。
- main/source 必须最终干净。任何后置门禁失败立即停止并如实报告；不得创建修复提交、重试 merge、
  修改 source、回退或清理。

## 禁止与状态

- 禁止真实 YouTube、任何真实 smoke、网络、登录/认证、Cookie/API key/凭据、媒体/ffmpeg、真实
  Vault/用户数据、模型、Ollama、OpenAI、其他云端/付费调用、push、source 清理及上述序列外的
  产品命令。
- 不得修改任务/项目状态、ADR、prompt 或控制面。TASK-014B11 合并后仍保持 `ACCEPTED`，TASK-014
  保持 `IN_PROGRESS / No-Go`；本授权和任何离线整合都不等于 `DONE`、产品 bug 修复、真实 smoke
  通过、普遍 yt-dlp 兼容性证明、正文可读、发行批准或最终 Go。
