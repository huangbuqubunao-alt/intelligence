# 创始人决策请求队列（Founder Decision Requests · L3）

> **边界声明**：以下事项触及代码主线合并、公开仓库可见性、外部用户触达与无人值守定时开启，严格属于创始人 **L3 终审权限**。在您未明确答复前，AI 产品负责人绝不默认视为批准或越权执行。

---

## FD-001：将工作分支 4 笔已全量验证提交整合进 `main` 并推送 `origin/main` 激活 GitHub Actions

- **状态**：`COMPLETED (方案 A 已执行 · 2026-11-23)` — `main` 已同步至 `9f65417a6589823096bea5c6ae7d7580a602822a`，GitHub Actions [`Public Beta CI #45132090574`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45132090574) 双 Job 全绿通过（仍维持 `PUBLIC_BETA`，未打正式推广 Tag）。
- **需要决定什么**：是否批准将分支 `antigravity/task-user-readiness-20261112` 上的新增验证提交（Batch 1 安全/成本防线 `0fc61a7`、Batch 2 反幻觉拒答与 C4 恢复 `c85625b`、Batch 3 Markdown `TEXT_RANGE`+周报 7 天窗口+250 库检索 `89a9878`、Batch A 深链出处与日报引擎 `09f98d4`，以及 `product-ops/` 运营台账）cherry-pick / 整合回本地 `main` 并 `git push origin main`（同时维持 `PUBLIC_BETA` 定位，**暂不打对外正式 Release Tag**）。
- **为什么现在需要决定**：目前 `main` 与 `origin/main` 仍停留在 `4c034b7`，缺少上述安全修复、20 例反幻觉基准、跨源 Markdown 支持与可携带深链导出，且 GitHub Actions 在 `main` 上仍显示 `0` 次运行，阻塞后续对外试跑。
- **已有市场和用户证据**：Codex 独立源码评审指出的 Demo 误删与静默云端扣费阻塞均在分支已修并通过验证，[ci.yml](../.github/workflows/ci.yml) 已落地只待推主线触发云端双端运行。
- **方案 A / B / C**：
  - **方案 A（推荐）**：立即整合至 `main` 并推送 `origin/main`，观察 GitHub Actions（Python + Frontend）云端首跑全绿；仍保留 `PUBLIC_BETA` 与 Private 可见性，直到 `FD-002` 与 `EXP-002` 实机基准就绪。
  - **方案 B**：仅整合到局部测试分支暂不推 `origin/main`（导致线上主线滞后且 CI 始终无运行记录）。
  - **方案 C**：维持现状不动（安全修复长期滞留在个人 worktree 中）。
- **成本、收益及风险**：成本约 5 分钟 Git 整合、**$0**；收益为主线闭环与云端 CI 可见绿盾；风险极低（10 组 `pytest` `133/133` 与 Vitest `54/54` / `1237/1237` 已全部本地全绿）。
- **你推荐的方案**：**方案 A**。
- **推荐依据与信心程度**：本地全量自动化测试、静态类型与构建全部 0 失败，信心 **95%**。
- **如果暂不决定会发生什么**：产品主线继续停留旧代码状态，无法利用 GitHub Actions 自动验收，也无法基于安全完整版邀请外测用户。

---

## FD-002：授权将 GitHub 仓库转为 `PUBLIC` 并开展限额 5–10 名种子用户内测（`EXP-001`）

- **状态**：`COMPLETED (方案 A 已执行 · 2026-11-23)` — 在 `EXP-002`、`SEC` 合规复核及 CI `#45132090574` 双端全绿后，`https://github.com/huangbuqubunao-alt/intelligence` 已转为 **`PUBLIC`**（Apache-2.0），可直接向 5–10 名种子用户发出 `EXP-001` 内测邀请。
- **需要决定什么**：在 `FD-001`（主线同步 + CI 绿灯）与 `EXP-002`（真实 Ollama 陌生双语样本验证）完成后，是否授权将 `https://github.com/huangbuqubunao-alt/intelligence` 由 **`PRIVATE`** 转为 **`PUBLIC`**（Apache-2.0 协议），并允许整理发帖文案供您在目标小圈子内邀请 5–10 名外部双语研究者试用。
- **为什么现在需要决定**：`gh repo view` 显示仓库当前 `PRIVATE`，只要它不对外公开且没有真实使用者，产品的“核心价值/激活率/留存率”将永远停留在 `暂无数据`，产品就无法脱离工程阶段进入真实市场经营。
- **已有市场和用户证据**：2026-11-23 外部调研确认开源本地研究助手（`open-notebook` 4.2 万★ / `BiliNote` 7.8 千★）及 Reddit `r/notebooklm` 对“反幻觉 + 本地隐私 + Obsidian 联动”需求明确，但尚缺本产品自身的一手留存实证。
- **方案 A / B / C**：
  - **方案 A（推荐）**：分两步走——先把仓库在合规复查（确认 `.env` / `.var/owner` 零泄漏）后转为 `PUBLIC` 并低调开放 `v0.1.0 Public Beta`，由创始人向 5–10 位精准 Obsidian/双语科研朋友定向发内测邀请（`EXP-001`），先不泛网投流。
  - **方案 B**：仓库维持 `PRIVATE`，仅本地压缩发 2–3 位熟人私下试用（可测体验，但无法测试 GitHub 下载与开源漏斗）。
  - **方案 C**：暂不公开、继续闭门打磨新功能（强烈反对：脱离真实用户继续加功能是早期产品最大浪费）。
- **成本、收益及风险**：成本 **$0**（Apache-2.0 合规声明已备齐）；风险在于开源后可能收到安装环境报错 Issue 或曝光个人代码风格（应对：README 清晰标明 `PUBLIC_BETA` 定位与支持矩阵）。
- **你推荐的方案**：**方案 A**（前置：先完成 `FD-001` 与合规复检）。
- **推荐依据与信心程度**：闭门测试已完成充分验证，继续内部迭代边际收益递减，必须用真实外部样本校准方向，信心 **85%**。
- **如果暂不决定会发生什么**：北极星指标与用户增长漏斗将继续长期为 `暂无数据`，所有后续功能判断都只能停留在假设层面。

---

## FD-003：授权开启每晚 21:00 (Asia/Shanghai) 自动巡检与运营日报 Sidecar 调度

- **状态**：`COMPLETED (方案 A 已启用 · 2026-11-23)` — 已完成试跑与权限核验，并已由创始人在 Antigravity Automations 面板点击启用每晚 `21:00 (Asia/Shanghai)` 自动运行（`launchd` 继续保持未注册）。
- **需要决定什么**：是否由您在 Antigravity 面板启用已创建的 **`Intelligence 每日产品负责人运营日报`** 定时任务（每天北京时间 `21:00` 自动巡检仓库 Git、CI、市场竞品动向与 `product-ops/CURRENT_STATE.md` 并产出 `product-ops/reports/daily/<YYYY-MM-DD>.md`），以及未来是否授权配置项目自带 `config/launchd/` 模板用于本机内容定时采集。
- **为什么现在需要决定**：依据安全与系统指令纪律，AI 绝对不得擅自修改调度激活配置（`user_config.json`）或注册 `launchd`，否则“声称无人值守运行”即属虚假承诺；需要您显式授权或在控制台开关启用。
- **已有市场和用户证据**：工程上每天都有代码/CI/外部 GitHub 竞品变化，固定 21:00 落盘结构化日报能大幅压缩创始人管理负担。
- **方案 A / B / C**：
  - **方案 A（推荐）**：由您在 Antigravity Automations 面板审核权限作用域后开启 **`Intelligence 每日产品负责人运营日报`**（仅读写本工作区与 `product-ops/`，零付费模型调用与外网发帖），本机 `launchd` 仍继续暂缓按需开启。
  - **方案 B**：不启用后台定时，仅在每次手动开启会话时由您口头触发 AI 执行 `generate_daily_ops_report.py`。
  - **方案 C**：完全不维护日报（不符合持续产品运营要求）。
- **成本、收益及风险**：若本机 Antigravity 常驻开机，每天 21:00 自动刷新一次日报，**无额外第三方 SaaS 预算开销**（消耗 Antigravity 本身对话配额）；若电脑休眠/未开启对应自动化则会跳过当天触发。
- **你推荐的方案**：**方案 A**（日常日报交给 Antigravity 自动化调度；系统级 `launchd` 等真正跑日常真库采集时再单独批）。
- **推荐依据与信心程度**：脚本 [generate_daily_ops_report.py](../scripts/generate_daily_ops_report.py) 已内置只读安全与防覆盖保护并经 pytest 验收，信心 **90%**。
- **如果暂不决定会发生什么**：每日 21:00 无法实现无人值守自动产报，须靠您主动打开对话触发手动更新。

---

## FD-004：将迭代 #2（零配置 `youtube-intel start` 冷启动修复）同步上公开 `main` 分支

- **状态**：`PENDING`（等待创始人 L3 审批；推荐在对外发出 `EXP-001` 邀请前批准）
- **需要决定什么**：是否批准将分支 `antigravity/task-user-readiness-20261112` 上刚完成并全量验收的零配置 `youtube-intel start` 启动器、前置检查清单、`serve-api` `vault_root` 友好提示、5 个新增集成测试及新版 `README.md` 5 分钟上手指南整合回公开的 `main` 与 `origin/main`（仍保持 `PUBLIC_BETA` 不打正式推广 Release Tag）。
- **为什么现在需要决定**：按原 README 直接运行 `serve-api` 在纯新克隆机器上会因 `settings.example.yaml` 占位路径 `/absolute/path/to/obsidian/vault` 直接以 `Exit Code 2` 崩溃；现在仓库已转为 `PUBLIC`，若不在发出 `EXP-001` 邀请前同步上 `main`，外测用户拿到手第一条命令就会失败触发冷启动止损。
- **方案 A / B / C**：
  - **方案 A（推荐）**：立即整合至 `main` 并推送 `origin/main` 等 GitHub Actions（11 组 Python 套件 + Frontend Vitest）全绿，随后再用 1 条 `uv run youtube-intel start` 版文案发出 `EXP-001` 邀请。
  - **方案 B**：暂不更新 `main`，改在邀请消息里私聊提醒测试者手工修改 `config/settings.yaml` 的 `vault_root`（仍有漏看导致首次必崩风险）。
  - **方案 C**：维持旧 `main` 不动，暂不发邀请。
- **成本、收益及风险**：成本约 5 分钟 Git 整合 + CI 运行、**$0**；收益直接消除首个 100% 冷启动阻断；风险极低（已通过本地 `uv lock`、`ruff`、`mypy --strict` 及全套 CI Pytest）。
- **你推荐的方案**：**方案 A**（信心 **95%**）。
- **如果暂不决定会发生什么**：公开仓库 `main` 默认上手流程仍存在 `vault_root` 首次崩溃坑，`EXP-001` 邀测只能先用手工修改配置绕过。
