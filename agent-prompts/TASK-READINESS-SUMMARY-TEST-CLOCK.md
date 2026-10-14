# Summary lease test-clock implementer package

Task TASK-READINESS-SUMMARY-TEST-CLOCK / Implementer caption_resume / Reviewer intel_bounded_review，仅作者STOP后。正式base/tree/branch须开工root记录，Backup返修先提交STOP，不能同agent并行两writer。
Allowed scope/Required checks/Reuse/Special approvals以root同task为准：只测试fixture计时稳定与真实过期负控，所有原断言/生产10min lease/拒绝保护不变；无Schema/安全prod权限/网络/模型/正式数据/依赖改动。独立tree，从含task最新root接受base；不带尚未接受Backup变更。限定commit+handoffSTOP，不合main或写公共status。
