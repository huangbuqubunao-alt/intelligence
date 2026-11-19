# 全栈测试矩阵 (Test Matrix)

- 工作树: `/Users/hua/Documents/yia-worktrees/antigravity-readiness-20261112`
- 分支: `antigravity/task-user-readiness-20261112`
- 基线 Commit: `07a86fe624e82821f594231c78847cd603b00304`

## 1. 静态门禁与自动化基线 (Batch 1 — COMPLETED)

| 项 | 类型 | 命令 | 预期结果 | 实际结果 (基线) | 证据 / 分类 |
|---|---|---|---|---|---|
| `SEC-SCAN` | 安全静态扫描 | `bash scripts/security_scan.sh` | 生产代码零泄漏 | Exit 1 (`count=17`: `src/` 0, `frontend/` 0, `tests/` 16, `docs/` 1) | `qa/evidence/security_scan.log` (`SEC-001`) |
| `PY-RUFF` | Python Lint | `uv run --frozen ruff check src tests` | Exit 0 | **PASS** (Exit 0, `All checks passed!`) | `qa/evidence/ruff_check.log` |
| `PY-MYPY` | Python 类型检查 | `uv run --frozen mypy src` | Exit 0 | **PASS** (Exit 0, `134 source files`) | `qa/evidence/mypy_check.log` |
| `FE-BUILD` | TS 类型 + Vite 构建 | `cd frontend && npm run build` | Exit 0 | **PASS** (Exit 0, `✓ built in 781ms`) | `qa/evidence/fe_build.log` |
| `FE-VITEST` | 前端单测全量 (53 files) | `cd frontend && npx vitest run` | Exit 0, 100% pass | **FAIL** (Exit 1: `51 passed, 2 failed` files / `1221 passed, 4 failed` tests) | `qa/evidence/vitest_full.log` (`DEF-001`) |
| `PY-UNIT` | 后端 Unit 测试全量 | `uv run --frozen python -m pytest tests/unit -q --tb=short` | 记录并分诊全部失败 | `3997 passed, 37 failed, 153 errors, 1 skipped` (188 `SOURCE_INVENTORY_CHANGED`, 2 密封资格哈希漂移) | `qa/evidence/pytest_unit.log` (`GOV-001`) |
| `PY-INT` | 后端 Integration 测试全量 | `uv run --frozen python -m pytest tests/integration -q --tb=short` | Exit 0 / 定位真缺陷 | `3077 passed, 3 failed` (`test_fast_read_api`, `flood-EXECUTOR_OUTPUT_LIMIT`, `obsidian` 磁盘空间约束；`obsidian` 独立复验 `1 passed`) | `qa/evidence/pytest_integration.log` (`DEF-002`, `DEF-003`, `ENV-001`) |

## 2. 后端 HTTP API、DB、并发、异常与安全矩阵 (Batch 2 — COMPLETED, 55/55 PASS)

| 验证维度 | 用例数 | 实测结果 | 关键实测证据与指标 |
|---|---|---|---|
| 服务启动与 `/api/v1/system` | 1 | **PASS** | 仅绑定 `127.0.0.1:6491`，冷启动 ~1.12s，返回 `200` |
| 全量 25 个只读端点 + ZIP 导出 | 26 | **PASS** | 全部返回 `200`、零 `500`、ZIP `testzip() is None`；48 次冷热采样 `p50=9.63ms / p95=65.32ms / max=759.1ms` |
| 安全边界与脱敏 | 5 | **PASS** | 缺 `X-YIA-Request` 或恶意 `Origin` 均 `403 ORIGIN_REJECTED`；`/settings` 零明文 key；`../../etc/passwd.txt` 中性化为 `passwd.txt`，`../..` 拒绝 `422` |
| 参数校验与畸形输入 | 6 | **PASS** | 畸形 JSON `4xx`、未知路由/ID `404`、错误 Method `4xx`、非法语言 `422`、非 `octet-stream` 上传 `415` |
| 本地导入生命周期与幂等 | 7 | **PASS** | `.txt`/`.md` 导入 `201`，重复导入幂等返回 `200 duplicate=true`，空文件/`.exe`/非法 UTF-8 均 `422`，证据可查 |
| 设置/兴趣/主题(XSS·SQLi)/研究/Workspace-AI | 6 | **PASS** | 语言往返、`GLOBAL_CONTENT` 长期兴趣增改、主题增改置顶与 SQLi/XSS 字面量安全、`research` 构建与非法拦截、`is_read`/`starred` 标记、`409 NO_GROUNDED_CONTENT` 诚实阻断 |
| 备份下载、损坏拦截与取消还原 | 1 | **PASS** | 备份 ZIP 下载有效（90.5 KiB）、损坏字节 staging 返回 `409`、合法 staging 后 cancel `200` |
| 进程重启持久化 | 1 | **PASS** | `SIGTERM` 重启后 3 条视频、主题置顶改名、研究记录均完整恢复（二次启动 767.7ms） |
| 20 线程并发压测 (80 请求) | 1 | **PASS** | 零异常、零 `5xx`、并发上传互斥返回正常 `429`/`200`，`p50=228.02ms / p95=1220.14ms` |
| SQLite `integrity_check` / `foreign_key_check` & CLI `doctor` | 2 | **PASS** | `state.sqlite3` 与 `.workspace-ai/hub.sqlite3` 均 `integrity_check=["ok"]`、`FK=[]`；`doctor` 未初始化安全返回 rc=2，QA 目录安全诊断 rc=3 |

证据文件: `qa/evidence/backend-audit-report.json`、`qa/scripts/qa_backend_audit.py`

## 3. 前端页面与真实 E2E 交互矩阵 (Batch 3 — COMPLETED, Pre-Fix 11/12 PASS, 1 FAIL on DEF-004)

| 模块/入口 | 页面 Hash | 测试范围 | 实测结果 (修复前) | 证据 |
|---|---|---|---|---|
| 首次启动与引导 Onboarding | `#Home` | 空库首次引导 3 步流程 + 跳过 + 刷新持久化 | **PASS** | `00_onboarding.png` |
| 首页 Dashboard & 周报 | `#Home` | KnowledgeDelta、当前重点、置顶主题、新材料摘要卡片渲染 | **PASS** | `01_home.png` |
| 关注 Following & 添加关注 | `#Following` / `+ 导入` | 无效链接错误提示、关闭弹窗、macOS 原生守卫提示、Web 文件上传与详情持久化、频道详情与兴趣取消 | **PASS** | `02_import_modal.png`, `03_imported_detail.png`, `04_following.png` |
| 内容库 Content & 阅读器 | `#Content` / `#Content/:id` | 最新时间优先排序、>180s 不折叠 / 45s 短视频折叠展开、搜索筛选、Markdown 复制、返回内容与浏览器前进后退 | **PASS** | `05_content_list.png`, `06_content_detail.png` |
| 洞察 Intelligence | `#Intelligence` | 验证洞察列表渲染、收藏切换、`已收藏`页签及刷新持久化 | **PASS** | `07_intelligence.png` |
| 主题 Topics | `#Topics` | 专题列表、置顶主题并校验 `#Home` 置顶栏持久化生效 | **PASS** | `08_topics.png` |
| 研究 / AI 跨视频问答 | `#Research` | AI 跨视频深度问答界面 + 展开手动证据包构建并持久化 `#Research/:id` | **PASS** | `09_research.png` |
| 设置 Settings & 备份恢复 | `#Settings` | 全局兴趣无修改直接保存（不报错）、编辑与取消（触发 `DEF-004` DOM 卸载竞态） | **FAIL (`DEF-004`)** | `qa/evidence/playwright-e2e-report.json` |
| 全局快捷功能 & 响应式 | `*` | 命令面板 `Cmd+K`、深浅主题切换持久化、1440px 与 375px 零横向溢出、零 `pageerror`/HTTP 5xx | **PASS** | `11_cmdk_dark.png`, `12_mobile_375.png` |

## 4. 修复后全链路回归验收结果 (Batch 4 — COMPLETED)

| 回归套件 | 命令 | 修复后最终结果 | 关键证据 |
|---|---|---|---|
| 前端构建 (`tsc -b && vite build`) | `cd frontend && npm run build` | **PASS** (Exit 0, `✓ built in 792ms`) | 命令行输出 |
| Python Lint | `uv run --frozen ruff check src tests` | **PASS** (Exit 0, `All checks passed!`) | 命令行输出 |
| Python 静态类型检查 | `uv run --frozen mypy src` | **PASS** (Exit 0, `134 source files`) | 命令行输出 |
| 前端单测全量 (含 `DEF-001` & `DEF-004` 回归用例) | `cd frontend && npx vitest run` | **PASS** (Exit 0, **53/53 files, 1227/1227 tests**) | `qa/evidence/vitest_post_fix.log` |
| 后端针对性集成回归 (`fast_read_api`, `offline_transcription`, `obsidian`) | `uv run --frozen python -m pytest tests/integration/test_fast_read_api.py tests/integration/test_offline_transcription_jobs.py tests/integration/test_v1x_phase2_obsidian.py --tb=short -q` | **PASS** (Exit 0, **65 passed, 0 failed** in 170.88s) | `qa/evidence/pytest_targeted_post_fix.log` |
| 全栈真实服务端 HTTP / DB / 并发 / 安全 / CLI 审计 | `uv run --frozen python qa/scripts/qa_backend_audit.py` | **PASS** (Exit 0, **55/55 PASS**, `p50=5.03ms / p95=78.78ms`) | `qa/evidence/backend-audit-report.json` |
| 全栈真实 Google Chrome Playwright E2E + 截图走查 | `node qa/scripts/qa_playwright_e2e.mjs` | **PASS** (Exit 0, **12/12 PASS**, 0 `pageerror`, 0 `5xx`, 1 预期 4xx 负测控制台记录 / 0 意外错误，13 张真实截图) | `qa/evidence/playwright-e2e-report.json`, `qa/evidence/screenshots/*.png` |
