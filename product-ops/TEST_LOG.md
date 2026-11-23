# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **当前活跃基线（分支 `antigravity/task-user-readiness-20261112`）**：Iteration #5（基于 `6760028` 完成 `BL-007` 首轮引导与双语精修；`main` 已同步至 `f23954f`）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、九大质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-23） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 在 Iteration #5 最终代码后耗时 `3.23s` 零报错构建成功**；全量 Vitest **2 并发实测 `Test Files 54 passed (54) / Tests 1244 passed (1244)`**（耗时 `88.35s`，含 `Onboarding.test.tsx` `7/7`、步骤条跳转及缺失中文化回归；`0 failed`, `0 skipped`）。 |
| **2. 浏览器真实端到端 E2E（Demo + 全新空工作区）** | **PASS（AI 模拟复检）** | Chromium 实机访问未缓存空库 `http://127.0.0.1:8797/#Home`（`1440×900` Obsidian Dark & `375×812` Warm Paper Light）+ `http://127.0.0.1:8798/#Home`（跳过引导后空库），叠加 Demo `8799`（Iteration #4）与 `main@f23954f` | **Iteration #5（`BL-007`）实机复检 `PASS`**：<br>· Obsidian Dark `1440×900`：Steps 1–3 可点击步骤条切换顺畅，祖母绿进度条、Step 2 双链接按钮组（`8px` 间距）与 Step 3 三栏来源卡片并排工整，0 报错；<br>· Warm Paper Light `375×812`：Steps 1–3 全宽度 `364px` 内容区零横向溢出/零裁切，单列卡片与全宽按钮对齐清晰、文字对比鲜明，0 console errors、0 HTTP `>= 400`；<br>· 跳过后空首页正常呈现支持格式提示与 `"导入第一个内容"` 主 CTA。（Demo `8799` `#Content` 秒开与 `main@f23954f` 拒答/上传 `201` 保持全绿。） |
| **3. 后端静态检查与类型安全** | **PASS** | `uv run --frozen ruff check src tests scripts && uv run --frozen mypy src` | 全部 `.py` 改动完成后实跑：`ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 136 source files`。 |
| **4. 后端合同与核心集成套件（11 组 CI Pytest）** | **PASS（合跑 + 竞争复跑）** | 11 组 CI `pytest` 合跑；随后无 `.py` 改动单跑 `uv run --frozen python -m pytest tests/integration/test_fast_read_api.py -v` | 11 组套件合跑实测 **141 passed, 1 failed**：唯一未过项为并发高负载下 `tests/integration/test_fast_read_api.py:448` 性能耗时门限（实测 `217.6ms < 120.0ms`，当时宿主机存在高并发进程与 Vite/Chromium 竞争），其余 141 项含全部功能与新增 32 例 Eval 均一次通过；随后无任何 `.py` 修改单独复跑 `test_fast_read_api.py` **`2 passed in 210.42s`**（0 failed, 0 skipped），完整覆盖全部 142 条 CI 用例。 |
| **5. 反幻觉评测与本机模型基准（`EXP-002` + `BL-005`）** | **PASS** | `tests/integration/test_grounding_refusal_eval.py`（`32` 例）+ `tests/integration/test_public_beta_demo_showcase.py`；隔离临时工作区 + 本机 `ollama/qwen3.5:9b` | 离线/回放基准由 `20` 例扩充至 **`32` 例（`8/8` 测试函数全绿）**：新增 12 例双语多源冲突分辨、时序锚点与越界拒答用例，强化 Demo 拒答词根与框架停用词过滤；本机模型真机 `EXP-002` 保持 **3/3 `GROUNDED` + 2/2 `REFUSED_INSUFFICIENT_EVIDENCE`**，云端开销 `$0`。 |
| **6. HTTP API & 边界错误检验** | **PASS** | Demo `/api/v1/videos/vidDemoAgt1/evidence` 实测采样 + 核心只读端点与反 SSRF/CORS 单测 | Iteration #4 为 `/api/v1/videos/<id>/evidence` 补齐单快照快读投影：实机延迟从 **`583–713ms` 降至 `39.6ms`（冷读）/ `3.8–5.8ms`（热缓存）**（9 路由压测均值 `19.5ms`）；全核心只读接口 HTTP `200`，反 SSRF/Origin 校验严格 fail-closed。 |
| **7. 数据库迁移与持久化恢复** | **PASS** | 双库 SQLite WAL + Linux inode 复用防丢表校验 + Cold start `ensure_ready()` + zero-secret backup/restore | Cold-start 启动幂等创建 `hub.sqlite3` 且保留用户既有 `settings.yaml` 与 `videos`；恢复重跑 0 数据错乱；快照不含明文私钥。 |
| **8. 安全基线扫描 & 零个人目录泄漏** | **PASS** | `bash scripts/security_scan.sh` & 个人主目录路径排查 | 源码 `src/`、`frontend/`、`scripts/`、`product-ops/` 全部 **0 命中**（扫描仅报告历史测试假密钥哨兵 17 条，`product-ops/` 个人主目录路径泄漏为 0）。 |
| **9. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@f23954f` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` (`main@f23954f`, Run `#45149288840`) / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：已按 `FD-005` 同步至 `main@f23954f` 并双端 **PASS**（[`#45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840)：`Frontend Build & Vitest` `1m43s` + `Python Lint, Typecheck & Public Beta Integration` `3m14s`）；Iteration #4 保留在开发分支暂未推 `main`；<br>· Windows WSL2 实机：**`NOT_TESTED`**（手头无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，依安全准则严禁绕过）。 |

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
