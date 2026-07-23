# TASK-011：周报

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Owner role: 实现 Agent
- Size: M
- Risk: Medium
- Depends on: TASK-009, TASK-010

## 目标

按配置时区和 ISO 周聚合已完成视频，生成稳定排序、可重复更新、包含 Obsidian 双链的每周趋势报告。

## 范围

- 实现周边界、候选查询、Top N 选择、关键词/趋势输入和周报渲染。
- 按 DEC-08 处理无内容周；同一周期使用稳定唯一键 upsert。
- 趋势生成默认复用已有分析或已批准的周报策略，不隐式新增云调用。

## 范围外

- 不重新下载、转写、评分或总结视频。
- 不修改视频笔记。
- 不发送邮件、消息或发布周报到外部系统。

## 验收标准

- [ ] 测试覆盖跨年 ISO 周、夏令时无关时区行为、周边界、并列分数、少于 Top N 和空周。
- [ ] 同一周重复执行更新同一文件/记录，排序与双链稳定，不产生重复条目。
- [ ] 周报包含 PRD 规定的统计、Top N、推荐理由、趋势、重复关键词和持续关注方向。

## 验证

- [ ] `python -m pytest tests/unit/test_week_period.py`
- [ ] `python -m pytest tests/integration/test_weekly_report.py`
- [ ] `mypy src && ruff check .`
- [ ] 人工检查：在临时 Vault 检查一个跨年周和一个空周的渲染结果。

## 预计触达文件

- `src/youtube_intel/reporting.py`
- `prompts/weekly.md`
- `templates/weekly.md`
- `tests/unit/test_week_period.py`
- `tests/integration/test_weekly_report.py`

## 交付证据

- 周边界测试结果。
- 重复生成前后的文件哈希/差异说明。
- 趋势生成是否涉及模型调用及其已批准策略。

## 2026-07-23 只读预检授权

- TASK-009/TASK-010 已 `DONE`，但本任务仍为 `BLOCKED/UNASSIGNED`。只授权独立 Scout 读取现有文档、
  接口与任务卡，冻结 ISO 周/时区/空周/稳定排序、数据来源与周报 upsert、趋势策略、模板双链、临时 pytest
  Vault I/O、安全文件边界、复用和精确实施范围。
- 不创建 worktree、不运行产品命令、不修改代码/状态，不授权真实 Vault、用户笔记、外部发送、云调用、
  凭据、网络、媒体或删除/移动操作。预检结论须先形成 ADR 提案并由产品负责人批准。

## 2026-07-23 ADR-010 已接受

- 产品负责人已批准 completed_at 配置时区 ISO 周、确定性高价值候选/排序、空周稳定报告、已验证
  Analysis 聚合、包内固定 Jinja2 模板和仅 pytest 临时 Vault 原子写。TASK-011 可在正式分配后实施。
- 范围扩展为 `reporting.py`、`state.py` 的只读候选查询、`providers/obsidian.py` 周报 upsert、
  `src/youtube_intel/templates/weekly.md`、既定 tests/fixtures 与 handoff；仍禁止 Schema/migration、
  `complete_stage`、新增依赖、真实 Vault/用户笔记、云调用、网络和外部删除。

## 2026-07-23 正式实施分配

- Base：`main@44fc64be2cb4602cb93c1d03f84d6dd2a1677750`；worktree：
  `/Users/hua/Documents/yia-worktrees/task-011`；branch：`codex/task-011-weekly-report`。
- Codex 为唯一 Implementer；完成后由全新独立 Codex Reviewer 审查。仅允许 ADR-010 的八个路径组和
  任务卡离线门禁；未授权路径、真实 Vault、用户内容、网络、云调用、凭据、依赖/锁、Schema/migration 与
  `complete_stage` 继续禁止。

## 2026-07-23 实现证据与独立审查授权

- Source：`0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`，唯一父为固定 base；实际修改七个允许路径，
  未触及 fixtures、依赖、锁、Schema/migration、CLI 或真实资源。
- Implementer 自报 focused=`2/3`、full pytest=`404`、mypy、Ruff、CLI、locked sync、offline build 与
  package inclusion 通过。这些仅为待独立复跑证据；Reviewer 只可追加 source handoff。

## 2026-07-23 第一轮审查拒绝与 Correction 1

- Reviewer evidence：`3759d54a74abaa8e6627b8107298d0938fbe3441`，唯一父为 implementation
  `0ae7f9366b49395fbe8c4908bbbc19c127bc0a8e`，只修改 source handoff；Verdict=`REJECT`，P1=1。
- 周报趋势、关键词和持续关注方向只读 `ScoreResult.topics`，没有将 verified `AnalysisResult` 作为必要
  输入，违反 ADR-010 W-03 和验收项。原 Implementer 只获 `reporting.py`、两份周报测试和 handoff 的
  Correction 1；须以确定性 Analysis 聚合关闭 P1，禁止扩大契约、状态、模板或真实资源边界。

## 2026-07-23 Correction 1 实现证据与第二轮独立审查授权

- Correction source：`f4e30a56ddcf7d654bda4e0579f6080af59698f5`，唯一父为 Reviewer 1 evidence
  `3759d54a74abaa8e6627b8107298d0938fbe3441`；仅修改 `reporting.py`、周报 integration test 与 source
  handoff，完整产品范围仍为七个允许路径，依赖/锁未变。
- Implementer 自报 verified Analysis-only 趋势/关键词/方向、NFC/空白/casefold 标准化、稳定频率/并列排序及
  Analysis 缺失/篡改/identity mismatch 的零写入 fail-closed；focused=`2/8`、full pytest=`409`、mypy、Ruff、CLI、
  locked sync、offline build 与 package inclusion 通过。这些均为待 Reviewer 2 独立复跑的证据；不得预写 verdict、
  ACCEPTED、merge 或 DONE。

## 2026-07-23 第二轮审查拒绝与 Correction 2

- Reviewer 2 evidence：`6f9c75df90e10b964b36dbcefc52618422d83216`，唯一父为 Correction 1
  `f4e30a56ddcf7d654bda4e0579f6080af59698f5`，只修改 source handoff；Verdict=`REJECT`，P1=1。
- 周报仅从索引行构造视频 NoteRef，未复核受管视频笔记的路径安全、文件存在性与内容 SHA-256；缺失或篡改笔记
  仍可写入无效链接，违反 ADR-010 W-02/W-03。Correction 2 仅获 `reporting.py`、两份周报测试和 handoff，须在
  所有 Vault/reports 写入前 fail-closed；禁止扩大状态、Adapter、模板、依赖或真实资源边界。
