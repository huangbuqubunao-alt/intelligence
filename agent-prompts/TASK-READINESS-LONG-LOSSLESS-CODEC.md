Task: TASK-READINESS-LONG-LOSSLESS-CODEC
Role: Implementer
Agent: Codex inherited default
Base: codex/task-end-to-end-user-readiness@a073354 + root task/prompt metadata only
Worktree: /Users/developer/Documents/yia-worktrees/readiness-long-lossless-codec
Branch: codex/task-readiness-long-lossless-codec
Allowed scope: tasks/TASK-READINESS-LONG-LOSSLESS-CODEC.md（仅新增纯codec/unit tests/对应handoff/证据）
Required checks: focused pytest、Ruff、strict mypy src、git diff --check；独立语义roundtrip/negative
Reviewer: root在clean STOP SHA后指定独立Reviewer
Special approvals: 用户持续默认授权，CONTINUING_AUTHORIZATION_2026_10_15.md
Reuse decision: DIRECT标准库/现纯值合同，REFERENCE已接受local_grounding，无新依赖或网络
Parallel now: tracked40只写其原范围；本任务不得改任何既有产品/测试，root明确允许纯函数例外
Waiting: 全部新迁移/生产接线/模型生成等tracked40及混合字幕核心接受后串行

按AGENTS规定先读规则和权威规范。先回报最小接口/输出shape理解与边界；可直接做task内纯切片，不逐文件向用户申请。主控不写产品代码。保留原语义标准，任何实质不确定先报告，不猜历史 authority 或自行扩大20。作者真实模型IO必须0。只读真实Sasha位置由root后续指明，不搜用户目录或私有holdout。现有原fail与qualificationclosed不改；此切片不能声称长内容支持完成。交接按模板、准确SHA、clean STOP，不自行合main。
