# Intelligence 第六轮定向终审唯一残余问题收口报告（Round 6 Targeted Sign-off Report）

> **工作分支**：`antigravity/remediation-20261125`（线性基于 `origin/main@d1b58f731adc4185fe78cc5538e9e211b8a0e211`，`main` 零改动）
> **Draft PR**：[#50 — antigravity/remediation-20261125 -> main](https://github.com/huangbuqubunao-alt/intelligence/pull/50)（`isDraft: true`，未开启 auto-merge，无冲突 `mergeable=true`）
> **最新 `VERIFIED_CODE_SHA`（代码与 14/14 一次全绿 CI 验证基线）**：`78b7da91cf689a2e4322ea8f349a6c11ac17243c`
> **前序基线**：`0ad549b9ea20b0ef3492f576f2010a68e8eddf9a`（第 5 轮代码）/ `dd809060104c9818a156b18ebe60c3c99c6fbfe5`（第 5 轮文档）
> **双 SHA 零代码差异规则**：本报告与更新后的 [`FINAL_BLOCKER_CHECKPOINT.md`](FINAL_BLOCKER_CHECKPOINT.md) 构成紧随 `78b7da91cf689a2e4322ea8f349a6c11ac17243c` 的纯文档交付提交 `DOCS_DELIVERY_SHA`，满足 `git diff --stat 78b7da91cf689a2e4322ea8f349a6c11ac17243c..HEAD -- src frontend tests scripts .github` 严格为空。
> **Gate R1 最终裁决**：**`HOLD`（第 6 轮定向终审唯一的剩余子项 `3/6-A` 确定性归一化口径错误已精准修复，六项放行门禁全部关闭；等待独立 Reviewer 定向核签与项目所有者人工批准合流 `main`，严禁自动合流）**。

---

## 1. 定向核签唯一定向修复说明（`dd809060..78b7da91`，仅改 2 个文件）

1. **修复比较基准与事实限定词归一化越界（[`src/youtube_intel/workspace_intelligence_hub.py#L1760-L1775`](../../../src/youtube_intel/workspace_intelligence_hub.py#L1760-L1775)）**：
   - 将 `_EXACT_GLUE_CHARS_RE` 从 `r"(?:同比|环比|共|约|为|是|的|了)"` 严格收窄为仅剥离中性句法虚词 `r"(?:为|是|的)"`，彻底保留 `同比`、`环比`、`约`、`共`、`了` 等决定经济比较口径与确数/约数的事实限定词。
   - 同步收窄 `_EXACT_CANON_PAIRS`，移除跨指标口径或否定态归并项（如 `销售额->收入`、`客单价->售价`、`仍不/还不/不支持->尚未`），仅保留同指标同义词与趋势词映射（`营收->收入`、`上涨/上升/提升->增长`、`下滑/下跌/减少->下降`）。
   - 未触碰前端、授权系统、采集入口、媒体安全、备份导出、CI 配置与概念词典。

2. **对照回归测试覆盖（[`tests/integration/test_final_blocker_closure.py#L1068-L1070,L1406-L1520`](../../../tests/integration/test_final_blocker_closure.py#L1406-L1520)）**：
   - 补齐 5 组限定词对照反例，实证均严格降级为 `HEURISTIC_ONLY`（绝不获 `EXACT_SUPPORTED`）：
     1. `「公司收入环比增长 5% [E1]。」` vs 原文 `「公司收入同比增长 5%。」`（同比 vs 环比）
     2. `「公司收入同比增长 5% [E1]。」` vs 原文 `「公司收入环比增长 5%。」`（环比 vs 同比）
     3. `「2025年公司营收增长 5% [E1]。」` vs 原文 `「2025年公司收入同比增长 5%。」`（遗漏 `同比`）
     4. `「2025年公司收入同比增长 5% [E1]。」` vs 原文 `「2025年公司收入增长 5%。」`（虚增 `同比`）
     5. `「产品售价 50 美元 [E1]。」` vs 原文 `「产品售价约 50 美元。」`（删去 `约`）
   - 同步验证口径完全一致的同义表述 `「2025年公司营收同比增长 5% [E1]。」` vs 原文 `「2025年公司收入同比增长 5%。」` 稳定通过为 `EXACT_SUPPORTED` / `SUPPORTED`；端到端 `ask_research_question`（`R6_YOY_VS_MOM`）在面对原文「同比」输出「环比」时，返回 `fact_verification_state == "HEURISTIC_ONLY"`、`contains_heuristic_claims is True`，且 Markdown 输出 `启发式相关性提示`。
   - 原 `NOTE_SMUGGLE` 夹具因回答 `「2025年公司营收增长 5% [E1]。」` 客观省略了原文中的 `同比` 且其 `note_zh` 被裁剪，现严格断言复合态 `PARTIAL_PRUNED_HEURISTIC` 与 `contains_heuristic_claims is True`。

---

## 2. 远端 GitHub Actions CI（Run `45789204307` — `attempt = 1` · 14/14 全部通过）

- **Workflow**：`Public Beta CI`（`pull_request` on Draft PR [#50](https://github.com/huangbuqubunao-alt/intelligence/pull/50)）
- **Run ID / URL**：[`45789204307`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307)
- **headSha**：`78b7da91cf689a2e4322ea8f349a6c11ac17243c`
- **总结论**：**`success`（`attempt = 1`，14 / 14 全部一次通过，零失败重跑）**

| # | Job 名称 | Job ID | 结论 | 链接 |
|---|---|---|---|---|
| 1 | Python Lint, Typecheck & Public Beta Integration | `139803636853` | `success` | [Job 139803636853](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803636853) |
| 2 | Python Full Integration & E2E Suite (Shard 4/8) | `139803637121` | `success` | [Job 139803637121](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637121) |
| 3 | Python Full Integration & E2E Suite (Shard 0/8) | `139803637138` | `success` | [Job 139803637138](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637138) |
| 4 | Python Full Unit Suite (Shard 2/4, ex-GOV-001) | `139803637170` | `success` | [Job 139803637170](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637170) |
| 5 | Python Full Integration & E2E Suite (Shard 7/8) | `139803637173` | `success` | [Job 139803637173](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637173) |
| 6 | Python Full Integration & E2E Suite (Shard 2/8) | `139803637198` | `success` | [Job 139803637198](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637198) |
| 7 | Python Full Integration & E2E Suite (Shard 1/8) | `139803637214` | `success` | [Job 139803637214](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637214) |
| 8 | Python Full Unit Suite (Shard 0/4, ex-GOV-001) | `139803637233` | `success` | [Job 139803637233](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637233) |
| 9 | Frontend Build & Vitest | `139803637280` | `success` | [Job 139803637280](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637280) |
| 10 | Python Full Unit Suite (Shard 3/4, ex-GOV-001) | `139803637293` | `success` | [Job 139803637293](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637293) |
| 11 | Python Full Integration & E2E Suite (Shard 6/8) | `139803637294` | `success` | [Job 139803637294](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637294) |
| 12 | Python Full Integration & E2E Suite (Shard 3/8) | `139803637295` | `success` | [Job 139803637295](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637295) |
| 13 | Python Full Unit Suite (Shard 1/4, ex-GOV-001) | `139803637357` | `success` | [Job 139803637357](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637357) |
| 14 | Python Full Integration & E2E Suite (Shard 5/8) | `139803637424` | `success` | [Job 139803637424](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45789204307/job/139803637424) |

---

## 3. 本地验证与服务状态

- **本地静检、清单与 6 组核心事实核验回归套件（on `78b7da91`）**：
  - `.venv/bin/ruff check src tests scripts` → `All checks passed!`
  - `.venv/bin/mypy src` → `Success: no issues found in 138 source files`
  - `.venv/bin/python scripts/ci_test_manifest.py verify` → `CI manifest verified: total_collected=7399 unit_files=133 integration_files=132 unit_runnable=3990 integration_runnable=3198 total_runnable=7188 gov001_excluded=190 capacity_excluded=21`
  - 6 组集成测试套件（`test_final_blocker_closure.py`, `test_codex_round3_remediation.py`, `test_grounding_refusal_eval.py`, `test_research_adversarial.py`, `test_research_backup_restore.py`, `test_workspace_intelligence_hub.py`）→ **`95 passed in 151.10s`**（`0 failed`、`0 skipped`）
- **本地预览服务**：`http://127.0.0.1:8792/` 已重启运行于 `78b7da91`，HTTP **`200`**。
- **合规红线与最终状态**：零真实个人 Cookie / 付费云模型 / 真实 Vault / 真人招募，未修改 `main`，未开启 auto-merge；**Gate R1 保持 `HOLD`**。
