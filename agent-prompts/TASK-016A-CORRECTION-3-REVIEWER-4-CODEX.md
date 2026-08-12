# TASK-016A Correction 3 独立 Reviewer 4

固定 source worktree/branch 不变，HEAD `af3d168c89bed09f563e4ce00ac902d6c340bf14`，
唯一父 Review 3 evidence `81ec5c6f9d015d5d48cc36053ca6a680be893acb`，后者必须
handoff-only。只审查，不修复；唯一写入为追加 source handoff 并创建 handoff-only commit。

核验 Correction 三路径、完整 TASK 五路径、父链/动态授权/洁净/diff/禁止范围。对抗审查：

1. Result 不得是 Content 子类；`KnowledgeContent.model_validate(result)`、Result mapping、
   Result JSON 都必须拒绝，只有显式 `result.content` 可接受。
2. Content 不能携带 Registry/excerpt/hash/timestamp；Result 必须要求可信 Registry 并校验
   content 所有 Evidence 引用，未知/重复/缺失 fail-closed。
3. 非有限时间戳、trusted basis、config mode/legacy mapping/fallback/digest、Weekly、
   update-bypass 不退化。

无 P0/P1 后独立运行 lock/sync/contracts/mypy/Ruff/full pytest/build/YAML safe-load/two diff
checks。发现 P0/P1 立即停止。禁止网络、模型、Key、Vault、merge/push/016B–H。

最终以 P0-P3 和 APPROVE/REJECT 追加 handoff，Reviewer commit 唯一父必须为
`af3d168c89bed09f563e4ce00ac902d6c340bf14`，且只能修改 `handoffs/TASK-016A.md`。
