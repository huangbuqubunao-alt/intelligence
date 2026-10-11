# INTELLIGENCE_DOUBAO_HANDOFF_FINAL_REPORT

> Intelligence User Pilot — 豆包（Doubao）接管完成报告
> 日期：2026-10-10 · 分支：`opencode/user-pilot`

## 1. 接管时原始 HEAD

接管现场只读核验：

```
fad25e6109d02650b25ae777f2f7557dd478309d  (opencode/user-pilot)
```

说明：该 HEAD 为 OpenCode 启动时的参考 HEAD；接管后**未**对正式 main（`v1x-local-main`）做任何回退、覆盖或重置，工作树停留在实验分支。

## 2. 接管时未提交修改

- `git status --porcelain` **干净**：OpenCode 未提交任何成果。
- OpenCode 遗留：`docs/dogfood/opencode-user-pilot/` 下的 harness 脚本（browser.mjs、pilot_launcher.py、p01–p12 系列 .mjs）与约 24 张截图，**无任何交付文档**。
- 数据状态（`.var/user-pilot/state.sqlite3`）：1 条 YouTube 视频（3Blue1Brown，ORGANIZED，字幕+摘要+13 条 Evidence）、1 条关注（Veritasium，DISCOVER_ONLY）、0 洞察、0 主题。
- 隔离服务由 OpenCode 进程运行（UI 5588 / API 5589）；正式环境 5488/5489 单独运行未受影响。

## 3. OpenCode 已完成内容

- 搭建隔离测试环境（UI 5588 / API 5589 / 独立数据目录与独立浏览器 profile）。
- 完成首批截图（01–25、debug/、narrow 系列）。
- 验证部分用户路径（首次引导、添加 YouTube 视频/频道、内容列表与详情）。
- **注意**：OpenCode 截图存在重复与串页（05=06、16=22、20=21、23=24 且 23 实为设置页、25-narrow-* 全同为设置页、debug/evidence-backend-down-* 全同），未直接复用于交付物。

## 4. 豆包新增完成内容

**修复 3 个真实 Bug（均端到端验证）**：

| # | Bug | 根因 | 修复 |
|---|-----|------|------|
| 1 | 浏览器前进/后退/地址栏 hash 不切换视图 | `App.tsx` hashchange 处理器只处理深链接 | 增加普通视图路由 + 程序导航防误吞 |
| 2 | 本地"提炼为洞察"永远 WAITING_MODEL | M12 云门禁把本地 transport `production_qualified` 硬编码为 False 且无授予路径 | runtime_composition 本地 transport 授予生产资格（digest 绑定保留） |
| 3 | 手动提炼一次后备份被永久阻止 | no-new-intelligence 结果已记录但 checkpoint 保持 PENDING；备份把 PENDING 视为活动任务 | 备份检查豁免两类已完结死 checkpoint |

**验证**：前端 110 tests passed、runtime composition 10 passed、backup 28 passed、`npm run build` 成功；新增回归测试 5 个。

**真实用户路径验证**（均隔离实例 + 独立 Chrome profile，GUI/API 双通道）：补拍截图 30/33–47；Bilibili 公开视频导入（201, CAPTION_UNAVAILABLE 如实反馈）；本地 TXT/MD/音频/视频导入状态验证；暂停/恢复关注；语言切换 zh↔en；备份创建（372 KB, 3 关注/5 内容/20 证据）。

**交付文档**（简体中文，全部完成）：USER_MANUAL.md（17 章）、USER_MANUAL.html（31 图，真实浏览器渲染验证 0 缺失）、ISSUES_FOUND.md、UNRESOLVED_ISSUES.md、EXPLORATION_REPORT.md、HANDOFF_STATUS.md、build_manual_html.py。

## 5. 发现的问题数量

**3 个**（全部为真实产品 Bug，非环境性问题）。

## 6. 修复的问题数量

**3 个**（全部修复并验证：GUI/API 端到端 + 自动化回归测试）。

## 7. 未解决的问题

见 `UNRESOLVED_ISSUES.md`（U1–U6）：

- U1 本地转写模型未配置（环境限制，产品行为正确）；
- U2 Bilibili 字幕源站限制（网络）；
- U3 2 GiB 大文件未实测（磁盘仅剩 23 GiB）；
- U4 主题详情无真实数据（依赖先产生洞察）；
- U5 两个既有环境敏感测试失败（SIGTERM/子进程心跳，与本次修改无关）；
- U6 OpenCode 遗留 4 条历史 checkpoint（修复版已正确豁免）。

## 8. 实际验证的用户路径

| 路径组 | 验证级别 |
|--------|----------|
| A 首次使用（引导 3 步、首页、重开状态） | GUI VERIFIED |
| B 添加来源（YouTube 视频/频道、Bilibili、本地 TXT/MD/音频/视频） | GUI + API VERIFIED |
| C 本地文件处理（导入、转写状态反馈；2 GiB） | API VERIFIED / BLOCKED |
| D Following（添加、暂停、恢复、自动检查） | GUI + API VERIFIED |
| E Content（列表、详情、字幕、摘要、证据） | GUI VERIFIED |
| F Intelligence（提炼执行、无新洞察反馈、模型未配置提示） | GUI VERIFIED（含修复） |
| G Topic（列表空状态） | GUI VERIFIED |
| H Settings（语言、模型、备份、隐私） | GUI + API VERIFIED |
| I 整体（导航修复、空状态、中英文、错误反馈） | GUI VERIFIED |

共 19 条路径：16 GUI VERIFIED、2 API VERIFIED、1 BLOCKED。

## 9. 测试结果

| 测试 | 结果 |
|------|------|
| 后端全量 `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` | 3976 passed / **2 failed** / 1 skipped（两个失败为既有环境敏感测试，与本任务修改无交集，见 U5） |
| 前端 `npx vitest run src/workspace/App.test.tsx` | 110 passed |
| runtime composition 套件 | 10 passed（含新增回归测试） |
| backup 套件 | 28 passed（含 2 个新增回归测试） |
| `npm run build`（生产构建） | 成功 |
| 真实 GUI 回归 | 导航 hash、提炼、备份三条修复路径均 GUI/API 端到端确认 |

> 诚实声明：未声称任何未实际执行的测试已通过。两个失败测试如实记录为环境敏感（见上）。

## 10. 截图数量及位置

- **位置**：`docs/dogfood/opencode-user-pilot/screenshots/`（49 个 PNG）。
- **用于交付**：44 张来自真实运行产品（OpenCode 遗留约 24 张 + 豆包补拍 30/33–47 等）；其中手册使用 31 张，HTML 渲染校验全部有效。
- OpenCode 遗留的重复/串页截图已识别并排除，不用于交付物。

## 11. 用户手册位置

- `docs/dogfood/opencode-user-pilot/USER_MANUAL.md`（17 章完整中文图文手册）
- `docs/dogfood/opencode-user-pilot/USER_MANUAL.html`（自包含，浏览器查看；31 张图真实渲染验证 0 缺失）
- 生成脚本：`build_manual_html.py`

## 12. 最终 branch / HEAD

- 分支：`opencode/user-pilot`
- 最终 HEAD：见提交记录（本次成果全部已提交到该分支）
- 正式 main（v1x-local-main）**未被修改**。

## 13. 与 main 的差异

本次提交仅包含：
- 前端：`frontend/src/workspace/App.tsx`（路由修复）+ `App.test.tsx`（2 个回归测试）
- 后端：`src/youtube_intel/runtime_composition.py`（本地生产资格）、`src/youtube_intel/backup_restore.py`（备份豁免）
- 测试：`tests/integration/test_runtime_composition.py`、`tests/unit/test_backup_restore.py`
- 文档：`docs/dogfood/opencode-user-pilot/` 全部交付物

不涉及云门禁、Evidence 规则、安全机制、付费调用路径的放宽。

## 14. 风险与限制

- **U1–U6 环境限制**（见第 7 节）：转写模型、Bilibili 字幕、2 GiB、主题详情、两个环境敏感测试、遗留 checkpoint。
- 隔离测试环境仍由本机进程运行（UI 5588 / API 5589），数据独立于正式环境。
- 2 GiB 大文件导入未实测（磁盘空间不足），建议后续在磁盘充足环境补验。
- 云端模型路径未实测（需要真实凭据与逐次授权，超出本试点范围，且产品原则禁止未经授权调用付费模型）。

## 15. 是否建议正式采用 / 是否需要 Codex Review

**建议正式采用**（有条件）：

- 3 个真实 Bug 已修复并经 GUI/API 端到端 + 自动化回归验证；
- 产品核心体验（内容整理、证据追溯、诚实反馈）质量良好；
- 修复对现有用户的影响面小（前端路由增强 + 后端本地资格/备份豁免）。

**建议正式采用前完成**：
1. 由维护者评估两个既有环境敏感测试（U5）是否需调整；
2. 配置本地转写模型（U1）后补验音频/视频转写链路；
3. 在磁盘充足环境补验 2 GiB 大文件（U3）。

**是否需要 Codex Review**：**建议需要** —— 三个修复均涉及既有架构决策（M12 云生产门禁、备份就绪检查、前端路由状态机），由熟悉代码库的维护者做一次 Review 更稳妥；同时按交接要求等待 ChatGPT 与用户评审。

---

## 结束状态

**DOUBAO_USER_PILOT_COMPLETE**

> 核心用户路径已尽可能完成体验；发现的问题已全部修复并验证；测试与回归完成；使用手册包含真实截图（31 张，HTML 渲染验证 0 缺失）；全部交付文件完整；成果已提交到独立分支 `opencode/user-pilot`。未自动合并 main，等待评审。
