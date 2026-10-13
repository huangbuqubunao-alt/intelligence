# TASK-READINESS-QWEN35-THINKING-V2 交接报告

## 元数据与权限

- Role：Implementer `/root/intel_bounded_review`，不自审；Reviewer `/root/caption_resume`。
- Base：`4270ce6016c79ecfbe052cfaab46dbfcb25d2fb7`
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-qwen35-thinking-v2`
- Branch：`codex/task-readiness-qwen35-thinking-v2`
- Reported：2026-10-14（Asia/Shanghai；冻结时间以 JSON UTC 为准）
- 实现 SHA：本交接所属提交，提交后回传主控。
- Specific approval：`QWEN35_THINKING_FOLLOWUP_APPROVAL.md`，用户“批准该精确单次模式验收范围”。作者只合同与首例 prepare-only；没有真实执行许可。
- 提交后 STOP，建议 IN_REVIEW。Root 掌握每例独立代码/快照审查后的外部开始许可；未设置 DONE/main。

## 精确实现与复用

DIRECT 已审 Qwen35 research harness、ordinary v5 两角色 prompt/schema/parser、真实 Evidence resolver、SQLite reservation/ledger、独占 durable attempt marker、外部绑定 permit、完整 opaque response 审计。ADAPT 现有脚本的固定 profile 选择和顺序复核，不新增平行生成系统或生产接口。旧 module 默认 V1 供原合同测试使用；新 CLI 只接受显式 V2，不能重开旧 V1 prepare/execute，旧 JSON 可直接只读审计。execute_case 也拒绝 V1。

新 profile 为 `readiness-qwen35-9b-official-thinking-v2`。同已装真实 tag/digest/Ollama0.40.1，仅 `think=true / temperature=1.0 / top_p=0.95`；其他 topK20/minP0/presence1.5/repeat1/seed20261013/ctx8192/predict4096/300s 全不变。旧 V1 profile/freeze、输入及政策文件字节没有改写。四例固定 EN→ZH→NO_NEW15→injection、原语义阈值保留，旧 nonthinking 首例四项 P1 FAIL 仍失败，其余未执行。

新增外部 V2 receipt 要绑定 installation/static runtime 文档 hash 与“静态实现支持、非参数实效/资格”的原意义，还须 root 明确确认重量任务互斥、无未解决的先前重量执行。原 review/install/start/model/digest/profile/code/freeze/prepared/free-space/Cloud=false/production=false 条件保留。后例准备和执行均要求完整有序的前例独立 semantic PASS，绑定其实际 V2 case/model/digest、result SHA、一次 generation/invocation 和正确协议终态；错序/旧模式/失败/损坏 receipt 拒绝。作者不能 mint 外部真实 start。

运行 profile 更换或 tamper 会在 dispatch 前拒绝。完整 V2 freeze 必须覆盖原 V1 所有 code/input/policy 项，加原 V1 freeze、新 profile、批准/提案、安装与公开 static support；原 ordinary_v5_generate SHA 固定。

只 final message.content 进入旧 parser；不读取 thinking 字段。测试里的 Mapping sentinel 若读取 thinking 则失败；response 作为 opaque JSON 保留及 hash，没有展示或语义解释思考字段。仍只精确删除已批准 INTELLIGENCE marker，NO_NEW raw 不变，不修 prose/引用/stance/kind。length/已知 truncated 保持旧拒绝；V2 即使 done_reason=stop 而 output_tokens>=4096 也按固定预算耗尽拒绝，原响应/attempt 保留，不能重派。timeout/unknown 保留 durable marker，禁止下一重量实验前的未解决执行；没有结束他人任务代码。

## 冻结与真实首例准备（零调用）

新文件：`QWEN35_RESEARCH_PROFILE_V2.json`、`QWEN35_PRE_OUTPUT_FREEZE_V2.json`。

- profile SHA：`845d354fa6b98fdaaf5620eac393915d6d42d2395ebd4eef192d8ef0dda6d072`
- freeze SHA：`ce6a0c3a32723da83b934e320b386524629ea3dc36bf4528ebcdd36f6d3a3714`，26 项文件。
- harness SHA：`9963e688088983a26146dfae1796c03d12545ac1b4421cf1a8cab0610263b1cb`
- ordinary v5 generate SHA：`92c003ee4b5a84716f98d06253a6cf181f7a9ac972660c1737d30ff4f283b7e0`，与原 V1 相同。
- 原 real corpus SHA `a7c96ee6...`、frozen corpus `cededc00...`、semantic review `61cac8bf...` 全部原值，未修历史适用冲突或门槛。

首例目录 `.var/readiness-qwen35/readiness-qwen35-9b-official-thinking-v2/real-deepthink-en/`，其它三例尚未 prepare。

- prepared SHA：`3164b2e48c543912d1c478752e3fa5270889c5f04659cad0c6bcaba659e78654`
- DB SHA：`176b4b0265124ce36da68f05bf7544ce68f7993854f43820e2d807b834c25018`
- VerifiedInput SHA：`1cda0703943eec515f08c7e3520011c110e4069805173f5afc5971e9cc355136`
- 实际 Google DeepMind `QoXRfTb7ves`，2 Evidence、18 个完整 DATA 文件，正规原时间轴/Hash 匹配冻结实际源。
- 所有旧 V1 VerifiedInput 字段逐项 EXACT MATCH（包括 semantic hash/excerpts/时间/政策/身份）；唯一附加字段是已接受 LOCAL 切片带来的 `content_provider=YOUTUBE / local_content_context_hash=null`，不改变原 prompt 或 semantic payload。
- 只读 SQLite 核验：本新 execution 为 `PENDING / invocation_count=0 / RESERVED_NOT_DISPATCHED`。
- 准备时将普通 transport._request 设为拒绝 sentinel；实际 provider access 0，未访问 tags/chat/show、未启动模型。没有 generation.started/request/response/execution-permit/result 文件。没有关闭/停止任何模型或 ASR 任务。
- 数据来源仅 root 既有隔离 runtime 的只读 SQLite backup 和 DATA 副本，不是正式 owner 数据。新 case 路径独占创建，已存在者拒绝，未覆写旧 case。

## 检查与失败证据

日志 `/tmp/qwen35-thinking-v2-*.txt`：

- TDD 新模式初跑：6 fixture errors（select_profile 尚未实现）、4 CLI negatives PASS、36 原 tests deselected；`red.txt`。是未实现 profile 的红证据，不是语义验收。
- 最终 `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/test_readiness_qwen35_research.py tests/unit/test_ollama_local_distillation.py`：**73 PASS / 15.04 秒**，`contract-final.txt`。原 research36 + ordinary4 共40 项保留，33 新合同扩展。测试原文件完整 bytes 为新文件精确前缀，无旧测试/断言变化。
- 新合同涵盖三项参数差异、两角色/固定 schema、final-content-only/opaque thinking、一次 generation、budget/length/timeout、重启拒绝、普通 production 门禁、未授权/退役 CLI、profile 变更、错 seed/type/政策/输入、partial freeze 拒绝、V2 exclusive/static/install/code/profile/freeze/prior tamper、后例精准前序语义 receipt。
- Ruff 两文件：PASS；py_compile：PASS；`MYPYPATH=src .venv/bin/mypy --strict scripts/qualify_readiness_qwen35_intelligence.py`：PASS；`git diff --check`：PASS。
- 初 mypy 缺 MYPYPATH，把 workspace 源当 installed untyped package，报8个 import/subclass/no-any-return；原日志保留，明确指定现有 src 后通过，没有 ignore 或类型门槛削弱。
- 初新测试紧凑行触发11个 E701/E702；只格式化新增测试段，未改旧文件前缀或 toolchain；原 lint 输出未用于声称通过。
- 最终 freeze.validate 与 readonly snapshot 核验 PASS。未因更新 handoff 改动 frozen code/test/profile/core。
- 未跑全 backend/frontend/TS/build：只 research脚本/合同/冻结文档变化，没有产品源或前端；主控整体门禁仍需执行。

## Diff、风险与交接

只获批 research script、原 tests 追加、新 V2 profile/freeze、handoff。没有 src、runtime reader、配置/凭据、Schema、依赖/锁文件、下载、Cloud、正式数据或生产资格收据变化。graph 无该 research script 节点，依任务精确文件继续读源码；复用既有 harness。当前安装/static support 是既有公开证据，不是本模式实际效果、容量或资格证明；新 freeze 明确 actual runtime execution/semantic quality 仍 false。

原模式 FAIL 不受新模式影响。全部后续真实 cases 必须依赖独立预输出代码/本 prepared 快照审查、root fresh install/资源/无未解决重任务检查与外部一次 permit。任何 FAIL 不准备后例、不补输出/seed/提示/预算。即使四例通过仍只 research 证据；LOCAL8例依赖不解除，普通 production reader 保持关闭，最终采用另外审批。

## 实现者结论

提交后 STOP。请求独立 Reviewer 精确代码/freeze/首例 sealed snapshot 审查，不能仅采信本交接的自报结果。暂无额外变更审批请求；没有真实模型调用或审自己的变更。

## Reviewer / 主控结果

待独立审查与 root 外部开始许可；实现者不填写 APPROVE/资格 PASS。
