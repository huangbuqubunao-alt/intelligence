# TASK-008 Correction 2 — 第三位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-008 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-008.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-REVIEWER-3-CODEX.md`；main 中 TASK-008 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-008` /
  `codex/task-008-deep-analysis@71e1c24936b0ed1be3a98c49efa7770f7456d85c` /
  `473119704c7638d7afd4e68d84d00e85064ceabd`。
- Correction 唯一父为 reviewer-2 evidence `02317f2...`，其证据链继续回到 Correction 1 `8317cd9...`、first-review evidence `b61f46f...` 和 implementation `10478a9...`。
- 完整允许范围：`analysis.py`、`providers/cloud_llm.py`、`prompts/summary.md`、`tests/fixtures/analysis/**`、
  `test_analysis_policy.py`、`test_summary_provider.py`、`handoffs/TASK-008.md`。
- Source 卡和项目状态是固定 base 的历史 `BLOCKED/UNASSIGNED` 快照；不得作为冲突或写回 source。TASK-009 source 不得读取、修改或清理。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-008 source 运行会写入 `.codebase-memory/` 的索引动作；直接针对本包固定文件与 Git Diff 做窄范围只读审查。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围：Correction 只可改 `analysis.py`、集成测试和 handoff；禁止依赖/锁、公共契约、配置、`state.py`、Schema/migration、CLI、TASK-009 变更。
2. 独立复跑：`uv lock --check`、`uv sync --locked`、两组 focused tests、全量 pytest、mypy、Ruff、CLI help、`uv build --offline`、sdist/wheel 的 prompt、固定 tokenizer 和 migration SQL inclusion、固定 `git diff --check`。
3. 独立探针：
   - A：持久化与非持久化路径在关闭、低分、缓存、预算耗尽、token 超限、缺凭据时均零 credential/transport/Repository 副作用，且凭据最后读取。预算预先耗尽 + 普通合成字幕的真实临时 SQLite 必须确认 ProviderCall/Artifact=None、Pipeline=`SCORED`、Job=`RUNNING`、Resolver/transport=0。
   - B：token 边界、payload/采样/request hash 确定性，SDK 仅在白名单环境隔离子进程导入；无 OpenAI/Azure/代理/凭据继承或真实网络。
   - C：Structured Outputs success/refusal/缺字段/语义或 evidence 错误、429/5xx/timeout 的安全映射和完整异常图脱敏。
   - D：成功原子完成、complete_stage 注入失败全回滚/本次文件清理/provider call 可重试、成功 call/artifact 重排零 transport、RAW_RESPONSE_30D 过期时间精确为创建时间加 30 天。
   - E：ADR-008 A-01 至 A-17、AC、五轴、复用/许可证和范围；无真实 OpenAI、密钥、付费、网络、Vault/用户内容或测试目录外文件操作。
4. 在 source handoff 追加 checks、探针、AC/ADR matrix、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。
