# 创始人决策请求队列（Founder Decision Requests · L3）

> **边界声明**：凡涉及对外发布可见性、主线 `main` 合流、真人用户开放试跑及后台调度授权的事项，严格归属创始人 **L3 终审权限**。在创始人明确回复批准前，AI 产品负责人绝不擅自假定放行或越权执行。

---

## 待审批 L3 请求（PENDING）

- *当前暂无待审批的 L3 决策请求*（`FD-001` ~ `FD-009` 已全部按创始人批复执行完结；`EXP-001` 与 `BL-009` 继续维持 `HOLD`，仓库保持被动 `PUBLIC`、零外宣、无 GitHub Release、保留 4 个历史 tag）。

---

## 历史已完结 L3 决策归档（2026-11-23 ~ 11-24）

- **`FD-009`（`COMPLETED` — 完成双端实机浏览器走查后，执行选项 A 将 Iteration #10 / `BL-013` 线性合流 `main` 并获云端 14 组 CI 双绿验收）**：
  1. **合流前实机浏览器真人模拟走查（Ports `8793` + `8794` PASS）**：在真实 Chromium（`1440×900` 桌面端 + `375×812` 移动端 & Obsidian Dark / Warm Paper Light 双主题）完整验证：
     - `http://127.0.0.1:8793`（Offline Demo）：全部 3 条默认推荐提问胶囊 + 专题推荐胶囊均稳定返回有据回答与 3 条引用卡片，越域问题「Ollama 本地模型的价格是多少？」明确拒答且 0 引用，历史会话切换、`⌘K` 专题直达及视频/`demo-architecture-notes.md` 详情导出控件全通；
     - `http://127.0.0.1:8794`（355 条内容库，含 220 条新视频 + 135 条旧匹配视频）：`#Content` 远程搜索首屏返回 `100 / 135`、点击「加载更多搜索结果」扩展至 `135 / 135`、`⌘K` 显示 `库内命中共 135 条` 截断提示；全流程 `0` console error / `0` page error / `0` HTTP `>=400` / `0px` 横向溢出；
  2. **线性合流 `main` 与云端 CI 全绿验收**：经 Claude Round 3 结论 A 放行与实机通过后，将 `c16f0e8`、`0519284`、`b28ba5d` 线性拣选合入 `main@37bb685` 并推送；首轮云端 [`#45337676192`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45337676192) 仅新接入第 14 组中的 `test_p2_01_p2_02_p2_06` 因未断网隔离本机 Ollama 地址导致 1 项失败（业务代码零缺陷）；补充纯测试隔离提交 `5e7dac3` 合入 `main@4f3fe7084814198fb31fef668aebabf4d05aab91` 后，[`Public Beta CI #45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 双作业全绿通过——`Frontend Build & Vitest` `1m37s`（`vite build` `1.37s` + `57/57` / `1257/1257` tests passed）与 `Python Lint, Typecheck & Public Beta Integration` `5m55s`（`ruff`/`mypy` 137 文件 0 错 + 14 组全量 **`175 passed in 309.20s (0:05:09)`**）；
  3. **严守被动公开与内部阶段红线**：核验仓库维持 `PUBLIC`（`Stars: 0`、`Forks: 0`、无 GitHub Release、`no releases found`，保留 4 个历史 tag）、零外部推广，真人试点 `EXP-001` 与 `BL-009` 继续维持 `HOLD`。

- **`FD-008`（`COMPLETED` — 创始人批复将 Iteration #9 / `BL-012` 合流 `main` 并留存云端绿标）**：
  1. **线性合流 `main`**：将研发分支 `antigravity/task-user-readiness-20261112` 提交 `3a92efb`（含 Round 19 `⌘K` 深入专题洞察/追问动作、`#Topics` 搜索排序、提问框防遮挡细滚动条、`--check-only` 一行式就绪结论及新增测试）在临时隔离 worktree 线性合入 `main@c54b8184df45b7befb9944d4763d2fa59ed2bd5e` 并推送 `origin/main`（后续台账收口同步至 `main@ca4e17f`）；
  2. **云端 GitHub Actions 双端全绿验收**：[`Public Beta CI #45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) 双作业 `success`——`Frontend Build & Vitest` `1m7s`（`vite build` `1.08s` + `56/56` / `1249/1249` tests passed）与 `Python Lint, Typecheck & Public Beta Integration` `5m0s`（仅失败重跑：首轮云端 `test_fast_read_api.py` 实测 `149.3ms > 120ms` 未通过，未改源码也未放宽阈值，重跑即 `ruff`/`mypy` 137 文件 0 错 + 13 组全量 **`152 passed in 256.97s`**）；`main@ca4e17f` [`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703) 一次全绿；
  3. **严守被动公开与内部阶段红线**：核验仓库维持 `PUBLIC`（`Stars: 0`、`Forks: 0`、无 GitHub Release、`no releases found`，保留 4 个历史 tag）、零外部推广，真人试点 `EXP-001` 与 `BL-009` 继续维持 `HOLD`。
- **`FD-007`（`COMPLETED` — 创始人批复将 Iteration #8 / `BL-011` 合流 `main` 并留存云端 13 组绿标）**：
  1. **线性合流 `main`**：将研发分支 `antigravity/task-user-readiness-20261112` 提交 `e540b28`（含按需轻量关键帧融合分析 MVP、`WorkspaceVisualKeyframes.test.tsx`、`test_visual_keyframe_analysis.py` 及 `.github/workflows/ci.yml` 第 13 组 CI 接线）在临时隔离 worktree 线性合入 `main@092951bfb19a4664cc1f0cc36fa631120b217f8c` 并推送 `origin/main`；
  2. **云端 GitHub Actions 双端全绿验收**：[`Public Beta CI #45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) 双作业 `success`——`Frontend Build & Vitest` `1m19s`（`vite build` `1.30s` + `55/55` / `1247/1247` tests passed in `60.13s`）与 `Python Lint, Typecheck & Public Beta Integration` `19m59s`（`ruff` / `mypy` 137 文件 0 错 + 13 组完整套件 `151 passed in 305.18s`）；
  3. **严守被动公开与内部阶段红线**：核验仓库维持 `PUBLIC`（`Stars: 0`、`Forks: 0`）、`no releases found`、零外部推广，真人试点 `EXP-001` 与 `BL-009` 继续维持 `HOLD`。
- **`FD-006`（`COMPLETED` — 创始人批复将 Iteration #4–#7 合流 `main` 并留存云端绿标）**：
  1. **合流 `main` 与扩展云端 CI 守卫**：将 Iteration #4–#7 全部验证成果（`6760028` / `2be958f` / `dbc7e89` / `f908d95`）连同 [`test_long_media_and_obsidian_vault.py`](../tests/integration/test_long_media_and_obsidian_vault.py) 接入 `.github/workflows/ci.yml`（`028d10e`），线性合入 `main@aec26da2190a235f03be0b0013080b76b06c5b15` 并推送 `origin/main`；
  2. **云端 GitHub Actions 双端全绿验收**：[`Public Beta CI #45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双作业 `success`——`Frontend Build & Vitest` `1m43s`（`vite build` `1.52s` + `54/54` / `1244/1244` tests passed）与 `Python Lint, Typecheck & Public Beta Integration` `4m42s`（`ruff`/`mypy` 0 错 + 12 组套件 `146 passed in 231.25s`）；
  3. **严守被动公开与内部阶段红线**：核验仓库维持 `PUBLIC`（`Stars: 0`、`Forks: 0`）、无 GitHub Release（保留 4 个历史 tag）、零外部推广，真人试点 `EXP-001` 与 `BL-009` 继续维持 `HOLD`。
- **`FD-005`（`COMPLETED` — 创始人明确批复执行三项裁定）**：
  1. **仓库维持 `PUBLIC` 被动状态且严守零外宣**：仅保持代码可见，无 GitHub Release（本轮不新增发布标签）、零外部推流、零真人私信或招募；
  2. **批准合流 `main` 并激活最新云端绿标**：已将 Iteration #3 与 Stage C/E 全套验证提交（`b8759e0`、`fee43f4`、`256a058`）同步合入 `main@f23954f9f1f7922ce626e3bbdafe4ee2d8ca01aa`，GitHub Actions [`Public Beta CI #45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端全绿（`Frontend Build & Vitest` `1m43s` + `Python Lint, Typecheck & Public Beta Integration` `3m14s`）；
  3. **继续 `/goal` 内部自主迭代、真人测试再缓缓**：保持当前“内部自主迭代与产品完善阶段”硬边界，`EXP-001` 维持 `HOLD`，直至创始人另行批准退出阶段门槛。
- **`FD-004`（`COMPLETED`）**：Iteration #2（零配置 `youtube-intel start`）同步上 `main@a820152` 且 CI [`#45137542384`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45137542384) 双端全绿。
- **`FD-003`（`COMPLETED`）**：创始人在 Antigravity Automations 面板启用每晚 `21:00 (Asia/Shanghai)` 自动巡检与日报侧车（`launchd` 继续未注册）。
- **`FD-002`（`COMPLETED` — 仅完成仓库 `PUBLIC` 公开；其附带外部 `EXP-001` 邀测已随现行内部完善边界裁定暂置 `HOLD`）**。
- **`FD-001`（`COMPLETED`）**：历史基线同步至 `main@9f65417` 且 CI [`#45132090574`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45132090574) 双端全绿。
