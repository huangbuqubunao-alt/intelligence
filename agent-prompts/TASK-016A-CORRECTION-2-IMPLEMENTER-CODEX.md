# TASK-016A Correction 2 Implementer — trusted Evidence Registry boundary

固定 source worktree/branch 不变，HEAD 必须为 Reviewer 2 evidence
`2ea00258ec2b1843e268d4ed1ffef03bd6b0347d`，唯一父为 Correction 1 `26a74cd…`；
Reviewer evidence 必须 handoff-only，source 必须干净。

只修复 P1：Provider/model 生成的 `KnowledgeContent` 只能携带 Evidence ID 引用，不能
携带 `EvidenceRegistry`、excerpt、hash 或 timestamp。应用拥有的 `EvidenceRegistry`
必须位于可信 `KnowledgeResult` 边界；应用封装 Result 时统一校验 summary、why-it-matters、
core points 和其余字段的所有 ID 都已登记。未知 ID fail-closed。

仅允许修改：

- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `handoffs/TASK-016A.md`

先写失败测试证明 Content 不能接受 Registry、Result 必须由应用注入 Registry 且未知 ID
被拒绝，再做最小实现。原有限时间、mode/provenance/config/Weekly/update-bypass 契约不得
退化。运行 focused、mypy、Ruff、full pytest、offline build 和 Correction/完整范围检查，
只创建一个单父 Correction commit。禁止后续任务、依赖/Schema/Runtime/Provider、真实资源、
merge/push。
