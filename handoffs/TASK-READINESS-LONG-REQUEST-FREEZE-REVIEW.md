# Pure long-request freeze 独立审查

2026-10-20；Reviewer `subtitle_recovery_preflight_oct19`，非作者。**APPROVE，新增P0/P1/P2/P3发现0。** 仅纯候选描述/请求冻结，不代表生产接线、源authority、容量、模型资格或完整Goal。

## 固定范围

- Base `25c7b015f253c9250e149a3ba52890a424343b23` → candidate `799c62552c0a76b46e70f9ddba551df404c76f02`，core `d990c4139d466ec1603b571e8cc59e993b58ac9b`；作者clean STOP。
- 独立新WT `/Users/developer/Documents/yia-worktrees/readiness-long-request-freeze-review`，branch `codex/review-readiness-long-request-freeze`。先完成上个WAIT取消只读答复，才按root单Reviewer包创建本WT；无并行Reviewer。
- 已读root精确task/package、作者immutable READY范围/新handoff/evidence及完整四新增文件diff。使用 code-review-and-quality、git-workflow-and-versioning；graph无本新符号，fallback固定源码。DIRECT已接受pure codec/projection/canonical、旧schema/profile及stdlib；无新增依赖/外部实现。
- 实现仅NEW module279行、test538行、handoff/evidence；零existing修改。未动Schema/state/registry/CODE_FILES/runtime/capacity/前端/配置/凭据、旧失败profiles或旧语义标准。本review仅新增本报告及ignored private probes。
- 运行仅root既有venv，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:.`，打印确认模块来自本reviewWT。无真实数据库/HTTP/vocab/tokenizer/model/holdout/owner/credential IO，无安装/全backend/GUI重跑；既有harness一例的临时SQLite执行范围偏差另见下文。

## 核心核验

- `long_distillation_profile.py:44–109`：候选profile为冻结bytes，独立profile_id/hash，绑定固定9b model/digest/runtime及300s timeout、完整prompt/base schema/codec/projection版本、全部采样参数/byte bounds；context32768明确UNVERIFIED_CANDIDATE。旧resolve_profile不接受新ID；对象无permit/dispatch/qualified/capacity API。
- `:227–279`：factory实际从原packet/value/三完整side bytes调用accepted `prepare_long_projection`，不接受任意messages或PreparedProjection替代packet。先做exact bytes/长度/有界depth扫描，再由accepted模块完整验证。原VerifiedInput及旧source_profile/semantic身份保持；没有bind/replace/reseal旧authority。
- 完整native JSON恰八字段：model/messages/format/stream/think/options/truncate/shift，两个messages与真实accepted projection完全相等。request_hash只绑定完整body；freeze_hash另绑定profile与完整semantic snapshot。独立改旧source profile/semantic以及side lexical bytes，model request可不变但freeze必变；新profile不冒充旧来源proof。
- `:178–225`：schema从旧schema bytes深拷贝。每个reference alternative把alias/start/end整组三项绑定，不能拼接别条range；positive1..min(20,N)，NO_NEW min=max=N，未添加wire_version/prose分支。重复/NO_NEW原序/supporting stance/严格prose仍由accepted codec强制，schema本身不是authority。所有原cue/run/context九字段与side完整保留，不截源/删Evidence/补模型文字。
- 独立N=1/20/21/114/4102逐项核对两分支全部exact alternatives及计数；positive20正控经decode/canonical通过，positive21、交叉alias/range、NO_NEW乱序被拒。caller递归修改所有返回alternative/options/messages与解析descriptor，不影响冻结bytes或后续请求，旧schema/profile goldens保持。
- 独立nested duplicate keys、Infinity、lone surrogate、超深及memoryview side输入拒绝；完整snapshot原空白/escape bytes和SHA保留，不把side中的伪指令放进模型messages。原focused集合还覆盖UTF8/nonfinite/bool/类型/oversize与深度前置拦截。
- 实际未patch limit的8,000,000B request通过，8,000,004B拒绝，该case已在本次424集合真实运行；不是仅monkeypatch小阈值。8MB是serialization guard，不能据此宣称schema grammar/native rendering或32768 token容量可行。

## 实际独立检查

| 检查 | 实际结果 |
|---|---|
| strict mypy src（先行） | PASS，116 source files |
| Ruff新module/test；base..candidate diffcheck | PASS |
| 新focused＋accepted codec/projection/canonical＋旧profile/qualification/harness goldens七文件 | **424 PASS /16.48s**，实际exit0 |
| 新私有schema全alternative、跨引用拼接、source/candidate身份与deep mutation、side bytes恶意输入 | **13 PASS /1.06s** |
| 入库两source/test SHA及synthetic114/2406的12个identity/byte字段重建 | 全部一致 |
| git diff scope | 四项全NEW，existing产品/test零diff |

424命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. <root-venv>/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_long_distillation_profile.py tests/unit/test_long_grounding_codec.py tests/unit/test_long_grounding_projection.py tests/unit/test_long_card_canonical.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_qualification.py tests/unit/test_local_grounding_harness.py`。

私有实际source/log/hash清单：`/Users/developer/Documents/yia-worktrees/readiness-long-request-freeze-review/.var/long-request-review/`，含`test_independent_freeze.py`、`accepted-goldens-424.log`、`independent-probes.log`、`evidence-sha256.json`。此处114/2406是accepted synthetic fixture，不是真公开源或holdout，也未生成模型输出。

执行范围偏差（Reviewer）：七文件424集合中，既有 `test_local_grounding_harness.test_dedicated_preparation_preserves_verified_input_without_provider_io` 实际创建全新tmp SQLite与合成DATA/音频、使用mock executor并禁provider IO。精确包要求0DB IO，本Reviewer应预先排除此例；现明确披露，不冒称全程零DB。没有真实/frozen/owner库或实际模型/HTTP访问，新增纯builder自身的禁止SQLite/HTTP测试及源码检查通过。此为Reviewer运行范围偏差，不是新模块新增数据库能力。

本轮无FAIL/skip；作者记录原模块缺失RED与共享旧schema mutation后重绑source_hash的单个fixture FAIL仍在原handoff/evidence，未冒称产品缺陷，也未删改正式断言。本review实际重新验证同一packet/value的深层共享/caller mutation隔离。

## 限制与交回

新candidate仅数据冻结，后续仍需可信source factory、profile/request/code身份持久化、原子proof/claim/receipt、current/history/NO_NEW/Save/Topic/Backup双向闭包及真实native template/slot/资源/严格语义资格。旧失败profiles继续STOP；ctx32768、bytebound、synthetic通过或对象类型均不授调用权限。root此前完整5334是旧core组合证据，本review未将其冒称覆盖新纯切片；也未重复全backend。WAIT取消/mixed属于后续独立共享核心任务，不在此扩大。

**APPROVE，report-only提交后clean STOP。** root决定接受/整合及真实公开输入身份核对；不main/push/发布，不改共同task/status。
