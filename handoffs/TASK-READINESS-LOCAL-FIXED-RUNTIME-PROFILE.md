# TASK-READINESS-LOCAL-FIXED-RUNTIME-PROFILE 交接报告

## 元数据

- Role: Implementer；agent/session `/root/local_fixed_runtime`，接替已停止旧会话。
- Base: `b3410a489f06d17ea8c62d2f27d637d3bbe25cc2`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-local-fixed-runtime`。
- Branch: `codex/task-readiness-local-fixed-runtime`。
- Product/test commit: `e021fb5646acfa09caef0819eab52610fa964524`；本报告与结果摘要后续独立提交。
- Reported: 2026-10-21 00:43 Asia/Shanghai（工具实际 UTC 2026-10-20 16:43 换算）。
- 已读 root 绝对路径 AGENTS/COLLABORATION/PROJECT_STATUS/PRD/SYSTEM_DESIGN/REUSE_REGISTER、任务卡和开工包；任务包较基线新，未改写公共任务或看板。

## 目标与实际范围

新增不可变、未获资格的 `local-grounding-qwen35-9b-fixed-runtime-v2`，固定 `num_batch=512`、`num_predict=8192`、context16384、content8101 UTF-8 bytes、原请求12288 bytes、timeout300秒、响应1000000 bytes。完整输入上界最多8191，8191+8192+1=16384。Sampler、seed、模型/digest/runtime、Prompt、Schema、native thinking不变。新增响应上限只进入v2投影；v1三scope投影及请求原字节哈希、6144预算和无显式batch的options保持。

实际改动仅三个允许产品文件、一个新测试文件、原R13测试的两处fake session节点，以及本handoff/结果摘要。没有state、Schema、资格reader/resource、harness/factory、长profile、source authority、UI、依赖或配置修改。

## 实现与边界

1. Resolver只接受两个固定ID，返回frozen实例。v2的所有新预算/显式batch均进入投影及hash；未知ID、旧profile hash套用新ID、覆盖options或不完整请求均不能获得容量证明。
2. `LocalCapacitySession(profile_id=...)`在后端构造时固定可信profile，默认仍v1。Prepare将完整value投影、canonical请求和实际wire字节绑定到proof，准备前封存hash；重入、transport claim与consume不能借用不同完整value。准备期间改动请求也会在最终ready检查关闭。原lease/线程/恢复保护保留，claim后的consume不增加HTTP、文件或进程观察。
3. v2无论cold还是warm512都只发送一次严格空messages的load-only请求，options与纯请求完全相同。重复prepare使用既有未消耗proof，不重发probe。
4. 普通runner/host校验没有接受1024。仅在v2的独立load-only转换预检中，允许固定安装manifest/6blobs/3binary、唯一固定server、同model/digest/context16384 slot、单parallel、loopback和**完整已知legacy argv集合**的paired1024。端口限1024..65535并保持可变；额外/缺失/未知/不对称参数、相似名称binary、未知slot、并发任务、缺盘或不足完整cold RAM reserve均在空probe前拒绝。没有kill、unload或restart。空load response必须精确无生成/无eval元数据，之后重新验证ps、strict512 runner和普通host；安装文件/引用/server必须与预检相同。legacy观察从不进入Ready；Ready只持有最终512观察。
5. 纯响应门使用可信resolver的output cap：v1 6143允许/6144拒绝；v2 8191允许/8192拒绝。length、非stop、donefalse、缺失/布尔/负数/超输入界计数、错误模型和空final仍拒绝，不读thinking、不修补输出。R13持久失败收尾实现保持。
6. v2 transport qualification入口显式拒绝，甚至泛用重签permit.matches为真也不能准入。generate在容量consume/POST之前再次拒绝v2，避免手动拼装session绕过未资格边界。旧v1 reader/harness/factory整文件逐字不变，重签v2 receipt仍被旧路径拒绝，资格资源仍 `records=[]`。

## 检查与外部证据

完整命令、源SHA、日志SHA、旧/新三scope与request冻结hash见：
`docs/validation/end-to-end-user-readiness/LOCAL_FIXED_RUNTIME_IMPLEMENTER_2026_10_21.json`。
全部测试使用fake transports和临时SQLite/安装字节，不产生真实HTTP/load/generation或owner数据访问。

| 检查 | 实际结果 |
|---|---|
| 首个新profile TDD RED | 45 FAIL / 2 PASS / 7.07s，未知v2；v1黄金断言通过 |
| 相似binary、probe期间request突变对抗RED | 2 FAIL / 0.76s，之后最小修正binary完整token边界与准备前hash封存 |
| 早期新旧profile/capacity/manifest/qualification五文件 | 193 PASS / 10.04s（追加最终对抗前，不冒称最终完整组） |
| 最终固定产品源码14文件完整相关组 | 391 PASS / 5 FAIL / 133.85s；见下文两处旧fake缺新方法，原完整结果保留 |
| 修正fake后整R13+旧adapter/dispatch三文件 | **44 PASS / 38.78s**，含全部原5个失败 |
| 与完整value绑定相关的v2增量 | **7 PASS / 1.92s**，49 deselected为明确限定的增量选择；不是跳过原完整组 |
| `python -m compileall -q src` 与新/必要原测试编译 | PASS |
| `PYTHONPATH=src:tests:. .venv/bin/mypy --strict src` | PASS，116 source files |
| `.venv/bin/ruff check src tests scripts` | PASS，项目既定全工程范围 |
| 额外 `.venv/bin/ruff check . --output-format concise` | 既有docs40项；本scope35项已修。五个既有docs与base逐字等，未扩范围修改；不声称`.`通过 |
| `git diff --check` | PASS |
| 四Cloud类与原LocalTextDistillationProfile AST | 与base完全相同 |
| state/backup/source authority/qualification/harness/runtime composition/resource | 全文件字节与base完全相同；records=[] |
| 原R13全部Assert AST | 与base完全相同，未删除、跳过或弱化 |

### 失败证据与修正说明

14文件命令为 `PYTHONPATH=src:tests:. .venv/bin/pytest -q` 后跟摘要内精确14路径。
失败全部位于 `tests/integration/test_local_rejection_accounting.py` 的两个原fixture节点（2+3参数化），在响应断言之前于固定产品commit的 `distillation.py:2582` 抛出：
`AttributeError: 'types.SimpleNamespace' object has no attribute 'matches_value'`。
它们原来仅stub `consume`，用于隔离测试R13响应收尾/复用诊断；所有实际session、有效v1流程、profile、history/restore、Cloud/harness以及新增v2用例通过。

Root确认后，仅为两个fake补 `matches_value=lambda value: value == profile._input()`，精确匹配完整固定输入，不使用无条件True；所有原响应、诊断、不串案、调用次数和恢复断言原样保留。产品源码完全未再改变；按root要求只运行整R13/adapter/dispatch44及相关v2增量7，不反复完整14文件组。不能将391/5与增量结果混称最终396项单次全绿。原日志完整保留在ignored `.var/local-fixed-runtime/`，摘要记录hash。

## 复用与来源

- DIRECT：已安装Python标准库与仓库现有profile/resolver/request builder、固定host/manifest/runner观察、应用lease、SQLite事务、fake transports和隔离fixtures。未安装依赖；仅按授权symlink root已有 `.venv`。
- REFERENCE：Ollama MIT固定官方commit `cf2a313a298066d572c36812e5ad30a21c0db13b`：routes显式num_batch禁自动选择、sched选项变化reload、llama_server映射-b/-ub。依据root独立handover audit；没有复制第三方实现或新增许可证负担。
- 唯一legacy实际argv只读来源为root `.var/end-to-end-user-readiness/olama-serve-20261020.log` 第449、1086行starting llama-server；仅阅读该两行，不读取thinking，不改旧证据。它们只定义可预检形状，不是新诊断permit或合格证明。
- REJECT/DEFER：自动batch、服务restart作为常规流程、1024可执行白名单、旧LOCAL8 permit续签、降低资源/模型资格标准、cloud fallback。

## Diff复核、风险与未做

- 相对base仅上述3产品+2测试及自己报告/摘要；无依赖/工具链/生成客户端、Schema、凭据/owner配置/正式数据、UI/长内容协议、main合并或发布。
- v1黄金哈希和原history/proof/NO_NEW/Cloud/restore代表真实运行覆盖；最终完整backend/frontend/普通GUI仍由root最终门禁处理。
- 本任务只证明工程；真实cold/warm/1024→512 load-only转换仍待新资源观察及独立冻结协议。Root00:29 available RAM4.985GiB低于cold-load门，不构成加载许可；本次真实模型HTTP/load/generation均0。
- 8192不保证300秒内完成；超时是真失败，不补答、不重跑择优。新profile仍未获任何模型资格，不采用旧case1 NO_NEW为正向。
- qualification code fingerprint会因允许产品文件变更而变化；旧receipt不得被重新解释为当前代码资格。
- 尚待独立review/root验收和整合；之后仍有version-specific qualification/harness、长协议、真实语义正向和最终GUI/BackupRestore/完整回归/采用门禁。

## 实现者结论

建议仅 `IN_REVIEW`。Product/test SHA `e021fb5646acfa09caef0819eab52610fa964524`；报告提交SHA由最终回传提供。提交后clean STOP，不自行ACCEPT/DONE或合并main。

## Reviewer结论

待独立Reviewer填写；作者未自签APPROVE。

## 主控验收与整合

待root决定；本报告不授采用、发布或模型资格。
