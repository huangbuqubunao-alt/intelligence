# TASK-011：周报

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
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
