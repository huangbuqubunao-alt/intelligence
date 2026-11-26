# TASK-014B7 — 字幕目录安全来源与结构指纹 P1 Correction 2 独立 Reviewer

你是 TASK-014B7 P1 Correction 2 的全新独立 Codex Reviewer。只审查固定 source 的离线 Correction 与审查 evidence；不得修复、
重构、重新设计、启动真实资源或修改产品代码。本包不启动 Reviewer。

## 固定审查对象

```text
Task: TASK-014B7 — safe subtitle directory origin and fingerprint P1 Correction 2
Role: Independent Reviewer
Control-plane baseline: main@e195cd72430d6062a7514152b2f5a69289b5a308
Execution main: dynamic clean main at the single-parent Reviewer authorization commit containing this prompt; it must descend from the control-plane baseline and contain no unreviewed product changes
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b7-safe-directory-origin-fingerprint
Reviewed source branch: codex/task-014b7-safe-directory-origin-fingerprint
Reviewed source HEAD: 4d4366f6a6403403a0d9bed65fbbf862a362eede
Required sole parent of Correction 2: 069e62ececada5152871fb7c626e64c146a270ad
Required sole parent of Correction 1: 8d06197557de4ce92c2752f4a8ef74582a0efdca
Required sole parent of original implementation: 5b7dcca2ba9bd9e52e254a8944e584542838e24b
Correction 2 review range: 069e62ececada5152871fb7c626e64c146a270ad...4d4366f6a6403403a0d9bed65fbbf862a362eede
Complete B7 review range: 5b7dcca2ba9bd9e52e254a8944e584542838e24b...4d4366f6a6403403a0d9bed65fbbf862a362eede
Reuse decision: DIRECT — existing locked subtitle Adapter, B4 directory-only, B5 safe summary, ADR-017, ADR-018, and offline integration tests; no dependency or third-party change
```

- 开始前只读核验 dynamic main、source 分支/HEAD、三重父链、Correction/完整 Diff 范围、fixture 删除状态和双方洁净度；任一不符立即停止并报告。
- 上次授权未创建提交；两位更早的 Reviewer 均在发现 P1 后停止，未创建 evidence commit。不得伪造或引用任何 Reviewer evidence SHA。
- Correction 2 Diff 必须精确且仅为：

  1. `src/youtube_intel/providers/subtitles.py`
  2. `tests/integration/test_subtitle_provider.py`
  3. `handoffs/TASK-014.md`

- `tests/integration/test_public_subtitle_smoke.py` 是初始授权上限内但无需改动的文件；未修改是最小范围的正确结果，不得为了迎合范围文档
  制造无关改动。完整 B7 Diff 必须是原六路径允许范围的五路径子集，已删除 fixture 不得恢复、替代或在任何路径重现。
- Reviewer 唯一可写路径是 source `handoffs/TASK-014.md`，仅追加审查 evidence，且 evidence 必须以 `4d4366f…` 为唯一父提交。
  不得修改业务代码、测试、ADR、任务/状态控制面或其他 source 路径。

## 必须审查与负向验证

- 审查私有、无值的结构状态→固定安全分类接口；原始目录结构检查必须仍封装在 Adapter 内，不得成为新的公共 CLI、Provider、配置、
  logging、JSONL schema 或输出面。
- 验证 ADR-018 四个固定 `directory_origin`、六个固定 `directory_fingerprint`、ADR-017 B6 `directory_diagnostic`、仅目录
  `INVALID_RESPONSE` 的出口及正文 `INVALID_RESPONSE` 无 origin/fingerprint；directory-only 维持 enumerate=`1`/read=`0`。
- 独立验证测试、fixture、stdout、stderr、JSONL 均不含字段名、字段值、URL、语言、轨道名、身份值、原始响应、Cookie、token、
  payload 或用户数据；已删除 fixture 不得以改名、移动、嵌入或其他路径重现。
- 验证解析接受面、CLI、`logging.py`、依赖、锁文件、Schema、读取计数、退出码、default/directory-only、临时根、ID 上限、无重试、
  零业务记录与所有 fail-closed 边界没有退化。

## 允许检查与绝对禁止

- 仅在已有离线 `.venv` 可用时，允许运行两份 B7 聚焦 pytest、mypy Provider/smoke、Ruff B7 tests、
  `.venv/bin/youtube-intel --help`、`git diff --check` 与静态范围/泄漏扫描。不得运行 `uv`、构建、真实 smoke、其他 CLI 子命令、
  Python/import、数据库或网络诊断。
- 禁止真实 YouTube、网络、媒体、ffmpeg、认证、Cookie、API key、真实 Vault、用户数据、模型、Ollama、OpenAI、付费调用、
  launchd、push、合并、source 清理和 `.codebase-memory` 工件。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3、实际检查和未运行项。TASK-014 继续 `IN_PROGRESS / No-Go`；离线审查不构成真实服务验证、
  发行批准或最终 Go。
