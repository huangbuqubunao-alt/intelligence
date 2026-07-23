# TASK-008 Correction 5 — 第六位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-008 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-008.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-REVIEWER-6-CODEX.md`；main 中 TASK-008 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@dcbbd38fe8bab79fd6db1679f43a8ca48fb472ea` / `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Correction 5 唯一父为 reviewer-5 evidence `78ae101786ada5f04d2b7c734c84a216f8820803`；完整证据链继续回到 prior corrections 和 original implementation。
- 完整允许范围：`analysis.py`、`providers/cloud_llm.py`、`prompts/summary.md`、`tests/fixtures/analysis/**`、`test_analysis_policy.py`、`test_summary_provider.py`、`handoffs/TASK-008.md`。
- Source 卡和项目状态是固定 base 的历史 `BLOCKED/UNASSIGNED` 快照；不得作为冲突或写回 source。TASK-009 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-008 source 运行会写入 `.codebase-memory/` 的索引动作；直接针对本包固定文件与 Git Diff 做窄范围只读审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围：Correction 5 只可改 `cloud_llm.py`、指定集成测试和 handoff；禁止依赖/锁、公共契约、配置、`analysis.py`、`state.py`、Schema/migration、CLI、TASK-009 变更。
2. 独立复跑全部门禁：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel prompt、固定 tokenizer 与 migration SQL inclusion、固定 `git diff --check`。
3. 独立探针：
   - A：Fake child/Popen seam 验证永不 handshake、handshake 后永不 response、EOF、畸形 JSON、非零退出、写入失败与成功 response；每个非成功路径必须在有限 deadline 内关闭 pipe、terminate/kill/reap child，并映射为安全脱敏错误，无 orphan/线程泄漏。
   - B：A-17 隔离仍成立：主进程不导入 SDK，child 只得白名单环境，credential 不在 env/argv/file/log；不做真实 API、密钥或网络。
   - C：完全缓存命中与篡改/缺失 Artifact 的 fail-closed 完整性；A-03 的关闭、低价值、token、预算、缺凭据零副作用；成功、`complete_stage` 回滚、重排和 RAW_RESPONSE_30D 30 天。
   - D：payload 白名单、Structured Outputs success/refusal/缺字段/语义或 evidence 错误、429/5xx/timeout 与完整异常图脱敏。
   - E：ADR-008 A-01 至 A-17、AC、五轴、复用/许可证和范围；无真实 OpenAI、密钥、付费、网络、Vault/用户内容或测试目录外文件操作。
4. 在 source handoff 追加 checks、探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。
