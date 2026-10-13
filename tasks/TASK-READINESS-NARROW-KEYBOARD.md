# TASK-READINESS-NARROW-KEYBOARD

2026-10-13，READY。主控 /root；实现者 /root/caption_resume；Reviewer /root/intel_bounded_review。依赖已审查的窄窗 CSS 530528b / 727b5fe，已整合 d367bea / 59ab68b。

目标：真实 macOS Chrome 320px 窗口 Tab/Shift+Tab 到侧栏六个目的地时，聚焦按钮必须完整可见并可激活，只有 nav 自身横滚，document 不横向溢出；宽屏、鼠标导航和页面状态保持。

复现：5908 隔离负例 Content detail，innerWidth320/client305/scroll305。Home→Tab Following→Content→Intelligence，Intelligence rect x238.976/right335.672，nav client277/scroll467/scrollLeft0；2秒等待仍不完整。失败截图 `.var/end-to-end-user-readiness/narrow-keyboard-navigation-failure.png`，旧宽度修复没有声称此键盘边界已解决。

允许：frontend/src/workspace/App.tsx 或现有 sidebar 组件仅焦点可见边界；styles.css 仅必要导航滚动样式；相关 frontend tests、此 task/handoff。不要重构 App、改路由/文案/模型/权限/持久化/状态/依赖。如需要别的 product file 先报告。

Reuse decision：DIRECT 现有 nav/button/CSS 和浏览器标准滚动 API；REFERENCE DESIGN.md、frontend-ui-engineering；不新增依赖/外部组件。不得全局 overflow 隐藏、裁剪导航或正文。

验收：针对焦点滚动的有意义行为测试（不要复述样式常量）；完整前端 386+ 回归、TS、production build、diff；主控真实 320/768/1024/1440 GUI 与六目的地 Tab/Shift+Tab、激活已有页面（不得触发模型/云调用）。明确提交 SHA 并停写，独立审查后整合。不改正式数据或 config；无需新的敏感批准。

立即启动本任务。LOCAL_TIMED 仅后端独立树可继续；migration 等具体批准与 LOCAL state 串行整合；真实 LOCAL qualification 因 9b 原资格 FAIL 保持 BLOCKED。
