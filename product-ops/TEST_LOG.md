# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **当前活跃基线（分支 `antigravity/task-user-readiness-20261112` 与 `main@aec26da` 同步）**：Iteration #7 + 12 组全量 CI 接线（`028d10e` / `main@aec26da`，GitHub Actions [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端全绿）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-23） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Iteration #5 `2be958f` · 本轮零前端改动）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 在 `2be958f` 后耗时 `3.23s` 零报错构建成功**；全量 Vitest **2 并发实测 `Test Files 54 passed (54) / Tests 1244 passed (1244)`**（耗时 `88.35s`，`0 failed`, `0 skipped`；Iteration #6–#7 零 `frontend/` 改动）。 |
| **2. 浏览器真实端到端 E2E（Demo + 全新空工作区）** | **PASS（AI 模拟复检 · Iteration #5 `2be958f`）** | Chromium 实机访问未缓存空库 `http://127.0.0.1:8797/#Home`（`1440×900` Obsidian Dark & `375×812` Warm Paper Light）+ `http://127.0.0.1:8798/#Home`，叠加 Demo `8799` 与 `main@f23954f` | **Iteration #5（`BL-007`）实机复检 `PASS`**：Obsidian Dark `1440×900` 与 Warm Paper Light `375×812` 首轮三步引导 + 跳过空首页 `0` 横向溢出、`0` console errors、`0` HTTP `>=400`；Iteration #6–#7 未改前端。 |
| **3. 后端静态检查与类型安全** | **PASS** | `uv run --frozen ruff check src tests scripts && uv run --frozen mypy src` | Iteration #7 全部 `.py` 最终改动后实跑：`ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 136 source files`。 |
| **4. 后端合同与核心集成套件（11 组 CI Pytest）** | **PASS** | Iteration #7 最终改动后完整独立执行 `.github/workflows/ci.yml` 全部 11 组套件 `-q --tb=short` | **11 组套件一次全部通过：`143 passed in 437.61s (0:07:17)`**（`0 failed`, `0 skipped`，含 600 条大库分页/检索/热快照、全部 fast-read 延迟/篡改校验与 32 例 Eval）。 |
| **5. 4 小时课程、300KB 长文本与 Obsidian `.zip` 真解压专项（`BL-010`）** | **PASS** | Iteration #7 最终改动后实跑 `uv run --frozen python -m pytest tests/integration/test_long_media_and_obsidian_vault.py -v` | **`3 passed in 19.04s`**：<br>· 4 小时讲座（`14390s` / `3200` 原始分段）成功合并并拒绝 `>14400s`（`LOCAL_MEDIA_TOO_LONG` / `TRANSCRIPT_INVALID`），问答精确命中 `03:52` 处 `TIME_RANGE` 锚点；<br>· `>300KB`（`2900` 行）Markdown 拒绝空/NUL/`>2MiB`，均匀采样覆盖开篇到 96% 尾段并通过 `TEXT_RANGE` 溯源召回；<br>· Obsidian `.zip` 真解压至临时磁盘目录：115 字中文标题（`<=180B` UTF-8）未超限、`CON` 重命名为 `_CON.md`、大小写与重名均无覆写、全 `.md` 通过 `yaml.safe_load()`、排版空行完整、Index 全 `[[wikilinks]]` 闭合且纯文本零 `00:00` 假时长。 |
| **6. 600 条大库规模、分页与冷读加速基准（`BL-008` · `dbc7e89`）** | **PASS** | `pytest tests/integration/test_cross_source_markdown_and_scale.py -k test_600_item -v -s` + cProfile 对比 | `dbc7e89` 实测 600 条库（且本轮 11 套件 `143/143` 复跑通过）：无参 `/videos` 保持 `200` 条旧契约（`141.0ms`）、3 页分页 `[97.9, 48.1, 53.8]ms`、跨库问答命中第 561 条仅 **`0.23s`**、`obsidian-bundle?scope=all` / `.zip` 完整收录、`.backup()` 热快照 **`5.5ms`** (`53,248B`)；cProfile 高负载下 `COLD /videos` `68.56ms`（3.5x）、`COLD /intelligence` `21.90ms`（2.2x）。 |
| **7. 反幻觉评测与本机模型基准（`EXP-002` + `BL-005`）** | **PASS** | `tests/integration/test_grounding_refusal_eval.py`（`32` 例）+ `tests/integration/test_public_beta_demo_showcase.py`；本机 `ollama/qwen3.5:9b` | **32 / 32 (100%) PASS**（包含于 Iteration #7 `143/143` 全绿）；本机 `EXP-002` 保持 **3/3 `GROUNDED` + 2/2 `REFUSED_INSUFFICIENT_EVIDENCE`**（`$0` 云开销）。 |
| **8. 数据库热快照、迁移与恢复校验** | **PASS** | `tests/integration/test_v1x_phase1b_backup_restore.py` + `tests/integration/test_research_backup_restore.py` + 600 条核心备份 & `.backup()` 热快照 | `dbc7e89` 备份恢复专项 **`27 passed in 59.89s`**（本轮 `backup_restore.py`/`state.py` 零改动）；600 条库 `BackupRestoreService.create_backup()` 校验 `content_count=600`（`1398.2ms`），`create_sqlite_hot_snapshot()` `5.5ms`、`0o600`、`PRAGMA integrity_check == "ok"`。 |
| **9. 安全基线扫描 & 零个人目录泄漏** | **PASS** | `bash scripts/security_scan.sh` & 个人主目录路径排查 | 源码 `src/`、`frontend/`、`scripts/`、`product-ops/` 与新增测试文件全部 **0 命中**（仅历史测试假密钥哨兵 17 条；`product-ops/` 个人主目录路径泄漏 `0`）。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@aec26da` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` (`main@aec26da`, Run `#45187713845`) / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：已按 `FD-006` 同步至 `main@aec26da` 并双端 **PASS**（[`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845)：`Frontend Build & Vitest` `1m43s` [`54/54` / `1244/1244`] + `Python Lint, Typecheck & Public Beta Integration` `4m42s` [12 组全量 **`146 passed in 231.25s`**，含 `test_long_media_and_obsidian_vault.py`]）；<br>· Windows WSL2 实机：**`NOT_TESTED`**（手头无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，依安全准则严禁绕过）。 |

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
