# TASK-014B4 — 受限 directory-only 公开字幕 smoke Reviewer

你是 TASK-014B4 的全新独立 Codex Reviewer。只审查固定 source 的产品 Diff 与离线证据；不得修复、重构、
重新设计、启动真实资源或修改产品代码。本包不启动测试、`uv`、构建、网络或 smoke。

## 固定审查对象

```text
Task: TASK-014B4 — restricted directory-only public subtitle smoke
Role: Independent Reviewer
Review control-plane base: main@6c9bc8e37769bfc2da4ff1dc8c904e7afb38c6d0
Reviewed source worktree: /Users/developer/Documents/yia-worktrees/task-014b4-directory-only-smoke
Reviewed source branch: codex/task-014b4-directory-only-smoke
Reviewed implementation HEAD: 2959275b0f61a1fb3a7e9ac520a56fa89e4e2b14
Required sole parent: bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d
Product review range: bbd3fddd3c7fa1b8624dffb39b5fb8b262afba7d...2959275b0f61a1fb3a7e9ac520a56fa89e4e2b14
```

- B4 架构谱系基线为 `bdf2bf2adeb337b61747d869fa91619e3163a298`，分配控制提交为
  `ccc747800b59e2bacc918f1e7b81e065b1520d9a`；两者都不是当前产品审查范围的起点。
- 开始前只读核验 source 分支、HEAD、唯一父提交和洁净度；任一不匹配立即停止并报告。不得 rebase、
  cherry-pick、清理、切换、修复或改写 source。
- Reviewer 唯一可写路径是该 source 的 `handoffs/TASK-014B4.md`，仅可在独立审查结论中追加证据。
  审查 evidence 必须以 `2959275…` 为唯一父提交；不得修改任何产品路径、任务卡、prompt、状态或其他文件。

## 审查重点与必须核验

- `smoke-public-subtitles --directory-only` 对每个合法目标严格为 metadata=1、directory enumerate=1、
  body read=0；目录成功与失败都没有正文读取。
- 未带 `--directory-only` 的默认 smoke 保持 metadata=1、enumerate=1、至多一份正文读取的既有契约。
- smoke 路径的 `--project-root`、`--settings`、`--channels` 在 runner、Adapter 或 temporary-root 初始化前
  拒绝；非 smoke 子命令拒绝 `--directory-only`。
- 保持最多 1--3 个唯一 ID、不存在绝对 temporary root、无重试和 fail-closed 安全边界；没有媒体、认证、
  Cookie、API key 或其他额外产品路径。
- directory `INVALID_RESPONSE` 只复用 ADR-015 固定脱敏 `directory_diagnostic` code；JSONL 不新增字段，
  不泄漏 URL、标题、字段值、正文、Cookie、token、payload、异常文本或用户数据。
- 受限 smoke 保持零业务记录：不创建 Pipeline、Job、ProviderCall 或 Artifact；范围只限任务卡五条产品路径。

## 检查与禁止项

- 本次 Reviewer 授权只允许 Git/文本/静态范围审查、固定 source Diff、handoff 追加与 `git diff --check`。
  不得运行 `uv`、pytest、Ruff、mypy、构建、产品 CLI、Python/import 或任何网络诊断。
- 禁止真实 YouTube、网络、真实 smoke、媒体、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、
  Ollama、OpenAI、付费调用、launchd、`.codebase-memory` 工件、push 与合并。
- 输出 `APPROVE` 或 `REJECT`，列出 P0--P3 与未运行的检查。不得将离线/静态审查表述为真实 B-1、
  发布批准或 TASK-014 Go；TASK-014 继续 `IN_PROGRESS / No-Go`。
