# HANDOFF_STATUS — Muse 独立评审轮

> 分支：`muse/user-pilot-consolidation` · 基线：main `fad25e6` · 更新：2026-10-11

## 分支与 HEAD
| 项 | 值 |
|---|---|
| Muse 分支 | `muse/user-pilot-consolidation` |
| 当前 HEAD | `0667a285`（2026-10-11，M-5 回退提交） |
| 基线 main HEAD | `fad25e6109d02650b25ae777f2f7557dd478309d`（已核实，未动） |
| 豆包分支 HEAD | `8d63bbfeb5a764a0dc2cee8aa540e102a22ed6f4`（只读参考，未动） |

## 提交历史（本分支）
| SHA（短） | 内容 |
|---|---|
| `e986cfe7` | 3 处 Bug 代码修复（Bug1+`#`修正、Bug2、Bug3） |
| `fa88c71b` | 回归测试（豆包 5 个 + Muse 1 个导入回归测试） |
| `92883646` | `docs/dogfood/muse-consolidation/` 8 个文档 |
| `a2e03f2d` | HANDOFF_STATUS.md（分支状态记录） |
| `0667a285` | M-5：回退 Bug3 的 WAITING_MODEL 豁免（3 个既有集成测试回归）+ 6 个文档更新 |

## 已完成
- [x] 三项 Bug 审查与落地（Bug1=MODIFY 含 `#` 修正、Bug2=ACCEPT、Bug3=MODIFY 部分采用：保留 PENDING 豁免，回退 WAITING_MODEL 豁免）
- [x] M-5：全量套件对比发现豆包 WAITING_MODEL 豁免破坏 3 个既有集成测试，已回退并定向验证 40 passed
- [x] 后端全量套件对比：muse-work 704 failed/3265 passed vs main 基线 702 failed/3264 passed；差集仅 M-5（已修复）+ 1 个环境抖动项，其余 701 个失败两分支完全一致（pre-existing 环境限制），无新增回归
- [x] 6 个测试文件改动（豆包 4 个测试采用 + Muse 1 个新回归测试；1 个随 M-5 回退移除）
- [x] 后端相关套件实测：`test_backup_restore.py` 27 passed、`test_runtime_composition.py` 10 passed、task022 3 用例 passed（muse-work）
- [x] 豆包 2 个失败测试复核：在全量套件中未出现 FAILED，确认为环境敏感时序测试
- [x] 前端：111 passed（App.test.tsx）、`tsc -b` 通过、`vite build` 成功
- [x] 8 个中文文档 + 空 screenshots 占位（无伪造）
- [x] 提交已推送，无 force push，未动 main / opencode 分支

## 未完成 / 进行中
- [ ] Codex 审核：等待安排（M-5 回退决定请 Codex 复核）
- [ ] GUI 真实验证：本环境无浏览器自动化能力，未执行
- [ ] 手册截图补拍：待 GUI 验证环境

## 测试结果（已确认）
| 范围 | main 基线 | muse-work | 结论 |
|---|---|---|---|
| 后端全量（`pytest tests/` 不含 e2e） | 702 failed / 3264 passed | 704 failed / 3265 passed（含 M-5 回退前） | 差集=3 个 M-5 回归（已修复）+ 1 环境抖动；其余 701 失败完全一致，无新增回归 |
| 后端定向验证（回退后） | — | 40 passed（backup_restore 27 + runtime_composition 10 + task022 3） | M-5 修复确认 |
| 前端 App.test.tsx | 110（豆包分支值；main 为 108） | 111 passed | 无回归 |
| 类型检查 / 构建 | — | tsc 通过，vite build 成功 | — |
| 豆包 2 个失败测试 | — | 全量中未出现 FAILED | 环境敏感，非改动引入 |

## 未解决问题
见 `docs/dogfood/muse-consolidation/UNRESOLVED_ISSUES.md`（U1–U8）。关键：
- macOS 特有能力（Keychain/APFS clonefile/原生选择器）：NOT TESTED
- GUI 未实际运行验证：本轮方法边界
- M-2/M-3：低严重程度 pre-existing 问题，未修复

## 给下一位 Agent 的说明
- 本分支所有改动均已提交并推送；`main` 与 `opencode/user-pilot` 未被触碰。
- 后端全量测试日志：`~/workspace/muse-backend-tests.log`（muse-work）、`~/workspace/main-backend-tests.log`（main 基线）；失败集合差集结论见 TEST_REPORT.md。
- 工作区：`~/workspace/intelligence/muse-work`（muse 分支内容）；`~/workspace/intelligence/main`（基线，只读）。
- venv：`~/workspace/intelligence/venv`；前端 node_modules 已装（`--ignore-scripts`，playwright 浏览器未下载）。
- M-5 回退说明：`src/youtube_intel/backup_restore.py` 中仅保留 PENDING+no-new 豁免；如 Codex 认为 WAITING_MODEL 豁免应以更窄条件保留，需同步更新 3 个 task022 集成测试的断言（仓库红线：不得弱化测试，需用户/主控明确批准）。
- 如需继续：等 Codex 审核结论；GUI 真实验证与手册截图需有浏览器自动化能力的环境。
