# Intelligence 项目独立 Review 整改与集成验收报告（05_INTEGRATION_REMEDIATION_ACCEPTANCE_REPORT）

> 对应整改任务书：`docs/validation/ux-redesign-2026-11-25/04_INDEPENDENT_CODE_REVIEW_AND_AGY_REMEDIATION.md`（基线 `9cee10df`）
> 目标分支：`antigravity/remediation-20261125`（从 `origin/main@d1b58f73` 线性创建，未自动合并 `main`）
> **已验证代码提交基准（VERIFIED_CODE_SHA）**：`913b2c06030caf7fa9a69e5f07737cc5269e57f2`（短哈希 `913b2c06`；后端与 Python 源码/测试自 `1d97f61d` 起零改动）
> **文档与截图交付提交**：本报告与 7 张脱敏实机截图以独立纯文档提交追加于 `913b2c06` 之后，`src/`、`frontend/`、`tests/`、`scripts/` 与 `913b2c06` 逐字节一致。

---

## 1. 总结论与分支拓扑状态

- **整改与验收结论**：**全部 9 道验收门禁（`M1, S1, S2, S3, U1, U2, E1, E2, R1`）已闭环验证通过**。任务书识别的 **7 项 P1 阻断项（P1-01 ~ P1-07）**、**5 项 P2 结构/质量问题（P2-01 ~ P2-05）** 与 **3 项 TOP 产品级体验优化（TOP 1 ~ TOP 3）** 已全部完成源码级独立复核、最小化安全修复、自动化回归与全新无缓存 Chromium 实机验收（含实机捕获并顺带清零的“模态抽屉内收起 `<details>` 导致前向 Tab 焦距逸出”真实缺陷）。
- **分支拓扑与线性基线证据（P1-07 闭环）**：
  - `git merge-base --is-ancestor origin/main 913b2c06` 退出码 `0`（`ANCESTOR_OK`）。
  - 起步期已验证 `origin/main@d1b58f73` 与原历史起点 `5cc76ab8` 拥有完全相同的 Git tree（`5953e737`），并通过线性 cherry-pick（`5cc76ab8..9cee10df`，零冲突）验证 `HEAD^{tree} == 9cee10df^{tree}`（`TREE_PARITY_OK`），再在其上小批次线性提交本次整改与验收交付，零强推、零 `main` 改动。
  - `git diff --check origin/main..HEAD` 退出码 `0`。

---

## 2. 全量问题逐项闭环清单（P1-01 ~ P1-07 / P2-01 ~ P2-05 / TOP 1 ~ TOP 3）

| 编号 | 级别 | 独立源码复核结论与根因 | 整改落地摘要 | 验证提交 SHA |
|---|---|---|---|---|
| `P1-01` | P1 | **CONFIRMED**：`/api/*` 与文件流导出缺少统一 loopback `Host` 允许列表、`Sec-Fetch-Site: cross-site` 拦截与 `Cross-Origin-Resource-Policy: same-origin` 响应头 | 在 `src/youtube_intel/local_api.py` 统一全路径 loopback `Host` 白名单（含 `127.0.0.1`、`localhost`、`[::1]` 动态端口及桌面桥 `origins`）、拦截跨站 `Sec-Fetch-Site` 与非本机 `Origin`、为 `/api/*` 统一附加 `Cross-Origin-Resource-Policy: same-origin` | `812d638a` |
| `P1-02` | P1 | **CONFIRMED**：`fast_read_api._resolve_local_media_file` 接受未知 `storage_root` 并返回裸 `Path`，导致 `open_managed` 无法执行逐级 `O_NOFOLLOW` 校验与资产 SHA-256 核验 | 在 `src/youtube_intel/source_authority.py` 与 `src/youtube_intel/fast_read_api.py` 新增 `ManagedMediaFile` / `ManagedMediaError` / `managed_open_error`（同时保持既有调用方的 `OSError` 兼容），严格限定 `storage_root in {'SOURCE_DATA', 'DATA'}`，并加入基于不变 stat 指纹的 bounded SHA-256 缓存 | `812d638a` |
| `P1-03` | P1 | **CONFIRMED**：`workspace_intelligence_hub._prune_ungrounded_ref_clauses` 仅校验引用标签 `[E1]` 是否存在，未核验数字/百分比/货币/年份/数量词与否定极性与原话是否一致 | 在 `src/youtube_intel/workspace_intelligence_hub.py` 增加确定性 `_check_clause_against_cited_evidence`，统一覆盖实时问答、历史重读、备份恢复与 Obsidian ZIP 导出，冲突时触发受控拒答/降级码 `CITATION_FACT_CONFLICT`；并修正 `#编号` 索引标签与「一人/一家」等中文习惯用语误杀 | `69dd2858`, `1d97f61d` |
| `P1-04` | P1 | **CONFIRMED**：`youtube_auth_fallback` 仅靠进程内检査-释放锁-写记录，多实例/并发请求下存在最后配额与冷却槽位竞态 | 在 `src/youtube_intel/youtube_auth_fallback.py` 使用 SQLite `BEGIN IMMEDIATE` 实现 `_reserve_attempt_slot` 原子预留（`RESERVED`）与 `_finalize_attempt_slot` 结算，异常中止保守计入配额与跨实例持久化的 30 分钟熔断 | `0a778a07` |
| `P1-05` | P1 | **CONFIRMED**：`.reader-ref-drawer` 关闭时仍在无障碍树与 Tab 链路内；且实机 Chromium 验收额外发现当抽屉内 `<details>`（转写诊断）收起时 `Tab` 第 4 步会跳过 `<summary>` 逸出背景导航 | 抽出 `frontend/src/workspace/ReaderReferenceDrawer.tsx`：关闭态原生 `inert`（20 次 `Tab` `0/20` 进入）+ 按钮 `tabIndex=-1`（未强加 `aria-hidden` 以保持现有 DOM 查询与读屏真实 `inert` 语义一致）；开启态 `role="dialog" aria-modal="true" aria-labelledby="reader-ref-drawer-title"`、WAI-ARIA `tablist`/`tab`/`tabpanel`（支持 `ArrowLeft`/`ArrowRight`/`Home`/`End`）、`Escape` 关闭回焦；通过 `isInsideClosedDetails` 与可见性过滤修补闭合 `<details>` 焦点逸出（实机 `0/15` 逸出） | `192847d6`, `913b2c06` |
| `P1-06` | P1 | **CONFIRMED**：`local_api` 对 `HEAD` 仍回写正文；`_send_file` 异常吞没未区分发送前 HTTP 4xx/413 与发送后安全断流 | 将 `do_HEAD` 统一接入 `_handle` 并确保所有分支（含错误响应）严格零正文；区分发送前 `404`/`409`/`413` 与发送后安全关闭及脱敏告警 | `812d638a` |
| `P1-07` | P1 | **CONFIRMED**：待验收候选基线与 `origin/main` 分叉（101/105 独有提交） | 基于 `origin/main@d1b58f73` 创建线性分支 `antigravity/remediation-20261125` 并完成无冲突线性重放，全部整改与交付线性提交在其上 | `75da5130` |
| `P2-01` | P2 | **CONFIRMED**：`_parse_byte_range` 使用宽泛 `int()` 接收 `+4`/Unicode 数字且多区间回退不合规 | 重写严格 RFC 9110 ASCII Range 解析，拒绝非 ASCII 数字/正负号/空白/多区间并返回合规 `416` | `812d638a` |
| `P2-02` | P2 | **CONFIRMED**：Netscape Cookies 导入域名边界校验偏宽，可能保留非 YouTube/Google 第三方行 | 收紧 `validate_netscape_cookies_txt` 为严格 DNS 域边界并强制剥离仅保留 `_ALLOWED_COOKIE_ROOTS`（`youtube.com`, `youtu.be`, `google.com`, `googlevideo.com`, `ytimg.com`），增补跨库/备份/日志零泄漏测试 | `0a778a07` |
| `P2-03` | P2 | **CONFIRMED**：Research 范围统计对快照类来源未调用 `verify_source`，UI 易将候选资料误表述为已核验范围 | 在 `workspace_intelligence_hub._build_research_scope_options` 为快照来源接入 `verify_source` 门禁，并在 `WorkspaceAiWidgets.tsx` 明确文案为「当前提问范围：候选资料 N 篇（提问时将实时核验原文）」及有效引用/覆盖来源计数 | `69dd2858` |
| `P2-04` | P2 | **CONFIRMED**：本地媒体加载失败仅泛化提示，未按 `MediaError.code` 区分解码/网络/格式错误与一键恢复 | 抽出 `ReaderMediaStage.tsx` 实现 `MediaError.code` 1–4 分类诊断、一键重载重试及直达字幕抽屉兜底入口 | `192847d6` |
| `P2-05` | P2 | **CONFIRMED**：`App.tsx` 中 `ContentDetailPanel` 过于臃肿（>1,200 行） | 模块化拆出 `ReaderMediaStage.tsx`、`ReaderReferenceDrawer.tsx` 与 `ReaderRecoveryPanel.tsx` | `192847d6` |
| `TOP 1` | 产品体验 | **CONFIRMED**：YouTube 受限阻断场景跳转设置后与返回内容之间缺少零跳页内闭环 | 新增 `ReaderRecoveryPanel.tsx`（`InlineYouTubeAuthRecovery`）实现当前详情页明确授权说明、取消零请求、一键确认并立即重试 | `192847d6` |
| `TOP 2` | 产品体验 | **CONFIRMED**：列表/详情 AI 评分徽章易被误读为事实核验结论 | 在 `AiScoreBadge` 补充「排序分」辅助提示语，与事实引用核验严格区隔 | `192847d6` |
| `TOP 3` | 产品体验 | **VERIFIED**：内容详情聚焦核心摘要与媒体预览、辅助资料收归按需抽屉，Mobile 390px 零横向溢出 | 通过无头 Vitest 与 390x844 真实 Chromium 实机验证确认交互闭环与零溢出 | `192847d6`, `913b2c06` |

---

## 3. 9-Gate 验收门禁实证矩阵

| Gate | 验收范围 | 实际执行命令 | 实测结果（最新基准） | 对应 SHA | 结论 |
|---|---|---|---|---|---|
| **M1** | 线性历史、Tree 等价、独立 `.venv` 隔离 | `git merge-base --is-ancestor origin/main HEAD && git diff --stat origin/main 5cc76ab8` | `ANCESTOR_OK`, `TREE_PARITY_OK`, `.venv` 指向本 worktree | `75da5130` | ✅ PASS |
| **S1** | 传输安全、受管文件流、`HEAD` 零正文、RFC 9110 Range | `.venv/bin/pytest -q tests/integration/test_local_video_post_import_resilience.py tests/integration/test_local_content_adversarial.py tests/integration/test_dogfood_day2_native_import.py tests/unit/test_bigmodel_settings.py tests/unit/test_qa_launch_isolation.py` | `149 passed in 115.81s`（后在 `1d97f61d` 上再全量复跑通过） | `812d638a` | ✅ PASS |
| **S2** | YouTube 备用登录 SQLite 并发防越额与 Cookie 域严格过滤 | `.venv/bin/pytest -q tests/unit/test_manual_ux_remediation.py` | `9 passed in 6.41s`（含并发 Barrier、异常保守扣额、零泄漏测试） | `0a778a07` | ✅ PASS |
| **S3** | 事实核验防越句夹带、`CITATION_FACT_CONFLICT`、Research 候选范围与前端联动 | `.venv/bin/python -m pytest -q tests/integration/test_codex_round3_remediation.py tests/integration/test_workspace_intelligence_hub.py` + `vitest` | `30 passed in 78.15s`（后端）；`23 passed in 13.58s`（前端）；`ruff` 0 错 | `69dd2858` | ✅ PASS |
| **U1 / U2** | 前端类型检查、Vite 生产构建、全量 React 单测/无障碍/回归测试 | `cd frontend && npx tsc --noEmit && npm run build && npx vitest run --minWorkers=1 --maxWorkers=1` | `vite build` 9.95s 生成 `assets/index-BFMi-sz-.js`；**`58 test files passed (58), 1276 passed (1276)`** in `428.92s` | `913b2c06` | ✅ PASS |
| **E1** | 公测全链路核心集 + 补充单元/集成回归 + 代码规范 + 严格类型 + CI 清单核对 | 1) 公测全链路 17 文件：`tests/unit/test_contracts.py` 等 17 个套件；<br>2) 补充 6 文件：`test_local_api.py` 等；<br>3) `ruff check src tests scripts` + `mypy src` + `scripts/ci_test_manifest.py verify` + `git diff --check` | 1) **`205 passed in 1021.58s`**（exit 0，无并发争抢）；<br>2) **`290 passed, 1 warning in 357.23s`**（exit 0）；<br>3) `ruff` All checks passed；`mypy` 138 文件 0 错；`manifest verify` 7,388 收集 / 7,177 可运行（190 GOV-001 + 21 容量排除）；`git diff --check` exit 0 | `1d97f61d`（Python 源码自此零修改） | ✅ PASS |
| **E2** | 全新无缓存端口 `8796`（验证工作区）+ 人工工作区 `8792` 真实 Chromium 验收 | Playwright/Chromium 实机访问 `http://127.0.0.1:8796` 与 `http://127.0.0.1:8792`（加载 `index-BFMi-sz-.js`） | `0` Console errors，`0` HTTP>=400 请求；MP4 播放与 HTTP `206` Range；关闭态 `inert=""` 且 20 次 Tab **`0/20` 误入**；开启态 `role="dialog" aria-modal="true"`、10 Tab + 5 Shift+Tab **`0/15` 逸出**、方向键切 Tab、`Escape` 回焦；Mobile `390x844` **`0` 横向溢出**；`YtAuthGate1` 页内授权面板取消 **`0` 网络请求**；`#Research` 范围条实测展示；7 张截图已落盘审阅 | `913b2c06` | ✅ PASS |
| **R1** | 验收报告、检查点更新、纯文档交付提交及远端分支推送 | 本报告 + `REMEDIATION_CHECKPOINT.md` + `git push -u origin antigravity/remediation-20261125` | 已生成并推送至 `origin/antigravity/remediation-20261125`（`main` 未改动） | 本交付提交 | ✅ PASS |

---

## 4. 实机 Chromium 验收截图与关键核验发现

1. **实机捕获并当轮根治的真实缺陷（体现 E2 价值）**：第一轮在 `8795` 跑实机时，虽然静态单测全绿，但真实 Chromium 探测发现 `ReaderReferenceDrawer` 开启后，若内部「转写诊断」`<details>` 处于收起态，其子代 `<button>` / `<input>` 仍被 `listFocusableInDrawer` 计为最后可聚焦元素，导致第 4 次 `Tab` 从 `<summary>` 直接逸出弹窗落入背景栏「快捷导入」。根因定位后已在 `913b2c06` 增加 `isInsideClosedDetails` 与可见性过滤及 Vitest 回归测试，并在全新无缓存端口 `8796` 上实机复测确认 **10 次 Tab + 5 次 Shift+Tab 共 15 步 `0 / 15` 逸出**，从 `<summary>`（转写诊断）按 `Tab` 稳定回绕到「原始字幕」页签。
2. **脱敏实机截图清单（均在最终代码基准 `913b2c06` / `index-BFMi-sz-.js` 上抓取并经人工视觉核验）**：
   - 桌面深色阅读器（原生 `<video>` 播放至 `0:03 / 0:03`、HTTP `206`、右侧辅助抽屉关闭态 `inert=""`）：[01_reader_desktop_dark_media_inert.png](screenshots/01_reader_desktop_dark_media_inert.png)
   - 桌面深色阅读器无障碍参考资料抽屉展开态（`role="dialog" aria-modal="true"`、`原始字幕` 聚焦、收起态 `▶ 转写诊断` 焦点安全回绕）：[02_reader_desktop_dark_drawer_dialog.png](screenshots/02_reader_desktop_dark_drawer_dialog.png)
   - 移动端 `390x844` 暖纸浅色主题阅读器（零横向溢出、`html/body/main` 宽度锁定视口内）：[03_reader_mobile_390_light.png](screenshots/03_reader_mobile_390_light.png)
   - YouTube 访问受限项 `YtAuthGate1` 页内授权同意弹窗（TOP 1 闭环：仅明确授权确认且取消发 `0` 请求）：[04_youtube_auth_inline_recovery.png](screenshots/04_youtube_auth_inline_recovery.png)
   - Research 跨视频问答候选范围条实拍（「当前提问范围：候选资料 1 篇（提问时将实时核验原文）」）：[05_research_candidate_scope.png](screenshots/05_research_candidate_scope.png)
   - 人工工作区 `8792` 首页深色实拍：[06_workspace_home_8792.png](screenshots/06_workspace_home_8792.png)
   - 人工工作区 `8792` 设置页深色实拍：[07_workspace_settings_8792.png](screenshots/07_workspace_settings_8792.png)

---

## 5. `NOT_TESTED` 与披露边界（Disclosed Exclusions）

为确保独立复审可完全信赖报告口径，以下未在本次本地流水线中跑完或刻意受控禁用的项目**明确按事实披露，不做超范围宣称**：

1. **GOV-001 封存基线夹具与容量排除项（211 项）**：`scripts/ci_test_manifest.py verify` 确认总收集 `7,388` 项用例中，存在 `190` 项 `GOV-001` 有意 fail-closed 基线夹具与 `21` 项容量排除项，按仓库 CI 规范自动排除，实际 CI 可运行范围为 `7,177` 项（单元测试 `3,987` / 集成测试 `3,190`）。
2. **完整 12 分片 Python CI 矩阵（`run-unit --shard 0..3`、`run-integration --shard 0..7`）**：在最终代码基准上本机完整串行实测并全部通过的是 **前端全量 `1,276/1,276` 项**、**核心公测与整改全链路 `205/205` 项** 及 **补充核心单元/集成回归 `290/290` 项**（`1d97f61d`，`src/`/`tests/`/`scripts/` 与 `913b2c06` 零差异），外加 `ruff`、`mypy` 与 `ci_test_manifest verify`。其余未纳入上述 23 个核心测试文件内的全分片用例（约 6,682 项常规分片），受本地单机耗时约束未全部逐分片在最终 commit 后重跑一次，将由 GitHub Actions `.github/workflows/ci.yml` 在远端分支推送后全分片自动跑齐。
3. **禁止触碰的真实外部副作用（安全与隐私合规）**：
   - 未在实机上点击「确认授权并立即重试」读取用户本机真实 Chrome/Safari YouTube Cookie；`TOP 1` 与 `P1-04`/`P2-02` 的提取执行路径均通过隔离的单元测试、SQLite 并发替身与假 Netscape Cookies 文件验证，实机 Chromium 仅验证「弹窗披露 + 点击取消发 0 请求」。
   - 未触发真实付费云端大模型调用，未向真实 Obsidian Vault 写入内容，未招募外部真实测试用户。

---

## 6. 独立复审与复现入口（Independent Re-Review Guide）

1. **拉取分支与确认唯一代码基线**：
   ```bash
   git fetch origin antigravity/remediation-20261125
   git checkout antigravity/remediation-20261125
   git merge-base --is-ancestor origin/main 913b2c06 && echo ANCESTOR_OK
   # 验证文档提交相对于已验代码基准 913b2c06 对代码零改动：
   git diff --stat 913b2c06..HEAD -- src frontend tests scripts
   # 审阅相对于 main 的全部代码与文档改动：
   git log --oneline origin/main..HEAD
   ```
2. **复现本轮核心质量与安全测试**：
   ```bash
   .venv/bin/ruff check src tests scripts
   .venv/bin/mypy src
   .venv/bin/python scripts/ci_test_manifest.py verify
   .venv/bin/python -m pytest -q tests/unit/test_manual_ux_remediation.py tests/integration/test_codex_round3_remediation.py tests/integration/test_local_video_post_import_resilience.py
   cd frontend && npx tsc --noEmit && npm run build && npx vitest run --minWorkers=1 --maxWorkers=1
   ```
3. **持续服务端口状态**：本地人工验证服务运行于 `http://127.0.0.1:8792/`（`913b2c06`，返回 `HTTP 200`）；临时 Chromium 验证端口 `8796` 已清理关闭。
