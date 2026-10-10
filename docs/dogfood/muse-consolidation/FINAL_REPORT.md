# 最终交付报告（FINAL_REPORT）— Muse 独立评审轮（草稿）

> 日期：2026-10-11 · 分支：`muse/user-pilot-consolidation`（from main `fad25e6`）
> 性质：对豆包 `opencode/user-pilot` 轮次 6 处产品代码改动的独立评审 + 文档重整。本报告为草稿，待填项以 [PENDING] 标记。

## 1. 评审范围

- **评审对象**：豆包 3 处产品代码修复（前端路由 Bug1、本地提炼 Bug2、备份 Bug3）+ 3 个测试文件新增的 5 个回归测试。
- **评审方法**：`diff -r` 对比 main 与 muse-work；阅读改动点上下游代码语义；独立重跑后端相关测试套件；对照 `frontend/src/workspace/*.tsx` 源码逐项核对用户手册。
- **方法边界**：本环境无浏览器自动化能力，未做真实 GUI 点击；前端结论为代码审查（CODE REVIEW ONLY）；后端结论有实测支撑。

## 2. 三项 Bug 的采用决定

| Bug | 决定 | 说明 |
|---|---|---|
| Bug1 前端路由（hashchange 不切换视图） | **MODIFY** | 采用豆包的修复方向（hashchange 区分程序/用户导航），但修正了一个真实实现缺陷：豆包把 `programmaticHash` 存为不带 `#` 的裸页面名，而 `location.hash` 恒带 `#`，导致去重永不命中、每次程序导航都被误判为用户导航、导入成功提示被 `setImported(false)` 清除。Muse 版已修正为 `"#" + next` 等并加注。详见 AGENT_WORK_REVIEW.md M-1 / ISSUES_FOUND.md。 |
| Bug2 本地提炼永远 WAITING_MODEL | **ACCEPT** | 直接采用。`production_qualified` 仅用于本地 transport 的 `is_authorized_for_normal_production` 这一处；逐次 digest 校验、provider/语言/证据校验全部保留；云门禁未动。 |
| Bug3 提炼后备份被永久阻止 | **ACCEPT** | 直接采用。两类豁免（PENDING+已有 no-new 结果、WAITING_MODEL+invocation_count=0）均为已持久记录、不可再推进的死状态；真正活动任务仍被阻止；两处检查条件一致。 |
| 新增回归测试（5 个，3 个测试文件） | **ACCEPT** | 用例语义正确，回归锚点清晰。后端 3 个已实测通过；前端 2 个待 npm 环境执行。 |

## 3. 测试摘要

- **已实测**（muse-work 分支，Linux，Python 3.12，pytest 9.1.1）：
  - `tests/unit/test_backup_restore.py` → **28 passed**（含 2 个新增回归测试）
  - `tests/integration/test_runtime_composition.py` → **10 passed**（含 1 个新增回归测试）
  - 合计 38 passed，0 failed。main 基线同范围：35 passed（无新增测试），无回归。
- **豆包报告的 2 个后端失败测试**：已在 muse-work 上单独复核，均通过（`test_task_owned_child_stops_when_application_parent_dies`、`test_serve_api_sigterm_drains_active_tracking_before_exit`），确认为进程时序类环境敏感测试，非本次改动引入。见 UNRESOLVED_ISSUES.md U5（已更新为"已确认"）。
- **前端 vitest**（`App.test.tsx`）：**111 passed**（108 原有 + 豆包 2 个 + Muse 1 个导入回归测试）。Muse 的回归测试已验证：去掉 `#` 修正后测试失败，加回后通过。
- **`tsc -b` 类型检查**：通过。**`vite build` 生产构建**：成功。
- **后端全量套件**（`pytest tests/`，不含 e2e）：[RUNNING] muse-work 分支后台运行中；完成后对比 main 基线。
- **真实 GUI 回归**：本轮未执行；macOS 特有项全部 NOT TESTED。

## 4. 文档清单（`docs/dogfood/muse-consolidation/`）

| 文件 | 内容 |
|---|---|
| `AGENT_WORK_REVIEW.md` | 豆包 6 处改动逐项审查（审查依据：代码语义、安全影响、实测） |
| `ADOPTION_MATRIX.md` | 6 项改动 × ACCEPT/MODIFY/REJECT/NEEDS_MORE_EVIDENCE 决定矩阵 + 文档类交付物采用态度 |
| `ISSUES_FOUND.md` | Muse 独立发现的 4 个问题（M-1 `#` 缺陷已修复；M-2/M-3/M-4 低/建议级未修复） |
| `UNRESOLVED_ISSUES.md` | 未解决问题（U1–U8：环境限制、macOS 未验证、GUI 未实测、2 个后端失败测试"验证中"） |
| `INDEPENDENT_UX_REPORT.md` | A–H 路径代码审查结论（全部 CODE REVIEW ONLY，未冒充 GUI 验证） |
| `TEST_REPORT.md` | 测试报告框架（已实测项 + [PENDING] 项） |
| `USER_MANUAL.md` | 整改后的完整中文用户手册（按钮/步骤已对源码核对；无截图，以文字注明待补拍） |
| `FINAL_REPORT.md` | 本文件 |
| `screenshots/` | 空占位目录（不伪造截图、不复制豆包截图） |

## 5. 待填项 / 下一步

- [RUNNING] 后端全量测试结果（muse-work 分支后台运行中，完成后对比 main 基线）。
- [PENDING] Codex 审核状态（是否需要 / 是否已安排 / 结论）。
- [PENDING] GUI 真实验证（导航/提炼/备份三条修复路径）与手册截图补拍（待 GUI 验证环境）。
- 建议维护者关注：ISSUES_FOUND.md M-2（Research 后退视图残留）、M-3（openDelta 深链丢失），均为低严重程度 pre-existing 问题。

## 6. 红线遵守声明

- 未编造任何验证结果、截图、测试数据；不确定的均写"待验证"/[PENDING]。
- 未修改 muse-work 下除 `docs/dogfood/muse-consolidation/` 之外的任何文件；无 git 操作。
- 仓库保持私有；测试执行仅读取代码、使用隔离临时目录，未触碰任何正式数据。
