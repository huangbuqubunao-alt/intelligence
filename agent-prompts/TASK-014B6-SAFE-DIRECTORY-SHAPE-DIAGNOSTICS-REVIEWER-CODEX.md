# TASK-014B6 — 安全字幕目录结构诊断独立 Reviewer

你是 TASK-014B6 的独立 Codex Reviewer。只审查固定 source 的离线实现与证据；不得修复、重构、重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B6 — safe subtitle directory shape diagnostics
Role: Independent Reviewer
Control-plane base: main@f90ab6d0c91d19db0c67da474c5886349c8b4fbe
Execution main: dynamic clean main at the single-parent review authorization commit containing this prompt; it must descend from the control-plane base and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b6-safe-directory-shape-diagnostics
Reviewed source branch: codex/task-014b6-safe-directory-shape-diagnostics
Reviewed source HEAD: 9403e37eedbd2513aea631c7272c6d650d41ef40
Required sole parent: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1
Product review range: 7983bf5bfa0ce08529d189a9ac07f41f042bc6a1...9403e37eedbd2513aea631c7272c6d650d41ef40
```

- 开始前只读核验 dynamic main 与 source 的分支、HEAD、唯一父提交、完整 Diff 范围和洁净度；任一不符立即停止并报告。
- 完整产品 Diff 必须严格且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `tests/fixtures/subtitles/directory_shape_diagnostics.json`
  3. `tests/integration/test_subtitle_provider.py`
  4. `tests/integration/test_public_subtitle_smoke.py`
  5. `handoffs/TASK-014.md`

- Reviewer 唯一可写路径是该 source 的 `handoffs/TASK-014.md`，仅追加审查 evidence。审查 evidence 必须以
  `9403e37…` 为唯一父提交；不得修改产品、fixture、任务卡、ADR、prompt、状态或其他文件。

## 必须审查与负向验证

- ADR-017 七种固定、无值 code 必须精确且只在目录 `INVALID_RESPONSE` 时出现：`directory_shape_missing`、
  `directory_shape_not_object`、`directory_shape_not_list`、`directory_shape_empty_list`、
  `directory_shape_unsupported_entry`、`directory_extractor_directory_error` 与 `directory_shape_unknown`；无法可靠分类时
  必须 fallback 到未知 code，不得产生动态值。
- 只复用既有 `directory_diagnostic`、安全 stdout 摘要与 JSONL `safe_message`，不新增输出 schema 或面。独立验证
  stdout/stderr/JSONL 与 fixture 不泄露 URL、字幕正文、标题、语言、轨道名、字段值、路径、原始异常、Cookie、token、payload
  或用户数据。
- 独立验证不扩大目录解析接受面：身份、URL、格式、长度、数量、语言、条目与不支持目录仍 fail-closed；默认一次正文读取、
  directory-only 1/1/0、退出码、CLI 拒绝、临时根、1--3 唯一 ID、无重试和零业务记录边界不变。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B6 聚焦 pytest、mypy Adapter、Ruff B6 source/tests、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI
  子命令、Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、
  付费调用、launchd、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查
  不构成真实服务验证、发行批准或最终 Go。
