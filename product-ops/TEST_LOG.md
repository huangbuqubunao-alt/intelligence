# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-24（`Asia/Shanghai` · Iteration #11 / Codex Round 2 全量闭环）
- **当前活跃基线**：研发分支 `antigravity/task-user-readiness-20261112@ce6f8dcc`（待创始人合流决策）；公开主线当前仍为 `main@d1b58f7`（docs-only 跟随提交；上一次云端 CI [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 对应代码为 `main@4f3fe70`，涵盖当年 14 组核心公开测试子集 + 57 文件前端）。
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览（研发分支 `antigravity/task-user-readiness-20261112@ce6f8dcc`）

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-24） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（默认 CI 命令全绿 + 10x 稳定性）** | `cd frontend && npx tsc --noEmit --incremental false && npm run build && npx vitest run` + `App.content-status-load.test.tsx` x10 | `tsc --noEmit` 0 错 / `vite build` **`1.38s`** / 默认并发 Vitest **`Test Files 57 passed (57)` / `Tests 1259 passed (1259)` in `65.21s`**（同步解决 2s 轮询重置分页与 200 卡超时抖动）；`App.content-status-load.test.tsx` **`10/10` 连续通过**（17/17 each）。 |
| **2. 浏览器真实端到端 E2E（已公开基线 `b28ba5d`/`4f3fe70` 实机双端口）** | **PASS（Iteration #10 `8793` + `8794`；本轮 `d36cfe55` 前端改动待合流后可选复走）** | 隔离 Chromium 实机走查 `http://127.0.0.1:8793`（Demo）与 `http://127.0.0.1:8794`（355 条库）+ 桌面 `1440×900` / 移动 `375×812` / 双主题 | Iteration #10 全部核心流程 PASS（`0` console error / `0` HTTP `>=400` / `0px` 溢出）；Iteration #11 新增前端 2s 轮询保页与 Demo 引导隔离均由 `CodexReviewRemediation.test.tsx` (`10/10`) 单元测试覆盖。 |
| **3. 后端静态检查与类型安全** | **PASS（`ce6f8dcc` 最终代码）** | `uv run --frozen ruff check --no-cache src tests scripts && uv run --frozen mypy --no-incremental --cache-dir=/dev/null src` | 本地实跑通过：`ruff`: **`All checks passed!`**；`mypy`: **`Success: no issues found in 137 source files`**。 |
| **4. 后端核心公开子集与全仓分片 CI（`7,124` 项 Python 测试）** | **PASS（分支实测全绿 · `.github/workflows/ci.yml` 已接入全量分片，待合流 `main` 上云）** | 14 组 `python-ci` 公开子集 + 4 分片 `python-unit-full` + 8 分片 `python-integration-full` | · **14 组 `python-ci` 公开测试子集（`d36cfe55`）**：**`181 passed in 686.65s (0:11:26)`**；`ce6f8dcc` 补充要点水合修复后复测 `test_codex_review_remediation.py` + `test_grounding_refusal_eval.py` **`32 passed in 127.76s`**（`python-ci` 现收录 **`182` 项**）；<br>· **全仓分片本地实跑（剔除 `GOV-001` 与外部 worktree 依赖前核验）**：Unit 4 分片 **`3,954 passed, 1 skipped, 2 deselected`**；Integration+E2E+Scripts 4 分片 **`3,166 passed`** + 隔离 `test_fast_read_api.py` **`2/2` (`137.97s`)**；`test_local_capacity_composition.py` (`--deselect`) **`28 passed, 1 deselected`**；<br>· **Expanded `.github/workflows/ci.yml` 总覆盖**：`python-unit-full`（`3,955` 项）+ `python-integration-full`（`3,169` 项）= **`7,124` 项**（`GOV-001` 6 文件 `211` 项 + 2 密封单测与 `21` 项外部 `CAPACITY_BASELINE_ROOT` 测试已透明披露）。 |
| **5. 按需本地视频关键帧融合与恢复专项（`BL-011` + `N3`/`N6`/`N7`）** | **PASS** | `test_visual_keyframe_analysis.py` + `test_codex_review_remediation.py` + `ce6f8dcc` 前置 `tests/integration` 分片 | 40 MiB/64 MiB 分级裁剪、`gen-<uuid>` 原子目录回收及无 Sidecar/恢复一致性均纳入全量集成测试与 CI 守卫并通过。 |
| **6. 大库列表性能、TOCTOU 屏障与连接/延迟守卫（`P1-1`/`P1-3`）** | **PASS** | `test_cross_source_markdown_and_scale.py` + `test_fast_read_api.py` + `test_codex_review_remediation.py` | `list_research_sessions()` 600 条历史会话由全表解码改为轻量查询 + 单事务批量核验 + LRU 缓存 **`<300ms`**；`_connect_read` 改 `.as_uri()`；`/api/v1/dashboard` 无 Sidecar `fast == raw` 一致性修复后独跑 `2/2` 与 14 组 `181 passed` 全通过。 |
| **7. 反幻觉逐句清洗、要点水合、`qwen3.5:9b` `EXP-002` 与 SSRF/解码（`P0-1`/`P2-1`–`P2-8`）** | **PASS（含真实本机 `qwen3.5:9b` 100% 实测）** | `test_grounding_refusal_eval.py` + `test_codex_review_remediation.py` + 隔离本机 `ollama/qwen3.5:9b` (`EXP-002`) | · **规则与测试**：全角/小写/空格 `[E*]`、内联清单、Markdown 表格行、`answerable` 严格布尔、要点/行动引用水合（`ce6f8dcc`）、GB18030/UTF-16 本地导入、SSRF/DNS 重绑定/`4 MiB` 封顶/`http_proxy` 绕过与原子 `422 RESTORE_INVALID_PAYLOAD` 恢复全部通过（`32/32`）；<br>· **真实 `ollama/qwen3.5:9b` (`$0`, `253.92s`)**：**3/3 (100%) `GROUNDED`**、**2/2 (100%) 拒答**、**13/13 (100%) 逐句引用命中**、**18/18 (100%) 要点/行动引用命中**（`out_of_range_refs=0`），Obsidian ZIP 全部 5 篇 `04-跨视频深度问答/*.md` 含 `ev:`。 |
| **8. 数据库热快照、原子备份配置与并发竞争** | **PASS** | `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` + `test_codex_review_remediation.py` | `cloud_daily_call_limit` 备份恢复闭环、预校验与单事务写回、`BEGIN IMMEDIATE` 与 `_complete_json` 并发竞争锁均全通过。 |
| **9. 安全基线扫描 & 零个人路径/邮箱泄漏（`P2-12` 选项 B）** | **PASS（分支最终树复扫）** | `bash scripts/security_scan.sh`、`git grep`、`.git` 日报哈希比对 `git diff 8e63e04 -- product-ops/reports/daily/2026-11-23.md` | · 完成 `995` 份历史追踪文件（`agent-prompts/`/`docs/`/`handoffs/`/`tasks/`/`scripts/`/`qa/`）当前工作树脱敏（`7a3a0556`），全仓库 `git grep` 个人路径/邮箱/主机名 **`0` 命中**；<br>· `scripts/security_scan.sh` 输出 **`status=findings count=17`**：实为 `16` 条预置假密钥/假带凭据 URL 测试哨兵 + `1` 条历史集合清单日志行 [`full-suite-collection.txt:3938`](../docs/validation/dogfood-day2-d2-02/full-suite-collection.txt)，**`src/`、`frontend/`、`scripts/`、`product-ops/` 全区 `0` 告警**；<br>· `product-ops/reports/daily/2026-11-23.md` 与 `8e63e04` diff 为空。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`main@4f3fe70` CI [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 为历史 14 组基线 · 分支 `7,124` 项待合流触发云端 CI / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：已公开主线 `main@d1b58f7` 承接自 `4f3fe70`（14 组核心公开子集 [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 双绿：`175` 后端 + `1257` 前端）；研发分支已扩展至 `7,124` Python + `1,259` Vitest + `tsc` 全量分片 CI，待合流 `main` 验证云端运行；<br>· Windows WSL2 实机：**`NOT_TESTED`**（无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，严禁绕过）。 |

---

## 二、Stage A 实机发现缺陷与 Stage D 关闭对照（严守复盘真实性）

| Defect ID | Stage A 首测状态 | 复现步骤与现象证据 | Stage D 修复后验证（`fee43f4`） |
|---|---|---|---|
| **QA-A01** | **FAIL (P0)** | Demo 模式在 `#Research` 问“量子引力场在火星大气层的实测数值是多少？”返回 `200` + `GROUNDED` + 3 条无关引用 | **PASS**（新增全词边界匹配与中文停用切分；Chromium 实机与集成测试确认 `REFUSED_INSUFFICIENT_EVIDENCE` + 0 citations） |
| **QA-A02** | **FAIL (P0)** | macOS 用户运行 `youtube-intel start` 并在浏览器点击 `+ 导入 → 本地文件`，因 `/local/native/capability = false` 导致文件选择完全锁死 | **PASS**（保留原生警告合约下新增浏览器回环上传恢复按钮，Chromium 实机上传 `verify-note.md` HTTP `201` 并打开正文） |
| **QA-A03** | **FAIL (P0)** | 全新空库初访 `#Settings` 因 `hub.sqlite3` 尚未生成而误报 `⚪ 待检查模型就绪状态` 与底层安装提示矛盾 | **PASS**（`prepare_local_workspace` 调用 `hub.ensure_ready()`；实机 `#Settings` 即时亮绿 Ollama 状态并收起工程诊断） |
| **QA-A04** | **FAIL (P1)** | 空库 `#Research` 允许盲点提问引发 HTTP `409 Conflict`，`#Topics`/`#Intelligence` 缺导入按钮，Import 弹窗不支持 `Escape`，移动端 `.nav-item` 仅 `34px` | **PASS**（空库禁用 Ask 并带一键导入 CTA，实现 `0` 笔 `409`；弹窗 `Escape` 关闭后 `[role="dialog"] = 0`；移动导航 `>= 40px`、`0px` 横向溢出） |
| **GOV-001** | **BLOCKED (历史设计行为)** | 190 项历史封存试跑夹具因代码哈希推进继续保持 Fail-Closed，非本次回归，按项目规范不解锁不篡改 | **持续保留**（已在 `ci.yml` 与 `RELEASE_CHECKLIST.md` 透明披露） |
| **EXP-001 真人实测** | **NOT_TESTED / HOLD** | 当前处于内部自主迭代阶段，禁止招募或联系真实用户 | **等待未来阶段授权**（不以 AI 模拟结论冒充通过） |
