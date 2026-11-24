# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-24（`Asia/Shanghai`）
- **当前活跃基线**：开发分支 `antigravity/task-user-readiness-20261112`（已在 `c16f0e8` 基础上完成 Claude Round 1 `Conclusion B` 全部 `N1`–`N11` 缺陷修复，对比公开主线 `main@ca4e17f`）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览（Round 2 修复 `N1`–`N11` 后）

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-24） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Round 2 最终改动后）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 耗时 `770ms` 零报错**；全量 Vitest **`Test Files 57 passed (57) / Tests 1257 passed (1257)`**（耗时 `55.92s`，`0 failed`, `0 skipped`，含 `CodexReviewRemediation.test.tsx` **`8/8`**，新增验证 `#Content` 搜索结果超过 100 条分页 `100 / 140` + 续拉及 `⌘K` `库内命中共 85 条` 截断提示）。 |
| **2. 浏览器真实端到端 E2E** | **PASS (Round 1 `c16f0e8`) · `NOT_TESTED` (Round 2 `N10` 改动后未重跑)** | 此前在隔离测试服务 `http://127.0.0.1:8794`（`1440×900`）验证（Iteration #10 Round 1） | Round 1（`c16f0e8`）在 `8794` 实机通过：`#Research` 切换立即刷新（`P2-05`）、`⌘K` 切专题清锁（`P1-15`）、第 31 段直达（`P1-06`）、`#Content` 搜索（`P1-12`）、Keyframe Lightbox + `Escape` 焦点归还（`P2-03`），`0` console error / `0` HTTP `>=400` / `0px` 溢出。<br>**透明边界**：Round 2 改动 `App.tsx` / `CommandPalette.tsx` 及后端后，未重新拉起 `8794` 端口实机浏览器复验（已由 `CodexReviewRemediation.test.tsx` jsdom 集成测试覆盖）。 |
| **3. 后端静态检查与类型安全** | **PASS（Round 2 最终改动后）** | `uv run ruff check --no-cache src tests scripts && uv run mypy --no-incremental --cache-dir=/dev/null src` | Round 2 最终修改后实跑：`ruff`: **`All checks passed!`**；`mypy`: **`Success: no issues found in 137 source files`**。 |
| **4. 后端合同与核心及恢复集成套件（14 组 CI + 2 组恢复共 16 组 Pytest）** | **PASS（Round 2 最终改动后）** | `.github/workflows/ci.yml` 全部 14 组套件 + `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` 顺序无干扰独跑 `-q --tb=short` | **16 组套件一次性全绿：`200 passed in 595.70s (0:09:55)`**（`0 failed`, `0 skipped`，含第 14 组 `test_codex_review_remediation.py` **`21/21`**；注：曾检出一次 `N1` 逗号放行导致既有跨视频测试失效及冷 `/api/v1/dashboard` 连接增至 `4` 条，以及 `test_fast_read_api` 一次 `161.5ms` 波动，已全部通过 `get_video_briefs_map(repo_conn=...)` 连接复用与实质引用子句判定修复并在纯净环境下顺序重跑 16 组全绿）。 |
| **5. 按需本地视频关键帧融合与恢复专项（`BL-011` + `N3`/`N6`/`N7`）** | **PASS（合成测试，Round 2 真 Ollama 未重跑）** | `test_visual_keyframe_analysis.py` + `test_codex_review_remediation.py`（`N3`/`N6`/`N7`） | · 全部计入上述 `200 passed`：超过 `40 MiB` 关键帧预算（`VISUAL_BUDGET_EXCEEDED`）与接近 `64 MiB` JSON 总上限（`BACKUP_SIZE_BUDGET_EXCEEDED`）时自动平滑降级部分图片并完整保留全部摘要/问答/配置且通过 `64 MiB` 导入往返恢复；单视频分析串行锁与跨提交后过期 `gen-*` 目录自动清理；`ollama /api/show` 先行能力探测 + 去除 `[:8]` 截断。<br>· 真实本机 `ollama/gemma3:4b` 实机与 `8796` 演示证据来自 Iteration #8（Round 2 未重连真模型）。 |
| **6. 大库分页、全库搜索、TOCTOU 屏障与连接/延迟守卫** | **PASS（Round 2 最终改动后）** | `test_cross_source_markdown_and_scale.py` + `test_fast_read_api.py` + `test_codex_review_remediation.py` | 320 条库 `?q=` 全库、`?limit=200&offset=200` 分页及 300 同步除限全通；`get_video_briefs_map` 复用 `repo_conn` 与按需免读正文修复后，`/api/v1/dashboard` 与全冷读路由严格维持 `<= 3` SQLite 连接且低于 `120ms` 预算（`test_fast_read_api.py` 计入上述 `200 passed`；注：此前 Round 1 隔离 40 视频 5 轮中位为 `41.393ms`，Round 2 未单独重做 5 轮中位微基准）。 |
| **7. 反幻觉评测、混合拒答与 Obsidian 复核（`N1`/`N2`/`N4`/`N5` + `EXP-002`）** | **PASS（合成测试，Round 2 最终改动后）** | `test_grounding_refusal_eval.py`（`32` 例）+ `test_public_beta_demo_showcase.py` + `test_codex_review_remediation.py` | `[E88]`/`【E77】`/`[ E88 ]`/`[E88,E1]`/`(E88)`/裸 `E88` 全识别剥离且不再遗留悬空假断言或存根（含全历史/导出 Markdown 检查）；文本笔记错位时取消回退首段改标 `NEEDS_REVERIFICATION`；恢复后摘要/问答及其 Obsidian Markdown / `.zip` 导出强制重建并带复核告警与清除不可信摘录；Demo 去除 `0.65` 放行率彻底拒绝复合诡计题并全部放行推荐问题。 |
| **8. 数据库热快照、迁移、预算并发竞争与传输安全（`N8`/`N9`）** | **PASS（Round 2 最终改动后）** | `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` + `test_codex_review_remediation.py` | 移除 `_STDLIB_URLOPEN` 探测开关，生产默认无 `_http_opener` 路径强制经过 `_NoCloudRedirect` 且实证拦截重定向；双 `WorkspaceIntelligenceHub` 实例并发多线程（`Barrier(8)`）竞争每日预算严格放行配额次数并阻断超额请求。 |
| **9. 安全基线扫描 & 零个人目录泄漏（`N11`）** | **PASS（Round 2 台账同步与还原后）** | `bash scripts/security_scan.sh`、个人主目录绝对路径排查、`git diff 8e63e04 -- product-ops/reports/daily/2026-11-23.md` | 已还原 `product-ops/reports/daily/2026-11-23.md` 至 `8e63e04` 基线；`product-ops/` 零个人主目录路径泄漏；`security_scan.sh` 仅余历史测试哨兵 17 条，Round 2 全量改动 **0 告警**。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@ca4e17f` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest`（`c54b818` [`#45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) · `main@ca4e17f` [`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703)） / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：此前 `c54b818` 运行 [`#45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) 首轮 Python 作业因 `test_fast_read_api.py` 实测 `149.3ms > 120ms` 失败，未放宽阈值重跑全绿；随后合入并收口的 `main@ca4e17f` 运行 [`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703) 首次执行全绿。Iteration #10 Round 2（含第 14 组 `test_codex_review_remediation.py` `21/21`）已完成本地 16 组 `200 passed`，待 Claude Round 2 复核及 `FD-009` 批复合流后再上云跑批；<br>· Windows WSL2 实机：**`NOT_TESTED`**（无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，严禁绕过）。 |

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
