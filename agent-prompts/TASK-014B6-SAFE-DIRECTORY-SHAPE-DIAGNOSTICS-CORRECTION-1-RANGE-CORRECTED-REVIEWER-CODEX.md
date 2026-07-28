# TASK-014B6 — 安全字幕目录结构诊断 P1 Correction 1 范围修正独立 Reviewer

你是 TASK-014B6 P1 Correction 1 的全新独立 Codex Reviewer。只审查固定 source 的离线修复与证据；不得修复、重构、重新设计、启动真实资源或修改产品代码。本 prompt 取代上一份少列完整范围路径的 Reviewer prompt；本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B6 — safe subtitle directory shape diagnostics P1 Correction 1
Role: Independent Reviewer
Control-plane base: main@d2bd5c78733f4777307f81692eeb0e52d7bbcf96
Execution main: dynamic clean main at the single-parent range-corrected review authorization commit containing this prompt; it must descend from the control-plane base and contain no unreviewed product changes
Reviewed source worktree: /Users/hua/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics
Reviewed source branch: codex/task-014b6-safe-directory-shape-diagnostics
Reviewed source HEAD: b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78
Required sole parent of Correction 1: 9403e37eedbd2513aea631c7272c6d650d41ef40
Required sole parent of original implementation: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
Correction review range: 9403e37eedbd2513aea631c7272c6d650d41ef40...b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78
Complete B6 review range: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1...b58ba26fcb5dc0985c03fc6f387514fbcd3e2f78
```

- 上一 Reviewer 因完整范围文档少列必要的 `public_subtitle_smoke.py` 而停止，未写 evidence commit；不得伪造或引用任何 Reviewer SHA。
- 开始前只读核验 dynamic main 与 source 的分支、HEAD、双重父链、Correction/完整 Diff 范围和洁净度；任一不符立即停止并报告。
- Correction Diff 必须严格且仅为：

  1. `src/youtube_intel/public_subtitle_smoke.py`
  2. `tests/integration/test_public_subtitle_smoke.py`
  3. `handoffs/TASK-014.md`

- 完整 B6 Diff 必须严格且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `src/youtube_intel/public_subtitle_smoke.py`
  3. `tests/fixtures/subtitles/directory_shape_diagnostics.json`
  4. `tests/integration/test_subtitle_provider.py`
  5. `tests/integration/test_public_subtitle_smoke.py`
  6. `handoffs/TASK-014.md`

`public_subtitle_smoke.py` 仅允许将有限、无值 Adapter 分类传递到既有安全摘要；此范围修正不允许增加任何其他源、测试、依赖、锁、
Schema、CLI 结构、`logging.py` 或解析接受面。Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，仅追加审查 evidence，
且 evidence 必须以 `b58ba26…` 为唯一父提交。

## 必须审查与负向验证

- 精确验证未知目录 `INVALID_RESPONSE` 的安全 stdout/JSONL `directory_diagnostic` 只为
  `directory_shape_unknown`；旧 `directory_unknown_invalid_response` 不得从 stdout、stderr 或 JSONL 输出，也不得以动态内容替代。
- 复审 ADR-017 其余六种固定无值分类及 unknown fallback；stdout/stderr/JSONL 与 fixture 不得泄露 URL、字幕正文、标题、语言、
  轨道名、字段值、路径、原始异常、Cookie、token、payload 或用户数据。
- 验证不扩大目录解析接受面：身份、URL、格式、长度、数量、语言、条目与不支持目录仍 fail-closed；默认一次正文读取、
  directory-only 1/1/0、退出码、CLI 拒绝、临时根、1--3 唯一 ID、无重试和零业务记录边界不退化。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B6 聚焦 pytest、mypy Provider/smoke、Ruff B6 source/tests、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI
  子命令、Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、launchd、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查
  不构成真实服务验证、发行批准或最终 Go。
