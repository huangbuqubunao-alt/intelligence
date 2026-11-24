# 阶段退出检查单与合流门禁（Release & Stage Exit Readiness Gate）

- **更新日期**：2026-11-24（`Asia/Shanghai` · Iteration #11 / `BL-014`）
- **评估对象分支与主线**：研发分支 `antigravity/task-user-readiness-20261112@ce6f8dcc`（Codex Round 2 全量闭环待合流；当前公开主线仍为 `main@d1b58f7`，前置 CI 绿标代码基线 `main@4f3fe70` [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823)，严守被动 `PUBLIC`、零外宣、无 GitHub Release、保留 4 个历史 tag）
- **门禁用途**：记录 Iteration #11（Codex Round 2 审查全部 `P0-1`/`P1-1..4`/`P2-1..13` 闭环、995 文件脱敏、`7,124` 项 CI 分片扩展与 `qwen3.5:9b` `EXP-002` 100% 逐句/要点引用实测）的内部退出就绪度，并支撑后续 `main` 合流与未来 `EXP-001` 审批决策。

---

## 一、六维退出检查单（严格四态与实测归因）

| 检查维度 | 当前状态 | 核验依据与实测数据 | 已知边界 / 未关闭风险 |
|---|---|---|---|
| **1. 核心多源研究闭环** | **PASS** | `youtube-intel start` 零配置冷启动 + `--check-only` 全量识别本地模型并用 `/api/show` 精准标出 Vision 能力；支持 YouTube、B 站 `BV`、本地音视频（`<=4h` / `<=2GiB`）与本地 `.md`/`.txt`（含 **UTF-8 / GB18030 / UTF-16 BOM** 与保留后缀截断及 `verify_source` 权威一致）；跨源 FTS5 启用 CJK 2-gram 索引与全库召回；内容页 `?q=`、分页与 `⌘K` 齐全。 | 非 WSL 原生 Windows 受限于 `fcntl` 不可用（已有明确错误引导，非静默崩溃）。 |
| **2. 反幻觉防线与 Fail-Closed 安全隔离** | **PASS（含真实本机 `qwen3.5:9b` 逐句 100% 实测）** | 无条件逐句/内联清单/Markdown 表格行无据剥离（支持全角/小写/空格 `[E*]` 与 `"answerable"` 严格布尔），历史回读/备份恢复统一重剪枝，要点与行动建议跨句引用自动水合（`ce6f8dcc`）；Demo 拦住「多少钱」与反向否定前提；真实 `ollama/qwen3.5:9b` `EXP-002` 重测 **3/3 `GROUNDED` + 2/2 拒答 + 13/13 (100%) 逐句引用 + 18/18 (100%) 要点/行动引用**；BYOK 防 DNS 重绑定/非规范 IP SSRF/`nip.io`/`CGNAT`、4 MiB 上限与回环直连绕过 `http_proxy`；`security_scan.sh` 对 `src/`、`frontend/`、`scripts/`、`product-ops/` 全区 **0 告警**（基线 `count=17` 全在历史测试哨兵及集合日志）。 | 真实长视频在多变外网字幕格式下的泛化幻觉率尚待未来真实用户场景验证（内部仅实测合成测试与本机 `qwen3.5:9b` 双语盲测样本）。 |
| **3. 大库容量、4 小时课程、关键帧备份还原与导出可靠性** | **PASS** | `list_research_sessions()` 轻量排序 + 单事务批量核验 + LRU 缓存（600 会话 `<300ms`）；`_connect_read` 使用 `.as_uri()` 防特殊路径失败；备份恢复导回含 `cloud_daily_call_limit` 与原子 `engine_config` 事务写入、预校验返回 `422 RESTORE_INVALID_PAYLOAD`；40 MiB/64 MiB 关键帧分级裁剪与单视频 `gen-<uuid>` 锁；`.zip` 解压与大小写碰撞安全。 | Windows 物理机及长期海量关键帧主动清理策略尚未在实机实测。 |
| **4. 前端可用性、双主题与响应式无障碍** | **PASS** | 本地默认并发（无线程降限）`npx tsc --noEmit` 0 错 + `vite build` `1.38s` + Vitest **`57/57` / `1,259/1,259` passed (`65.21s`)** + `App.content-status-load.test.tsx` 10/10 连续全绿；修复 2s 轮询保持第 2 页/远程搜索、`⌘K` 立即清空过期计数与 Demo/真实工作区引导隔离；前置基线 `8793`/`8794` 实机浏览器通过（`0` console error / `0px` 溢出）。 | 真视觉模型 `ollama/gemma3:4b` 对低分辨率或强遮挡复杂课件的 OCR 精细度依赖本机视觉模型能力上限。 |
| **5. 跨平台及外部受控环境兼容性** | **PARTIAL / KNOWN LIMIT** | 研发分支 `.github/workflows/ci.yml` 已从 `14` 组核心公开子集（`182` 项）扩展至 **4 分片 `python-unit-full`（`3,955` 项）+ 8 分片 `python-integration-full`（`3,169` 项）= `7,124` 项 Python CI 覆盖**（并在 `RELEASE_CHECKLIST.md` 公开披露 `GOV-001` 与外部 worktree 测试）；本地实跑分片+核心套件全部通过，待合流 `main` 触发全量云端 Actions 绿标（当前 `main@d1b58f7` 持有的云端 CI [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 为原 `main@4f3fe70` 14 组基线）。 | ① **Windows WSL2 实机：`NOT_TESTED`**（无物理环境）；<br>② **公网免 Cookie YouTube 抓取：`BLOCKED`**（触发平台反机器人核验，严格不绕过）；<br>③ **安装包分发 (`BL-009`)**：维持 `HOLD`。 |
| **6. 创始人 L3 治理与零隐私遥测边界** | **PASS（995 份历史文件当前树脱敏 · `EXP-001` 维持 `HOLD`）** | `agent-prompts/`/`docs/`/`handoffs/`/`tasks/`/`scripts/`/`qa/` 共 995 份追踪文件完成当前工作树个人路径/邮箱/主机名脱敏（`7a3a0556`，全仓库 `git grep` `0` 匹配）；`product-ops/reports/daily/2026-11-23.md` 与 `8e63e04` 一致；Zero-Telemetry 零外部上报；仓库严守被动 `PUBLIC`、`0` GitHub Release。 | **研发分支合流 `main`（上云跑 `7,124` 项全量 CI）**与**外部真人试跑（`EXP-001`）**均为 L3 门禁，未获明确批复前不执行。 |

---

## 二、真实外部指标清单（严守零伪造）

- **真实外部用户激活率 / Day-7 留存率 / NPS / 真实付费转化率**：**`当前不可评估`**（内部迭代阶段禁止接触或招募任何真实用户）。
- **结论摘要**：当前产品在**内部工程质量、反幻觉与 Fail-Closed 安全、600 条大库与 4 小时课程/300KB 长文本扩展、以及 Obsidian `.zip` 真实解压可用性**上均已达到 **内部完备标准（Internal Exit Ready）**；下一步产品价值是否成立，取决于后续获批进入真实用户测试（`EXP-001`）后的实际留存反馈。
