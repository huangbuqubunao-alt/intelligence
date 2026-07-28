# TASK-014B3：公开字幕目录兼容性诊断

- Status: `ACCEPTED`
- Assignee: `Codex Implementer（source 已接受，待 Product Integrator）`
- Reviewer: `全新独立 Codex Reviewer（APPROVE；P0–P3 均无）`
- 依赖：ADR-013、ADR-015、TASK-014B0 `DONE`、TASK-014B2 `DONE`
- 基线：`main@9c5f08ec829629591b095bd68841ca3ce0b22532`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics-implementation`
- Branch：`codex/task-014b3-public-subtitle-diagnostics-implementation`
- Reuse decision：`DIRECT` — 现有锁定 yt-dlp Adapter、ProviderCallMetadata、JsonlLogger、公开字幕 smoke 和离线 fixture/test；不新增第三方代码或依赖

## 背景与目标

旧 worktree `/Users/hua/Documents/yia-worktrees/task-014b3-public-subtitle-diagnostics` 及其旧分支已废止：禁止访问、
修改、合并、清理或复用。上述 worktree/branch 是本任务唯一实现 source。

唯一 B-1 evidence `9acab5d876b38d64a9aeab7aca3474be2676ce38` 是真实 smoke `FAIL`：两个固定公开视频各完成
一次元数据读取和一次字幕目录调用，但均在目录响应映射完成前、正文读取前以 `INVALID_RESPONSE` 失败，正文读取为零。evidence 不合并、不写成通过，也不
授权重新执行网络。

实现 ADR-015 的有限、脱敏目录兼容性诊断，使离线测试能断言“哪类结构校验失败”，而不记录原始响应或降低安全边界。

## 最小允许修改范围

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `tests/fixtures/subtitles/**`（仅新增/调整脱敏目录形状 fixture）
6. `handoffs/TASK-014B3.md`

不得修改其他路径；尤其不得修改 `pyproject.toml`、`uv.lock`、依赖、Schema/migration、domain 公共契约、默认 CLI、
`logging.py`、README/发布结论、TASK-014 状态或 B-1 evidence。

## 验收标准

- [ ] 对目录枚举的 `INVALID_RESPONSE` 仅产生 ADR-015 允许的固定诊断 code；没有动态值、原始异常或响应片段。
- [ ] Adapter 将固定 code 放入现有 ProviderCallMetadata diagnostics；smoke 仅在目录 `INVALID_RESPONSE` 时以固定
  `directory_diagnostic=<code>` 追加到既有脱敏 `safe_message`，不新增任意 JSONL 字段。
- [ ] 不改变元数据 → 目录 → 排序 → 一次正文读取的顺序、调用次数、退出码、临时根或正文不持久化边界。
- [ ] 脱敏 fixture 覆盖每个新分类及一个明确良性兼容变体（若实现该变体）；危险 URL、缺字段、超限和不支持格式继续
  fail-closed。
- [ ] Smoke Fake 覆盖目录 `INVALID_RESPONSE` 的 `metadata=1 / enumerate=1 / read=0` 审计记录，且没有重试。
- [ ] B3 不执行任何真实资源；离线实现/测试通过不等于 B-1 成功、发布批准或 TASK-014 Go。

## 允许的离线检查（Implementer 启动后）

- 仅在预先存在的、已批准的离线环境可用时运行聚焦 pytest、Ruff、mypy 与 `git diff --check`；环境不可用时停止报告，
  不运行 `uv sync`、安装、下载或改锁文件。
- 检查命令和实际结果必须记录在 handoff；本任务控制面创建本身不运行任何测试、构建、lint、typecheck 或网络命令。

## 红线与交付

- 禁止网络、YouTube、真实 smoke、媒体下载、Cookie/登录/API key、真实 Vault/用户数据、ffmpeg、模型、Ollama、
  OpenAI、付费调用、launchd、`.codebase-memory` 工件和任何自动重试。
- 完成时仅创建一个只含允许路径的 Implementer commit，交由新独立 Reviewer；不得自行 `ACCEPTED`、`DONE`、合并、push
  或启动真实验证。
- Reviewer 必须独立复核固定诊断集合、脱敏、fail-closed 回归、范围和离线检查；真实验证另行授权。
