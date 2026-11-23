# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-23（`Asia/Shanghai`）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`
- **最新已验证主线基线（`main` & `origin/main`）**：`9f65417a6589823096bea5c6ae7d7580a602822a`（GitHub Actions [`Public Beta CI #45132090574`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45132090574) Python + Frontend 双 Job 均 `success`）

---

## 核心运行状态快照

- **当前产品目标**：通过 `EXP-001` 定向邀请首批 5–10 名 Obsidian / 双语研究者完成真实冷启动、跨源核验与导出闭环，并回收首轮激活与留存数据。
- **正在进行的任务**：等待创始人批复 `FD-004` 将零配置 `youtube-intel start`（`DEC-OPS-005`）同步上公开 `main` 并在 CI 全绿后，发出首批 `EXP-001` 定向内测邀请。
- **最近完成的步骤**：
  1. 完成全面产品/技术现状审计与 2026-11-23 一手市场及 10 竞品调研；
  2. 完成 L1 高价值迭代 #1（`09f98d4`）及全套本地门禁校验；
  3. 完成 `EXP-002` 本机免费 `ollama/qwen3.5:9b` 隔离实测（**3/3** 跨源有引用作答 + **2/2** 诱导拒答 + 深链 `.md` 导出零 `00:00` 伪时间戳，总耗时 `227.6s`）；
  4. **完成 `FD-001` / `FD-002` / `FD-003`**：合流并修复跨平台 CI 至 `main@9f65417`（[`#45132090574`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45132090574) 双 Job 全绿）、公开 GitHub 仓库（`PUBLIC` · Apache-2.0），并启用每晚 `21:00` 日报自动化；
  5. **完成 L1 自主迭代 #2（`DEC-OPS-005`）**：在纯新克隆模拟时捕获 `serve-api` 因占位路径 `/absolute/path/to/obsidian/vault` 触发的 100% 冷启动 Exit Code 2 崩溃，实现零配置 [workspace_launcher.py](../src/youtube_intel/workspace_launcher.py)（`uv run youtube-intel start`、`--check-only`、`--vault`）、共用 `run_fast_read_server_loop`、`serve-api` `vault_root` 友好排错提示、新版 `README.md` 5 分钟上手清单及 [test_workspace_start_launcher.py](../tests/integration/test_workspace_start_launcher.py) 集成测试（已接入 CI）。
- **测试与发布状态**：
  - `release_posture`：`PUBLIC_BETA`（`deep_analysis_tier: EXPERIMENTAL`，未打对外推广 Release Tag）；
  - GitHub 仓库当前 **`PUBLIC`**、`main@9f65417`（待批 `FD-004` 同步迭代 #2 上主线）、Stars `0`、Forks `0`。
- **L3 创始人裁决与执行状态（2026-11-23）**：
  - **`FD-001` / `FD-002` / `FD-003`**：均已 `COMPLETED`；
  - **`FD-004`（PENDING）**：批准将迭代 #2（零配置 `youtube-intel start` + `README.md` 5 分钟指引 + 测试与 CI 更新）同步至公开 `main` 并看 CI 绿灯后再外发 `EXP-001` 邀请。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 先检查 `git status -s` 与 `git log -n 3 --oneline` 与 `gh repo view huangbuqubunao-alt/intelligence`；
  2. 记录外部试用者的 `EXP-001` 安装/冷启动耗时、报错点与 Week-1 回访结果至 `product-ops/USER_INSIGHTS.md` 与 `product-ops/EXPERIMENTS.md`。
