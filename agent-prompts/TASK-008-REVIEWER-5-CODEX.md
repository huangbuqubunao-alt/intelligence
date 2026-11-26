# TASK-008 Correction 4 — 第五位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-008 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-008.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-REVIEWER-5-CODEX.md`；main 中 TASK-008 必须为 `IN_REVIEW`。
- Source/base：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@bb195a59ddee25cb804b0078676c504e94c44441` / `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Correction 4 唯一父为 reviewer-4 evidence `19323923057adb0b5a9f59cac5eb7c32cce5888a`；完整证据链继续回到 prior corrections 和 original implementation。
- 完整允许范围：`analysis.py`、`providers/cloud_llm.py`、`prompts/summary.md`、`tests/fixtures/analysis/**`、`test_analysis_policy.py`、`test_summary_provider.py`、`handoffs/TASK-008.md`。
- Source 卡和项目状态是固定 base 的历史 `BLOCKED/UNASSIGNED` 快照；不得作为冲突或写回 source。TASK-009 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-008 source 运行会写入 `.codebase-memory/` 的索引动作；直接针对本包固定文件与 Git Diff 做窄范围只读审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围：Correction 4 只可改 `analysis.py`、指定集成测试和 handoff；禁止依赖/锁、公共契约、配置、`state.py`、Schema/migration、CLI、TASK-009 变更。
2. 独立复跑全部门禁：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel prompt、固定 tokenizer 与 migration SQL inclusion、固定 `git diff --check`。
3. 独立探针：
   - A：真实临时 SQLite + Fake Resolver/transport 建立完全匹配成功缓存；确认缓存重排零 Resolver/transport/新 ProviderCall/Artifact，并可按 A-12 通过 `complete_stage` 原子恢复当前 `SCORED -> ANALYSIS_READY` Job。
   - B：逐一篡改 structured `request_hash`、provider、model，raw/structured 文件内容，Artifact 的 `content_hash`，以及删除 raw 或 structured Artifact。每项都必须安全 fail-closed：零 Resolver/transport/新或失败化 ProviderCall/Artifact，Pipeline/Job 不推进；不得重新调用云端。
   - C：关闭、低价值、token 超限、预算耗尽、缺凭据、缓存、成功、complete_stage 注入失败回滚、成功重排、RAW_RESPONSE_30D 精确 30 天；验证 A-03 顺序、零副作用与 ProviderCall 可重试语义。
   - D：token/哈希/SDK 隔离、payload 白名单、Structured Outputs success/refusal/缺字段/语义或 evidence 错误、429/5xx/timeout 和异常图脱敏。
   - E：ADR-008 A-01 至 A-17、AC、五轴、复用/许可证和范围；无真实 OpenAI、密钥、付费、网络、Vault/用户内容或测试目录外文件操作。
4. 在 source handoff 追加 checks、探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。
