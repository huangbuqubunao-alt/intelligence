# TASK-025 交接报告

## 元数据

- Task: `TASK-025 — Weekly Foundation`
- Role: `Implementer / adversarial reviewer`
- Agent/session: `Codex`
- Approved base / START_HEAD: `92874d4994ec2507e192d18eeafc694fc143a0ff`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-025-weekly-foundation`
- Branch: `codex/task-025-weekly-foundation`
- Implementation commit: `54dd03a435ed42dfdbc7325c8aace243f70a3a56`
- Started / reported: `2026-09-08`

## 目标与范围

- TASK-025 新增 immutable **Weekly V1 Brief**：它是指定历史周内、以
  Intelligence/Topic 为主单位的跨视频快照，而不是视频列表、当前 Topic
  投影或第二个 Intelligence/Topic truth root。
- `m013` 将 SQLite 从 `user_version=12` 前进至 `13`；只创建空的 Weekly
  V1 结构，绝不回填/推断历史周、Preference、Topic 或 Intelligence，也不调用
  model/provider。
- 新增 `WeeklyBriefService` 和只读 local API seam：
  `GET /api/v1/weekly/v1` 与 `GET /api/v1/weekly/v1/{brief_id}`。它们有明确
  `weekly-v1` 身份，保留既有 `/api/v1/weekly` generic reports 和 frozen Weekly V2
  的独立 authority。
- 明确未做：TASK-026 IA/UI、Daily Brief、Ask Intelligence、Investigation、Early
  Signal、Evidence Expansion、Deep Analysis、真实 provider/model 调用、第二个
  resource ledger、TASK-024 编排改动；m006–m012 未修改，未创建 m014。

## 设计与信任边界

| 领域 | 决定与约束 |
|---|---|
| Period / identity | 通过既有后端 `week_period_for` 得到设置时区的精确 `[start, end)` UTC window；logical ID 为 `weekly-v1:<timezone>:<start>:<end>`，opaque `brief_id` 是其 SHA-256。 |
| Trusted input | 候选必须是本周期 TASK-023 primary Topic membership（NEW_INFORMATION、NEW_EVIDENCE、CONTRADICTORY_INFORMATION）并且能被 `AuthoritativeIntelligenceReader.read_current_card` 复验。raw Intelligence、raw model text、没有 legal Topic membership 的 card 都不能进入。 |
| Cross-video selection | 同 Topic 只保留一个 primary item；contradiction 优先于 new evidence，再优于 new information；SUPPORTING_REPETITION 与 LOW_VALUE_DUPLICATE 不会填充 Weekly。 |
| Content / lifecycle | V1 item 保存 Topic、Intelligence revision、exact Evidence、claim kind、source state 与 card 的 exact core conclusion；FACT、OPINION、PREDICTION、RUMOR、SYSTEM_INFERENCE 和 DISPUTED 不会被压平为事实或共识。 |
| Personalization | 仅使用 generation-time active Preference 的投影来排序；记录 preference ID/horizon/provenance/statement hash，不写回 Preference，也不把 DERIVED 改成 EXPLICIT。 |
| Immutability | finalized Weeklies、items、item Evidence 与 preference projection 都拒绝 UPDATE/DELETE；Topic rename、later Intelligence revision 不会重写原有文本、Topic name 或 revision。 |
| Corrections / deletion | 追加式 marker 仅允许 current trusted later revision 的 `SUPERSEDED`，或实际 `DELETED`/`UNAVAILABLE` Evidence 的 marker。marker reason 是 task-authorized constant；不能由调用方伪造。Evidence → Weekly item 查询保留删除影响，同时 FK `RESTRICT` 阻止历史 cascade deletion。 |

## 迁移

- `src/youtube_intel/migrations/013_add_weekly_brief_foundation.sql`
- 新表：`weekly_briefs`、`brief_items`、`brief_item_evidence`、
  `weekly_brief_preference_projections`、`brief_item_markers`。
- Fresh DB 为 `user_version=13`；v012 → v013 保留 prior Intelligence 数据，且
  `weekly_briefs` 为空。m014 不存在。
- 数据库 trigger 复验 item 的 current Topic membership/revision/content hash 与
  immutable Distillation Card conclusion；还复验 supersession 是 current revision，
  evidence marker 对应实际不可用 Evidence。因而底层持久化 API 也不能直接写入任意
  Weekly bullet 或 marker。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| migration / schema | PASS | TASK-025 v012→v013、fresh schema、无 synthetic Weeklies、无 m014；既有 migration/schema tests 同步检查 v013。 |
| period / idempotency | PASS | UTC start-inclusive/end-exclusive boundary、stable opaque ID/logical identity 与 duplicate finalization 均有覆盖。 |
| trust / provenance | PASS | reader-only Topic candidate、raw-card-only exclusion、direct arbitrary item text rejection、item → Topic/Intelligence revision → Evidence retained。 |
| topic / personalization | PASS | primary Topic de-dupe、repetition exclusion、new Evidence priority、contradictory DISPUTED RUMOR preservation，以及 Preference projection 无 mutation。 |
| history / correction | PASS | Topic rename 和 later revision 不改 finalized snapshot；in-place update、forged marker、available-evidence marker 都被拒绝；legal supersession/deletion marker 追加。 |
| V2 / frozen boundaries | PASS | Weekly V1 read seam 与 generic reports/Weekly V2 explicit separate；TASK-019 reader、TASK-022 distillation/ledger、TASK-023 Topic、TASK-024 orchestrator、scoring/dispatch/AMBIGUOUS 不变。 |
| provider / cost | PASS | `WeeklyBriefService` 是 deterministic persistence/read composition；没有 transport/provider imports、调用或 TASK-022 ledger writes。Deep Analysis 仍 BLOCKED。 |

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| 初始 TDD | PASS | 新 TASK-025 test 先因 `ModuleNotFoundError: youtube_intel.brief` 失败。 |
| `uv run --offline pytest -q tests/integration/test_task025_weekly_foundation.py` | PASS | 最终 `13 passed`。 |
| TASK-018→TASK-024 / dispatch / AMBIGUOUS / migration regressions | PASS | `238 passed`。 |
| `uv run --offline pytest -q` | PASS | `2149 passed, 1 skipped, 1 warning`；warning 是既有 TASK-016C Pydantic serializer adversarial test。 |
| `uv run --offline mypy src` | PASS | `Success: no issues found in 53 source files`。 |
| `uv run --offline ruff check .` | PASS | `All checks passed!`。 |
| `uv build --offline` | PASS | sdist 与 wheel 均成功；仅现有 uv build-system version warning。 |
| `git diff --check` | PASS | 无 whitespace error。 |
| `bash scripts/security_scan.sh` | REVIEWED | **EXIT 1**，`findings count=11`，精确为既有接受的 synthetic fixtures；new blocking findings=`0`，绝非 PASS。新增 Weekly 哈希 helper 仅触发 review-level high-entropy WARN，无 secret/API-key finding。 |

## 对抗审查

- P0: `0`
- P1: `0`
- P2: `0`
- 已攻击并关闭：raw DB Intelligence/card 或 caller text 的 Weekly authority；claim/state
  提升；disagreement → false consensus；repetition/source-count domination；outside-period
  membership；browser timezone authority；finalized item overwrite/delete；live Topic/later
  revision rewrite；Evidence cascade deletion；forged correction/deletion marker；duplicate
  finalization；hidden model/ledger use；V1/V2 ambiguity；m013 synthetic history/m014；
  TASK-024/023/022/019/scoring/Deep Analysis/TASK-026 leakage。
- 两个实现期 P1 已修复并重测：
  1. marker trigger 现在要求 actual current revision 或 actual invalidated evidence，并
     固定 reason；
  2. item trigger 现在要求 immutable trusted card conclusion 与 snapshot summary 完全相等。

## 失败、跳过与风险

- 无未解决 P0/P1，无阻塞项。
- 生产环境目前没有获授权的 live model/provider；Weekly V1 不尝试弥补此能力，只消费
  已合法持久化的 Intelligence card。
- V1 是 task-owned backend/read foundation；最终 first-level navigation 和 product visual
  integration 属于尚未授权的 TASK-026。

## 实现者 / Reviewer 结论

- 建议状态：`APPROVE`。
- 审查对象：`54dd03a435ed42dfdbc7325c8aace243f70a3a56`。
- Reviewer：`Codex self adversarial review`（非独立人类审批）。
- 未解决 P0/P1：`0 / 0`。
- 不执行 push、merge、tag 或 release；不启动 TASK-026。
