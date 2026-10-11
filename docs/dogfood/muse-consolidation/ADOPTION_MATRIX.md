# 采用决定矩阵 — 豆包改动与交付物

> 评审分支：`muse/user-pilot-consolidation`（from main `fad25e6`）。决定含义：ACCEPT=直接采用；MODIFY=方向采用、实现需修正；REJECT=不采用；NEEDS_MORE_EVIDENCE=证据不足、暂不决定。

## 一、产品代码改动（6 项）

| # | 改动 | 文件 | 决定 | 理由 |
|---|------|------|------|------|
| 1 | 前端路由：hashchange 区分程序/用户导航，支持前进后退与地址栏 hash | `frontend/src/workspace/App.tsx` | **MODIFY** | 方向正确（修复了真实 Bug：hash 变化不切换视图）。但豆包实现把 `programmaticHash` 存为不带 `#` 的裸页面名（如 `"Settings"`），而 `location.hash` 恒为 `"#Settings"`，去重比较永不命中 → 每次程序导航都被误判为用户导航 → `setImported(false)` 清除导入成功提示。Muse 版已修正为 `"#" + next` / `"#Content"` / `"#" + destinations[kind]` 并加注，已在 muse-work 分支落地。 |
| 2 | 本地提炼 transport 授予 `production_qualified=True` | `src/youtube_intel/runtime_composition.py` | **ACCEPT** | M12 云门禁把本地 transport 硬编码为 `False` 且无任何授予路径，导致本地提炼永远 `WAITING_MODEL`（核心功能失效）。`_production_qualified` 仅用于 `is_authorized_for_normal_production` 这一处；逐次校验（模型名+digest 精确匹配、Ollama 已安装 digest 核对、provider/语言/证据校验）全部保留，安全等级未降；云门禁路径未动。 |
| 3 | 备份就绪检查豁免两类终态 checkpoint | `src/youtube_intel/backup_restore.py` | **MODIFY（部分采用）** | 原决定为 ACCEPT；全量套件对比发现 `WAITING_MODEL`+`invocation_count=0` 豁免破坏 3 个既有集成测试（`test_task022_personalized_distillation.py::test_backup_quiescence_requires_confirmed_user_cloud_success_for_local_wait` 的 3 个参数化用例），这些测试明确要求未调用的本地 WAITING_MODEL 执行继续阻止备份（fail-closed 备份安全语义；另与 `test_quiescence_keeps_resumable_model_work_and_other_attention_runs_blocked` 的命名意图冲突，且与 WAITING_BUDGET 同类状态仍被阻止的处理不对称）。已回退该豁免（删除 `_is_uninvoked_waiting_model` 及其两处调用），保留 `PENDING`+已有 no-new 结果豁免（无争议、确为死终态）及 `_is_cloud_completed_local_wait` 原有路径。详见 ISSUES_FOUND.md M-5。 |
| 4 | 前端新增 2 个回归测试 | `frontend/src/workspace/App.test.tsx` | **ACCEPT** | 覆盖用户 hash 导航切换视图、hashchange 深链接打开内容详情两条核心路径；断言方式合理。Muse 分支独立实测：111 passed（含本项 2 个 + Muse 新增 1 个导入回归测试）。 |
| 5 | 后端新增 1 个回归测试 | `tests/integration/test_runtime_composition.py` | **ACCEPT** | `test_local_distillation_transport_is_production_authorized` 锚定 M12 门禁回归；Muse 分支独立实测通过（套件 10 passed）。 |
| 6 | 后端新增 1 个回归测试（原 2 个，采用 1 个） | `tests/unit/test_backup_restore.py` | **MODIFY** | `test_backup_is_not_blocked_by_completed_no_new_intelligence` 保留（覆盖 PENDING+no-new 结果豁免）；`test_backup_is_not_blocked_by_uninvoked_waiting_model` 随 WAITING_MODEL 豁免回退一并移除（其断言的行为与 3 个既有集成测试矛盾）。Muse 分支独立实测：27 passed。 |

## 二、豆包文档类交付物

| 交付物 | 位置（豆包分支 `~/workspace/intelligence/pilot/docs/dogfood/opencode-user-pilot/`） | 采用态度 | 说明 |
|---|---|---|---|
| 中文用户手册（含 HTML 版） | `USER_MANUAL.md` / `USER_MANUAL.html` | **MODIFY** | 结构完整（17 章）、语言面向普通用户，予以保留并整改为本目录 `USER_MANUAL.md`：① 对照 `frontend/src/workspace/*.tsx` 源码逐项核对按钮名与步骤，不一致处修正；② 删除/修正不可用能力的表述（Bilibili UP 主持续关注、macOS 原生选择器在非 Mac 环境）；③ 模型配置章节明确"本地需 Ollama + digest 匹配、云需单独授权"，不做错误承诺；④ 不复制豆包截图，配图位置以文字注明"截图待 GUI 环境补拍"。 |
| 问题清单 | `ISSUES_FOUND.md` | **参考** | 3 个 Bug 的发现过程与根因分析可信，已被本评审复核吸收；Muse 版 `ISSUES_FOUND.md` 独立重写（含 `#` 缺陷等新发现），不直接复制。 |
| 未解决问题 | `UNRESOLVED_ISSUES.md` | **参考** | U1–U6 分类合理；Muse 版 `UNRESOLVED_ISSUES.md` 在此基础上更新状态（macOS 能力未验证、GUI 未实测、2 个后端失败测试验证中等）。 |
| 体验报告 | `EXPLORATION_REPORT.md` | **参考** | 19 条路径的 GUI 验证记录保留作历史证据；Muse 无浏览器自动化能力，未复做 GUI 验证，`INDEPENDENT_UX_REPORT.md` 仅做代码审查结论并明确标注 CODE REVIEW ONLY，不冒认豆包的 GUI 结果为本次验证。 |
| 最终报告 | `FINAL_REPORT.md` | **参考** | 结构借鉴；Muse 版 `FINAL_REPORT.md` 重写为本轮交付口径，待填项用 [PENDING] 标记。 |
| 验证 harness（`harness/` 脚本） | `harness/browser.mjs`、`p*.mjs` 等 | **ACCEPT（保留）** | 留在豆包分支目录备查；本轮未新增 harness。 |
| 截图（`screenshots/`，49 张） | `screenshots/` | **不复制、不冒充** | 本目录 `screenshots/` 为空占位。USER_MANUAL.md 中配图位置以文字注明"截图待 GUI 环境补拍"，不把豆包截图复制过来冒充新版验证。 |

## 三、待定事项

- Codex 审核状态：[PENDING]（等待安排）。
- 后端全量测试：[PENDING]（后端测试子代理验证中）。
- 前端 vitest：[PENDING]（待 npm install 完成后执行）。
- GUI 真实验证：本轮未做；macOS 特有能力（Keychain/APFS clonefile/原生文件选择器）未验证。
