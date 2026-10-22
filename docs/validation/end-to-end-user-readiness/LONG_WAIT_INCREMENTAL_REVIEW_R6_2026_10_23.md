# R6 独立增量审查：被动备份检查与恢复重连反馈

结论：**REJECT**。无新增 P0/P1；发现一项直接违反本次反馈合同的 P2。修复仍由原实现者完成，本审查没有修改产品代码。不是对既有三方审核的重启，也不是模型资格或正式采用审查。

- Reviewer：`/root/backup_reconnect_review`，独立新对话。
- Base：`29228606ea230d1d3ccbe5b1fd2ef1e3111b0da4`。
- Candidate：`b187e8223de16ab4472455796956ed8d4899364f`。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r6`。
- 范围：准确的8文件差异；唯一后端产品文件是 `backup_restore.py`，另为恢复反馈、语音保存及媒体时长文案/测试和handoff。读取了仓库角色规则、产品/设计/复用规范以及root最新任务包和真实GUI合同；未扩大任务。

## P2：已知恢复失败会被下一次读取断连改回“正在重新连接”

位置：`frontend/src/workspace/App.tsx:3674` 与 `:3695`。

在确认ACK后，匹配当前restore_id的 `REJECTED`、`ROLLED_BACK` 或未知状态会先正确显示恢复失败和Retry，也会清除计时器，但 `confirmedRestore.current` 仍具有原来的60秒重连资格。下一次普通GET若断连，catch只检查该对象及deadline，便重新设置 `reconnecting=true` 并清除已知失败错误。用户看到恢复似乎仍在重试，实际终态失败已被确认。成功GET若返回不相关receipt，也可走同一中性分支。这违背“已知失败保持明确错误，不能再次隐藏为预期重连”的本轮合同。

独立复现：正常选择预览、输入RESTORE、confirm成功ACK、读到matching REJECTED并断言错误出现；随后仅让下一次GET断连并推进10秒。该probe **1 FAIL**：预期不存在中性重连文案，实际返回 `<p role="status">Reconnecting and validating the restored data…</p>`；confirm POST始终仅一次。没有真实恢复、模型或正式数据操作。

应保留已知终态失败并撤销该次中性重连资格，直到明确新操作；后续状态读取失败、无receipt或不相关receipt不能重新开启中性窗口。补齐REJECTED/ROLLED_BACK/未知状态的后续读取反控，仍保留匹配APPLIED、超时、普通GET/confirm失败及不重复确认规则。

隔离probe及原失败日志：`.var/r6-review/terminal-disconnect.test.tsx`、`terminal-disconnect-probe.log`。Probe SHA在 `scope-and-boundaries.json`，未放入正式测试路径或改写作者测试。

## 已独立通过的检查

使用root既有虚拟环境和既有frontend/node_modules符号链接，无下载或安装：

| 检查 | 结果 |
|---|---|
| compileall src及修改的backend测试 | PASS |
| Ruff `src tests scripts` | PASS |
| Strict mypy src | PASS，119 source files |
| TypeScript `tsc -b --pretty false` | PASS |
| 完整 `tests/integration/test_local_intelligence_settings.py` | **74 PASS / 91.36s** |
| `App.backup-feedback-context.test.tsx` + `TranscriptionSetup.test.tsx` | **57 PASS / 3.39s**（39+18） |
| 新独立终态失败后断连probe | **1 FAIL / 1.30s**，见上述P2 |
| `git diff --check` | PASS |

日志分别为 `.var/r6-review/backend-settings.log`、`frontend-focused.log`、`ruff.log`、`mypy.log`、`typecheck.log`。所有成功检查与新失败分别保留，不把它们合并成全绿。完整后端影响组（76文件）由作者在固定源码运行中；本review没有重复该长组，也没有以57项替代作者991项完整前端。完整组和root最终新源macOS GUI仍是接受条件。

## 其余增量结论与边界

Condition仅协调同一服务对象的passive检查与维护意图，等待在flock和SQLite之前，pending拒绝新poll插队/第二command，重入拒绝和异常finally通知均保留。真实HTTP反控、native/background SH及外部进程锁反控通过；原quiescence、数据库与DATA验证没有被移除。已知本进程维护忙碌用私有typed exception精确映射MAINTENANCE_ACTIVE，未知/外部/完整性失败继续failclosed。未发现该增量引入的安全放行或数据改写P0/P1。

语音保存文案中性、能力仍取真实状态；媒体时长独立key没有替换处理记录耗时。没有Schema/资格/profile/依赖/锁文件/凭据/正式配置变化。独立逐字核对原12个ASR绑定所在的8个完整文件与292相同，作者绑定hash均相等；migrations及模型资格profile不在差异中，见 `scope-and-boundaries.json`。这只证明可复用前提没有因本增量改变，不是新模型资格授予。

复用为DIRECT Python标准库Condition、既有OS锁/事务和React refs/effects，无新增框架或来源/许可证问题。未删除测试、减弱原断言、跳过失败、改正式数据、调用付费云端或进行模型加载/生成。reviewer只提交本报告；修复、新固定SHA及独立复核后由root决定接受，禁止据此合并或发布。
