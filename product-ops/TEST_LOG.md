# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-24（`Asia/Shanghai`）
- **当前活跃基线**：开发分支 `antigravity/task-user-readiness-20261112`（Iteration #10 / `BL-013` Codex 审查 15 P1 + 7 P2 缺陷修复本地全绿，对比公开主线 `main@ca4e17f`）
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-24） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Iteration #10 最终改动后）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 耗时 `814ms` 零报错**；全量 Vitest **`Test Files 57 passed (57) / Tests 1256 passed (1256)`**（耗时 `61.23s`，`0 failed`, `0 skipped`，含新增 `CodexReviewRemediation.test.tsx` `7/7`）。 |
| **2. 浏览器真实端到端 E2E（Iteration #10 `8794` + 叠加 #5/#8/#9）** | **PASS（Iteration #10 Chromium 实机）** | Chromium 实机访问隔离测试服务 `http://127.0.0.1:8794`（`1440×900` 桌面端）叠加 Iteration #5 `8797`、#8 `8796` 与 #9 `8795` | **Iteration #10（`BL-013`）实机复检 `PASS`**：`#Research` 历史问答点击切换立即刷新正文（`P2-05`）、锁定 2 篇视频后经 `⌘K` `围绕专题追问：新专题Beta` 自动清锁并聚焦新专题作答 `GROUNDED`（`P1-15`）、第 31 段尾段直达深链命中 `当前定位引用`（`P1-06`）、`#Content` 检索过滤正常（`P1-12`）、Visual Keyframe Lightbox 展开缩略图并按 `Escape` 优雅关闭且将焦点归还首帧按钮（`P2-03`）；全流程 **`0` console error / `0` HTTP `>=400`（40 请求）/ `0px` 横向溢出**。 |
| **3. 后端静态检查与类型安全** | **PASS（Iteration #10 最终改动后）** | `uv run ruff check src tests scripts && uv run mypy src` | Iteration #10 最终修改后实跑：`ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 137 source files`。 |
| **4. 后端合同与核心及恢复集成套件（14 组 CI + 2 组恢复共 16 组 Pytest）** | **PASS（Iteration #10 最终改动后）** | `.github/workflows/ci.yml` 全部 14 组套件 + `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` 合并无干扰独跑 `-q --tb=short` | **16 组套件一次性全绿：`193 passed in 422.38s (0:07:02)`**（`0 failed`, `0 skipped`，含新增纳入 CI 的第 14 组 `test_codex_review_remediation.py` `14` 个用例全面回归 `P1-01..P1-14`、`P2-01`、`P2-02`、`P2-06`、`P2-07`）。 |
| **5. 按需本地视频关键帧融合与恢复专项（`BL-011` + `P1-09..P1-11` + `P2-01..P2-03`）** | **PASS** | `test_visual_keyframe_analysis.py` + `test_codex_review_remediation.py` + `8794` 隔离实机 | · 全部计入上述 `193 passed`：SHA-256 校验 `visual_keyframe_assets` 打包还原、旧无图备份显式告警并剔除 Obsidian 失效图片引用、重新分析失败时保留原 `gen-<uuid>` 目录文件不丢图、`dir_fd`+`O_NOFOLLOW` 拦截符号链接、纯文本 Ollama 拦截 `409 LOCAL_VISION_MODEL_UNSUPPORTED`；<br>· Iteration #8 本机真 `ollama/gemma3:4b`（`$0`）生成 4 去重帧 / 3 信息帧，Iteration #10 隔离 `8794` 实机验证 3 关键帧渲染与 `Escape` Lightbox 全通。 |
| **6. 大库分页、全库搜索、TOCTOU 屏障与冷读基准（`P1-12..P1-14` + `P2-07`）** | **PASS** | `test_cross_source_markdown_and_scale.py` + `test_fast_read_api.py` + `test_codex_review_remediation.py` + 隔离 40 视频含摘要库 5 轮冷读实测 | · 320 条库 `?q=` 全库命中第 230 条、`?limit=200&offset=200` 分页及同步队列解除 300 上限全部通过；`published_to_cache` 读屏障阻断并发写入污染；<br>· `get_video_briefs_map_for_ids(..., include_markdown=False)` 启用后，隔离 40 篇已提炼视频库 5 轮冷读 `/api/v1/videos` 实测 `[43.533, 53.153, 41.048, 41.393, 38.435]ms`（`min=38.435ms`, `median=41.393ms`, `max=53.153ms`，全量低于 `120ms` 预算）。 |
| **7. 反幻觉评测、混合拒答与证据复核（`P1-01..P1-05` + `EXP-002`）** | **PASS** | `test_grounding_refusal_eval.py`（`32` 例）+ `test_public_beta_demo_showcase.py` + `test_codex_review_remediation.py` | 混合无依据断言整句从正文/要点/行动项/Markdown/历史剥离且无余依据即拒答；文本笔记按精确单段签发 `TEXT_RANGE` ID；跨库恢复未核验记录显式标 `NEEDS_REVERIFICATION`；Demo 混合前提拒答；CJK 2-gram 全文预检命中第 9 份第 121 段中文记录。 |
| **8. 数据库热快照、迁移与容量扩容校验（`P1-08` + `P1-09` + `P2-02`）** | **PASS** | Iteration #10 16 组统一回归已实时复跑 `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` + `test_codex_review_remediation.py` | 恢复通路扩容至 `64 MiB` 与前端大备份导出往返全通；多线程 `BEGIN IMMEDIATE` 预算竞争精确放行 1 次、拒答 `CLOUD_DAILY_BUDGET_EXCEEDED`。 |
| **9. 安全基线扫描 & 零个人目录泄漏** | **PASS（Iteration #10 纳管复扫）** | `bash scripts/security_scan.sh` & 个人主目录路径泄漏排查 | 已纳管全部改动后复扫：`status=findings count=17`（仅历史测试假密钥哨兵，Iteration #10 新增与修改的源码、前端、测试与 `product-ops/` 全部 **0 命中**；`product-ops/` 个人主目录路径泄漏 `0`）。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@ca4e17f` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest`（`main@ca4e17f` / `#45216029723`） / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI：此前 `c54b818` 首轮 Python 作业中 `test_fast_read_api.py` 实测 `149.3ms > 120ms` 失败，未放宽阈值重跑即全绿；文档收口 `main@ca4e17f` 一次全绿。Iteration #10（含第 14 组 `test_codex_review_remediation.py`）已完成本地 16 组 `193 passed`，待 `FD-009` 合流后上云跑批；<br>· Windows WSL2 实机：**`NOT_TESTED`**（无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，严禁绕过）。 |

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
