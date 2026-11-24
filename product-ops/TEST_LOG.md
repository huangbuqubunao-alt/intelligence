# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-24（`Asia/Shanghai`）
- **当前活跃基线**：开发分支 `antigravity/task-user-readiness-20261112`（已在 `0519284` 基础上完成 Claude Round 2 复核 `R2-D1` & `R2-D2` 闭环修复，对比公开主线 `main@ca4e17f`）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览（Round 3 修复 `R2-D1` & `R2-D2` 后）

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-24） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Round 2 最终前端改动后 · Round 3 前端零改动）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 耗时 `770ms` 零报错**；全量 Vitest **`Test Files 57 passed (57) / Tests 1257 passed (1257)`**（耗时 `55.92s`，`0 failed`, `0 skipped`，含 `CodexReviewRemediation.test.tsx` **`8/8`**，覆盖 `#Content` 搜索超过 100 条分页续拉与 `⌘K` 总命中截断提示）。 |
| **2. 浏览器真实端到端 E2E** | **PASS (Round 1 `c16f0e8`) · `NOT_TESTED` (Round 2/3 未重跑实机)** | 此前在隔离测试服务 `http://127.0.0.1:8794`（`1440×900`）验证（Iteration #10 Round 1） | Round 1（`c16f0e8`）在 `8794` 实机通过：`#Research` 切换立即刷新（`P2-05`）、`⌘K` 切专题清锁（`P1-15`）、第 31 段直达（`P1-06`）、`#Content` 搜索（`P1-12`）、Keyframe Lightbox + `Escape` 焦点归还（`P2-03`），`0` console error / `0` HTTP `>=400` / `0px` 溢出。<br>**透明边界**：Round 2（`App.tsx`/`CommandPalette.tsx`）与 Round 3（`demo_showcase.py`/`workspace_intelligence_hub.py`）改动后，未重新拉起 `8794` 端口实机浏览器复验（已由 `CodexReviewRemediation.test.tsx` 与 `test_codex_review_remediation.py` 集成测试覆盖）。 |
| **3. 后端静态检查与类型安全** | **PASS（Round 3 最终改动后）** | `uv run ruff check --no-cache src tests scripts && uv run mypy --no-incremental --cache-dir=/dev/null src` | Round 3 最终修改后实跑：`ruff`: **`All checks passed!`**；`mypy`: **`Success: no issues found in 137 source files`**。 |
| **4. 后端合同与核心及恢复集成套件（14 组 CI + 2 组恢复共 16 组 Pytest）** | **PASS（Round 3 最终改动后）** | `.github/workflows/ci.yml` 全部 14 组套件 + `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` 按 CI 顺序无干扰独跑 `-q --tb=short` | **16 组套件一次性全绿：`202 passed in 627.10s (0:10:27)`**（`0 failed`, `0 skipped`，含第 14 组 `test_codex_review_remediation.py` **`23/23`**；注：若在同进程紧邻 `64 MiB` 大快照测试后运行 `test_fast_read_api.py` 曾出现冷读 `213.2ms` 瞬时内存/GC 波动，按 CI 标准顺序无干扰独跑全绿）。 |
| **5. 按需本地视频关键帧融合与恢复专项（`BL-011` + `N3`/`N6`/`N7`）** | **PASS（Claude Round 2 核销关闭 · Round 3 全量复跑通过）** | `test_visual_keyframe_analysis.py` + `test_codex_review_remediation.py`（`N3`/`N6`/`N7`） | · 全部计入上述 `202 passed`：超过 `40 MiB` 关键帧预算（`VISUAL_BUDGET_EXCEEDED`）与接近 `64 MiB` JSON 总上限（`BACKUP_SIZE_BUDGET_EXCEEDED`）平滑裁剪并保留全部文字/配置且可导回恢复；单视频分析串行锁与提交后旧目录回收；`/api/show` 先行能力探测 + 去除 `[:8]` 截断。<br>· 真实本机 `ollama/gemma3:4b` 实机与 `8796` 演示证据来自 Iteration #8（Round 2/3 未重连真模型）。 |
| **6. 大库分页、全库搜索、TOCTOU 屏障与连接/延迟守卫** | **PASS（Round 3 最终改动后）** | `test_cross_source_markdown_and_scale.py` + `test_fast_read_api.py` + `test_codex_review_remediation.py` | 320 条库 `?q=` 全库、`?limit=200&offset=200` 分页、300 同步除限及 `get_video_briefs_map(repo_conn=...)` 复用连接全面通过（计入上述 `202 passed`；Claude Round 2 在隔离 40 视频库亦独立复测 `/api/v1/dashboard` `1` 连接 `61.84ms`、`/api/v1/videos` `2` 连接 `63.36ms`）。 |
| **7. 反幻觉评测、Demo UI 推荐胶囊拒答界限与 Obsidian 复核（`N1`/`N2`/`N4`/`N5` + `R2-D1`/`R2-D2`）** | **PASS（Round 3 最终改动后）** | `test_grounding_refusal_eval.py`（`32` 例）+ `test_public_beta_demo_showcase.py` + `test_codex_review_remediation.py` | · **`R2-D1` 关闭**：实测 `#Research` 全部中英文 UI 推荐提问胶囊（默认 3 条、专题、频道、频道+专题、单视频、多视频对比与收藏夹共 59 条）100% 返回 `GROUNDED`；9 类复合诡计问法 100% 返回 `REFUSED_INSUFFICIENT_EVIDENCE` 且 0 引用；<br>· **`R2-D2` 关闭**：恢复会话与整库 Obsidian Vault `.zip` 导出对 `scope_json.related_excerpts` 执行与 `citations` 同等主库核验，未过核验摘录与假 `ev:` 编号全部剥离并追加 `> [!WARNING]` 提示；<br>· **`N1`/`N4`**：全变体 `[E*]`/`E*` 仅留实质有效引用子句，文本错位禁回退首段并标未核验。 |
| **8. 数据库热快照、迁移、预算并发竞争与传输安全（`N8`/`N9`）** | **PASS（Round 3 最终改动后）** | `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` + `test_codex_review_remediation.py` | 无 `_STDLIB_URLOPEN` 后门，默认路径强制经过 `_NoCloudRedirect` 拦截 30x；双实例并发竞争每日预算严格放行配额次数（均已由 Claude Round 2 独立复测关闭）。 |
| **9. 安全基线扫描 & 零个人目录泄漏（`N11`）** | **PASS（Round 3 台账同步后复扫）** | `bash scripts/security_scan.sh`、个人主目录绝对路径排查、`git diff 8e63e04 -- product-ops/reports/daily/2026-11-23.md` | 保持 `product-ops/reports/daily/2026-11-23.md` 与 `8e63e04` 一致；`product-ops/` 零个人主目录路径泄漏；`security_scan.sh` 仅余历史测试哨兵 17 条，本轮全量改动 **0 告警**。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@ca4e17f` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest`（`c54b818` [`#45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) · `main@ca4e17f` [`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703)） / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：此前 `c54b818` 运行 [`#45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) 首轮 Python 作业因 `test_fast_read_api.py` 实测 `149.3ms > 120ms` 失败，未放宽阈值重跑全绿；随后合入并收口的 `main@ca4e17f` 运行 [`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703) 首次执行全绿。Iteration #10 Round 3（含第 14 组 `test_codex_review_remediation.py` `23/23`）已完成本地 16 组 `202 passed`，待 Claude Round 3 复核及 `FD-009` 批复合流后再上云跑批；<br>· Windows WSL2 实机：**`NOT_TESTED`**（无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，严禁绕过）。 |

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
