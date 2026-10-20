# OpenCode LOCAL 交接独立证据审查

- Reviewer：`local_budget_evidence_audit`，2026-10-20；与产品实现者分离。
- Report base：`e21029d3ff612b1b60c9f54b6ac6b0a09ae761bf`；WT `readiness-opencode-local-handover-review`，branch `codex/review-opencode-local-handover`。
- 实际证据审计时生产源码为 root `a989873773c0f4018cc696930789566925e88c7c`；之后 root 仅有交接/决策文档变更。本报告不审查尚未提交的 R13 修复。
- **结论：不接受旧 LOCAL8 链为完整资格或普通用户可用证明。** 接受下述有限真实观测；正式资格继续关闭。报告不授模型 permit、产品采用或部署资格。

## 已实际核验

只读重算 `.var/end-to-end-user-readiness/local-grounding-review/` 与被引用文件；检查实际 traceback、Ollama 日志、原 prepared/request/DATA、仅隔离 SQLite 的 `mode=ro` 行。未读取模型 thinking，未调用本地模型 HTTP，未调用/加载模型，未触及正式数据、配置、凭据。源码定位先查 codebase-memory graph，再读对应固定文件。没有重跑生成或旧失败。

1. 升级 JSON SHA256 `09547fb436080db3e7c6760ce66b678f1b108a9a5c8da939677c419b951d3ba9`、MD `d246472fd52fe70cef9940370e20eaa146f3e2b838b6bfc4bd546a0f95232235` 匹配。JSON 内 **15 个引用 hash 中 14 个匹配**：term-sheet 声明 `7f96f4259f1d39b4593e4242e73672786f39a0ea0af0d93568bec8cd18f6c5f5`，实际 `0dea4080126b38c1467ab934530f9d9745f86546f1b7658f7d12621b94d456ec`。term-sheet 后续追加了升级内容；不能声称“17 项证据链全部相等”。旧材料不改写，新增纠正记录即可。
2. 八案的 prepared 文件 hash、request hash、完整 DATA path/hash 集合、source-manifest digest/输入关联均重算匹配；两 scope 的 current code/profile binding 相等。这证明封存关联，不能替代语义或先决资格。
3. r3、r4真实日志均为 prompt 1075、eval 6144，runner `-c 16384 -b 512 -ub 512`；完成时间分别 **18:38:50、19:07:22**。两次使用同一 request/seed/execution ID、分别新隔离 DB/服务。两次预算耗尽属实；不推出统计独立、必需输出长度、中文 token 成本解释或 8192 成功概率。日志 `truncated=0` 是 runner context 指标，不能用来否认输出预算耗尽。
4. case1 真实返回 `NO_NEW_INTELLIGENCE`，prompt 760、eval 4355；final SHA256 与 receipt 相等，receipt schema 的 `passes(now)` 当时为 true。图书馆/麦克风测试的 NO_NEW 可为正确负向结果，**不等于六正向之一**。其 raw checkpoint 为 PENDING、usage 表空，由真实 `distillation_no_new_intelligence_results` 及 `get_distillation_execution()` 的验证 overlay 表达成功，是既有设计，不误报为新 P1。

## 未满足的门禁与真实缺陷

- **覆盖不合规格**：`LOCAL_INTELLIGENCE_CHAIN_PROPOSAL.md` 要求 timed/TXT/MD 中英六正向及 NO_NEW/注入。旧选择为图书馆测试语音、四份仓库文件前五行（标题、版本、日期、Assignee 等），不足六正向；部分所谓 en 案原文仍中文，仅输出语言为 en。保留这些负控事实，不能据编号自动计完整资格。
- **原资格先决证据缺失**：`LOCAL_MODEL_GROUNDING_PORT_PLAN.md` 要求原四例及未见 YT holdout 10 案通过后，再 LOCAL8；LOCAL 提案亦要求原四例通过才开始真实 LOCAL。提供的交接链没有这项通过证明；tracked V11 仍 REJECT，固定资格资源仍 `records=[]`。LOCAL case1 不替代该前提。
- **firstFAIL 纪律未遵守**：r3 真实生成失败后，reviewer 自批 EXACTLY-ONCE 再生成 r4；新的 DB/permit 没有改变原 firstFAIL 停止约束。旧记录保留，不能以 reviewer 反复续 permit 代替主控新方案决定。
- **R13 已证实**：`validate_local_grounding_response` 在保存真实观察 metadata 为 transport result 之前抛 `KnownLocalDistillationResponseError(result=None)`；service 尝试 REJECTED_OUTPUT/invocation=1 收尾，state 的实际身份规则正确拒绝双 None，导致异常逃逸、无 result.json，r3/r4 留 PENDING/DISPATCH_CLAIMED/invocation=1、usage 空。需修复错误收尾，保留真实可验证 metadata；未知身份保持 AMBIGUOUS/1，禁止合成实际身份、伪零调用、绕过 state 校验或自动重发。
- **C-OPT1 范围描述不准确**：旧 `LocalDistillationProfile.options()` 没有 scope 参数，YT_TIMED/LOCAL_TIMED/LOCAL_TEXT 共用一个 profile。直接改 6144 会改变全部 scope 的 profile 投影及历史读取身份。应另建不可变新 profile，旧 profile/hash 不改；新 profile 默认无资格，严格绑定合法 scope。
- **延迟/容量不同**：6144 两次真实生成分别约 294/284 秒，timeout300 秒。8192 按同速约需 392/379 秒（仅推算）。`input bound <=8191` 只证明上下文空间，不证明时限内完成；不能仅抬输出预算发 permit，或在失败后才继续放宽响应字节/时间。

## R14 官方固定源码预检

使用 agent-reach 的 GitHub 官方源码路由及现有只读 GitHub connector。官方 v0.40.1 tag 在本次查询指向 commit `cf2a313a298066d572c36812e5ad30a21c0db13b`。以下为实际取回全文 UTF-8 SHA256；源码检查不代表已运行安装二进制验证：

| 官方文件 | SHA256 | 相关合同 |
| --- | --- | --- |
| [api/types.go](https://github.com/ollama/ollama/blob/cf2a313a298066d572c36812e5ad30a21c0db13b/api/types.go) | `75369e029dcfc815013243b1e728fcff32514a3b38b26f3288eb1ee2b7fa4d1b` | Runner 暴露 `num_batch`，默认512 |
| [server/routes.go](https://github.com/ollama/ollama/blob/cf2a313a298066d572c36812e5ad30a21c0db13b/server/routes.go) | `3fc5a208dabafa715d4ca3114aa84c8181d7d5f215c151b79224885883b060b6` | 默认→模型→request 覆盖；显式 num_batch 使 auto=false |
| [server/sched.go](https://github.com/ollama/ollama/blob/cf2a313a298066d572c36812e5ad30a21c0db13b/server/sched.go) | `660ad9b4b523ad3c349c42712fe93ace84ece742f617495fda75740f5948c1ee` | auto 才动态 batch；16384ctx 默认候选1024、按 headroom 降级；显式512不同于旧1024应重载 |
| [llm/llama_server.go](https://github.com/ollama/ollama/blob/cf2a313a298066d572c36812e5ad30a21c0db13b/llm/llama_server.go) | `8ce37fcd02f921ebd90ab51244e5f0a7f3ec52e3db1f9902a7c5be4853c034c1` | appendBatchArgs 将 NumBatch 映射为 -b/-ub |

最小新方案假设为不可变 profile 显式 `num_batch=512`，保留严格 runner whitelist。没有发现“服务生命周期第一次必为512”的官方规则；旧冷/暖相关性不足以定位具体资源输入差异。须真实证明暖服务连续运行及卸载重载，不能用每案重启 Ollama 的验收技巧宣称普通用户可用。

`LocalCapacitySession.prepare/_loaded` 当前硬编码旧 PROFILE_ID，新 variant 还需可信 profile/value/request 同一绑定；load-only probe 已完整使用 profile.options()。保留全部 loaded/ready/arm/consume/runner 检查，不覆盖全局旧 ID。

## 后续安全顺序

1. R13 最小修复、真实错误响应负控、未知状态/重启/Backup/禁止重发回归，独立审查后整合。原失败 DB 不改写。
2. 新不可变 profile 与显式 batch 合同；时间、输入/输出容量、scope、历史兼容写清，0真实调用先工程验收与独立审查。不能删除中文案例、放弃 LOCAL 或降低标准制造通过。
3. 保留原资格门，冻结有实质来源和限制的正向样本、真正未见 holdout、版本/code/source/request/profile/capacity。旧 mic-test/文件标题不能充六正向；未满足原资格不续 LOCAL。
4. 按新冻结逐例一次，独立语义通过才下一；首失败停止。暖服务与普通 GUI 连续操作、保存/主题/Evidence回跳、重启及全表全DATA Backup/Restore 和最终完整回归后，才考虑采用。

来源盘点不授资格：phase9 corpus 明确 synthetic_only、内容为图书馆/测试叙述；未找到现成非私人且有实质判断的中文音频。可另预检完整短篇工程决策文档作为 TXT/MD 来源（如英文 ADR-027、中文 ADR-012/ADR-010），不能截前五行；完整生产请求容量及语义覆盖仍须冻结前证明。已保留的 YT holdout 不预先挪作 LOCAL 或向实现者公开私有语义控制。

本任务仅新增此独立报告；未修改产品、测试、旧封存证据或模型资格。后续 R13 代码审查须另读作者固定提交并实际验证，不由本预检代签。
