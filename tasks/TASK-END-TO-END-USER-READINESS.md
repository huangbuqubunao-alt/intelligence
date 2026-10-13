# TASK-END-TO-END-USER-READINESS

状态：IN_PROGRESS（用户 2026-10-12 明确要求修复所有不通链路，完成后再交用户测试）。
2026-10-13 续作：用户具体批准固定 qwen3.5:9b-q4_K_M 隔离下载与原标准验收，替代下文最初“只用已安装8b、不新增权重”限制的这一精确项；无运行时/依赖升级、正式采用或门禁放行。字幕补全、旧429精确终止、firstplain捕获及最多两份真实接受capture的winner precommit hash补充也已有各自具体批准。权威最新状态见 READINESS_MATRIX.md / PROGRESS.md，不以历史已通过局部操作替代当前 OPEN。
工作树：`/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness`。
分支：`codex/task-end-to-end-user-readiness`；基线：`73ee7e747b4461b9de8a201d6b47669eb3913d1a`。

## 完成标准

真实本机执行和真实 macOS GUI 证明：本地视频→可用原始字幕→摘要/Evidence；真实文本/字幕→Intelligence→保存/主题→来源回跳；YouTube 关注→发现/处理新内容→去重/暂停恢复。首次使用和跳过后都能完成配置；错误、取消、重启与备份恢复可恢复且保留证据。付费云和不支持的第三方能力不以模拟成功冒充支持。

测试夹具通过不等于模型或来源可用；未达标项保持 OPEN，不交给用户作为“已完成”版本。任何候选必须通过既有完整回归、真实流程和独立审查；正式采用需要具体最终批准。

## 顺序与切片

模型整改具体批准已于 2026-10-12 收到，见 MODEL_REMEDIATION_PROPOSAL。READINESS-02 声学和 READINESS-03 洞察资格验收的模型、状态和业务文件互不重叠，可在各自独立 worktree/DB 串行执行各自推理，并行实施；16 GiB 本机重量推理必须协调，不同时加载两个模型。后续准备流程与统一产品验收依赖两者结果。

1. READINESS-01：复现公共频道 Feed 404，保留响应/安全路由证据；验证公开频道身份，修复正常来源发现。重点文件 youtube_network/youtube_channel 与对应测试，不绕过 TLS、SSRF、Cookie/登录边界，不无限重试或导入历史。
2. READINESS-02：既有精确 MLX Whisper 模型和运行时的隔离声学整改。先冻结实验政策/输入，再执行。中长、短、中英混合、设计停顿、噪声、纯静音与纯噪声控制全部过原门槛才具资格；失败、历史 tuple/receipt 不覆写。
3. READINESS-03：既有精确 qwen3:8b 的真实本地 Intelligence 资格验收，修复发现的输出/绑定缺陷。端到端保存、主题与溯源需要真实 admitted Intelligence。旧 Scoring/Summary 资格不替代。不得直接翻转 production_qualified 布尔值。
4. READINESS-04：普通用户准备流程，基于真正合格的能力解释/引导/检查与回跳；仅在隔离环境进行配置。需要正式模型部署、依赖、Schema 或授权改动时先提供精确方案。
5. READINESS-05：独立 DB/DATA/config/Vault、真实浏览器与原生文件选择器，覆盖所有现有入口的正向、错误、取消、重启、重复和 Backup/Restore；更新图文手册。完整 Backend/Frontend/TS/build/Ruff/strict mypy/diff check 与独立审查。

## 复用和边界

DIRECT 既有 Python/React/urllib/ffmpeg/MLX/Ollama、现有资格 scorer/validator、来源身份、invocation ledger、checkpoint、Source Run、Backup 和模型目录端点。ADAPT 原生已有能力的普通用户准备链路。REJECT 假结果、降低资格标准、配置即生产权力、Cloud 自动回退和删历史。

本轮不修改正式 owner 数据/配置/凭据；不使用真实 Vault；不增加或升级依赖/权重，不调用付费云，不改 Schema。涉及这些动作另行精确审批。Jev 路由 HTTP 451 不可用，继续现有强推理/人工审批安全流程。

## 当前证据

正式 ASR MODEL_MISSING / production_eligible=false；现有 Whisper large-v3-turbo 历史资格 FAILED，中长音频非有限时间/重复尾部及静音噪声幻觉。权重可在此前隔离模型目录只读复用。

Ollama qwen3:8b 已存在且精确 digest 匹配，但 Intelligence production_qualified=false；需真实能力和语义证据。

2026-10-12 两个已知真实 YouTube 频道通过当前公开 Feed 路径均 NOT_FOUND（约 1.49 秒），必须继续诊断，不能将“有错误提示”标成来源发现成功。原始探针保存在 `.var/end-to-end-user-readiness/public-feed-probe.json`。
