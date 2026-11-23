# 全维度测试与质量验收台账（QA & Verification Log）

- **更新日期**：2026-11-23（`Asia/Shanghai`）
- **当前活跃基线**：公开主线 `main@092951b`（已按 `FD-007` 同步 Iteration #8 `BL-011` 与第 13 组视觉 CI，GitHub Actions [`#45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) 双端全绿），研发分支 `antigravity/task-user-readiness-20261112` 代码对齐。
- **台账纪律**：严格采用四态标识 **`PASS / FAIL / BLOCKED / NOT_TESTED`**。仅当测试命令在对应代码版本实际执行完毕且见到真实输出时方能标 `PASS`；修复前失败与修复后复检分列存档，绝不涂改历史、绝不跳过或弱化断言。

---

## 一、质量域当前最新验收总览

| 质量域 | 验收状态 | 覆盖范围与真实命令/动作 | 真实结果摘要（观测日期：2026-11-23） |
|---|---|---|---|
| **1. 前端单元测试与类型构建** | **PASS（Iteration #8 最新改动后）** | `cd frontend && npm run build && npx vitest run --minWorkers=1 --maxWorkers=2` | **`vite build` (`tsc -b && vite build`) 耗时 `875ms` 零报错**；全量 Vitest **`Test Files 55 passed (55) / Tests 1247 passed (1247)`**（耗时 `63.51s`，`0 failed`, `0 skipped`，含新增 `WorkspaceVisualKeyframes.test.tsx` `3/3`）。 |
| **2. 浏览器真实端到端 E2E（Demo + 空库 + 关键帧视觉分析）** | **PASS（Iteration #8 Chromium 实机）** | Chromium 实机访问隔离端口 `http://127.0.0.1:8796` 覆盖 3 条 fixture（已分析 MP4 + 未分析 MP4 + 纯文本 `.md`）× 桌面 Obsidian Dark `1440×900` & 移动 Warm Paper Light `375×812`；叠加 `2be958f` 首轮引导与 Demo `8799` | **Iteration #8（`BL-011`）实机复检 `PASS`**：4 张关键帧 HTTP `200` 渲染与中文融合洞察无原始 JSON；筛选切换 `4 <-> 3` 正常；Lightbox `[role="dialog"]` `ArrowRight`（`1/4 -> 2/4`）+ `Escape` 关闭正常；`visual-pack.zip` 下载 `200`（`application/zip`, `7826B`）；未分析视频展示 CTA、纯文本笔记隐藏；双主题桌面与 `375px` 移动均 `0px` 横向溢出、`0` console error、`0` HTTP `>=400`。 |
| **3. 后端静态检查与类型安全** | **PASS** | `uv run --frozen ruff check src tests scripts && uv run --frozen mypy src` | Iteration #8 全部最终改动后实跑：`ruff`: `All checks passed!`；`mypy`: `Success: no issues found in 137 source files`。 |
| **4. 后端合同与核心集成套件（13 组完整 CI Pytest）** | **PASS** | Iteration #8 最终改动后独立运行 `.github/workflows/ci.yml` 全部 13 组套件 `-q --tb=short` | **13 组完整 CI 套件一次全绿：`151 passed in 367.69s (0:06:07)`**（`0 failed`, `0 skipped`，含新增 `test_visual_keyframe_analysis.py`、`test_long_media_and_obsidian_vault.py`、600 条大库、fast-read 延迟与 32 例 Eval）。 |
| **5. 按需本地视频关键帧融合与真视觉模型专项（`BL-011`）** | **PASS** | `pytest tests/integration/test_visual_keyframe_analysis.py` + 本机 `ollama/gemma3:4b` `$0` 隔离实跑 | · 集成套件（`5/5` 已计入 13 组 `151 passed`）：真 `ffmpeg lavfi` 5 段多场景 MP4 精确用 dHash 去重重复页、`0o700`/`0o600` 权限、音频/文本 `409 VISUAL_MEDIA_REQUIRED`、路径穿越 `404`、BYOK 预算拦截保历史帧、`409 LOCAL_VISION_MODEL_UNSUPPORTED`、`/keyframes/*.jpg` + `visual-pack.zip` + 全库 `obsidian-bundle.zip` `assets/*.jpg` & `yaml.safe_load` + Sidecar 还原；<br>· 本机真 `ollama/gemma3:4b`（`$0`）：4 去重帧 / 3 信息帧与中文视觉对齐摘要实机生成通过。 |
| **6. 4 小时课程、300KB 长文本、600 条大库与冷读基准（`BL-008`/`BL-010`）** | **PASS** | Iteration #8 全量 13 组 `151 passed` 已完整复跑 `test_long_media_and_obsidian_vault.py` + `test_cross_source_markdown_and_scale.py` + `test_fast_read_api.py` | 全部持续 **PASS**：4h（`14390s`）讲座 `03:52` 锚点、`>300KB` 尾段均匀采样、Obsidian `.zip` 实解压、`600` 条库分页/问答与 fast-read 毫秒预算全绿。 |
| **7. 反幻觉评测与本机模型基准（`EXP-002` + `BL-005`）** | **PASS** | `tests/integration/test_grounding_refusal_eval.py`（`32` 例）+ `tests/integration/test_public_beta_demo_showcase.py`；本机 `ollama/qwen3.5:9b` | **32 / 32 (100%) PASS**（包含于 Iteration #8 `151/151` 全绿）；本机 `EXP-002` 保持 **3/3 `GROUNDED` + 2/2 `REFUSED_INSUFFICIENT_EVIDENCE`**（`$0` 云开销）。 |
| **8. 数据库热快照、迁移与恢复校验** | **PASS** | Iteration #8 最终改动后实跑 `pytest tests/integration/test_v1x_phase1b_backup_restore.py tests/integration/test_research_backup_restore.py -q` | **`27 passed in 39.46s`**（`0 failed`, `0 skipped`），且 `video_visual_analyses` + `keyframes/*.jpg` 随 Sidecar 快照备份还原验证通过（`test_visual_keyframe_analysis.py`）。 |
| **9. 安全基线扫描 & 零个人目录泄漏** | **PASS** | `bash scripts/security_scan.sh` & 个人主目录路径排查 | Iteration #8 最终改动后复扫：`status=findings count=17`（仅历史测试假密钥哨兵，新增代码与测试全部 **0 命中**；`product-ops/` 个人路径泄漏为 `0`）。 |
| **10. 跨平台及外部受控环境兼容性** | **PARTIAL (`PASS` Linux CI @ `main@092951b` / `NOT_TESTED` WSL2)** | GitHub Actions `ubuntu-latest` (`main@092951b`, Run `#45201809374`) / Windows WSL2 / 公网免 Cookie YouTube 抓取 | · Ubuntu Linux CI（`main@092951b` 含 Iteration #8 + 第 13 组视觉测试）：[`#45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) 双作业 **PASS**——`Frontend Build & Vitest` `1m19s`（`vite build` `1.30s` + **`55/55` / `1247/1247 passed in 60.13s`**）与 `Python Lint, Typecheck & Public Beta Integration` `19m59s`（`ruff` / `mypy` 137 文件 0 错 + 13 组全量 **`151 passed in 305.18s`**）；<br>· Windows WSL2 实机：**`NOT_TESTED`**（无 Windows 物理机）；<br>· 公网免 Cookie `yt-dlp` YouTube 字幕抓取：**`BLOCKED`**（触发反机器人验证，严禁绕过）。 |

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
