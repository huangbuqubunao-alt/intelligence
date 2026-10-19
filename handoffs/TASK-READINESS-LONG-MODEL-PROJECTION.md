# TASK-READINESS-LONG-MODEL-PROJECTION 交接报告

## 元数据

- Role：Implementer；agent `long_lossless_codec_oct19`。
- Base：`fe4cfba56bb981c917c218747f54f1aeffd4ed8e`（已接受 codec `15ccb3f` + task metadata）。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-long-model-projection`。
- Branch：`codex/task-readiness-long-model-projection`。
- 实现 commit：`65670b785cf59fb42dcf489dc8c55ecbf6f91efe`；本独立报告另 commit，最终 HEAD 见回传及 `git log -1`。
- Reported：2026-10-19。建议 `IN_REVIEW`；作者提交后 clean STOP，不合 main。

## 目标与范围

只新增纯 `long_grounding_projection.py`、新 `test_long_grounding_projection.py` 与本报告。完整 codec packet 是侧证明，不把逐 cue index/time/hash 和内部完整 packet 都塞入模型 context。保留原 accepted builder 全部九个语义字段，仅把 Evidence 转成全量 alias + 范围 + 无损 RLE。原 Summary 完整字节只在独立 side snapshot，不擅自送模型。

无既有产品/测试文件变更，无 Schema/registry/profile/预算/transport/资格/依赖/前端变更。旧 codec WT 仍 clean。本实现无 source DB/真实源/holdout/thinking 读取，无网络、tokenizer、模型 load/context/generation 或 Provider IO。

## 复用与接口

DIRECT 已接受 `long_grounding_codec.expand_grounding` 及冻结 packet；现 `VerifiedDistillationInput` / `VerifiedEvidenceInput` 纯值；`local_distillation_profile.resolve_profile(PROFILE_ID).prompt("YT_TIMED")` 原固定可信 prompt；Python `dataclasses/json/hashlib`。没有第三方代码复制、新依赖或许可证资产；沿仓库 NOTICE。REFERENCE 旧 `build_local_distillation_request` context shape，不修改该 builder。

```python
prepare_long_projection(
    packet: EncodedGrounding,
    value: VerifiedDistillationInput,
    *, source_snapshot: bytes, summary_snapshot: bytes, policy_snapshot: bytes,
) -> PreparedLongProjection
```

返回仅四个冻结字段：`codec_input_hash`、`model_context_wire`、`messages_wire`、`semantic_snapshot_wire`；后三者各有独立 SHA-256 属性。没有 request model/options/schema、执行方法、注册入口或 qualification。选择模型等原值只冻结在 side，本模块不核发其模型身份/资格，不声明 messages_hash 是完整 executable request hash。

## 确定语义与边界

1. 先通过 accepted codec expand，随后核对同 video/provider、Evidence 数量及完整原序，每条 `VerifiedEvidenceInput` 的每个字段均与 packet 原 Evidence 精确同类型同值；不能按20截输入。bool 不冒充整数，原 excerpt/hash/timed ID/hash/时间/所有 locator/可选 source hash 都须相等。
2. 首切片仅 `YOUTUBE` / `ollama` / timed `wire_version=None`，输出语言 en / zh-CN。LOCAL/LOCAL_TEXT/Cloud 拒绝。完整旧 value（包括原 semantic hash、selected model、旧 profile/context 可选字段）只冻结保存，不验证其上游业务权威、不把旧 profile 身份作为新准入。
3. `model_context_wire` 精确九个字段：`video_id,video_title,source_display_name,evidence,personalization,focus,ignore,style,output_language`。metadata 与全部列表值/顺序保留，空列表、可空 metadata 与内部空白均不归一化。原 builder 本来没有独立 Summary；此处也没有。
4. 每条模型 Evidence 仅 `{evidence_id:"E1",start_ms,end_ms,runs:[{text,repeat}]}`。alias和run边界只能来自冻结 packet。repeat 为原非空 marker 数，即 exact 正整数；同一 Evidence 内相邻逐字符相同文本才复用。构建时展开 runs 后以原 `\n` 连接，必须精确等原 excerpt；不 trim/NFC/摘要/筛选/跨边界合并。完整逐 cue 证明保留在 side packet，不从范围推断个别 cue 时间。
5. `messages_wire` 仅固定 system + JSON user 两消息。system完整保留原 YT_TIMED prompt作为前缀，只追加固定版本/RLE/alias说明；source/title/Evidence/兴趣/focus/ignore/style始终 JSON data，不拼入 system。保留原归因、reported非独立验证、个人经历不推广、限定/不确定性/立场/语言规则。未声称系统prompt隔离等于模型已通过注入或语义验收。
6. `PROJECTION_VERSION=long-grounding-model-projection-v1`、`PROMPT_VERSION=long-grounding-lossless-rle-instructions-v1` 同时进入 system消息和 side身份。没有沿用或提高旧short合同/预算；追加说明仍 positive≤20，NO_NEW全N原序，但实际新 schema/执行准入尚未实现。

## 冻结 side 与哈希

`semantic_snapshot_wire` 是新的 canonical JSON envelope，固定字段为 projection/prompt版本、原 trusted prompt hash、`codec{canonical_wire,input_hash}`、完整原 `value`、三种 `snapshots{wire,hash}`、model context hash和messages hash。canonical为严格 UTF-8、sort_keys、紧凑分隔符、ensure_ascii=False、allow_nan=False。

三种 opaque snapshot 要求非空 strict JSON object；duplicate key、NaN/±Inf/指数溢出、错UTF-8、lone surrogate、超深、空/非对象/尾随数据均拒绝。未知业务 key 刻意原样保留，不臆造业务 Schema。原 bytes（包括空白、转义形式、key顺序）以 UTF-8 字符串无损封入 side，读取后 encode 可精确还原；不是用重新canonical后的 snapshot 代替原 bytes。

**非空/语法合法/哈希相等并不证明snapshot真实或完整。** 本纯结果没有任何authority字段或执行能力；未来factory/proof必须核对完整 source/Summary/policy记录、所有版本/关系及原业务身份，不能拿任意伪JSON获得准入。原 public final wire/hash和decoded canonical/hash仍由既有codec分别保留，本模块不接收或改写模型输出。

## 资源限制

以下全部是新纯预览的内存/序列化安全上限，不是修改旧profile预算，也不是 model context/slot允许值；超限显式 ValueError，无截断或降质。

| 资源 | 限制 |
|---|---|
| codec packet/cues/Evidence/单excerpt | 完全沿用 accepted codec全部上限和唯一canonical校验 |
| 每个 opaque snapshot | raw及校验canonical各≤1000000 bytes，非空对象，JSON depth≤16 |
| 每个 personalization/focus/ignore tuple | ≤4096项，exact tuple / exact str，不丢项；不接受 mutable list |
| metadata/可选string | 严格UTF-8；单string≤8000000字符，metadata累计UTF-8≤8000000 bytes |
| 完整原 value canonical | ≤8000000 bytes（包含全部原Evidence） |
| model context / messages canonical | 分别≤5000000 / 6000000 bytes |
| 完整 semantic side canonical | ≤16000000 bytes |
| semantic/context/profile SHA-256字段 | 64位小写十六进制，optional字段允许None；仅冻结身份、不验证authority |

先精确验证Evidence标量slot，再复制dataclass，避免恶意循环/错误类型触发无界递归。metadata也是先类型/文本总量再冻结。所有返回bytes不引用原可变对象。

## 验收证据与检查

均使用现有 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/` 工具和 `PYTHONPATH=src`；未安装或更改依赖。

| 检查 | 结果 |
|---|---|
| `mypy --strict src` | PASS：107 source files（含新模块，语法/类型通过） |
| `ruff check src/youtube_intel/long_grounding_projection.py tests/unit/test_long_grounding_projection.py` | PASS |
| `python -m pytest -q tests/unit/test_long_grounding_projection.py tests/unit/test_long_grounding_codec.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_harness.py tests/unit/test_local_grounding_qualification.py tests/integration/test_local_grounding_proof.py` | PASS：291，55.37s；其中68新projection +110既有codec +113既有grounding回归 |
| `git diff --cached --check`、相对base完整新增diff人工复核 | PASS；只有本任务两新文件，随后独立报告 |
| 旧short/Cloud、registry/profile/预算/transport/资格/依赖diff | 零改；旧builder真实纯函数构造与新context测试逐字段对照 |

新增68用例覆盖全114 Evidence逐excerpt展开、同/跨Evidence重复、9字段与原prompt前缀、Unicode/控制字符/空白、注入字符串仅数据、Summary等三快照只side原字节/完整原value保留、每种metadata及side字段/hash变化、输入后续修改、全部Evidence绑定/顺序/数量/错误scope、strict JSON、实际1MB/深度边界、4096项边界、各生成wire超限和无执行能力。

合成fixture尺寸示例（**不是实际Sasha文本、token/slot或模型内存实证**）：

| 合成输入 | codec bytes | model context bytes | messages bytes | side bytes |
|---|---:|---:|---:|---:|
| 4 cue / 2 Evidence | 1448 | 403 | 3181 | 4021 |
| 228 cue / 114 Evidence | 55284 | 13983 | 19225 | 118587 |

114合成示例 model_context SHA-256：`00cf6e9bf4738699fbddcd15dbf610d6813f8718b6f29cf91f6fbf8dd553d387`；messages SHA-256：`a5f12edca7aaa2ce0b0a1c2c2abda1fddfc20cd2ae8d5382b62f8134f0c8dabf`。完整packet保留在side，模型只接上述context/messages。

## 已解决失败、跳过与风险

- 首次TDD collection预期 `ImportError: cannot import name long_grounding_projection`；新增模块后解决。
- 初次strict mypy：新模块optional文本循环变量类型冲突，改独立变量后107文件PASS；新测试import顺序Ruff修复，无旧文件format。
- 新snapshot测试最初用普通词`original`判定side泄漏，和固定prompt里的`original`误撞；检查失败断言后改用source/policy专属唯一sentinel，断言仍验证无side泄漏，未改产品prompt来迎合测试。
- `pytest ... -k both_new_versions` 先报 projection版本不在system；补两版本固定说明后PASS。
- `pytest ... -k before_recursive` 先在 `asdict(item)` 报 `RecursionError: maximum recursion depth exceeded`；复制前验证exact scalar类型/值后PASS。没有删除、跳过或弱化测试/现有断言。
- Jev bounded routing HTTP451不可用；保持原默认模型/独立review流程，无降级或自动接受。
- 未跑全仓suite/build：本任务是未注册纯新增模块，按task执行全src静态及291相关测试；最终全回归与产品验收留串行集成。
- 未读真实源/数据库/holdout/thinking，未网络/tokenizer/model IO；完整真实messages离线测量由root后续QA，不在作者范围。
- 新schema/profile/ctx/options/请求预算、inputproof/receipt、原业务authority验证、反向reader闭包、Backup Restore和真实模型语义资格仍OPEN，等tracked40+混合字幕修复后串行。此切片不能作为长内容已可执行/已可用的证据。
- `DECISION NEEDED`: None；全部任务内约定已实现，等待独立review。

## Diff复核与实现者结论

仅新增本task module/tests/handoff，未改任何既有产品、测试、Schema、依赖、凭据、真实Vault或执行配置。旧codec WT clean。建议IN_REVIEW；作者clean STOP，不设DONE，不合main、不发布。

## Reviewer结论

待root指定独立Reviewer核对base…最终HEAD、复跑检查并记录findings/verdict；作者未自行APPROVE。

## 主控验收与整合

ACCEPT/REJECT、批准整合SHA、主线commit及整合后检查均待root；本报告不是主控验收。
