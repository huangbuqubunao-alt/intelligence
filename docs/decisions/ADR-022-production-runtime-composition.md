# ADR-022：正式 CLI 生产组合与首次运行边界

## 状态

Accepted

## 日期

2026-08-12

## 背景

核心 Provider、SQLite 状态机、Pipeline、Obsidian 与周报已经分别实现，但正式 CLI
在没有测试注入时仍固定使用 `_UnavailableOperations`。因此自动化服务流可以通过，
真实用户的 `check`、`process`、`retry` 和 `weekly` 却必然 fail-closed。首次安装还
没有 `data/state.sqlite`，而只读 `doctor` 对此静默退出。

## 决策

1. 新增独立 production composition root；CLI 只负责解析、配置加载、输出与调用，
   不在 `cli.py` 内堆叠 Provider 和 Job handler 初始化。
2. 所有非 `doctor` 业务命令先执行幂等 bootstrap：只创建配置指定的项目内 DATA、
   logs、SQLite schema/migrations，以及已存在 Vault 根下的受管子目录。不得覆盖文件、
   绕过 migration、跟随 symlink 逃逸或创建 Vault 根。
3. `doctor` 保持只读：不创建 Job、数据库、日志或 Vault；逐项输出 config、DATA、
   SQLite、Vault、yt-dlp、MLX Whisper、Ollama、模型和 Cloud 状态及安全修复建议。
   为完成用户明确要求的本地模型诊断，本 ADR 仅替代 ADR-011 O-02 中“不得探测
   loopback”这一条：只允许对配置校验后的 loopback Ollama 做一次有界 `/api/tags`
   读取；仍不得调用业务 Provider、YouTube、云端、凭据或 Vault 内容。
4. `check` 使用 RSS discovery 并持久化发现结果；`process` 通过既有 Planner/
   Orchestrator 和 job-bound services 执行；`weekly` 只使用已验证持久数据。
5. Cloud 继续默认关闭且不读取凭据。缺少本地模型、音频或其他运行先决条件时必须
   安全停止并给出可操作提示，不得降级为未声明的模型、云调用或测试替身。
6. 无字幕转写需要受管媒体获取、音频 Artifact 注册和固定模型资源。现阶段若没有
   已登记音频，生产运行明确报告 prerequisite；不得复用 E2E 手工 fixture 路径。
7. 新增 Production Composition Test：从正式 CLI 默认路径进入真实 composition，
   只在外部 Provider 边界使用受控替身，不注入 Fake `Operations`。
8. 字幕 Adapter 保持既有 512 条资源上限与 fail-closed 校验。真实目录若因自动字幕
   翻译展开超过上限，必须停止并报告受限前置条件；不得提高上限、启用 Cookie/认证，
   或声称 yt-dlp 的 `skip=translated_subs` 可以抑制自动字幕翻译展开。
9. Ollama grammar 仅发送其本地 API 支持的结构型 JSON Schema 子集；数值、字符串
   与集合边界仍由既有 `ScoreResult` Pydantic 契约二次校验并 fail-closed。评分值
   额外用该 API 支持的整数枚举 `0..10` 约束，避免本地模型误用百分制；不得静默缩放
   越界结果。
10. `check --limit N` 同时限制报告数量与写入 SQLite 的候选数量，避免用户随后无参
    `process` 处理超出明确上限的工作；Discovery cursor 仍按本次响应前沿推进。
11. Cloud 关闭时，高价值且 `COMPLETE` 的受管视频笔记仍进入周报 Top N。周报使用
    固定的“深度分析未启用”说明；趋势、关键词与持续关注方向仍只聚合已验证的
    `ANALYSIS_STRUCTURED`，不得用评分主题冒充深度分析。
12. 评分 prompt 必须作为 `youtube_intel` 包资源读取；源码、sdist 与 wheel 中内容
    一致。yt-dlp 的日志接口由 Adapter 静默接收，终端只显示应用层安全消息。

## 结果

- 首次合法业务命令可以安全建立本地运行状态。
- CLI 的成功、失败阶段和下一步对用户可见，同时 JSONL 继续使用脱敏消息。
- 本地 smoke 的能力结论必须区分真实通过、先决条件阻塞和未授权大型模型下载。
- 本 ADR 不授权真实用户 Vault、OpenAI、付费调用、大模型下载、依赖或 Schema 变更。
