# R7 独立增量复审：恢复终态失败反馈闭包

结论：**APPROVE**，仅指本任务候选工程范围。R6唯一P2已真实关闭；本次未发现新增P0/P1/P2。最终新界面普通macOS验收、root整合及整个Goal的真实洞察资格/正向链路仍须分别完成，不能据此发布或授模型资格。

- Reviewer：`/root/backup_reconnect_review`，延续发现R6问题的独立审查会话，无产品写入。
- Base：`b187e8223de16ab4472455796956ed8d4899364f`。
- Candidate：`acc0f989f3bb5b4c57f03e24e320705a6d9a52a7`。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-long-input-wait-review-r7`。
- 实际差异：仅 `frontend/src/workspace/App.tsx`、对应反馈测试及原任务handoff，共3文件。没有重新启动完整三方审核。

## 独立复核

确认尝试新增失败锁存：matching REJECTED/ROLLED_BACK/未知状态后，GET断连、无关历史receipt不再重新获得中性重连资格；明确失败与Retry保留。锁存不伪造最终状态：只有相同restore_id的真实APPLIED且restore_pending=false才解除失败并结束当前尝试。单纯APPLIED/pending=true仍保持关闭。确认期间保留inspected id，防止无关历史状态把稍后真正完成误标为“上一次恢复”。没有confirm重发、延长期限或放宽状态身份/乱序校验。

独立运行结果：

| 检查 | 结果 |
|---|---|
| TypeScript `tsc -b --pretty false` | PASS |
| 完整备份反馈文件 + 转写设置文件 | **64 PASS / 3.14s**，46+18，包含新增7例和全部原断言 |
| R6原1FAIL probe逐字复制，无修改 | **1 PASS / 1.36s** |
| 独立新增：3种失败→matching APPLIED但仍pending→清pending | **3 PASS / 1.12s**；pending时无成功/重连，结束时显示本次成功，confirm始终一次 |
| `git diff --check` | PASS |
| 候选与作者最终源码freeze | 全495 hash逐项相等 |
| 本次后端复用边界 | 全420 tracked `src/tests` 文件逐字等于b187，无后端/测试代码变化 |

本次日志与隔离probe在 `.var/r7-review/`：`typecheck.log`、`frontend-focused.log`、`original-r6-probe.log`、`terminal-applied-pending.log`。原R6 probe SHA256 `b26ae1db406f26862fffddaa4212b0bc5d1a0e300d399589445e688a5484fa83`，新组合probe SHA256 `44392de6cb05fad9a314a582b1c7622d665084dd0f43db635c4e1af370551463`。未把QA-only probe写入产品/正式测试目录。一次QA命令使用错误工作目录，尚未运行检查即路径失败；纠正自有QA目录后执行上述实际检查，没有修改配置或依赖。

## 累计证据及接受边界

已直接读取作者完整76文件组原日志及result：固定b187实际 **2188 PASS / 1既有重复ZIP反例warning / 1810.33s**，pytest_exit=0，495源码/前端/测试hash运行全程不变。result SHA256 `0bd7b62128ff21f06f05eb5272b344a6611fbf3e0f5fcd45303396b6707659c4`核对相等。本次420后端源码/测试逐字相等，因此复用该实际结果及R6独立74项backend/compile/Ruff/strict119，不重复35分钟大组，也不冒称该完整组在acc0f UI上重新执行。

另读取作者最终完整前端日志：**998 PASS / 38files / 23.85s**；TypeScript/build通过证据保留，独立本次64项和两组probe不替代该完整前端。此前R5/R6的安全审查、固定292与b187真实普通GUI证据各自保留，当前修改没有触及其后端实现。Schema001–041、模型profile/资格、ASR12绑定及含绑定的完整文件保持b187/292对应字节，未重签资格或新增调用。

DIRECT复用既有React refs/effects/API和测试框架，没有新依赖/许可证来源。未删除或弱化旧断言，没有正式数据/凭据/配置、模型加载/生成、付费云端、main或部署操作。工程累计检查及增量独立复审证据已足够支持root对本任务进行最终验收；仍须由root核实最终新UI真实恢复反馈/数据一致性并决定整合。完整Goal尚未完成，局部APPROVE不能代替洞察语义资格、正向保存/主题链路、最终全仓回归或正式采用条件。
