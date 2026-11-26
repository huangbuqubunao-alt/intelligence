# 新候选独立验收窗口（短编号 + 原生思考）

2026-10-25。此窗口已在真实Terminal打开，当前等待用户手动退出Codex/ChatGPT；不是模板或下一步计划，也不是模型已合格。控制器PID46802、冷metadata owner46042。独立源审查d268a4b及具体绑定审查74b2621均通过；新验收尚0load/0generation，旧Q4失败和once完整保留。

## 用户现在操作

1. 保留Terminal和Jimmm，使用⌘Q完全退出Codex/ChatGPT；最小化窗口不能释放相同内存。
2. 等Terminal明确提示“诊断窗口已停止，请重新打开Codex”。期间不要重复打开启动文件或提前重开Codex。程序不会自动关闭任何应用。
3. 重新打开本对话，发送“读取新候选验收结果继续”。不用输入终端命令；遇到错误也保留记录后返回，不自行重试。

关闭抖音和Chrome后内存仍波动，控制器现场观察6020300800B<7776604301B，且Codex仍开着；因此尚未加载。用户此前要求保留Codex，主控不能自动关闭它。程序独立于Codex运行，只有应用退出、原RAM/磁盘门、固定包/当前owner等保护全部通过才执行一次。等待最多30分钟；原生成上限300秒、子任务总时限720秒，任何结果后停止并正常清理精确owner。不能承诺模型一定正确。

## 本次仅有的变更与边界

同一已安装官方9B Q4文本权重、pinned Ollama0.40.9；只把模型输入Evidence IDs换为E1/E2，并启用原生think=true。这是两项变化，不作单变量因果推断。原18cue/两Evidence/来源excerpt/系统prompt/schema/采样/seed/8192输出/16384context/300秒和语义标准保持。实际完整新prompt必须重新测N，不复用旧722。完整NO_NEW仍合法，不能强迫产出或补引用；只允许已有不可变映射回原IDs，正文不得修改。

所有实际原始体不透明保留，审查只读取公开message.content及允许的状态/用量，不读取或展示私有thinking。诊断通过也不颁生产资格；后续仍需原完整资格、真实GUI保存/主题/Evidence/重启/全部SQL与DATA备份恢复和最终回归，满足既定条件才采用main。本次无新模型下载、付费云、产品代码/Schema/正式配置/owner数据变化。

## 接续必须先读（不能盲重跑）

新BASE：`/Users/developer/Documents/yia-worktrees/readiness-alias-thinking-diagnostic/.var/alias-thinking-diagnostic`

- 控制器：BASE/controller.py，SHA5478a41226c5e55e706622ad702d4dc49fe6e2e6ed526dbce6bd6c7379a41d8d；launch-start.json已存在，重复启动拒绝。
- 等待/结果：BASE/run-20261025/wait-observations.jsonl、controller-result.json、child-stdout.log、child-stderr.log、可选cleanup-slots.json。
- **实际子输出**：BASE/real-once-alias-thinking-20261025/，尤其generation-raw.json、diagnostic-result.json、capacity.json、precheck.json、stopped-error.json。不要误读旧Q4路径或不存在的real-once-20261025。
- 新全局once：BASE/generation-start.json。先核验其是否存在及原始结果，不得删除/改写/换路径重跑。旧实验marker在旧WT中，仍已消耗。
- 执行harness：BASE/diagnostic.py，SHA8087ef0aa16090971408bb6837066e0027790b156a4e7490e97a51b210981d77。
- 具体包：BASE/reviewed-package.json，SHA d8307117ed8e0b3fe995ac907e7bc5dc3d56ec2311ecfa11de9c4ba268161326，607271B；只由受审模板增加owner绑定，2816输入不变。
- 实际命令：root `.var/end-to-end-user-readiness/model-chain-resolution-20261025/Start-Alias-Thinking.command`，SHA03b21acc166b731aa4d7ced3454be930d93bf8acfeec03b65b3e5e4cefa78615；真实controller→zsh→login→Terminal→launchd，无Codex祖先。
- Root准备/启动实测：同root目录metadata-launch-precheck.json、concrete-package-root-precheck.json、actual-launcher-verification.json、controller-terminal-ready-v2.json。v2纠正初次检查使用了无用子目录名的问题，已实际核验正确子输出目录不存在；不改变任何冻结代码/包/marker。
- 新候选canonical f258e0660691cb99f4526a9ccee4ad0631cee75e5986037814b060e5a91eb13e；codec8193fc58ce69adee283679ddb4e0bcf3a12eaffb632823cd616fe835124ef9f2。source-case和原冻结语义在BASE/prepared.json及root原sourcecase中。

读取结果后先独立公开内容/精确Evidence/归因/猜测/相似关系/人工验证边界审查，以及实际调用数、native容量和精确owner清理。终端exit0和合法JSON不是领域接受。失败、超时、无公开正文、引用或语义不合格均REJECT_STOP；不继续后续negative/资格案例，不改预算或修补输出。成功也仅诊断信号，按Goal计划另建最小生产适配任务及完整验收，不能自动资格/main。

## 已完成检查

固定531离线PASS/27.27秒，独立531PASS/27.43秒+6边界PASS；compile12/Ruff/zsh/template拒绝通过。原旧测试直接129PASS/12FAIL为已消耗marker假设，完整日志保留；独立状态141PASS单列，未改旧断言或真实标记。2794保护hash/2816绑定/585产品文件/16旧原始凭证一致。已有产品完整6003后端/1026前端和79SQL25DATA真实GUI恢复证据不变，本次未假称重跑全部产品测试。

旧自动Goal工具仍usageLimited；本次实际工作由当前对话推进并保存了全部断点，独立Terminal不依赖自动Goal续跑。正式main/资格未动，Goal尚未完成。
