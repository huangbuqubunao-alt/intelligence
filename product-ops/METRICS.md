# 数据指标体系与采集规范（Metrics & Telemetry Policy）

- **更新日期**：2026-11-24（Iteration #11 / Codex Round 2 全量闭环收口）
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

| 维度 | 指标名称 | 实测基线（2026-11-24 · 分支 `antigravity/task-user-readiness-20261112@ce6f8dcc`；公开主线 `main@d1b58f7` 前置 CI 基线为 `4f3fe70` [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823)） | 验证方式 |
|---|---|---|---|
| **工程构建与代码质量** | Python Lint (`ruff src tests scripts`) / 静态类型 (`mypy src`) / 前端构建 (`tsc + vite build`) | **100% 零报错**（`ruff` 0 错、`mypy` **137 文件** 0 错；`tsc --noEmit` 0 错、`vite build` **`1.38s`**） | `ruff` / `mypy` / `tsc` / `vite build` |
| **自动化回归通过率** | Public Beta 核心子集 + 全仓分片 CI + 前端 Vitest | · **分支最新代码（`d36cfe55`/`ce6f8dcc`）**：`python-ci` 14 组核心子集 **`181 passed in 686.65s`**（后补充要点引用水合修复 +2/+32 passed），扩展后 `.github/workflows/ci.yml` 新增 4 分片 `python-unit-full`（`3,955` 项）+ 8 分片 `python-integration-full`（`3,169` 项），合计 **`7,124` 项 Python CI 覆盖**（已透明披露 `GOV-001` 6 文件 `211` 项 + 2 密封单测及 `21` 项本机外部目录夹具）；<br>· **分支实跑全库分片**：Unit 4 分片 `3,954 passed, 1 skipped, 2 deselected`；Integration+E2E+Scripts 4 分片 `3,166 passed` + solo `test_fast_read_api.py` `2/2`；<br>· **前端 Vitest**：默认并发 **`57/57` / `1,259/1,259 passed`（`65.21s`）** + `App.content-status-load.test.tsx` **10/10 连跑全绿**。 | 本地实跑 + 待合流触发全量云端 CI |
| **按需视觉关键帧融合分析（`BL-011`）** | `ffmpeg` 抽帧、dHash 去重、`gemma3:4b` 实跑、Chrome E2E 与带图包 | · **真视觉模型（`ollama/gemma3:4b`, `$0`）**：5 段多场景 MP4 实测去重抽出 **4 帧**（识别 3 信息帧 + 中文融合洞察）；<br>· **Chromium 实机（`8796`）**：Dark `1440×900` & Light `375×812` 全帧加载（`200`）、筛选 `4<->3`、Lightbox `ArrowRight`/`Escape`、`visual-pack.zip`（`7826B`, `200`）、空态 CTA 与文本屏蔽（`0` 报错 / `0px` 溢出） | `test_visual_keyframe_analysis.py` + `WorkspaceVisualKeyframes.test.tsx` + 隔离端口实机 |
| **大库、4h 课程与 Obsidian `.zip` 边界指标（`BL-008` / `BL-010`）** | 600 条跨库检索/问答列表、4h 讲座归一化、300KB 长文采样、`.zip` 解压与冷启动延迟 | · **600 条库（`dbc7e89` + Round 2 优化）**：`/videos` 3 页分页 `[97.9, 48.1, 53.8]ms`、跨库 Q&A 命中第 561 条 **`0.23s`**、`list_research_sessions()` 在 `600` 历史会话下由全表解密优化为轻量元数据+单事务批量核验+LRU 缓存 **`<300ms`**、`create_sqlite_hot_snapshot()` **`5.5ms`** (`53,248B`)；<br>· **长边界与真解压（Iteration #7）**：`14390s`（3200 段）-> `03:52` 锚点命中；`>300KB`（2900 行）8 窗口均匀覆盖 0%–96%+；`.zip` 解压文件名 `<=180B`、100% YAML 合法 & 全 Index 双链闭合、文本笔记零 `00:00` | `test_cross_source_markdown_and_scale.py` + `test_long_media_and_obsidian_vault.py` + `test_codex_review_remediation.py` |
| **反幻觉基准（离线 Eval）** | 32 例双语/多源冲突与拒答基准 + 逐句无据校验 | **32 / 32 (100%) PASS**（含全角/小写/空格 `[E*]` 变体、内联清单、Markdown 表格行逐句清洗、要点/行动项引用水合与双格式编码导入） | `tests/integration/test_grounding_refusal_eval.py` + `test_codex_review_remediation.py` |
| **真机本机模型基准（`EXP-002`）** | `ollama/qwen3.5:9b` 处理陌生双语资料（`253.92s`/5 问 · `ce6f8dcc` 实测） | **3/3 (100%) `GROUNDED`**（均值 `52.26s`）+ **2/2 (100%) 诱导拒答**（均值 `48.57s`）+ **13/13 (100.0%) 逐句引用命中** + **18/18 (100.0%) 要点/行动引用命中**（`out_of_range_refs=0`），`$0` 云花费 | 隔离临时工作区实跑（用后清理） |
| **Demo 与全场景端到端 Chromium 检查** | 关键帧图表 + 引导 + 空库上传 + 详情页 | **Iteration #10（`8793`/`8794`）Demo 推荐胶囊 100% `GROUNDED`、拒答 0 引用、355 条库续拉 `135/135` & `⌘K` 明示 `135` PASS**；叠加 `8796` 关键帧/`8795` 专题/双主题 `375×812` 全通 | Chromium 隔离端口实机验证 |
| **Demo 接口读延迟（本地回环）** | `/api/v1/videos/vidDemoAgt1/evidence` & 核心只读接口响应 | **`/evidence` 由 `583–713ms` 降至 `39.6ms`（冷读）/ `3.8–5.8ms`（热缓存）**；`/api/v1/dashboard` 无 Sidecar 一致性修复后 `test_fast_read_api.py` 独跑与 14 组混跑全绿 | 本地回环压测与 `test_fast_read_api.py` |
| **静态安全与隐私脱敏扫描** | `scripts/security_scan.sh` & 个人路径/邮箱/主机名全库扫描 | **`src/`、`frontend/`、`scripts/`、`product-ops/` 全部 0 告警**（总输出 `status=findings count=17`：16 条预置假测试哨兵 + 1 条历史集合清单日志行 `docs/validation/dogfood-day2-d2-02/full-suite-collection.txt`）；当前工作树完成 `995` 份历史文档/脚本脱敏后 `git grep` 匹配为 **`0`** | `bash scripts/security_scan.sh` + `git grep` |

---

## 三、本地隐私安全只读巡检机制

- [generate_daily_ops_report.py](../scripts/generate_daily_ops_report.py) 默认完全只读 Git 事实与 `product-ops/` 运营文件（支持 `--template cpo` 生成标准 9 节 CPO 日报）；
- 即使传入隔离测试库 `--hub-db`，也以 SQLite URI `?mode=ro` 仅统计计数，绝不读取个人真实库，绝不发起任何外网埋点上传。
