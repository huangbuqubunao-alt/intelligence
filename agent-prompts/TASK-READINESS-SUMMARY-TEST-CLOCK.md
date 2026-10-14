# Summary lease test-clock implementer package

Task TASK-READINESS-SUMMARY-TEST-CLOCK / Implementer caption_resume / Reviewer intel_bounded_review，仅作者STOP后。正式base/tree/branch须开工root记录，Backup返修先提交STOP，不能同agent并行两writer。
Allowed scope/Required checks/Reuse/Special approvals以root同task为准：只测试fixture计时稳定与真实过期负控，所有原断言/生产10min lease/拒绝保护不变；无Schema/安全prod权限/网络/模型/正式数据/依赖改动。独立tree，从含task最新root接受base；不带尚未接受Backup变更。限定commit+handoffSTOP，不合main或写公共status。

2026-10-15 开工定位：Base=5cfbad1（root所有已接受产品代码+本卡）；worktree=/Users/hua/Documents/yia-worktrees/readiness-summary-test-clock；branch=codex/task-readiness-summary-test-clock。caption作者只有Backup提交STOP后才领取，intel reviewer先完成Backup复审再独立审此任务；禁止并行改同tree。依赖runtime/node现路径可symlink复用，不安装/改工具链。
