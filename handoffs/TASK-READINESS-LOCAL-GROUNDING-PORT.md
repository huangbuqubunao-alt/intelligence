# TASK-READINESS-LOCAL-GROUNDING-PORT 交接报告

## 元数据

- Task: `TASK-READINESS-LOCAL-GROUNDING-PORT`
- Role: `Implementer`
- Agent/session: `native_scan_resume`
- Base: `c166377110a2c0923e44378c33a8957950a4e185`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-local-grounding-port`
- Branch: `codex/task-readiness-local-grounding-port`
- Increment: `cbbd6e6e52ca868093f5c103fd5d0f665efa9ebd`; remaining implementation and this report are the final delivery commit (exact SHA in delivery message).
- Reported: 2026-10-15

## 目标与范围

新固定 9b native-thinking profile、生产/准备/once harness 共享请求 builder、严格固定包资格 reader、39 历史 proof 兼容；工程验收与负控，0 真实模型调用，0 新资格。

- `local_distillation_profile.py`: registry allowlist 固定 id/model/digest/runtime/prompt/schema/options/request limit；通用忠实归因/必要限定与实质保留规则，无旧样例答案。`max_request_bytes=7680` 仅是请求体资源限制，**不是 token 容量证明**。
- `distillation.py`: optional profile 默认 None，semantic/reservation/text execution 身份仅新 profile 加绑定；单一新 request builder；new-only marker/strict parser 与完成 metadata 检查；新 text proof 复用原 v2 wire/39 表。当前通用输入导出仅省略新增且为 None 的两个 profile key。
- `intelligence_read.py`: 先验证完整 stored proof/profile allowlist，再重建旧/新执行身份；历史读取不依赖当前资格。
- `local_distillation_qualification.py` 与固定 `resources/local_distillation_qualification_v1.json`: 当前 `records=[]`。严格 binding/code/schema/route/scope/language/case 集合、once/ledger、独立语义审查、时效、来源与真实未见 holdout 校验；外部传入 fixture bytes 无法铸造固定包生产 authority。YT10 与 LOCAL8 隔离。
- `runtime_composition.py`: 提供六个 scope/output-language 状态；只让固定包当前资格选择独立 Intelligence 9b transport，原 fast scoring 8b/DeepAnalysis 不变。
- `scripts/qualify_local_grounding_v1.py`: 默认 describe-only；准备重用普通 reservation/完整 Evidence；真实执行需完整 freeze/来源/资源证明与逐例 once permit，前例独立 PASS 才续；完整 DATA/database/hash 检查、磁盘/内存/manifest+所有 blobs、串行重模型检查；仅保存公开 final/完成 metadata/opaque raw hash，不读取 thinking，不自动签发资格。
- 任务内必要兼容补充，经 root 明确批准：旧 `qualify_readiness_qwen35_intelligence.py::historical_timed_input_projection` 只为原研究封存格式导出 YT/TIMED。字段白名单、39/profile 新字段全默认才允许；LOCAL/TEXT/range/未来字段拒绝，不套用新请求、普通39导出、资格或历史卡读取。
- 新 unit/integration 测试；复用原39恶意 archive/反向读取12项矩阵，覆盖新 profile，原测试与断言不改。

没有修改 state/source_policy/local_api/App/CreatorFollowing、Schema、依赖/锁/工具链、owner config/凭据、正式 DATA/Vault。仅复用现有 .venv/node_modules symlink，无安装。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 默认 None 旧 Cloud/8b 请求与 reservation、旧 TextProfile hash | PASS | 黄金 byte/hash 单测；旧 provider/授权/费用与39集成回归 |
| 新 profile deterministic identity / 同 builder | PASS | profile/harness/proof 单测及 integration；无真实 provider IO |
| 固定包空资格与所有否定资格分支 | PASS | 初始资源严格 `records=[]`；fixture结构阳性仅用于 reader 拒绝控制，不能授生产 authority |
| 原39/新39 provenance、恶意多记录联动与 backup/reverse consumers | PASS | 原39测试与新 profile 同一12项恶意矩阵；未改15列/trigger/512KiB |
| once 执行协议/opaque thinking | PASS（离线结构） | fake wire 的容量算法仅测试内替代，once claim、重复拒绝、公开 final/metadata 断言；不能推导真实模型资格 |
| 新 prompt 完整输入容量 | **BLOCKED for actual permit** | `complete_input_token_upper_bound` 明确抛 `LOCAL_CONTEXT_CAPACITY_UNVERIFIED`；生产与once两执行门、harness资源检查均关闭 |
| 真实模型语义/holdout/LOCAL8/普通GUI完整链路 | 未执行 | 本任务明确0真实调用；等待全部 core+UI 接受、容量方案接受与统一 freeze/逐案permit |

## 检查结果

所有日志位于 ignored `.var/grounding-port/`，未用 fixture PASS 更新资格资源。

| 命令/检查 | 结果 | 日志 |
|---|---|---|
| compileall 修改模块/脚本/测试 | PASS | shell 实际 exit0 |
| Ruff `check src tests scripts` | PASS | `final-ruff.log`；最终代码再次 exit0 |
| strict mypy `src/youtube_intel` + 两研究/新 harness 脚本 | PASS，106 source files | `historical-export-mypy.log` |
| 新 profile/reader/harness 容量负控单测 | 59 PASS（历史适配前） | `capacity-closed-green.log` |
| 历史适配负控+旧 research/capacity 整组 | 119 PASS | `historical-export-green.log`；包括原 sealed-input 不变断言 |
| 新39 proof+12项恶意矩阵 | 17 PASS | `legacy-export-and-proof-green.log` 中另有下述旧断言 FAIL，未混报全绿 |
| 新 timed 普通 service 正/零 marker 与身份绑定 | 2 PASS | `new-timed-markers-green.log`；离线 transport，未授资格 |
| 最终完整受影响后端26文件集合 | 715 PASS，421.12s | `final-affected-v2-pytest.log`；1项预期恶意duplicate ZIP fixture UserWarning，无失败；随后补充2项timed测试亦 PASS |
| 全前端测试 | 468 PASS / 28 files | `final-frontend-tests.log` |
| TypeScript + Vite build | PASS | `final-frontend-build.log`；前端0 source diff，之后后端变更未重复无关前端检查 |
| `git diff c166377 --check` 与范围复核 | PASS | 无空白问题；未触并行作者文件/Schema/依赖/资格凭据 |
| 旧 TextProfile AST 与零资格/容量边界审计 | PASS | exact-base AST dump 对比完全相同；resource[]、6 scope/language NOT_QUALIFIED、容量函数抛 UNVERIFIED；无 provider IO |

## 失败、跳过与风险

真实失败全部保留，未删/skip/减弱测试或改变旧 semantic 标准：

1. 初始 TDD 缺模块/缺新 profile 绑定/缺 harness 失败，见 `profile-red.log`、`qualification-red.log`、`proof-red.log`、`harness-red.log`。实现后相应 green 已通过。
2. once permit 的 scope 可误借给不同 LOCAL wire，`scope-permit-red.log`；增加固定 `case_scope` 与 scope/language 精确匹配后 green PASS。
3. 初次全量 `686 PASS / 1 FAIL`，`final-affected-pytest.log`：`tests/unit/test_readiness_qwen35_capacity.py::test_capacity_preparation_seals_original_input_data_and_fresh_execution`，旧脚本659行 `ValueError: single capacity must preserve original input in a fresh execution`。先只省略新增2个 None profile key，targeted 同断言仍 FAIL（`legacy-export-and-proof-green.log`），停止重复该方法。精确比较公开 verified-input（未读 response/thinking）发现旧封存早于39，新基线已经增加 wire/input/context 和 Evidence locator/range defaults。`git archive c166377` 到 ignored exact-base 独立 cwd 重跑，原脚本659行同断言 **1 FAIL**，见 `exact-base-sealed-input.log`，确认 pre-existing。root 批准严格历史 YT/TIMED export 适配后，原输入 SHA/DATA/新 execution/原断言均 PASS，旧 freeze/失败 receipt 不改。exact-base 首次从外层 cwd collection 导致模块混用 ImportError，改为独立 cwd 才得到有效基线证据。
4. 容量负控 `capacity-closed-red.log`：原完整 permit 可直接执行且 prompt_eval_count2049 被接受，2 FAIL/9 PASS。修复：所有新profile执行先要求编译的可信完整 renderer/tokenizer 上界；当前缺证直接关闭；回执/response 要求 prompt≤2048、生成<6144，且后验 token 数不能替代生成前完整输入证明。`capacity-closed-green.log` PASS。绝不升 ctx、截来源/Evidence、修输出或用旧912估计。
5. 中间 Ruff import 顺序、mypy JSON hook kwargs 等真实错误见对应 `*-mypy.log`，已按具体报错修复，最终 Ruff/strict mypy PASS。首次增量提交时 Ruff 曾失败仍进入提交，最终完整交付已修复并复验，未声称该增量当时全绿。

容量后续必须由 root 先固定官方 Ollama0.40.1 qwen35 renderer（`show.template` 的13字节不是完整 framing）、tokenizer/byte-fallback 与模板特殊token上界或精确 tokenizer 数据/算法，再决定 ctx/input资源合同。当前 .venv 没有 tokenizers/transformers/sentencepiece/gguf/mlx_lm，未下载；tiktoken/8b 不可近似替代。改变容量算法或 ctx 必须先独立审查，并会改变执行 code/profile fingerprint；当前不能签发实际 permit。

UI/capability 接线另需 root 从 SourceInterest 接受后的最新基线串行任务：使用 `local_distillation_capabilities()` 的确切 scope/output-language 状态与所选 Intelligence model；不能用当前 Settings 8b fast评分信号描述未来9b正资格，不改变8b/DeepAnalysis资格。本任务没有 local_api/App 权限且未扩范围。最终统一 freeze 必须在该接线和容量方案接受后。

## 复用与许可证

`DIRECT` 仓库现有标准库 urllib/json/hashlib/importlib.resources/SQLite/once ledger、Pydantic strict models、SourceAuthority/Evidence/parser/DeepAnalysis reviewed-resource pattern。依据任务卡、port plan 与 `docs/REUSE_REGISTER.md` 的既有已批准组件；未复制第三方源码，未新增依赖。Ollama HTTP adapter 沿用现代码（Ollama MIT），模型固定既装 manifest，本任务未下载或分发权重/tokenizer。`REJECT/DEFER` Ollama SDK/HTTPX/近似 tokenizer/外部 boolean authority：增加依赖不能替代完整 profile/容量/语义审查，现 stdlib 接口足够完成工程负控。

## 实现者结论

- 工程建议：独立 `IN_REVIEW`；容量与真实语义仍 `BLOCKED for actual permit`，不宣称本地洞察可用。
- 交付后 clean STOP，禁止作者 merge/main/授资格。Reviewer 与 root 填写后续审查/验收结果。

## Reviewer / 主控验收 / 整合

待独立 Reviewer、Orchestrator、Integrator 填写；作者不自签接受。

### 独立 Reviewer：APPROVE（2026-10-15）

- Reviewer：`local_text_review_resume`；固定 base `c166377110a2c0923e44378c33a8957950a4e185`，
  author candidate `2e754fb15b8e88afdd4c2789f7a316f2e517e8e6`（含 `cbbd6e6`）。开工及结束前重验
  exact HEAD/clean worktree，审查完整13路径 diff、task/package/plan及持续授权；graph-first 仅返回旧符号，
  新实现以该固定 source/diff 为准。
- **APPROVE；未发现当前任务内 P0/P1/P2。** 仅接受工程端口与负控。完整输入容量仍
  `LOCAL_CONTEXT_CAPACITY_UNVERIFIED`，固定包 `records=[]`，六 scope/language 均 NOT_QUALIFIED；
  真实模型语义/资格/普通GUI可用性未通过，不得据本结论签发 permit 或宣称可用。
- 本次只写本 handoff，无业务/测试/schema/config/资格资源修改、无模型/metadata调用、无正式数据访问。

#### 五轴审查

1. **规格/正确性**：仅可信 registry 的新 profile 增加 semantic/reservation/text execution 绑定。
   None 不序列化新增 profile keys；独立黄金 byte/hash 测试通过。以 `git show <base>:distillation.py`
   做 AST 对比，四个旧 Cloud transport（OpenAI/NvidiaNim/Moonshot thinking/nonthinking）及旧
   `LocalTextDistillationProfile` 完全相同。新普通 service 的 timed 正/零 marker 与 Text proof 正向通过。
2. **安全/资格**：复核固定包 authority seal、raw caller bytes无seal、严格字段/重复key/完整cases与时效/
   scope/language/model/runtime/profile/schema/code/once/ledger/review绑定；YT10不授LOCAL8。
   `production_qualified=True` 不放行新 profile。实际容量函数始终抛错，production和once两门及harness
   resource门均关闭，无环境或调用者容量开关。test-only monkeypatch 仅在测试中；新进程重新证明
   当前空资格、六种状态、容量关闭和零 urllib IO，不将结构阳性或fake wire当生产 authority。
3. **历史/恢复**：39表、trigger、15列、512KiB与旧/新proof验证不改存储合同。reader先验证完整proof及
   精确profile allowlist，再重建执行身份，不依赖当前资格。新profile重跑原12项恶意关联归档矩阵通过。
   独立额外future-id、已知profile options drift、顶层profile hash恶意proof均重算input/proof/DB/ZIP
   manifest hash、恢复原trigger，SQLite FK/integrity有效；stage和current/recorded/card/Save/listSaved/
   Topic全部拒绝，live全表/完整DATA不变。合法新profile历史读取在qualification方法被设置为必失败时
   仍成功；另以原SummaryRefresh正/负用例换新profile，合法未来Summary刷新后历史可读且revision不变，
   原Summary字节损坏后所有原可信入口关闭。
4. **边界/维护/性能**：生产和harness共用builder/response parser，固定请求/响应字节上限、有限scope与
   strict marker，不修输出、不访问thinking。once claim先于请求且文件exclusive+fsync，旧ledger防重发。
   历史export只有原YT/TIMED明确字段白名单，新增39/profile字段必须全默认，未来字段/LOCAL/range拒绝；
   原封存input SHA/DATA/fresh execution断言实际通过，未改旧freeze/失败receipt。
5. **范围/复用/红线**：完整13路径无state/source_policy/local_api/App/Schema/依赖/锁/正式配置/凭据变更，
   旧测试文件无修改，新增测试无skip/弱化标准；DIRECT现stdlib/strictparser/SQLite/resource/ledger，无
   外部实现复制或新许可。前端source零diff，因此本轮不重复无关前端测试/TS/build；不把作者468项前端
   或715项完整affected结果标成独立复验。root最终整合、全套与真实GUI另行记录。

#### 独立实际检查

| 检查 | 结果/证据 |
|---|---|
| compileall 修改生产模块/两个脚本/四个新测试文件 | exit0，先于测试 |
| `.venv/bin/ruff check src tests scripts` | PASS；`/tmp/grounding-review-ruff.log` |
| `PYTHONPATH=src:. .venv/bin/mypy --strict src/youtube_intel scripts/qualify_local_grounding_v1.py scripts/qualify_readiness_qwen35_intelligence.py` | **106 source files PASS**；`/tmp/grounding-review-mypy.log` |
| 新profile/qualification/harness/proof及原readiness capacity五文件 | **125 passed，54.26s**；`/tmp/grounding-review-focused.log` |
| 原openai/moonshot/ollama/dispatch/research、reservation、39 proof/text/timed/wire、trusted read十一文件 | **308 passed，256.30s**；`/tmp/grounding-review-regression.log` |
| runtime composition / distillation source context两文件 | **32 passed，36.61s**；`/tmp/grounding-review-runtime-context.log` |
| `/tmp/grounding-review-adversarial.py` 三种有效重哈希恶意归档+历史资格独立性 | **3 passed，12.18s**；`/tmp/grounding-review-adversarial-closed-connections.log` |
| 同外部探针 `-k new_profile_keeps`，新profile合法SummaryRefresh/损坏原Summary | **2 passed，3 deselected，7.16s**；`/tmp/grounding-review-new-profile-history.log`，此处deselected只是独立选择另两项，先前3项已实际跑完 |
| 新进程空authority/六状态/容量关闭，urllib设为必失败 | PASS，零IO；命令输出已记录审查工具证据 |
| `git diff --check c166377...HEAD`、完整范围及旧AST比较 | PASS；候选及旧失败证据未改 |

额外探针自身首轮误用不存在的repository私有helper，`/tmp/grounding-review-adversarial.log` 为3 FAIL；
按生产实际构造 `LocalTextInputProofWrite(**dict(row))` 后，又暴露探针SQLite context manager未关闭连接而
导致 `PRAGMA journal_mode=DELETE` locked（`/tmp/grounding-review-adversarial-fixed.log`，3 FAIL）。
显式关闭这两个临时连接后上述3项真实通过；这两次是探针问题，未改产品、未放宽archive格式或失败断言。
原作者所有RED与pre-existing sealed-input失败日志完整保留。

后续容量任务必须使用实际生产builder的 `/api/chat` system+user两条messages，不能套单user generate
的58字节封装结论；本次不改变ctx或其profile/hash。capacity、UI capability接线、全core整合后的统一freeze、
真正未见holdout/逐例once/firstFAILstop与真实语义仍是后续门禁。提交审查后clean **STOP**，无并发模型审查。
