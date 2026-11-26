# Intelligence 第五轮独立终审剩余两项冻结合流门禁最终收口报告（Round 5 Final Closure Report）

> **工作分支**：`antigravity/remediation-20261125`（线性基于 `origin/main@d1b58f731adc4185fe78cc5538e9e211b8a0e211`，`main` 零改动）
> **Draft PR**：[#50 — antigravity/remediation-20261125 -> main](https://github.com/huangbuqubunao-alt/intelligence/pull/50)（`isDraft: true`，未开启 auto-merge，无冲突 `mergeable=true`）
> **最新 `VERIFIED_CODE_SHA`（代码与 14/14 一次全绿 CI 验证基线）**：`0ad549b9ea20b0ef3492f576f2010a68e8eddf9a`
> **前序基线**：`00bb495c9367d66c98c3136eb69ef7ab52ce4847`（第 4 轮代码）/ `ad923685d707a5a4c1d5a6dfc686bc0b0501dd04`（第 4 轮文档）
> **双 SHA 零代码差异规则**：本报告与更新后的 [`FINAL_BLOCKER_CHECKPOINT.md`](FINAL_BLOCKER_CHECKPOINT.md) 构成紧随 `0ad549b9ea20b0ef3492f576f2010a68e8eddf9a` 的纯文档交付提交 `DOCS_DELIVERY_SHA`，满足 `git diff --stat 0ad549b9ea20b0ef3492f576f2010a68e8eddf9a..HEAD -- src frontend tests scripts .github` 严格为空。
> **Gate R1 最终裁决**：**`HOLD`（第 5 轮终审冻结的剩余 2 项阻断门禁 `3/6` 与 `4/6` 已全部逐项收口实证，六项放行门禁全数关闭；等待独立 Reviewer 最终签收与项目所有者人工批准合流 `main`，严禁自动合流）**。

---

## 1. 第五轮终审《六项冻结放行门禁》逐项最终状态

| 门禁序号 | 冻结门禁内容 | 第五轮前状态 | 本轮最终状态 | 源码与验证实证（基于 `0ad549b9`） |
|---|---|---|---|---|
| **`1/6`** | `P1-F02-A` 旧版活跃 `cookie_file` Grant 迁移安全撤销与 `grant:` 槽位隔离 | PASS（已关闭） | **PASS（未改动，完整保留）** | [`youtube_auth_fallback.py`](../../../src/youtube_intel/youtube_auth_fallback.py) 与前轮完全一致，零改动 |
| **`2/6`** | `P1-F02-B` 断开/全撤接口严格 `422` 校验（无空体/缺 `scope` 旁路） | PASS（已关闭） | **PASS（未改动，完整保留）** | [`fast_read_api.py`](../../../src/youtube_intel/fast_read_api.py) 与前轮完全一致，零改动 |
| **`3/6`** | `P1-F03-A / B`：纯词法/概念重叠/跨语意译不得获 `EXACT_SUPPORTED`；引用说明（`note_zh`）降级回传；裁剪与启发式并存复合态不互相覆盖 | 剩余阻断 1 | **CLOSED** | 详见第 2 节：`workspace_intelligence_hub.py` 严格收窄 `EXACT_SUPPORTED` 仅限同语种原子句确定性字面包含，`_sanitize_citation_note_with_grade()` 传播 `HEURISTIC_ONLY` 等级，新增 `PARTIAL_PRUNED_HEURISTIC` + `contains_heuristic_claims`，前后端及 Markdown 全链条保留双重提示 |
| **`4/6`** | `P1-F03-C`：备份导出对无引用历史记录与已拒答记录也必须无条件重生成衍生 `obsidian_markdown` | 剩余阻断 2 | **CLOSED** | [`export_backup_snapshot()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L11232-L11286) 移除 `if isinstance(cites_raw, list) and cites_raw:` 条件旁路，对全部历史行（含已拒答、`citations_json=[]`、`NEEDS_REVERIFICATION`）无条件通过 `_row_to_research_session_dto()` 重生成并净化正文与 Markdown，同时保留 `archive_status: "EXPORTED_SNAPSHOT_UNVERIFIED_UNTIL_RESTORE"` |
| **`5/6`** | 双 SHA 远端 14/14 CI 一次通过且不触碰 CI / 清单 / o200k 门禁文件 | PASS（待新基线重跑） | **PASS（14/14 一次全绿）** | `VERIFIED_CODE_SHA = 0ad549b9` 触发 Run [`45780647653`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653) **`attempt = 1` · 14/14 `success`**；`.github/workflows/ci.yml`、`scripts/ci_test_manifest.py`、`tests/unit/test_o200k_provisioning.py` 较 `ad923685` 零改动 |
| **`6/6`** | 双 SHA 零代码差异、PR #50 无冲突、`main` 未改动（`R1 = HOLD`） | PASS（待新交付完成） | **PASS（`R1 = HOLD`）** | `DOCS_DELIVERY_SHA` 仅提交 `docs/validation/ux-redesign-2026-11-25/` 两份文档，源码/测试/前端/CI 差异严格为空；`origin/main` 维持 `d1b58f731adc4185fe78cc5538e9e211b8a0e211` |

---

## 2. 本轮精确修复说明（仅改动 5 个文件，零扩大概念字典）

1. **严格确定性 `EXACT_SUPPORTED` 边界（[`workspace_intelligence_hub.py#L1778-L2028`](../../../src/youtube_intel/workspace_intelligence_hub.py#L1778-L2028)）**：
   - **未扩充概念字典**，而是移除了「同语种概念集合覆盖 / 2 个领域词命中 / 跨语概念覆盖」直接晋升 `EXACT_SUPPORTED` 的三条宽松路径。
   - 新增确定性归一化与子串包含判定 [`_normalize_for_exact_match()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L1778-L1790) 与 [`_exact_sentence_contains_claim()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L1793-L1802)（仅剥离 `[E#]` 引用、中性引述导语、标点空白、`同比/环比/共/约/为/是/的/了` 及极窄度量同义词 `营收↔收入`、`客单价/价格↔售价`、`上涨↔增长` 等，**绝不剥离状态/时态/能力动词**如 `正在/已经/申请/获得/保证/支持`）。
   - 效果实证：`「公司正在申请专利。」` 面对结论 `「公司已经获得专利 [E1]。」`（以及带数字版 `「公司正在申请 5 项专利。」` vs `「公司已经获得 5 项专利 [E1]。」`）、2 词以上局部重合改写与所有跨语意译（含 `GOOD_BILINGUAL`），现均严格降为 **`HEURISTIC_ONLY`**，绝不会误标 `EXACT_SUPPORTED` / `SUPPORTED`；仅同语种且在单条引用原句中确定性字面包含的事实（如 `「2025年公司营收增长 5% [E1]。」` 对 `「2025年公司收入同比增长 5%。」`、`「公司正在申请专利 [E1]。」` 对 `「公司正在申请专利。」`）方可获 `EXACT_SUPPORTED` / `SUPPORTED`。

2. **引用说明 `note_zh` 等级传播与复合态 `PARTIAL_PRUNED_HEURISTIC`（[`workspace_intelligence_hub.py#L2053-L2074`](../../../src/youtube_intel/workspace_intelligence_hub.py#L2053-L2074)、[`L8705-L9408`](../../../src/youtube_intel/workspace_intelligence_hub.py#L8705-L9408)、[`L11504-L12147`](../../../src/youtube_intel/workspace_intelligence_hub.py#L11504-L12147) & [`WorkspaceAiWidgets.tsx#L144-L147,L800-L806,L4321-L4336`](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx#L4321-L4336)）**：
   - 新增 [`_sanitize_citation_note_with_grade()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L2053-L2074)（及 `_is_substantive_note_claim()` 区分纯编号短签如 `g11` 与实质声明型 `note_zh`），在实时问答 `ask_research_question`、历史读出 `_row_to_research_session_dto` 及备份恢复 `_reverify_restored_session_item` / `restore_backup_snapshot` 全路径回传有效引用的 `note_verification_grade`。当主句精确支持但 `note_zh` 为启发式表述时，会话不再冒充 `SUPPORTED`，统一标注 `fact_verification_state = "HEURISTIC_ONLY"` 与 `contains_heuristic_claims = true`。
   - 新增 [`_compose_fact_verification_state()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L1805-L1812)：当同一回答**同时存在部分未支持内容裁剪与保留下的启发式声明/引用说明**时，返回复合状态 **`PARTIAL_PRUNED_HEURISTIC`**（并保留 `partial_pruned = true` 与 `contains_heuristic_claims = true`）。
   - Obsidian Markdown（[`L9021-L9034`](../../../src/youtube_intel/workspace_intelligence_hub.py#L9021-L9034)）与前端 [`WorkspaceAiWidgets.tsx#L4321-L4336`](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx#L4321-L4336) 针对 `PARTIAL_PRUNED_HEURISTIC`（及历史兼容 `PARTIAL_PRUNED + contains_heuristic_claims=true`）**同时展示「部分未支持内容已裁剪」与警告态「启发式相关 · 请核对原文」**，绝不因裁剪覆盖启发式警示，也绝不退回 `SUPPORTED`。

3. **备份导出全记录无条件 Markdown 重建（[`workspace_intelligence_hub.py#L11232-L11286`](../../../src/youtube_intel/workspace_intelligence_hub.py#L11232-L11286)）**：
   - [`export_backup_snapshot()`](../../../src/youtube_intel/workspace_intelligence_hub.py#L11258-L11286) 对数据库中**每一行** `research_qa_sessions`（不再跳过 `citations_json == "[]"` 或已拒答行）均调用 `self._row_to_research_session_dto(row)` 重新校验并覆盖写入 `answer_zh`、`key_takeaways_json`、`action_items_json`、`citations_json`、`obsidian_markdown` 与 `scope_json`（并强制保留 `archive_status: "EXPORTED_SNAPSHOT_UNVERIFIED_UNTIL_RESTORE"`、`source_integrity_status`、`fact_verification_state`、`contains_heuristic_claims`）。
   - 因 `export_backup_snapshot()` 现已无条件重建无引用行的衍生 Markdown，同步调整 [`tests/integration/test_codex_review_remediation.py#L1681-L1695`](../../../tests/integration/test_codex_review_remediation.py#L1681-L1695)（`test_n3` Case b 合成 64 MiB 体积压力测试夹具将测试文本由 `obsidian_markdown` 移入 `answer_zh`，原有全部断言一字未改）。

---

## 3. 本轮变更文件与新增回归覆盖（`ad923685..0ad549b9`，精确 5 个文件）

1. [`src/youtube_intel/workspace_intelligence_hub.py`](../../../src/youtube_intel/workspace_intelligence_hub.py)
2. [`frontend/src/workspace/WorkspaceAiWidgets.tsx`](../../../frontend/src/workspace/WorkspaceAiWidgets.tsx)
3. [`tests/integration/test_final_blocker_closure.py`](../../../tests/integration/test_final_blocker_closure.py) — 更新 `GOOD_BILINGUAL`（L1076–L1083）断言为 `HEURISTIC_ONLY`，并新增 [`test_round5_strict_heuristic_grading_note_propagation_composite_state_and_zero_cite_export()`](../../../tests/integration/test_final_blocker_closure.py#L1374-L1561) 完整覆盖 5 大回归场景（申请 vs 获得专利含数字/纯概念判定、2 词域词重合、仅 `note_zh` 启发式传播、混合裁剪+启发式 `PARTIAL_PRUNED_HEURISTIC` 全链条双重警示、已拒答行 & `citations_json=[]` 空引用行被投毒 `obsidian_markdown` 在历史/备份导出/备份恢复/Obsidian ZIP 全部清除）。
4. [`tests/integration/test_codex_review_remediation.py`](../../../tests/integration/test_codex_review_remediation.py) — `test_n3` Case (b) 合成压力夹具改在 `answer_zh` 承载大容量测试文本（全部断言保持不变）。
5. [`frontend/src/workspace/ManualUxRemediation.test.tsx`](../../../frontend/src/workspace/ManualUxRemediation.test.tsx) — `P1-F03-B` 单测新增 `PARTIAL_PRUNED_HEURISTIC` 与 `PARTIAL_PRUNED + contains_heuristic_claims=true` 病例，实证双徽章同时呈现且永不出现「结论已受证据支持」。

---

## 4. 远端 GitHub Actions CI（Run `45780647653` — `attempt = 1` · 14/14 全部通过）

- **Workflow**：`Public Beta CI`（`pull_request` on Draft PR [#50](https://github.com/huangbuqubunao-alt/intelligence/pull/50)）
- **Run ID / URL**：[`45780647653`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653)
- **headSha**：`0ad549b9ea20b0ef3492f576f2010a68e8eddf9a`
- **总结论**：**`success`（`attempt = 1`，14 / 14 全部一次通过，零失败重跑）**

| # | Job 名称 | Job ID | 结论 | 链接 |
|---|---|---|---|---|
| 1 | Frontend Build & Vitest | `139774980296` | `success` | [Job 139774980296](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980296) |
| 2 | Python Full Unit Suite (Shard 1/4, ex-GOV-001) | `139774980548` | `success` | [Job 139774980548](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980548) |
| 3 | Python Lint, Typecheck & Public Beta Integration | `139774980626` | `success` | [Job 139774980626](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980626) |
| 4 | Python Full Unit Suite (Shard 3/4, ex-GOV-001) | `139774980638` | `success` | [Job 139774980638](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980638) |
| 5 | Python Full Integration & E2E Suite (Shard 4/8) | `139774980639` | `success` | [Job 139774980639](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980639) |
| 6 | Python Full Integration & E2E Suite (Shard 2/8) | `139774980676` | `success` | [Job 139774980676](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980676) |
| 7 | Python Full Unit Suite (Shard 0/4, ex-GOV-001) | `139774980704` | `success` | [Job 139774980704](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980704) |
| 8 | Python Full Unit Suite (Shard 2/4, ex-GOV-001) | `139774980732` | `success` | [Job 139774980732](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980732) |
| 9 | Python Full Integration & E2E Suite (Shard 6/8) | `139774980756` | `success` | [Job 139774980756](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980756) |
| 10 | Python Full Integration & E2E Suite (Shard 1/8) | `139774980765` | `success` | [Job 139774980765](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980765) |
| 11 | Python Full Integration & E2E Suite (Shard 7/8) | `139774980775` | `success` | [Job 139774980775](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980775) |
| 12 | Python Full Integration & E2E Suite (Shard 0/8) | `139774980812` | `success` | [Job 139774980812](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980812) |
| 13 | Python Full Integration & E2E Suite (Shard 3/8) | `139774980830` | `success` | [Job 139774980830](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980830) |
| 14 | Python Full Integration & E2E Suite (Shard 5/8) | `139774980932` | `success` | [Job 139774980932](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45780647653/job/139774980932) |

---

## 5. 本地全量实测证据与预览服务

- **本地静检、清单与 14 组核心后端套件（on `0ad549b9` 同等源码）**：
  - `.venv/bin/ruff check src tests scripts` → `All checks passed!`
  - `.venv/bin/mypy src` → `Success: no issues found in 138 source files`
  - `.venv/bin/python scripts/ci_test_manifest.py verify` → `CI manifest verified: total_collected=7399 unit_files=133 integration_files=132 unit_runnable=3990 integration_runnable=3198 total_runnable=7188 gov001_excluded=190 capacity_excluded=21`
  - 14 组后端核心集成/单元测试套件 → **`178 passed in 528.60s`**（`0 failed`、`0 skipped`）
- **前端构建与全量 Vitest**：
  - `cd frontend && npm run typecheck && npm run build && npm test -- --run` → `tsc -b` 0 报错、`vite build` `built in 799ms`、Vitest **`Test Files 58 passed (58)`、`Tests 1280 passed (1280)`**
- **本地预览服务**：`http://127.0.0.1:8792/` 已重启运行于 `0ad549b9`（包含最新前端构建产物），健康探活 HTTP **`200`**。
- **合规红线核验**：全程未访问真实用户 Cookie、未调用付费云模型、未写入真实 Obsidian Vault、未招募真实用户、未修改 `main`、未开启 auto-merge；**Gate R1 保持 `HOLD`**，等待独立 Reviewer 第六轮终审放行及项目所有者批准合并。
