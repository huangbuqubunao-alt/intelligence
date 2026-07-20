# TASK-008：可选云端深度分析

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent + 隐私 Reviewer
- Size: M
- Risk: High
- Depends on: TASK-007
- Approval required: 云 Provider/依赖、密钥来源、发送范围、预算策略

## 2026-07-20 只读预检授权

- TASK-007 已为 `DONE`，代码依赖已满足；本任务仍为 `BLOCKED/UNASSIGNED`，尚缺云端
  共享契约确认、精确依赖/版本、锁文件/下载、密钥生命周期、发送范围、token/调用预算、
  缓存/事务边界和验证命令的任务级批准。
- 已生成 `agent-prompts/PREFLIGHT-TASK-008-READONLY.md`，可与 TASK-009 Scout 并行。
  Scout 只可静态读取 main 并在聊天返回报告，不得联网、读取环境变量值、安装依赖、运行
  产品命令、调用 Provider、创建 worktree/commit 或改变状态。
- 预检必须优先复用现有 `AnalysisInput`/`AnalysisResult`、`SummaryProvider`、Artifact/
  Provider-call/`complete_stage` 契约并复核 OpenAI SDK；若需要共享类型、Schema/`state.py`
  或额外前置切片，先向主控提出，不得由 Implementer 自行设计。

## 目标

仅对策略允许的高价值视频调用已启用的云端 Provider，返回通过 Schema 校验的深度分析，并通过稳定请求缓存避免重复成本。

## 范围

- 实现与具体云厂商解耦的 SummaryProvider 和至少一个已批准 Adapter。
- 执行开关、阈值、最大输入、调用/预算限制、超时和隐私策略。
- 解析深度分析契约，区分事实、推断和建议，并记录 Provider 使用量和缓存索引。

## 范围外

- 不在代码、YAML、测试或日志中保存真实密钥。
- 不在开关关闭、低于阈值或预算用尽时发送任何字幕内容。
- 不添加第二个云 Provider，除非另建任务并审批依赖。

## 验收标准

- [ ] Fake Provider 验证关闭、低分、预算用尽、超长输入均为零云调用；高分允许路径只调用一次。
- [ ] 合法、缺字段、非法 JSON、限流、5xx、超时和缓存命中均有测试，错误按统一分类映射。
- [ ] 隐私 Reviewer 确认密钥只从批准来源读取，日志/异常不含密钥或字幕全文，发送范围与 DEC-06 一致。

## 验证

- [ ] `python -m pytest tests/unit/test_analysis_policy.py`
- [ ] `python -m pytest tests/integration/test_summary_provider.py`
- [ ] `mypy src && ruff check .`
- [ ] 静态检查：仓库和测试产物不包含真实凭证格式；检查方法由 Reviewer 记录，不输出匹配值。

## 预计触达文件

- `src/youtube_intel/analysis.py`
- `src/youtube_intel/providers/cloud_llm.py`
- `prompts/summary.md`
- `tests/unit/test_analysis_policy.py`
- `tests/integration/test_summary_provider.py`

## 交付证据

- Provider/依赖/隐私审批记录。
- 零调用策略测试和缓存测试结果。
- 如未进行真实云端冒烟，必须明确标注；真实冒烟需另获用户授权。
