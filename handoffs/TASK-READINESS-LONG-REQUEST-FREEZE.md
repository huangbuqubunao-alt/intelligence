# TASK-READINESS-LONG-REQUEST-FREEZE 交接报告

## 元数据

- Role: Implementer；session `long_request_freeze_oct20`；reported 2026-10-20。
- Base `25c7b015f253c9250e149a3ba52890a424343b23`。
- Worktree `/Users/developer/Documents/yia-worktrees/readiness-long-request-freeze`。
- Branch `codex/task-readiness-long-request-freeze`。
- Implementation `d990c41`；证据/交接的最终提交 SHA 见最终回传及 `git log -1`。
- 建议 `IN_REVIEW`；提交后 clean STOP；未自行 DONE、main、push、发布或接线。

## 目标与范围

只新增纯候选 module、focused test、本报告及 `validation/readiness-long-request-freeze/freeze-evidence.json`。没有更改已有产品/测试、公共状态、Schema、registry、CODE_FILES、runtime、capacity、依赖、配置或凭据。所有原模型失败继续 STOP；32768 只是未验证的候选上下文值，没有 token 计数、容量证明或资格。

`DIRECT` 本仓库已接受 `long_grounding_codec`、`long_grounding_projection`、`local_distillation_profile.canonical/resolve_profile`、`distillation.local_profile_for_scope`；测试复用 accepted synthetic codec fixture，并通过 accepted decode 与 `long_card_canonical` 验证正向输出。只有 Python 3.12 标准库 json/hashlib/dataclasses/typing；无新增生产依赖/第三方代码复制。来源基线如上，项目许可证见 NOTICE；stdlib Python/PSF。`REJECT/DEFER` tokenizer、估算容量、HTTP/model、源 authority/DB/proof/receipt 与持久化；留后续串行任务。Jev 已由任务记录 HTTP451 不可用，继续默认强推理，没有自动降级。无 `.codegraph` 目录；先咨询 MCP graph 找 accepted projection/codec/schema symbols，再读实际源码。

## 精确接口与后续串行接线

```python
resolve_long_profile(profile_id: str) -> LongDistillationProfile
# profile_id 必须精确为 local-grounding-qwen35-9b-lossless-rle-thinking-v1
# frozen/slots profile_wire: bytes; profile_id/profile_hash properties

prepare_long_request(
    packet: EncodedGrounding,
    value: VerifiedDistillationInput,
    *, source_snapshot: bytes, summary_snapshot: bytes, policy_snapshot: bytes,
) -> PreparedLongRequest
```

此 builder **实际调用** `long_grounding_projection.prepare_long_projection(packet,value,三完整snapshot)`，不接受 arbitrary messages/projection dataclass。先做 exact immutable bytes/长度/词法深度 guard，再由 accepted codec/projection 严格核验包与各字段。selected_model 必须是候选固定模型，其他 unsupported source shapes 按 accepted projection fail closed，YT_TIMED only。原 `value` 无 replace/bind/reseal；其 local_profile_id/hash、semantic_hash、完整 evidence、九 context 字段、input/context JSON 和所有额外 source semantic 字段均原样保留。

`PreparedLongRequest` frozen/slots 字段：`profile_hash`, `source_semantic_hash`, `source_profile_id`, `source_profile_hash`, `projection: PreparedLongProjection`, `schema_hash`, `request_wire: bytes`。只读 `request_hash`、`freeze_hash`；`request()` 每次产生 fresh JSON dict，修改不影响冻结 bytes 或下次请求。它是数据，不是 capability；构造这个类型本身不建立 authority。

- `request_wire` 是完整 canonical native JSON，恰为 model/messages/format/stream/think/options/truncate/shift 八字段，messages 与实际 accepted projection 逐 bytes canonical 相等。无 wire_version 输出字段。
- `projection` 原样含 codec_input_hash、model_context_wire/messages_wire/semantic_snapshot_wire；各自 hash property 均 SHA256 原 bytes。side 内保存 packet.canonical_wire、完整原 value 及 source/summary/policy 三 snapshot **原格式 bytes 的 UTF8 字符串**及各自 SHA；不 trim/NFC/截断/筛选/分块，不把 side 秘密发送进模型消息。
- source_semantic_hash/source_profile_id/hash 是原源侧身份，**不同于** request 候选 profile_hash；后续 proof 必须分别绑定。不要把新 profile 写回旧 VerifiedInput 或声称旧 proof 被升级。
- request_hash = SHA256(request_wire)，只绑定 native body；schema_hash = SHA256(canonical(request.format))。
- freeze_hash = SHA256(canonical({version:FREEZE_VERSION, profile_hash, request_hash, semantic_snapshot_hash:projection.semantic_snapshot_hash}))。因原 semantic/value/snapshot 都在 side，改变任何 side 输入必改变 freeze_hash，某些 side 改变不应改变 model request_hash。
- 后续 serial factory 仍须独立验证 source/business authority、真实 native renderer/template/slots、资源与 token/capacity、模型资格、严格语义/语言、receipt/execution/reader/backup closure。这里没有 transport、permit、qualification 或 token upper-bound API。

固定 profile descriptor 冻结版本、base schema/canonical hash、完整 prompt hash、model/digest/runtime/timeout、全部 options 和各 byte/item bound。通过 byte snapshot 深拷贝旧 schema，后续共享旧 dict 或 caller mutation 不改变新 profile/request。request-dependent schema 有独立 hash，不冒充一个对所有 N 都相同的 schema。

## Schema 与实际边界

保持原 result/core/四信息列表/claim_kind/stance 字段及语义。每一 reference 的 alias 与 start/end 使用完整 exact alternative 绑定，不能交叉取别条时间范围。INTELLIGENCE 1..min(20,N)，NO_NEW min=max=N（1..4102），无 prose。重复、NO_NEW 原序、supporting stance 与首尾空白等仍必须由原 accepted decode validator 严格核验；schema 不是准入或语义证明。schema 正向 core4000、文本20×2000 与 codec 一致。

完整 request bound8,000,000B；原 messages6,000,000B/model context5,000,000B/value8,000,000B/side16,000,000B、每 snapshot1,000,000B/深度16 等不放宽。真实未 patch limits 的 request8,000,000B PASS，其 messages5,691,679B；下一值 request8,000,004B 明确拒绝。此边界由4102 synthetic Evidence 加 quote escaping 构成，**不证明任何 token/context capacity**。

## 验收证据

`validation/readiness-long-request-freeze/freeze-evidence.json` 保留固定 profile、synthetic114Evidence/2406cue 的 codec/context/messages/semantic/schema/request/freeze 独立 hashes、源 profile/semantic hashes、两个新增源码 SHA、实际字节边界、检查与失败记录。不包含原生成结果、holdout 或正式数据。

| 检查 | 实际结果 |
|---|---|
| syntax/type 先行：`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .../.venv/bin/python -m mypy --strict src` | PASS，116 source files |
| `.../.venv/bin/python -m ruff check src/youtube_intel/long_distillation_profile.py tests/unit/test_long_distillation_profile.py` | PASS；首次仅新文件 import order 已格式化修正 |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .../.venv/bin/python -m pytest tests/unit/test_long_distillation_profile.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/unit/test_long_card_canonical.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_qualification.py tests/unit/test_local_grounding_harness.py -q` | **424 PASS/16.44s**，含64新增测试及旧 Local/Cloud/request/identity goldens；没有 skip/delete/weaken |
| `git diff --cached --check` 与 staged scope/full source diff review | PASS；只有 scoped NEW files，无 existing diff |

以上 Python 绝对路径 `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`，命令 cwd 本 task WT；复用现成环境，无安装。重点测试：可重复完整请求和 golden hashes；synthetic114/2406全 cues/runs/aliases；1/20/21/4102 references；正向20/21与NO_NEW完整N；unknown/duplicate/reorder/wrongrange/bool/claim/stance/extra字段拒绝；strict UTF8/nonfinite/duplicateJSON/depth/oversize；caller/共享schema mutation；完整原 context/side/source identities；IO monkeypatch禁止 sqlite/HTTP。

## 失败、跳过与剩余风险

- TDD RED：新测试最初 `ImportError: cannot import name 'long_distillation_profile'`，exit2/0.09s，因为尚无模块；随后35 PASS/12.41s，未弱化断言。
- 扩充后一次 `1 failed,423 passed in16.38s`：新 mutation test line498 `assert prepare() == original`，source_profile_hash `693915c2… != 908575e9…`。检查发现 test 每次 `prepare()` 都重新 bind 旧 profile；mutate 旧schema后自然生成不同源身份。修正为 mutation 前冻结同一 packet/value，原 assertion 完整保留且实现无修改；最终424 PASS。不是隐藏产品失败。
- 全后端/GUI/真实公开114/2406请求身份/模型/tokenizer/HTTP/holdout未运行：本任务限纯切片，root 在独立review后用已接受私有真实fixture做精确 native identity，不能拿此 synthetic fixture 代替。
- 4102 schema 含全部 exact alternatives，synthetic schema2,308,050B/native request2,783,765B；8MB 是序列化安全边界，不声称这么大 schema 能在32768 tokens或真实runtime中执行。实际 native schema grammar/template/token/slot capacity 仍需后续验证；失败则 STOP。
- accepted projection 私有固定 `_RLE_INSTRUCTIONS` 仅用于冻结完整 prompt identity；builder仍使用它的实际公开投影函数。未来该 prompt变化会由 hash/golden/prompt check显式发现；没有复制重写投影逻辑。
- `DECISION NEEDED`: None；工程无 blocker。仍未取得模型资格、生产接线、源 authority 或完整长链路可用结论。旧失败 profile/gates 完全未动。

## Diff 复核与后续角色

四个新文件：module/test/handoff/evidence。无既有文件变动、依赖/锁/Schema/生产配置/凭据/正式数据写入，无 broad formatting、模型或网络动作。作者提交后 clean STOP。独立 Reviewer 应审 `25c7b01...HEAD`、重跑关键检查后记录 APPROVE/REJECT；root 决定接受、串行整合及真实fixture身份核对。本报告不替代 independent review 或 root 最终验收。

Reviewer：待独立 fresh review。主控验收/整合：待 root；未由作者执行。
