# TASK-READINESS-MODEL-STATE-COPY

2026-10-14 READY。Implementer /root/intel_bounded_review（独立新 UI 任务），Reviewer /root/caption_resume（migration safe stopped point 后）。Base 为本任务卡提交后的 root 最新已验收候选，独立 worktree readiness-model-state-copy / codex/task-readiness-model-state-copy。原 V2 research author tree STOP，不得修改其 freeze/input/code/结果。

目标/完成：真实 Settings 不能把 installed+digest matches READY 等同 Intelligence 合格；中文/英文如实显示安装身份、本地洞察资格、可选云端逐次授权，以及原 Content/Summary/Evidence 可读。独立 review、完整前端/TS/build、root 普通 GUI 通过后接受。任务不授模型资格或发布权。

只允许 frontend/src/workspace/App.tsx Settings 主面板的最小文案和既有 providers DTO 分支、uiLanguage.tsx 对应两语文案、App.test.tsx 仅追加有意义案例或新 App.model-readiness.test.tsx、此 task/handoff。不改 ModelSettings 凭据/授权 handler、API/backend/runtime/config/Schema/provider/依赖/toolchain/按钮行为，不创建新的 capability inference。不读取实际模型/credentials或调用任何推理。

DIRECT 现有 settings.runtime_local_model.status、providers Local / SCORING_SUMMARY_ONLY qualification_status 和 production_eligible read projection；现有 component test/语言 context。READY 的实际定义只是 API tags 精确 name/digest 匹配。安装提示改为 installed/identity verified，不写可使用/合格。仅 Local qualification_status=INTELLIGENCE_UNQUALIFIED 明确显示未通过洞察质量验收；字段缺失/未知不捏造合格或失败。保留原 readiness attention 以及现有 cloud eligible/credential blocked 分支，仅使 cloud 选择明确可选且逐次授权；内容整理仍不依赖 Cloud。不能把已装 9b research 权重显示成实际正式 runtime 模型。

关键检查：双语 READY+Local 未合格+Cloud blocked，不显示本地洞察可使用；Local 缺失/未知不授合格；云端 production eligible 仍需每次明确授权；未安装/digest mismatch attention；不新增 model/credential/provider请求、不变已有按钮/授权行为。先检查 actual DTO/代码/测试与 DESIGN.md，graph 优先；先语法/TS，再 focused、完整 frontend、TS/build、diff，不删旧断言。提交范围明确 SHA/handoff STOP 后独立审查；不自审。

本普通 truthful-copy 在用户已授权全用户链路整改内，不涉及新增敏感变更。Parallel now：caption Schema38 state/Backup 独立写；ROOT 独占已批准 V2 单模型验收。Waiting：migration review/integration、LOCAL_TEXT 串行、真实模型语义结果/独立 review，最终发行另批。任何超出此三前端业务文件/测试/说明边界先报告。
