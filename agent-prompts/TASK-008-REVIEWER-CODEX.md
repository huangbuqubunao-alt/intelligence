# TASK-008 — Independent Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-008 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-008.md`。冲突、范围异常、未授权资源路径或任何 P0/P1 立即 `REJECT` 并停止。

source worktree 固定在分配前 base，因此其中的 `tasks/` 与 `docs/PROJECT_STATUS.md` 显示旧 `BLOCKED/UNASSIGNED` 是历史快照；实时审查状态只能以本包动态解析的 main commit 中 TASK-008=`IN_REVIEW` 为准。不得把该快照当作冲突，也不得更新 source 的任务状态文档。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-REVIEWER-CODEX.md`
- Source/base：`/Users/hua/Documents/yia-worktrees/task-008` /
  `codex/task-008-deep-analysis@10478a9083df4eedae061d99d941c88cb4954179` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`
- Full allowed scope：`analysis.py`、`providers/cloud_llm.py`、`prompts/summary.md`、`tests/fixtures/analysis/**`、
  `test_analysis_policy.py`、`test_summary_provider.py`、`handoffs/TASK-008.md`。

## 强制审查

1. 核验 source 分支/HEAD/唯一父/cleanliness、main 授权状态和完整 Diff；禁止范围外、依赖/锁、公共契约、Schema/state/CLI/TASK-009 改动。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、migration SQL package inclusion、固定 `git diff --check`。
3. 独立探针必须覆盖：
   - A：关闭/低分/缓存/预算/token/缺凭据门禁均零 transport，且凭据最后读取；payload/采样/request hash/token 边界确定。
   - B：SDK 只在不继承父环境的隔离子进程导入；无 OpenAI/Azure/代理/密钥泄漏，真实网络/API/密钥均未触发。
   - C：Structured Outputs success/refusal/缺字段/语义或 evidence 错误、429/5xx/timeout 映射安全且异常图不含字幕全文、响应正文、密钥或本地路径。
   - D：真实临时 SQLite 成功原子完成、complete_stage 注入失败全回滚/本次文件清理/provider call 可重试、重排复用成功 call/artifact 并确保 transport 零调用；RAW_RESPONSE_30D 到期时间精确为创建时间加 30 天。
   - E：A-01 至 A-17、AC、五轴、复用/许可证和范围审查；无真实 OpenAI、密钥、付费、网络、Vault/用户内容或测试临时目录外文件操作。
4. 在 source handoff 写 checks、探针、AC/ADR matrix、P0–P3、skipped/risks、`APPROVE` 或 `REJECT`；单独提交该 handoff。不得改 task state、merge、push 或清理。
