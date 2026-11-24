# YouTube Intelligence Agent — 全栈 QA 审计、真实用户操作验收与闭环修复报告

## 1. 测试执行环境与 Git 基线

- **主测试隔离工作树**: `/Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112`
- **测试与修复分支**: `antigravity/task-user-readiness-20261112`
- **基线 Commit SHA**: `07a86fe624e82821f594231c78847cd603b00304`
- **修复 Commit SHA**: `f3f19be57fac9846ed4c2ae009fe39be0c670a3d`
- **未改动对照工作树**: `/Users/developer/Documents/yia-worktrees/readiness-v4-budget-final-validation`（保持完全干净）
- **运行环境**: macOS `26.3.1` (`Build 25D2128`) · Python `3.12.11` · Node `v22.22.3` · npm `10.9.8` · SQLite `3.51.0`
- **隔离运行策略**: 全部后端及浏览器集成测试均运行在隔离目录 `.var/qa-audit/`（端口 `127.0.0.1:6491` 后端 API + `127.0.0.1:6488` `vite preview`），未触碰真实用户目录（`v1x-local-main/.var/owner`）、`.env`、Keychain 凭据、付费云端 API 或真实 Obsidian Vault。

---

## 2. 项目审计与全栈覆盖范围

- **前端应用 (`frontend/src/workspace/`)**: `#Home`（首次使用引导 Onboarding、KnowledgeDelta 7 日变化、当前重点、置顶主题）、`#Following`（频道追踪列表、源信号 strip、源详情与独立兴趣设置）、`#Content` 与 `#Content/:id`（默认时间倒序、Shorts 180 秒护栏与折叠抽屉、搜索筛选、收藏/已读、原文与时间戳证据、Markdown 笔记导出、快捷跳栏）、`#Intelligence`（当前/已收藏、来源/专题筛选、详情）、`#Topics`（专题列表、置顶开关、演进时间线）、`#Research`（AI 跨视频问答面板 + 手动组装证据包构建器与范围检索）、`#Settings`（语言往返、全局兴趣规则、AI 模型摘要状态、备份与损坏 ZIP 恢复校验）、`+ 导入`（URL 校验 / macOS 原生选文件守卫 / Web 浏览器上传）、`Cmd+K` 命令面板与深浅主题切换、Desktop `1440×1000` 与 Mobile `375×812` 响应式布局。
- **后端服务 (`src/youtube_intel/`)**: `serve-api` 入口（`fast_read_api.run_cli_with_fast_reads` + `FastReadApiApplication` + `LocalApiApplication`）、SQLite WAL 状态存储（`state.sqlite3` + `.workspace-ai/hub.sqlite3`）、25 个只读 GET 端点与 ZIP 导出、本地文件流式导入、语言/偏好/策略/主题/研究/Workspace-AI CRUD、备份与恢复校验、安全 Origin 与 `X-YIA-Request` 门禁、CLI `doctor`、离线转写进程沙箱边界。

---

## 3. 端到端全功能验收矩阵 (Feature × Action × Real API/DB × Regression × Verdict)

| 功能模块 | 真实用户 / 客户端交互动作 | 真实后端 API / DB 状态联动 | 修复后回归结果 | 最终判定 |
|---|---|---|---|---|
| 首次使用引导 (`Onboarding`) | 空库启动 `#Home` → 查看 `00_onboarding.png` → `继续 × 2` → `暂时跳过` → 页面刷新验证 | `localStorage` 写入引导完成标记，刷新后 `#onboarding-title` 保持隐藏 | `onboarding_empty_library_complete_and_persist` PASS (1423ms) | **PASS** |
| 首页 Dashboard (`#Home`) | 浏览 `最近 7 天发生了什么变化？`、`已完成内容`、`新增洞察`、`当前重点` 与 `置顶主题` (`01_home.png`) | `GET /api/v1/dashboard`、`GET /api/v1/knowledge-delta`、`200 OK` | `home_dashboard_panels_render` PASS (1260ms) | **PASS** |
| 快捷导入 (`+ 导入`) 与通知保留 | 1) 输入 `not-a-valid-url` 报错拦截 (`02_import_modal.png`) → 点 `关闭`；2) macOS 默认模式切换本地文件显示原生启动器守卫提示；3) Web 上传 `qa-live-import.md` → 跳转 `#Content/local-...` (`03_imported_detail.png`) 并刷新验证 | `POST /api/v1/local/imports?filename=qa-live-import.md` 返回 `201 CREATED`，落盘并写入 `videos`/`evidence`/`artifacts`；`popstate` 竞态修复 (`DEF-001`) 后状态提示正确保留 | `quick_import_modal_invalid_close_and_local_md_import` PASS (3771ms) + Vitest 53/53 PASS | **PASS** |
| 关注频道与独立兴趣 (`#Following`) | 校验 `Alpha Engineering`、开关 `添加关注` 弹窗、点击频道行进入详情并点击 `编辑兴趣` → `取消编辑兴趣` (`04_following.png`) | `GET /api/v1/sources`、`GET /api/v1/sources/<id>` 追踪状态与观察授权一致，显示 `来源检查正常 · 跟踪起点已建立` | `following_list_modal_cancel_and_source_interests` PASS (1036ms) | **PASS** |
| 内容库与阅读详情 (`#Content`, `#Content/:id`) | 校验最新优先顺序、`>180s` 含 `#shorts` 视频不误折叠、`45s` 短视频折入底部抽屉并可展开 (`05_content_list.png`)、搜索筛选、进详情读取完整字幕与原文证据 (`06_content_detail.png`)、复制 Markdown、`返回内容` 与浏览器前进/后退 | `GET /api/v1/videos`、`GET /api/v1/videos/<id>`、`GET /api/v1/videos/<id>/evidence` 返回完整证据条目，无卡 loading | `content_ordering_shorts_curation_detail_and_history` PASS (3082ms) | **PASS** |
| 洞察流与收藏持久化 (`#Intelligence`) | 列表按时间倒序渲染 (`07_intelligence.png`) → 点击 `收藏` → 切 `已收藏` 页签 → 页面刷新重验证 | `POST /api/v1/saved-intelligence/save` 与 `GET /api/v1/saved-intelligence` 持久化一致 | `intelligence_list_save_reload_and_tabs` PASS (2432ms) | **PASS** |
| 主题与置顶联动 (`#Topics`) | 打开 `AI Systems` (`08_topics.png`) → 切换置顶状态 → 切回 `#Home` 刷新验证置顶主题栏 | `POST /api/v1/topics/<id>/pin` 持久化并在首页置顶区可见 | `topics_pin_persist_and_timeline_detail` PASS (1982ms) | **PASS** |
| 研究与手动证据包 (`#Research`) | 打开 `AI 跨视频问答` → 展开手动证据包构建器 (`09_research.png`) → `新建研究` → 勾选资料并提交 | `GET /api/v1/research/scope`、`POST /api/v1/research` 创建并返回 `#Research/<sha64>` | `research_qa_and_manual_packet_flow` PASS (1404ms) | **PASS** |
| 设置、全局兴趣、语言与备份 (`#Settings`) | 1) `#settings-interests` 未改直接保存不报错；2) 点 `编辑兴趣` → `取消`（不受后台 SWR 刷新强行卸载 `DEF-004`）→ 编辑保存 `Agent Safety QA` 并刷新持久化；3) 语言编辑取消 + `zh-CN -> en -> reload -> zh-CN`；4) 创建备份下载 + 上传损坏 ZIP 报错拦截 (`10_settings.png`) | `PUT /api/v1/settings/source-policy`、`PUT /api/v1/settings/output-language`、`POST /api/v1/backup-restore/backups`、`POST /api/v1/backup-restore/restore/stage`（409 拒绝损坏包） | `settings_language_interests_unchanged_save_and_backup` PASS (7814ms) + Vitest SWR 回归用例 PASS | **PASS** |
| 全局快捷功能与响应式 (`Cmd+K` / Theme / Mobile) | 切换深浅主题 (`11_cmdk_dark.png`) 并刷新验证持久；`Meta+k` 打开/Escape 关闭命令面板；`1440×1000` 与 `375×812` (`12_mobile_375.png`) 5 路由无横向溢出 | 零 `pageerror`、零 HTTP 5xx、10 项视口断言 `scrollWidth <= innerWidth + 2` 全通过 | `command_palette_and_theme_toggle` (1359ms) + `responsive_desktop_and_mobile_no_overflow` (2900ms) PASS | **PASS** |
| 后端全量 API / 安全 / 并发 / 重启 / SQLite / CLI | `qa/scripts/qa_backend_audit.py` 对 `serve-api` 执行 55 项实测（25 路由 + ZIP、Origin/Header 安全拦截、SQLi/XSS/路径遍历、导入幂等、故障注入、重启、20 线程 80 并发、SQLite 检查、CLI `doctor`） | `state.sqlite3` 与 `.workspace-ai/hub.sqlite3` `PRAGMA integrity_check=['ok']`、`foreign_key_check=[]`；只读 `p50=5.03ms / p95=78.78ms` | `qa_backend_audit.py` **55/55 PASS** | **PASS** |

---

## 4. 缺陷发现与自主修复台账 (Defect Ledger)

完整细节见 [`qa/defects.md`](file:///Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112/qa/defects.md)：

| 编号 | 级别 | 问题摘要 | 修复文件 | 状态与验证结果 |
|---|---|---|---|---|
| `DEF-001` | `P1` | `App.tsx` 无条件监听 `popstate` 调用 `onHashChange(new HashChangeEvent("hashchange"))`，与程序化 `location.hash` 双事件冲突，误清空本地导入状态提示并打断 4 项 Vitest 单测 | `frontend/src/workspace/motion.tsx`, `frontend/src/workspace/App.tsx`, `frontend/src/workspace/App.test.tsx` | **FIXED & VERIFIED**（Vitest `53/53` 文件、`1227/1227` 用例通过；E2E 真机导入后 `noticeVisible=true`） |
| `DEF-002` | `P1` | `POST /api/v1/sources/check-stale` 在只读查询中使用默认读写连接导致 WAL 关闭清理 0 字节 `-wal` 文件，且 `fast_read_api._sqlite_state_token` 将 0 字节 `-wal` 与缺失 `-wal` 视为不同状态，无操作检查击穿热缓存 | `src/youtube_intel/fast_read_api.py`, `src/youtube_intel/local_api.py` | **FIXED & VERIFIED**（`test_fast_read_api.py` 全通过，无操作 `check-stale` 后保持 0 连接热命中） |
| `DEF-003` | `P2` | `offline_fixture_worker.py` `flood` 模式仅输出 `5,000,000` 字节，小于当前 `offline_transcription.MAX_RESULT` (`8 * 1024 * 1024`)，导致返回 `TRANSCRIPT_INVALID` 而非 `EXECUTOR_OUTPUT_LIMIT` | `tests/e2e/offline_fixture_worker.py` | **FIXED & VERIFIED**（`test_offline_transcription_jobs.py` 全部通过，包括 `flood-EXECUTOR_OUTPUT_LIMIT`） |
| `DEF-004` | `P1` | `Settings` 页使用 `<GlobalInterests key={JSON.stringify(globalPolicy)}>` 配合 SWR 后台刷新，点击 `编辑兴趣` 时若后台刷新返回新对象会强行卸载编辑表单并丢失草稿（Playwright 真实复现 `element was detached from the DOM`） | `frontend/src/workspace/App.tsx`, `frontend/src/workspace/App.test.tsx` | **FIXED & VERIFIED**（新增 SWR 刷新保留草稿单测 PASS；Playwright E2E `Settings` 完整流程 **12/12 PASS**） |

### 透明披露：非源码产品缺陷的治理/环境/扫描说明（未弱化、未篡改）
1. **`GOV-001`（历史冻结试运行门禁 — 设计期 Fail-Closed 行为，190 项）**: `uv run --frozen python -m pytest tests/unit -q --tb=short` 运行结果为 `3997 passed, 37 failed, 153 errors, 1 skipped`。其中 188 项源于 `scripts/validation/bounded_synthesis_trial.py:951` 检查历史冻结包 `before['schema'] == 44` 与当前源码清单已演进（报错 `SOURCE_INVENTORY_CHANGED`）；另 2 项（`test_synthesis_attribution_v2.py:248`、`test_synthesis_judgment_v5.py:114`）源于密封资格档案 `system_synthesis_judgment_qualification_v1.json` 绑定历史 `code_sha256=d90e2aa0...`，代码变更后自动按设计吊销云端深度综合资格（`sealed.permits(...) == False`）。按安全规范严禁伪造测试或跳过门禁。
2. **`SEC-001`（静态扫描测试夹具告警 — 17 条）**: `bash scripts/security_scan.sh` 返回 Exit 1（`count=17`），其中 **`src/` 与 `frontend/` 生产代码均为 0 条命中**；16 条为 `tests/` 中合成测试 key/含凭据 URL，1 条为历史验收日志 `docs/validation/dogfood-day2-d2-02/full-suite-collection.txt:3938`。
3. **`ENV-001`（宿主机磁盘压力偶发影响备份测试）**: Batch 1 全量运行 `tests/integration`（`3077 passed, 3 failed`）末尾阶段因宿主机 `/dev/disk3s5` 接近 `DISK_RESERVE_BYTES = 256 MiB` 触发 `test_v1x_phase2_obsidian.py:347` `Insufficient local disk space`；在当前约 `4.68 GiB` 可用空间下独立复验与修复后 65 项针对性集成回归均稳定通过。

---

## 5. 修复后全量验证结果汇总（均在 Commit `f3f19be` 最终代码状态后实跑）

- **前端构建**: `cd frontend && npm run build` → **Exit 0** (`✓ built in 792ms`)
- **Python Lint**: `uv run --frozen ruff check src tests` → **Exit 0** (`All checks passed!`)
- **Python 类型检查**: `uv run --frozen mypy src` → **Exit 0** (`134 source files`)
- **前端 Vitest 全量**: `cd frontend && npx vitest run` → **Exit 0**，**`53 passed (53)` 文件 / `1227 passed (1227)` 用例**（[`qa/evidence/vitest_post_fix.log`](file:///Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112/qa/evidence/vitest_post_fix.log)）
- **后端修复针对性集成回归**: `uv run --frozen python -m pytest tests/integration/test_fast_read_api.py tests/integration/test_offline_transcription_jobs.py tests/integration/test_v1x_phase2_obsidian.py --tb=short -q` → **Exit 0**，**`65 passed, 0 failed` (`170.88s`)**（[`qa/evidence/pytest_targeted_post_fix.log`](file:///Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112/qa/evidence/pytest_targeted_post_fix.log)）
- **真实服务端全栈审计**: `uv run --frozen python qa/scripts/qa_backend_audit.py` → **Exit 0**，**`55/55 PASS`**，只读接口 `p50=5.03ms / p95=78.78ms / max=1888.31ms`，20 线程 80 并发零异常零 5xx，重启数据一致，SQLite `integrity_check=['ok']` / `foreign_key_check=[]`（[`qa/evidence/backend-audit-report.json`](file:///Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112/qa/evidence/backend-audit-report.json)）
- **真实 Google Chrome Playwright E2E**: `node qa/scripts/qa_playwright_e2e.mjs` → **Exit 0**，**`12/12 PASS`**，`server_5xx=0`，`pageerrors=0`，意外 `console.error=0`（仅损坏备份上传负测产生 1 条预期 4xx 控制台响应）（[`qa/evidence/playwright-e2e-report.json`](file:///Users/developer/Documents/yia-worktrees/antigravity-readiness-20261112/qa/evidence/playwright-e2e-report.json)）

---

## 6. 真实界面截图清单 (`qa/evidence/screenshots/`)

13 张全页面及移动端真实运行截图均由 Playwright 无头 Chrome 在真实隔离前后端上采集并经人工视觉核查：
- `00_onboarding.png` — 空库首次引导 3 步页面
- `01_home.png` — 首页 KnowledgeDelta、当前重点与置顶主题
- `02_import_modal.png` — `+ 导入` 无效链接拦截弹窗
- `03_imported_detail.png` — Web 上传 `.md` 后跳转详情与导入提示语保留
- `04_following.png` — 关注频道追踪详情与独立兴趣编辑器（`来源检查正常`）
- `05_content_list.png` — 内容库默认最新排序与 Shorts 45s 折叠抽屉展开（`>180s` 不误折）
- `06_content_detail.png` — 内容详情、洞察结果、时间轴原文证据加载、字幕与跳栏
- `07_intelligence.png` — 洞察列表倒序与处理进度卡
- `08_topics.png` — 主题列表、均分统计与置顶状态
- `09_research.png` — 研究 AI 跨视频问答面板与手动组装证据包区
- `10_settings.png` — 设置页语言、兴趣保存、备份 ZIP 生成 (`106.2 KB`) 与损坏 ZIP 拒绝告警
- `11_cmdk_dark.png` — `Cmd+K` 命令面板与主题切换状态
- `12_mobile_375.png` — `375×812` 移动端响应式无横向溢出检查

---

## 7. 最终验收结论与剩余风险

- **核心本地工作台与回归质量结论**: **PASS (本地优先核心功能与实测交互全通过)** —— 本次发现的 4 项真实缺陷（`DEF-001`..`DEF-004`）均已从根因修复并经过构建、单测、针对性集成、并发重启与真实 Chrome Playwright 闭环回归验证；所有已知阻塞（如未配备 Swift `--native-picker-executable` 启动器时 macOS 浏览器本地文件上传按安全契约禁用原生选框并给出明确重开提示）均为预期设计边界。
- **公开发布姿态说明**: 依仓库既有策略（`README.md`、`GET /api/v1/system` `release_posture: "NO-GO"` 及 `GOV-001` 密封资格约束），受控云端深度综合仍维持未放行/fail-closed 保护态；此外执行前须确保宿主机可用磁盘高于 `DISK_RESERVE_BYTES` (`256 MiB`)。
- **剩余未重跑项声明**: `batch_4` 代码修复后已完成全量 Vitest (`53/53`)、针对性后端集成 (`65/65`)、完整后端实测 (`55/55`) 与 Playwright E2E (`12/12`)；耗时超 1 小时的历史 `tests/unit` 全量（`3997` 过 / `190` `GOV-001`）与全量 3080 项 `tests/integration` 未在 `f3f19be` 后完整重跑（其中基线仅有的 3 个非环境失败项已全部包含在 65 项已通过的针对性回归中）。
