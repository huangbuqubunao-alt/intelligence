# TASK-009：Obsidian 视频笔记

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-007
- Approval required: 写入真实 Vault 前需用户明确授权

## 目标

将视频、评分和可选深度分析幂等渲染为 Obsidian Markdown 笔记，安全处理路径与同名冲突，并在更新时保留用户的 `我的思考`。本任务使用可选 AnalysisResult 契约/Fake，真实云分析集成由 TASK-010 完成。

## 范围

- 实现稳定 Frontmatter、文件命名、模板渲染、自动管理区和用户编辑区。
- 使用临时文件 + 原子替换，确保目标始终是完整旧版或完整新版。
- 校验所有路径位于配置的 Vault 子目录；同一 `video_id` 只对应一份笔记。

## 范围外

- 默认测试不得写用户真实 Vault。
- 不修改、移动或删除非本系统管理的笔记。
- 不实现周报。

## 验收标准

- [ ] 临时 Vault 测试覆盖首次创建、重复 upsert、标题变化、同名标题、路径穿越和写入中断。
- [ ] Frontmatter 可解析且字段类型稳定；低价值/高价值产物符合 DEC-08 和 PRD 内容契约。
- [ ] 用户修改 `我的思考` 后重新生成，用户内容逐字保留，系统管理区按新数据更新。

## 验证

- [ ] `python -m pytest tests/unit/test_note_rendering.py`
- [ ] `python -m pytest tests/integration/test_obsidian_sink.py`
- [ ] `mypy src && ruff check .`
- [ ] 人工检查：在临时 Vault 打开样例 Markdown，确认双链、Frontmatter、标题和用户区结构。

## 预计触达文件

- `src/youtube_intel/notes.py`
- `src/youtube_intel/providers/obsidian.py`
- `templates/video.md`
- `tests/unit/test_note_rendering.py`
- `tests/integration/test_obsidian_sink.py`

## 交付证据

- 临时 Vault 的脱敏样例路径/内容摘要。
- 原子写、路径边界和用户区保留测试结果。
- 真实 Vault 未触达声明；如触达则附用户授权和受控验证结果。
