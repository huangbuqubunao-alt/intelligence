# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **当前最新代码提交（分支 `antigravity/task-user-readiness-20261112`）**：`fee43f4d977bdf9edd03282b98e9b679aceea2c4`
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、九大质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-23） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS** | `cd frontend && npm run build && npx vitest run` | **`vite build` 1.87s 成功；`Test Files 54 passed (54) / Tests 1240 passed (1240)`**（0 skipped, 0 failed；含 Iteration #3 新增 macOS 回环上传兜底、`Escape` 关窗、空 `#Research` CTA 3 个单测） |
| **2. 浏览器真实端到端 E2E（Demo + 全新空工作区）** | **PASS（AI 模拟复检）** | Chromium 实机访问 `http://127.0.0.1:8799/`（Demo）与 `http://127.0.0.1:8798/`（全新 `youtube-intel start` 空库），`1440×900` & `375×812` | **Stage A（修复前）曾实测 4 项 `FAIL`（详见下节）→ Stage D（`fee43f4`）全部复检 `PASS`**：<br>· Demo 越域题返回 `200` + `证据不足 · 已诚实拒答` + `0` citations；<br>· `375×812` `0px` 横向溢出、`.nav-item` 高 `40px`、`首页` 不误亮；<br>· 新空库 `#Settings` 显示 `✅ 本地 Ollama 可用（免费 / qwen3.5:9b）` 且旧诊断折叠；<br>· 空 `#Research`/`#Topics`/`#Intelligence` 零 HTTP `409`、全配导入 CTA；<br>· 浏览器上传 `verify-note.md` 返回 `201 Created` 并渲染 `#Content/...` 原文；0 console errors。 |
| **3. 后端静态检查与类型安全** | **PASS** | `uv run --frozen ruff check src tests scripts && uv run --frozen mypy src` | `ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 136 source files`。 |
| **4. 后端合同与核心集成套件（11 组 CI Pytest）** | **PASS** | `uv run --frozen python -m pytest tests/unit/test_contracts.py tests/integration/test_console_entry.py tests/integration/test_public_beta_demo_showcase.py tests/integration/test_workspace_cloud_safety.py tests/integration/test_workspace_start_launcher.py tests/integration/test_grounding_refusal_eval.py tests/integration/test_cross_source_markdown_and_scale.py tests/integration/test_portable_citations_and_ops.py tests/integration/test_workspace_intelligence_hub.py tests/integration/test_fast_read_api.py tests/e2e/test_po_demo.py -q --tb=short` | **140 passed in 495.60s**（0 failed, 0 skipped）；随后追加日报 `--template cpo` 测试单独跑通 `test_portable_citations_and_ops.py` **4 passed in 5.70s** + `ruff` 0 错（待 Commit 2 后再重跑完整 11 组 CI 套件闭环）。 |
| **5. 真实本机模型反幻觉实测（`EXP-002`）** | **PASS** | 隔离临时工作区 + 本机 Ollama 回环 `qwen3.5:9b` 执行 3 跨源中文/英文问答 + 2 诱导性无解提问 | **3/3 `GROUNDED`**（YT `&t=85s` + B 站 `?t=115`/`?t=64` + Markdown `TEXT_RANGE P2 (47–213)`）+ **2/2 `REFUSED_INSUFFICIENT_EVIDENCE`**（`citations: 0`）；总耗时 `227.6s`、云端开销 `$0`。 |
| **6. HTTP API & 边界错误检验** | **PASS** | Demo（13 个核心只读 GET 采样）+ 新建空库导入/问答接口 + 测试单测反 SSRF 校验 | 全 13 个核心只读端点 HTTP `200`，耗时 `2.0ms – 52.0ms`；非法 URL 客户端拦截 0 写请求；防非回环 Ollama & 非 HTTPS 云接口单测返回 `422`；缺少请求校验返回 `403 ORIGIN_REJECTED`。 |
| **7. 数据库迁移与持久化恢复** | **PASS** | 双库 SQLite WAL + Linux inode 复用防丢表校验 + Cold start `ensure_ready()` + zero-secret backup/restore | Cold-start 启动幂等创建 `hub.sqlite3` 且保留用户既有 `settings.yaml` 与 `videos`；恢复重跑 0 数据错乱；快照不含明文私钥。 |
| **8. 安全基线扫描 & 零个人目录泄漏** | **PASS** | `bash scripts/security_scan.sh` & 个人主目录路径排查 | 源码 `src/`、`frontend/`、`scripts/`、`product-ops/` 全部 **0 命中**（扫描仅报告历史测试假密钥哨兵 17 条，`product-ops/` 个人主目录路径泄漏为 0）。 |
| **9. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `a820152` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` (`a820152`) / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：在 `main@a820152` 双端 **PASS**（[`#45137542384`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45137542384)），提交 `fee43f4` 尚待按 `FD-005` 决定同步 `main` 后再跑云端 CI；<br>· Windows WSL2 实机：**`NOT_TESTED`**（手头无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，依安全准则严禁绕过）。 |

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
