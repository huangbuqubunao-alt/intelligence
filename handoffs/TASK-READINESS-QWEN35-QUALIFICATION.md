# TASK-READINESS-QWEN35-QUALIFICATION 交接报告

## 元数据

- Role: Implementer; Agent/session: `/root/caption_resume`.
- Base: `08e02e2a1a3cabcf72f52ee2565eb3c14f3be7b5`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-qwen35-qualification`.
- Branch: `codex/task-readiness-qwen35-qualification`.
- Reported: 2026-10-13. Suggested state: IN_REVIEW; worker does not mark DONE or merge.

## 目标与实际范围

新增独立 research harness、36个无网络合同测试、9B真实身份 profile、pre-output代码/输入/政策freeze、任务卡和本交接。没有改生产src、原语料/期待/hash、原脚本、Schema、依赖、配置、正式数据或Cloud授权。没有调用本地模型，也没有伪造模型正向资格。

使用真正的 `qwen3.5:9b-q4_K_M` / 原官方manifest `sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`，保持production_qualified=false。原v5两角色prompt/schema不变；只替换已批准的固定官方non-thinking采样options。Ollama0.40.1依赖未升级，wrapper7dd7不冒充新权重，也不 alias8B。私有thinking既不读取解释，也不显示；opaque response.json完整保存Provider响应用于审计。

主控于2026-10-13明确补充批准：research-only subtype仅在真实9B provider/tag/digest/profile正确时，移除精确INTELLIGENCE表示字段`result`；每个内容/claim/Evidence字段不改。NO_NEW原样交普通parser。没有添加新业务状态或正式权限。服务沿用普通policy、预算、EvidenceResolver、CAS dispatch、immutable execution和resource ledger；原始response保存于独立audit，现有ledger没有raw-content列，未改Schema声称新增该列。

## 复用证据

- DIRECT: Python标准库JSON/hashlib/SQLite readonly backup/exclusive fsync、已批准项目strictservice/loopback adapter/policy/budget/ledger，基线08e02e2；项目NOTICE不改。
- ADAPT: 项目既有Ollama transport，truthful9B身份、options capture、独占且持久generation.started标记；既有controlled-input setup只以runpy载入函数，无旧transport/calibration执行。
- REFERENCE: 官方Qwen3.5-9B Sampling Parameters/Best Practices https://huggingface.co/Qwen/Qwen3.5-9B；主控已核验一致non-thinking通用参数。Apache2.0模型许可证与固定安装证据见MODEL_REPLACEMENT_PROPOSAL及主控安装receipt；没有复制外部产品代码或安装生产依赖。
- REJECT/DEFER: 8B alias、calibration、多轮输出修补、thinking inspection、自动reroll、抬阈值、Cloud、正式factory资格。

## 验收证据

| 项目 | 结果 | 证据 |
|---|---|---|
| 真实9B身份、原prompt/schema及官方参数 | PASS（合同） | fake HTTP exact request assertions，profile/schema/code hashes |
| 表示解码不改任何内容；错provider/tag/digest/profile/extra/missing/unknown marker | PASS | 36个newtests覆盖 |
| 完整15Evidence NO_NEW；漏项/错时间/未知ID；unknown claim | PASS | ordinary parser + actual isolated SQLite ledger返回成功或REJECTED_OUTPUT |
| 生产门禁、正常WAITING_MODEL零调用不复活 | PASS | normal production continuation永不接触Provider；后续资格读取同终态 |
| CAS ledger、一次dispatch、重启、transport未知 | PASS | SUCCEEDED/NO_NEW/REJECTED/AMBIGUOUS重复continuation一致；新transport0generation；durable marker禁止reroll |
| 准備零网络、fresh directory不可覆盖 | PASS | provider方法mock fail；prepared DB/data/VerifiedInput hashes；重复prepare FileExistsError |
| exact外部review/install/start与case顺序门禁 | PASS（合同） | wrongtag/Cloud/production/runtime/blob/start/preparedSHA/space/prior拒绝 |
| 固定权重真实安装 | 主控/独立审查PASS | freeze引用主控MODEL_REPLACEMENT_INSTALL_RECEIPT.json及其SHA；本worker未下载或调用API |
| 真实语义模型资格及普通factory/GUI/BackupRestore | NOT RUN | 必须等待独立pre-output审查、每例sealed-input复核和主控执行令；productionfalse |

## 检查结果

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m py_compile scripts/qualify_readiness_qwen35_intelligence.py tests/unit/test_readiness_qwen35_research.py` | PASS |
| `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_readiness_qwen35_research.py tests/unit/test_ollama_local_distillation.py -q` | 40 PASS /12.76秒；log `.var/readiness-qwen35/contract-final.txt` |
| `.venv/bin/ruff check scripts/qualify_readiness_qwen35_intelligence.py tests/unit/test_readiness_qwen35_research.py` | PASS |
| `MYPYPATH=src .venv/bin/mypy --strict scripts/qualify_readiness_qwen35_intelligence.py` | PASS |
| `git diff --check` / staged diff check | PASS |

`.venv`是忽略的现有runtime symlink，未安装依赖。必须显式PYTHONPATH=src；既有editable安装指向另一checkout，harness会拒绝从错误checkout导入生产class。

## Freeze和下一步执行流程

- `QWEN35_PRE_OUTPUT_FREEZE_V1.json` sealed harness/profile/测试、两份原corpus+hash、原semantic review、原setup和相关生产实现；research subtype/source hash另有记录。
- 固定顺序：real-deepthink-en → real-deepthink-zh-cn → no-new-fifteen → source-injection。原nonAI positives冲突/失败全部保留，四例不能宣称全V1通过。
- Reviewer先审commit和freeze。之后在本worktree以 `PYTHONPATH=src .venv/bin/python scripts/qualify_readiness_qwen35_intelligence.py --case <固定case> --prepare-only` 创建fresh snapshot及真实ordinary VerifiedInput；root source只读路径固定为主控隔离runtime，非owner。
- 每例输出前必须复核prepared.json、verified-input.json和输入政策；外部root手工receipt需要绑定其preparedSHA及harness/profile/freezeSHA、安装/runtimeoptions/余盘、pre-output APPROVE和root_start_authorized。不能由harness自己mint。
- `--execute-with-permit <receipt>` 只执行一例、保留exact request/opaque response/普通ledger结果。后续case还要求所有之前case的resultSHA和独立semantic PASS，decisiveFAIL/不支持runtime即停。无自动矩阵、无reroll。
- prepare-only若失败保留目录/partial证据；真实尝试目录固定且不可覆盖，不能以新attempt重试generation。
- 现有reservation固有identity只绑定v5与实际model，并不能表达新采样；外部freeze仅供研究，不是生产资格receipt。真实positive manual-command含profile；controls保留原源策略reservation，freshDB/profile/per-case外部sealedreceipt绑定尝试，不创造假Summary去改变资格。

## 失败、跳过与风险

- 原RED：缺少新module导致ImportError，log `.var/readiness-qwen35/red.txt`保留。
- 普通WAITING_MODEL是现有terminal读取语义。最初test先调用normal continuation再调用qualification期望SUCCEEDED，真实返回WAITING_MODEL；没有改状态机。分成fresh资格test和单独normal-gate test后均PASS。
- NO_NEW成功真实枚举为SUCCEEDED_NO_NEW_INTELLIGENCE，test/后续receipt按真实名称绑定。
- 单文件mypy开始只给PYTHONPATH，指向installed无py.typed模块；改用MYPYPATH=src检查当前源，没有ignore或降低严格性。
- 全backend/frontend/build与真实API/UI/BackupRestore不属于此无产品源码改动切片，未重复运行，后续真正资格和集成须主控完整验收。
- fake-wire contract不会证明固定runtime接受每个option、模型延迟/内存/语义可靠。外部receipt runtime_parameters_verified必须有真实独立来源证明，不能据mock结果填true。
- 当前无实际qualification attempt准备/执行（0 real calls）；worker已停止，等待独立pre-output review。此交接不能作为模型生产放行。
- 无超范围修改、依赖/Schema/配置/正式owner数据/网络/Cloud红线；没有删除或弱化测试。

## Reviewer与主控

等待 `/root/intel_bounded_review` 独立审查，commit SHA由实现者提交后回报主控。主控保留最终验收/任务状态/执行令，未批准整合或任何main采用。

## 独立 Reviewer：限定代码与冻结预审（2026-10-13）

- Reviewer: `/root/intel_bounded_review`；被审实现：`bdabef7b67df711e6d073ffbbb5c7127dba40591`，基线：`08e02e2a1a3cabcf72f52ee2565eb3c14f3be7b5`。
- Verdict: **APPROVE — 仅 research code/freeze PRE_OUTPUT**。P0/P1: 0。不是实际模型资格批准、运行授权或生产采用；每例 sealed prepared input 仍须独立复核，且须主控外部启动 receipt。
- 实现者已停写且审前 clean；审查没有改业务代码、测试、profile、冻结文件、正式配置或数据。现阶段没有准备四个实际病例，没有模型调用；本节仅补交接。

独立核对了全部新增实现、测试、任务范围、17项冻结文件 hash、原语料与原语义门槛、ordinary generate source hash 与 research subtype source hash。原 v5 prompt/schema、原 NO_NEW 完整 coverage 和 ordinary claim/Evidence parser 均保留。正向表示仅删除精确 `result` marker；错误身份、marker、额外字段、缺失字段和无效 Evidence 都拒绝，未修补文本或提高来源权限。prepare 用明确的隔离只读来源建立新目录/数据库，不触发网络；exclusive fsync 的 generation 标记在 HTTP 前持久化，重复、重启与不明结果不能 reroll。外部许可绑定代码、profile、freeze、prepared snapshot、安装身份、空间和固定病例顺序；后例要求前例精确 result hash 与独立语义 PASS，生产门禁保持 false。

独立执行：新研究合同测试 **36 PASS / 13.70秒**；普通 Ollama 测试 **4 PASS / 0.19秒**；两个新增 Python 文件 py_compile、Ruff 均 PASS；`MYPYPATH=src .venv/bin/python -m mypy --strict scripts/qualify_readiness_qwen35_intelligence.py` PASS；基线至候选 `git diff --check` PASS。首次 mypy 未给 MYPYPATH，读到另一 checkout 的 editable 安装而报 import-untyped；随后按任务指定源路径重跑通过，没有 ignore 或降低严格性。

源码级参数支持独立核查使用只读官方固定版本文件，不安装/编译/升级或调用模型：

- [Ollama v0.40.1 llama_server.go](https://github.com/ollama/ollama/blob/v0.40.1/llm/llama_server.go) 将固定 options 写入 `/v1/chat/completions` 请求，think 对应 template kwargs。
- [固定 native runner 版本](https://github.com/ollama/ollama/blob/v0.40.1/LLAMA_CPP_VERSION) 为 `b11351`；[CMake 构建引用](https://github.com/ollama/ollama/blob/v0.40.1/llama/server/CMakeLists.txt) 绑定该版本。
- [llama.cpp b11351 OAI 参数转换](https://github.com/ggml-org/llama.cpp/blob/b11351/tools/server/server-common.cpp) 转发剩余原生字段；[schema](https://github.com/ggml-org/llama.cpp/blob/b11351/tools/server/server-schema.cpp) 解析固定 temperature/top_k/top_p/min_p/repeat_penalty/presence_penalty/seed；[context](https://github.com/ggml-org/llama.cpp/blob/b11351/tools/server/server-context.cpp) 将解析结果交 `common_sampler_init`；[sampling](https://github.com/ggml-org/llama.cpp/blob/b11351/common/sampling.cpp) 使用这些参数及 seed 创建实际采样链。

这些证据证明固定官方源码中有参数语义路径，**不能证明已安装 binary 与源码逐字节对应，或真实9B加载/模板/容量/延迟/内存/输出质量已通过**。mock wire 与版本字符串不能替代实际测证；首个受控调用仍须记录真实兼容与语义结论，遇不支持或决定性失败即停。不得通过额外 debug render probe 加载模型。全后端/前端、正式 factory、macOS GUI 与 Backup/Restore 未在本限定无产品源码改动预审重跑，留给主控后续完整验收；此处无生产资格或 main 合并许可。
