# 数据指标体系与采集规范（Metrics & Telemetry Policy）

- **更新日期**：2026-11-23
- **阶段边界声明**：当前严格处于**内部自主迭代与产品完善阶段**（禁止启动真人试验与外部招募）+ **Zero-Telemetry**（绝不采集任何网络遥测或私有个人库内容）。因此，**所有真实外部用户留存、激活、满意度与付费指标当前均为 `当前不可评估`，严禁拿单测、Demo 或 AI 模拟数据冒充真实业务表现。**

---

## 一、北极星指标（North Star Metric · 未来授权阶段定义）

- **指标定义**：**周可核验研究收获人数（Weekly Verified Research Creators）**——自然周内完成至少 1 次真实资料（YouTube/B 站/本地音视频/`.md`）跨源问答（获得有证据作答或诚实拒答）并复制/下载含可用溯源引用 Markdown 笔记的独立用户数。
- **当前真实数值**：**`当前不可评估`**（原因：现阶段未启动真人用户测试，且产品严守 Zero-Telemetry）。

---

## 二、分层度量基线（严格区分外部真实用户指标 vs 内部研发/质量指标）

### A. 外部真实用户与商业指标（当前阶段全部不可评估）

| 维度 | 核心指标 | 当前真实状态 | 未来解锁评估的前提条件 |
|---|---|---|---|
| **真实激活** | 新用户 15 分钟内完成「冷启动 → 导入 >=2 份材料 → 提问 → 导出 `.md`」比例 | **`当前不可评估`** | 获创始人明确 L3 授权进入真人试点（`EXP-001`） |
| **真实留存** | 第 7 日 / 第 14 日自发回访与持续导出研究笔记比例 | **`当前不可评估`** | 获创始人明确 L3 授权并在隐私合规前提下观测受控试用群体 |
| **用户口碑** | 真实用户 NPS / 拒绝幻觉信赖感反馈 / 自然 GitHub Star 与外部 Issue 转化 | **Stars: `0` · Forks: `0` · NPS: `当前不可评估`** | 获授权正式进入外部推广与真人反馈收集 |
| **商业转化** | Pro 工具增值包或团队私有版真实付费转化率 / ARPU | **`当前不可评估`**（仅作假设分析） | 真人 W1 留存达标后才可启动定价实验（`EXP-004`） |

### B. 内部研发、AI 可靠性与体验指标（已实测有明确证据）

| 维度 | 指标名称 | 实测基线（2026-11-23 · 截至 Iteration #5 / `main@f23954f`） | 验证方式 |
|---|---|---|---|
| **工程构建与代码质量** | Python Lint (`ruff`) / 静态类型 (`mypy`) / 前端构建 (`tsc + vite build`) | **100% 零报错**（`ruff` 0 错、`mypy` 136 文件 0 错、Iteration #5 `vite build` `3.23s` 成功） | 本地实跑 + GitHub Actions CI (`main@f23954f`, [`#45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端 `success`) |
| **自动化回归通过率** | CI Pytest 套件 + 前端 Vitest | **Backend 11 组 `141/142` 合跑 + 单跑 `test_fast_read_api` `2/2 passed`**（`6760028`，本轮无 `.py` 改动）+ **Frontend `54/54` 文件 / `1244/1244` passed in `88.35s`**（`--minWorkers=1 --maxWorkers=2`） | 本地全量实跑与竞争后单独复跑实录（详见 `TEST_LOG.md`） |
| **反幻觉基准（离线 Eval）** | 32 例双语/多源冲突与拒答基准 | **32 / 32 (100%) PASS**（`8/8` 测试函数全通过，由 `20` 例扩充至 `32` 例） | `tests/integration/test_grounding_refusal_eval.py` + `test_public_beta_demo_showcase.py` |
| **真机本机模型基准（`EXP-002`）** | `ollama/qwen3.5:9b` 处理陌生双语资料（227.6s/5 问） | **3/3 (100%) `GROUNDED`**（YT/Bili/Markdown）+ **2/2 (100%) 诱导拒答**，`$0` 云端支出 | 隔离临时工作区实跑 + 原始 JSON/Markdown 证据归档 |
| **Demo 与空库端到端 Chromium 检查** | 首轮引导双主题 + 移动 `375×812` + 详情页 + 空库上传 | **Iteration #5 Obsidian Dark `1440×900` + Warm Paper Light `375×812` 首轮三步引导及跳过后空首页 PASS（0 溢出 / 0 报错）**；叠加 Iteration #4 `#Content` 秒开与 `main@f23954f` 拒答/上传 `201` PASS | Chromium `8797`/`8798`/`8799` 实机验证 + 截图核对 |
| **Demo 接口读延迟（本地回环）** | `/api/v1/videos/vidDemoAgt1/evidence` & 核心只读接口响应 | **`/evidence` 由 `583–713ms` 降至 `39.6ms`（冷读）/ `3.8–5.8ms`（热缓存）**（9 路由压测均值 `19.5ms`）；全只读核心接口 HTTP `200` | 本地回环实时压测采样 |
| **静态安全扫描** | `scripts/security_scan.sh` 源码与产物区告警 | **`src/`、`frontend/`、`scripts/`、`product-ops/` 全部 0 命中**（仅历史测试哨兵 17 条预置假字符串） | `bash scripts/security_scan.sh` |

---

## 三、本地隐私安全只读巡检机制

- [generate_daily_ops_report.py](../scripts/generate_daily_ops_report.py) 默认完全只读 Git 事实与 `product-ops/` 运营文件（支持 `--template cpo` 生成标准 9 节 CPO 日报）；
- 即使传入隔离测试库 `--hub-db`，也以 SQLite URI `?mode=ro` 仅统计计数，绝不读取个人真实库，绝不发起任何外网埋点上传。
