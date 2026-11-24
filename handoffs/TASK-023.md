# TASK-023 交接报告

## 元数据

- Task: `TASK-023 — Topic & Timeline Foundation`
- Role: `Implementer / Reviewer`
- Base branch/commit: `51c980928553a2161c70c980a8e79afcc61a70c5`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-023-topic-timeline`
- Branch: `codex/task-023-topic-timeline`
- Start commit: `51c980928553a2161c70c980a8e79afcc61a70c5`
- Implementation commits:
  - `6057a4099373a4e2201964996078ed5b77318fcf feat: add topic intelligence and timeline foundation`
  - `414425260880007dc102ab3f67369fef50fcdc5a fix: harden topic provenance and history`

## 目标与范围

- 在 v010 上以 m011 引入可长期存在、可审计的 Topic；升级只创建空 Topic 结构，不对历史 Intelligence 进行推断、聚类或模型调用。
- Topic 只通过 `AuthoritativeIntelligenceReader` 接纳当前 `VerifiedIntelligenceRead`；持久化精确 Intelligence revision 和 Evidence IDs，读取时再次验证。
- 实现稳定 Topic ID、rename、pin、有限 association 类型、跨视频重复/新证据/矛盾表示、动态 current state、不可变 Timeline、Related Topics、merge/split 与直接 revision 影响查询。
- 受控 local API 仅允许 Topic 名称、pin、有限 association、RELATED relation 及 merge/split 指令；不接受 summary、claim text、revision ID、Evidence ID、lifecycle、confidence 或任意 relation 类型。
- 未做：Source Run/队列/调度、Weekly/m012、Investigation/Early Signal、Evidence Expansion、外部验证、模型/Provider 调用、Deep Analysis、评分权威变更。

## 设计与信任边界

| 领域 | 实现与约束 |
|---|---|
| Identity / Pin | 稳定 `topic_id`；rename 与 pin 仅是产品交互状态，不能改变 claim、lifecycle、Evidence 或 confidence。 |
| Membership | 唯一 `(topic_id, intelligence_id, revision_id)`，确定性 membership ID；精确 revision/Evidence FK、触发器和不可变记录保留来源。 |
| Trusted input | `TopicApplicationService` 在写入和读取时使用 `AuthoritativeIntelligenceReader`；raw revision 不可由 API 提交，也不能在读取时成为未验证当前真相。 |
| Information gain | 有限 `NEW_INFORMATION`、`SUPPORTING_REPETITION`、`NEW_EVIDENCE`、`CONTRADICTORY_INFORMATION`、`LOW_VALUE_DUPLICATE`。重复不会生成主事实或无限 Timeline。 |
| Consensus | 需要至少两个 legal contribution，且其中有 `NEW_EVIDENCE` 的 `INDEPENDENT_VERIFICATION`；仅 source count/repetition 不能形成共识；不确定独立性保持 `UNKNOWN`。 |
| Current / history | current state 动态重算，不把可变或 raw Timeline state 当真相；Timeline 追加式、不可更新/删除，且每事件有同 Topic 的主 membership 与 revision/Evidence provenance。 |
| Relation / correction | relation 固定为非因果 `RELATED`；`affected_memberships(intelligence_id, revision_id)` 提供后续更正/删除影响入口。当前 revision 失效或改变会将旧 contribution 标为不可用；current event 依赖失效或不再有可用 contribution 时，current projection 为 `DEGRADED`。 |

## 迁移

- m011：`src/youtube_intel/migrations/011_add_topic_timeline.sql`
- `user_version`：`10 → 11`；m012 未创建且 migration 列表仅至 011。
- 保留既有 Source、Automation、Evidence、Intelligence、Preference、Policy 和 Ledger 数据。
- wheel 已验证含 `youtube_intel/migrations/011_add_topic_timeline.sql`。
- Timeline 触发器拒绝无同 Topic 主 membership、event-kind 与主 membership 不匹配、无矛盾依据的 `DISAGREEMENT`，及缺少两个成员和独立验证 Evidence 的 `CONSENSUS`。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| m011 / upgrade | PASS | TASK-023 测试覆盖 v010→v011、fresh v011、数据保留、无 Topic backfill、m012 缺席。 |
| 可信 membership | PASS | 测试覆盖 reader-only admission、raw revision API 拒绝、foreign revision 拒绝、类型/生命周期保留及幂等重复。 |
| 去重与状态 | PASS | 重复不生成主事件；新独立 Evidence 才可形成有限共识；矛盾为 disagreement，低价值重复保留在 Intelligence history。 |
| Timeline / provenance | PASS | 事件追加式；主 membership 和 junction 都会投影 revision/Evidence；无来源事件、raw consensus state 均被迁移约束拒绝。 |
| Relation / pin / correction | PASS | RELATED 唯一、有限、非因果；pin 不改真相；失效 revision 令 current 投影降级且历史仍可追溯。 |
| Frozen boundaries | PASS | TASK-019/022 reader contracts、scoring authority、dispatch/AMBIGUOUS、ledger/budget/model policy 与 Deep Analysis 均未改变。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| 初始 TDD | PASS | 新 Topic 测试先失败：`ModuleNotFoundError: youtube_intel.topic`。 |
| P1 回归：无来源事件 | PASS | 先失败，m011 增加 required primary membership 与 topic ownership 触发器。 |
| P1 回归：raw Timeline state | PASS | 先失败，m011 只允许有有限支持的 disagreement/consensus；current read 也只从 reader-validated membership 重算。 |
| P1 回归：主 provenance 投影 | PASS | 先失败，event reader 将 primary membership 与 junction membership 取并集。 |
| `uv run --offline pytest -q tests/integration/test_task023_topic_timeline.py` | PASS | `22 passed`。 |
| 关键前序/authority 回归 | PASS | `218 passed`（TASK-018/018A/019/020/021/022、TASK-023、state/local API、migration/schema、dispatch recovery、Deep Analysis persistence）。 |
| `uv run --offline pytest -q` | PASS | `2086 passed, 1 skipped, 1 warning`；warning 为既有 Pydantic serializer 测试警告。 |
| `uv run --offline mypy src` | PASS | `Success: no issues found in 50 source files`。 |
| `uv run --offline ruff check .` | PASS | `All checks passed!` |
| `uv build --offline` | PASS | sdist 与 wheel 均已构建；现有 uv build-system version warning 无变更。 |
| `git diff --check` | PASS | 无输出。 |
| `bash scripts/security_scan.sh` | BASELINE | 实际 `EXIT 1`，`findings count=11`，均为既有 accepted synthetic fixture finding；new findings=`0`。此结果不是 PASS。 |

## Diff 复核与对抗审查

- 实际修改限于 m011、Topic repository/service/API、doctor 的版本上限、受迁移版本影响的既有测试，以及本交接文件。
- 未添加依赖、密钥、credentials、网络调用、调度、Source Run、Weekly/Brief/m012 或 V2 runtime。
- 对抗检查后：`P0=0`，`P1=0`，`P2=0`。
- 已攻击并关闭：raw Intelligence/revision 与 copied summary；claim/lifecycle 提升；source-count consensus；重复事件；Timeline overwrite/delete；rename/duplicate membership；任意 relation/causal edge；pin truth mutation；foreign dependency；失效 support；raw event state；m011 inference/provider calls；TASK-024/025/V2 leakage；第二 scoring/intelligence trust root。

## 失败、跳过与风险

- 已解决失败：三项上述 P1 均用先失败、后通过的测试锁定。
- 跳过：无。完整 pytest 已运行。
- 已知非本任务基线：security scanner 的 11 个 synthetic fixture findings；scanner 退出为 1，未宣称通过。
- 剩余产品范围：自动 Source Run、纠正传播 UX、Weekly 和高级独立证据推断均按任务边界留给后续授权。
- `DECISION NEEDED`: `None`。

## 实现者 / Reviewer 结论

- 建议状态：`IN_REVIEW`，建议批准 TASK-023。
- 审查对象：`414425260880007dc102ab3f67369fef50fcdc5a`（含前一实现 commit）。
- Verdict：`APPROVE`。
- 未解决 P0/P1：`0 / 0`。
- 不执行 push、merge、tag 或 release；不启动 TASK-024。
