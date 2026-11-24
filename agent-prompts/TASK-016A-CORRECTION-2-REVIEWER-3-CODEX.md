# TASK-016A Correction 2 独立 Reviewer 3

全新独立 Reviewer 3，只审查，不修复。固定 source：
`/Users/developer/Documents/yia-worktrees/task-016a-intelligence-contract-foundation`，分支
`codex/task-016a-intelligence-contract-foundation`，HEAD
`dfe087924d1c99695b2608afbfea96e46e93175f`，唯一父 Review 2 evidence
`2ea00258ec2b1843e268d4ed1ffef03bd6b0347d`。Review 2 必须 handoff-only。

Correction 2 仅三路径：domain、contracts test、handoff；完整 TASK-016A 仅五条原授权路径。
核验父链/动态 main/范围/洁净度/diff/禁止路径后，独立静态与对抗审查完整契约：

- `KnowledgeContent`（模型侧）绝不能接受 Registry/excerpt/hash/timestamp，只能返回 ID；
- `KnowledgeResult`（应用侧）必须要求 Registry，并交叉验证所有 summary/point 引用；缺失、
  重复、未知 ID fail-closed；
- 非有限时间戳、trusted timestamp basis、mode/fallback/digest、config legacy mapping、
  Weekly V2、update-bypass 无退化；
- Local/Cloud Provider-neutral 且无依赖/Schema/Runtime/Provider 变化。

无 P0/P1 后独立运行 lock、offline sync、contracts、mypy、Ruff 全仓、full pytest、offline
build、YAML safe-load、Correction/完整 diff check。发现 P0/P1 立即停止后续门禁。禁止网络、
模型、Key、真实 Vault、用户数据、merge/push/016B–H。

唯一可写 source 路径为追加 `handoffs/TASK-016A.md`；创建一个 handoff-only evidence commit，
唯一父必须为 `dfe087924d1c99695b2608afbfea96e46e93175f`。记录 P0-P3 和 APPROVE/REJECT，
不得改任务状态或其他文件。
