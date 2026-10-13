# TASK-READINESS-CONTENT-STATUS-LOAD

2026-10-14 READY。Orchestrator root / Implementer caption_resume / Reviewer intel_bounded_review，作者完成提交STOP后审查。Base为本卡提交后的root最新已验收候选；独立tree readiness-content-status-load、branch codex/task-readiness-content-status-load。原Schema38作者tree必须STOP/不写，另一Reviewer正在Schema独立复审。两任务严格隔离，UI不改任何core/Schema/policy，准许本独立UI任务与Schema只读review并行；核心LOCAL_TEXT仍串行等待。

## 目标与真实红证据

CONTENT_CAPABILITY_LOADING_REPRODUCTION.json 和 screenshots/content-capability-loading-before.png：私有普通headful macOS Chrome真实已完成 Whisper视频，有4timed cues和Summary，GET transcription/deep-analysis仅2500ms有限延迟、无response替换。状态到达前显示错误“待转写”和“尚未运行”，后才真实转写完成/资格未通过。主动作未放行，但诊断null时也假显示缺模型/无runtime。必须在未知读取时保持明确中性加载，失败只显示真实错误与安全只读恢复；不能推断已执行/未执行/模型缺失/合格。原Content字幕/Summary/Evidence始终可读。

## 允许范围

仅 frontend/src/workspace/LocalTranscription.tsx 状态读取/呈现与readonly GET重试、App.tsx DeepAnalysisPanel读取/呈现分支（不得更改DeepAnalysis提交/consent/credential/publish处理器）、uiLanguage.tsx对应ZH/EN文案、LocalTranscription.test.tsx/新App.content-status-load.test.tsx或既有相关tests仅追加有意义案例、此task/handoff。复用useRemote与现GET/API/React本地state；先读DESIGN.md和workspace/DESIGN.md，不新依赖/改styles设计系统。

首次或ContentID切换且未收到对应read response，显示“正在读取转写状态…”/“正在读取深度分析状态…”。不显示fallback PENDING/NOT_REQUESTED或虚假diagnostics字段；状态未明/读取失败没有执行或配置命令可提交，不由此授资格。已知真实PENDING/NOT_REQUESTED则原行为保持。GET失败可明确手动重试原GET，不调用availability POST/模型PUT/转写POST或deep POST，不自动重放command。仅重新读取同Content，草稿/现可信文本不丢失。切换ID/卸载忽略旧响应、状态不串内容；刷新失败的旧状态不能冒充本次成功，可以清晰保留最后已知事实并显示失败，但运行需当前已知匹配。onCompleted/onStatus回调不由null/loading触发，不反复真实执行。精确实现选择由作者按现契约最小改动决定。

不改API/backend/state/migration/provider/授权预算/生产配置/凭据/资格/依赖/toolchain/Cloud/响应结构，不编辑原Schematree或研究freeze，不推理/下载/访问正式数据。常规用户链路UI整改已授权，若触及任何新增敏感边界先停报告。

## 外部验收

先TS与语法，再TDD：首次真实延迟READY、NOT_QUALIFIED等未到时无假PENDING/NOT_REQUESTED/缺模型；failed GET明确错误+手动原GET恢复/全部mutation0；ID切换与late旧response不能污染新Content；已知PENDING/RUNNING/READY/FAILED及真实NOT_REQUESTED/qualified/Cloud逐次授权既有行为不变。中英文、现文本可读、onCompleted仅真实READY/一次、按钮未知禁用、无自动POST/PUT和提交重放。全frontend/TS/build/diff，完整既有测试不删不弱化。提交精确SHA/handoff STOP后独立review，root真实上述延迟/失败/重试/切ID测并截图。无自审/采用/全链路完成声明。

Reuse decision DIRECT 既有React/useRemote/API client/本地read DTO、现组件测试，REFERENCE既有Source详情中性read状态实现；不用新的外部库。Parallel now Schema38独立review；waiting核心迁移接受/LOCAL_TEXT/模型资格/最终回归及另批正式采用。
