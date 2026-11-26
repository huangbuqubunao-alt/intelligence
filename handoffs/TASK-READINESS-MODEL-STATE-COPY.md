# TASK-READINESS-MODEL-STATE-COPY 交接报告

## 元数据

- Role: Implementer `/root/intel_bounded_review`；独立 Reviewer 待主控安排 `/root/caption_resume`。
- Base: `aa1a9b30f35c548ab7ba162b5877c925e33110d7`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-model-state-copy`。
- Branch: `codex/task-readiness-model-state-copy`。
- 实现 commit: `fc2d854`（完整 SHA 以本树 `git rev-parse fc2d854` 为准）。
- 日期：2026-10-14；实现者已停止写入，建议 `IN_REVIEW`，不自审、不设 DONE。

## 目标、范围与复用

真实设置页把 `runtime_local_model.status=READY` 译为“已安装，可使用”，而这个
字段只代表 `/api/tags` 精确名称及 digest 匹配，不代表模型通过洞察验收。
本任务在原主面板分开陈述安装身份、本地洞察资格与可选云端逐次授权。

DIRECT 现有 Settings/Panel/语言字典、`runtime_local_model.status`、既有 Local
`SCORING_SUMMARY_ONLY` provider 的 `qualification_status`、既有云端 eligibility/
credential 分支、React 18.3.1、Testing Library 16.1.0、Vitest 2.1.9。
来源为本仓库已批准依赖和既有领域 DTO，没有复制外部代码或引入新的许可证/
依赖。graph-first 查询 root 索引定位 Settings，随后核对本树实际代码及 DTO。
复核 root 与 workspace DESIGN.md，沿用暗色 Panel、hint 和现有详情结构，没有
新增设计文档、CSS、控件或导航。

实际业务修改仅 App.tsx Settings 和 uiLanguage.tsx；新增
App.model-readiness.test.tsx。不修改旧测试、不改变 API、模型/凭据处理、配置、
授权、按钮、生产资格、后端、Schema、锁文件或工具链。没有访问真实模型、云端、
owner 数据或 research V2 冻结树。node_modules 仅使用主控明确允许的现有依赖软链接。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| READY 仅说明安装与身份核对 | PASS | 双语显示“已安装，身份已核对”；不再显示“已安装，可使用” |
| 本地未合格显示真实状态 | PASS | 仅已知 Local/SCORING_SUMMARY_ONLY 且 INTELLIGENCE_UNQUALIFIED 显示未通过洞察质量验收 |
| 缺失/未知/其他 scope 不推断资格 | PASS | 同一双语测试覆盖缺 Local、UNKNOWN、OTHER scope，不输出通过或失败断言 |
| 云端是可选且逐次授权 | PASS | 既有 eligible、blocked、缺合格 row 三分支测试；eligible 原文字和行为保留 |
| 已有内容与本地整理仍可用 | PASS | 保留原文/字幕前提的本地整理说明，以及 Content/Summary/Evidence 可读说明 |
| 错误安装状态不被放行 | PASS | NOT_INSTALLED/DIGEST_MISMATCH/UNKNOWN/UNREACHABLE 四例保留 attention |
| 不创建模型/凭据/执行操作 | PASS | 读取请求精确限定既有七个路径且无 mutation method/body；发现的 research 9b 不替换当前 runtime 标识 |
| 真实 macOS GUI | 待主控 | 本实现者仅组件验收，没有把 fixture 当真实 GUI；须主控整合后核对 5908 Settings |

## 检查结果

| 命令 | 实际结果/日志 |
|---|---|
| `npm run typecheck` | PASS，先于测试检查；未改 tsconfig |
| `npm test -- src/workspace/App.model-readiness.test.tsx` | 12 PASS，188ms；`/tmp/readiness-model-copy-focused-final.txt` |
| `npm test` | 418 PASS / 26 files，12.40s；`/tmp/readiness-model-copy-full.txt` |
| `npm run build` | PASS，tsc + 50 modules；`/tmp/readiness-model-copy-build.txt` |
| `git diff --check` / staged diff check | PASS |

Build assets: `index-BsxpjgLs.js` / `index-DmN6_wU_.css`，仅本树 ignored dist；没有
更新正式产品或 served revision。完整测试的既有 React act warnings 保留日志，未隐藏。
后端/Ruff/mypy 不运行：未改任何 Python 或后端。没有真实推理或 provider probe。

## 失败证据及处理

先写新测试，旧实现 8 FAIL / 4 PASS（`/tmp/readiness-model-copy-red.txt`），主要错误
是缺少真实安装/资格区分文案。旧中文 eligible 文案在新测试第一次写错，核对既有
字典后更正新测试期望，没有修改旧文案或断言。新测试的首轮 green 尝试 2 FAIL /
10 PASS（`/tmp/readiness-model-copy-focused.txt`）：

- 新测试错误假定整个 Panel 不含发现的 9b；实际 9b 正常存在于折叠的候选 select。
  改为精确验证 runtime 身份段不会被候选替换，保留候选发现行为。
- 新测试错误假定 GET fetch 只传一个参数；实际 client 总是携带 headers/options。
  改为验证所有既有路径只有 GET/默认 GET 且无 body，仍禁止任何授权/执行 mutation。

这两项是本轮新增测试的边界误判修正，没有减少既有测试、弱化原产品门禁或修改
实现来掩盖问题；后续专项和完整套件通过。

## Diff 复核与剩余风险

- App 仅 5 增/2 删；语言字典仅追加 5 项，新测试 92 行，无格式化 churn。
- 原 Installed and ready 等旧字典条目保留以避免无关清理，Settings 已不再引用。
- 内容整理/本地摘要/云端执行原行为及门禁均不变；本任务不能证明模型合格。
- V2 真模型语义 gate、字幕迁移、后续用户链路和最终 main 采用由主控另行验收。
- 本任务无 `DECISION NEEDED`。独立 Reviewer 和真实 GUI 尚未完成，不授采用权。

## Reviewer / 主控

待独立审查固定实现 SHA 并重跑关键检查；主控负责真实 GUI、接受与整合。

### 独立 Reviewer：2026-10-14 / caption_resume

**APPROVE（本有界文案切片；真实 GUI / 资格 / 采用仍由主控验收）**。独立读取 task、实际 DTO producer 和完整 base `aa1a9b30f35c548ab7ba162b5877c925e33110d7` → author `fc2d854223eb3d00a1bd88049e00f2bb481fe5f3` / handoff `b6a62500cec964b5dcd994aaa6abd09e9a663181` Diff。仅两产品前端文件、追加专项测试、交接，无新增 P0/P1。

- 独立 typecheck PASS，随后专项 **12 PASS / 192ms**，build **50 modules PASS / 503ms**；证据 `/tmp/readiness-model-copy-independent-ts.txt`、`readiness-model-copy-independent-focused.txt`、`readiness-model-copy-independent-build.txt`。资产同作者 `index-BsxpjgLs.js` / `index-DmN6_wU_.css`。独立 baseline diff check PASS；作者全前端日志实际 **418 PASS / 26 files / 12.40s** 已核对，既有 act warnings 保留，无必要重复完整套件。
- `ModelSettingsService.runtime_status` 的 READY 实际只校验 exact installed name/digest；新 copy 忠实表达安装身份，不授 Intelligence 资格。现有 Local selection 明确 provider=`Local`、scope=`SCORING_SUMMARY_ONLY`；仅 `INTELLIGENCE_UNQUALIFIED` 输出未通过说明。缺失/未知/错 scope 不捏造通过或失败，research 9b 发现项不替换正式 runtime 身份。
- Cloud production_eligible / credential BLOCKED 原条件、ModelSettings credentials/授权 handlers、所有按钮和 fetch loaders 未改变；新文案明确可选与每请求单独授权，普通内容整理不依赖 Cloud。专项验证既有七 GET 路径且无 body/mutation，没有新增模型或凭据操作。
- 双语文案、新状态分支与测试覆盖一致；旧测试原样保留，无 backend/Schema/gate/state/config/dependency/toolchain/freeze/模型输出修改。只复用现有 Panel/提示/DTO，无新增布局、控制或键盘行为。

Reviewer 未访问真实 owner、模型或 Cloud，未推理；未把受控组件测试当 macOS GUI。主控须在真实隔离 Settings 核验当前 8b 安装身份、未通过本地洞察资格、Cloud 可选逐次授权及原阅读流程。V2 首例真实 FAIL 仍不合格，本审查没有新的资格或继续模型调用权。Reviewer 只追加本交接并提交，STOP。
