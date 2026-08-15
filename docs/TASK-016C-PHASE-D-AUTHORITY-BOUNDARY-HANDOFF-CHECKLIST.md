# TASK-016C Phase D：Authority Boundary Correction 交接清单

**状态：** READY / AUTHORIZED，仅限 ADR-026 correction。

## 实施者必须记录

- [ ] implementation HEAD 以 `39a1e864238388abe651c466c0a41a023934c872` 和本控制面提交为祖先；
- [ ] 仅修改 `runtime.py`、`quality.py`、必要的 `domain.py` 与授权测试/handoff 路径；
- [ ] 已移除 hard-coded production model/digest 作为 authority 的做法；
- [ ] capability 只由 runtime composition 在已加载 `AppConfig` 后铸造，且无 public Mapping/JSON/
  Pydantic/settings/config 构造入口；
- [ ] build/verify 只接受 opaque authority，未恢复 `settings=`、`config=` 或
  `trusted_provenance=` 形式的调用方参数；
- [ ] H1/H2 算法与既有 builder 未改；
- [ ] 没有 ScoreResult、Artifact、cache、ProviderCall、response ID、文件或数据库副作用；
- [ ] RED、GREEN、全部门禁和 final diff 范围已记录；
- [ ] 仅创建一个独立可 revert 的 correction commit。

## 独立审查必须验证

- [ ] 已加载的测试 `AppConfig` 经真实 runtime composition 铸造的 current model/digest 能 build 和
  verify PASS；
- [ ] 调用方新建 `LocalScoringSettings`、`AppConfig`、旧 provenance DTO、Mapping、JSON、provider
  response、cache/artifact 或 fixture 不足以授权 build/verify；
- [ ] 自洽 hash 伪造仍不能跨越当前 authority；配置 A 到配置 B 的 provider/model/digest/version
  变更均 fail-closed；
- [ ] `model_copy`、`model_construct`、subclass、property/serializer spoof 与 fake trusted flag 都失败；
- [ ] authority 没有成为公开产品 API，且文档没有声称抵抗任意进程内 Python 攻击者；
- [ ] `config.py`、`cli.py`、`scoring.py`、`providers/ollama.py`、`state.py`、DB、Artifact、cache、
  Finalizer、编排、TASK-016B、依赖与 lockfile 均未变；
- [ ] 必须门禁全部 PASS，且没有网络、真实 Ollama、下载或 Phase E–K 活动。

## 审查结论边界

该 correction 通过只表示 Phase D attestation 可以绑定运行中应用的当前 provenance。它不授权或
证明 Finalizer、持久化、cache recovery、ProviderCall、真实 scoring/Judge 调用或任何后续阶段。
