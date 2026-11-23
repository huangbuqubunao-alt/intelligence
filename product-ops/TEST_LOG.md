# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **当前活跃基线（分支 `antigravity/task-user-readiness-20261112`）**：Iteration #6（基于 `2be958f` 完成 `BL-008` >500 大库分页、全库检索、SQLite `.backup()` 零密钥热快照及冷读提速；`main` 已同步至 `f23954f`）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、九大质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-23） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Iteration #5 `2be958f` · 本轮零前端改动）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 在 `2be958f` 后耗时 `3.23s` 零报错构建成功**；全量 Vitest **2 并发实测 `Test Files 54 passed (54) / Tests 1244 passed (1244)`**（耗时 `88.35s`，`0 failed`, `0 skipped`；Iteration #6 零 `frontend/` 改动且 `/api/v1/videos` 无参响应维持字节兼容）。 |
| **2. 浏览器真实端到端 E2E（Demo + 全新空工作区）** | **PASS（AI 模拟复检 · Iteration #5 `2be958f`）** | Chromium 实机访问未缓存空库 `http://127.0.0.1:8797/#Home`（`1440×900` Obsidian Dark & `375×812` Warm Paper Light）+ `http://127.0.0.1:8798/#Home`，叠加 Demo `8799` 与 `main@f23954f` | **Iteration #5（`BL-007`）实机复检 `PASS`**：Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 首轮三步引导 + 跳过空首页 `0` 横向溢出、`0` console errors、`0` HTTP `>=400`；Iteration #6 确认 `#Settings` 诊断已默认折叠，未作前端 UI 改版。 |
| **3. 后端静态检查与类型安全** | **PASS** | `uv run --frozen ruff check src tests scripts && uv run --frozen mypy src` | Iteration #6 全部 `.py` 最终改动后实跑：`ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 136 source files`。 |
| **4. 后端合同与核心集成套件（11 组 CI Pytest）** | **PASS** | Iteration #6 最终改动后完整独立执行 `.github/workflows/ci.yml` 全部 11 组套件 `-q --tb=short` | **11 组套件一次全部通过：`143 passed in 505.13s (0:08:25)`**（`0 failed`, `0 skipped`，含新增 600 条大库分页与热备份用例、全部 fast-read 延迟/篡改校验及 32 例 Eval）。 |
| **5. 600 条大库规模、分页与冷读加速基准（`BL-008`）** | **PASS** | `pytest tests/integration/test_cross_source_markdown_and_scale.py -k test_600_item -v -s` + cProfile 对比 | Iteration #6 最终代码实测 600 条库（`vidBig000–vidBig599`）：<br>· 无参 `/api/v1/videos` 保持 `200` 条旧契约（`141.0ms`）；3 页分页 `?limit=200&offset=0/200/400` 耗时 `[97.9, 48.1, 53.8]ms` 覆盖 600/600、`400 INVALID_QUERY` 校验与 Raw/Fast 一致；<br>· 跨库问答检索到第 561 条仅 **`0.23s`**；`obsidian-bundle?scope=all` 与 `.zip` 均完整收录；<br>· cProfile 对比显示冷启动 `COLD /api/v1/videos` 从 `243.42ms` 降至 **`68.56ms`**（3.5x），`COLD /api/v1/intelligence` 从 `48.92ms` 降至 **`21.90ms`**（2.2x）。 |
| **6. 反幻觉评测与本机模型基准（`EXP-002` + `BL-005`）** | **PASS** | `tests/integration/test_grounding_refusal_eval.py`（`32` 例）+ `tests/integration/test_public_beta_demo_showcase.py`；本机 `ollama/qwen3.5:9b` | **32 / 32 (100%) PASS**（`8/8` 测试函数含于上述 `143/143` 全绿）；本机 `EXP-002` 保持 **3/3 `GROUNDED` + 2/2 `REFUSED_INSUFFICIENT_EVIDENCE`**（`$0` 云开销）。 |
| **7. 数据库热快照、迁移与恢复校验** | **PASS** | `tests/integration/test_v1x_phase1b_backup_restore.py` + `tests/integration/test_research_backup_restore.py` + 600 条核心备份 & `.backup()` 热快照 | Iteration #6 最终改动后备份恢复专项 **`27 passed in 59.89s`**；600 条库 `BackupRestoreService.create_backup()` 校验 `content_count=600`（`1398.2ms`），`create_sqlite_hot_snapshot()` 耗时 **`5.5ms`** 生成 `53,248B` `hub-snapshot.sqlite3`（`0o600`、`PRAGMA integrity_check == "ok"`、`engine_config` 零密钥列）。 |
| **8. 安全基线扫描 & 零个人目录泄漏** | **PASS** | `bash scripts/security_scan.sh` & 个人主目录路径排查 | 源码 `src/`、`frontend/`、`scripts/`、`product-ops/` 全部 **0 命中**（扫描仅报告历史测试假密钥哨兵 17 条，`product-ops/` 个人主目录路径泄漏为 0）。 |
| **9. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@f23954f` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` (`main@f23954f`, Run `#45149288840`) / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：已按 `FD-005` 同步至 `main@f23954f` 并双端 **PASS**（[`#45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840)：`Frontend Build & Vitest` `1m43s` + `Python Lint, Typecheck & Public Beta Integration` `3m14s`）；Iteration #4–#6 保留在开发分支暂未推 `main`；<br>· Windows WSL2 实机：**`NOT_TESTED`**（手头无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，依安全准则严禁绕过）。 |

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
