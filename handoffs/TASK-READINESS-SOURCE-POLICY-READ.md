# TASK-READINESS-SOURCE-POLICY-READ 交接报告

## 元数据、范围与复用

- Implementer: `/root/source_context`; 独立 Reviewer: `/root/intel_bounded_review`（待退休候选审查结束）。
- Base: `d903c609a90ac055b81a265890297f2b8f427e1b`。
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-source-policy-read`。
- Branch: `codex/task-readiness-source-policy-read`; 日期: 2026-10-13。
- 本报告与实现同一提交，提交后的完整 SHA 通过主控回传记录。

任务限定为既有来源配置表单的全局政策 GET 读取恢复；实际源码在 frontend/src/workspace/App.tsx/uiLanguage.tsx（已获主控确认并修正本地任务卡），专用测试与任务/交接文档。无后端、Schema、依赖、锁文件、凭据、配置、正式数据、模型资格或 main 修改。

DIRECT 复用现有 ApiClient、useRemote GET 读取生命周期及 reload、ErrorState、UiLanguageProvider、workspace DESIGN.md 的 Panel/field/button 样式。ADAPT 只为这一 loader 添加可选响应验证并展现读取状态；其它 loader 不传 validator，保留原行为。现有 React/Testing Library/Vitest 依赖的来源/许可证仍按既有 REUSE_REGISTER/NOTICE；无新依赖。

## 问题与实现

旧表单用 `globalPolicy.data?.policy?.focus_rules.join(...) || Not set` 渲染，读取加载中、失败、缺失响应都可能被称为未设置；畸形规则数组还会抛 TypeError 并让表单崩溃。

读取结果先验证真实政策的字段形状（字符串数组、非负整数初始历史、正整数每次限制、既有支持 style）；未通过按既有 READ_RESPONSE_INVALID 错误生命周期保留为失败，不允许未知值进入表单预览。成功且真实列表为空才显示 Not set。初次读取和重试显示可访问 loading；失败显示本地化说明、草稿保留说明与显式“重试加载全局兴趣”。重试按钮 type=button，只调用该 loader 的 GET，不提交或重放 command。

任何 focus/ignore/style 仍 INHERIT 时，真实政策读取成功前 Save disabled，submit handler 同样拒绝，因此程序化表单提交也不能绕过界面。全 OVERRIDE 设置不依赖未知全局内容，保持既有明确编辑及提交行为。所有草稿在表单本地状态中不随 GET 重试重建；卸载后的响应沿用既有 alive guard 不更新旧表单。

## 验收与检查

- TDD RED：专用 SourcePolicyRead.test.tsx 在改实现前 10 failed / 2 passed，另捕获原 `globalPolicy.data?.policy?.focus_rules.join is not a function`。失败定位于无 loading/error、失败读误显示空状态、继承操作未禁用与畸形响应崩溃。
- 初次正确路径执行前的 harness 命令用了重复 frontend/ 前缀，未写入文件也未跑测试；改为明确 repo cwd 与实际路径后执行。无依赖安装。
- 修复后初轮专用12与既有 AdvancedSourceForm2：14 passed；TypeScript PASS。
- `npm run typecheck`：PASS（最终20新测试和完整源码）。
- `npm test -- --reporter=dot`：**23 files / 379 tests passed**（11.17s，含20新测试）。完整套件中既有 App.test.tsx/ContentStatusLocalization 等文件输出 React act(...) 同步提示；本次专用文件没有该提示或 unhandled error，未更改测试脚本抑制它们。
- `npm run build`：PASS，50 modules；workspace bundle index-BxF978od.js，413.17kB / gzip132.33kB。
- `git diff --check`：PASS。
- 新专用最终20测试覆盖 loading、网络/503/不可解析/空对象/null/缺失政策/畸形数组/缺字段/未知 style、 repeated failure→successful GET、零 mutation、保留 URL/focus/history/time 草稿、真实空列表、zh-CN/en、卸载与重新打开、逐项继承限制及全 OVERRIDE 负控。

## Diff 复核、风险和跳过

只修改准许的实际路径，未修改/削弱已有测试。无重设计、无配置或权限更改。既有授权、预算与 Cloud 执行行为未触及。

该可选 validator 与稳定 useRemote lifecycle 组合，未来全局政策 API 正式新增 style 值时需同步 UI 支持；不把未知 style 假装成现有默认值。本 scoped 前端任务不跑后端；真实 headful GUI 与整合全产品验收由主控按任务卡完成，此交接不宣称已通过它们。

建议 `IN_REVIEW`；`DECISION NEEDED`: None。提交后停止写入，独立 Reviewer 和主控分别填写审查、整合与真实 GUI 验收结论；不自填 APPROVE/ACCEPT/DONE。

## 独立 Reviewer（2026-10-13）

- `/root/intel_bounded_review` 只读业务代码，审查 `d903c609a90ac055b81a265890297f2b8f427e1b...8e4b2d418617767887e3f7bfb29ac3bd2350fc5e`。**APPROVE，P0=0 / P1=0**，仅此 scoped 前端实现；不表示整体验收、正式采用或模型资格。
- `validGlobalPolicy` 是稳定的模块级函数，不产生 render/effect 请求循环；只验证这一个 loader，五个原 SourcePolicy 字段的类型/整数边界/既有 style 均校验。失败、null、缺失与加载中不再显示 Not set；成功且真实空数组仍显示正确空状态。JSON 错误沿用 ApiClient；没有改写其它页面读取或 backend 权威。
- 重试按钮 `type=button`，只增本 loader readRevision，普通 GET 与 alive guard 保留。URL/focus/history/time 等草稿不重置；INHERIT 依赖未知读取时 disabled 与 submit guard 两层拒绝；全 OVERRIDE 沿用本地明确值。既有 AdvancedSourceForm.test.tsx 的全 OVERRIDE POST/PATCH/PUT/automation 提交断言仍通过，未弱化测试。
- 独立 `npm test` **23 files /379 tests passed，无跳过，12.05s**，日志 `/tmp/readiness-source-policy-read-review-tests.log`；`npm run typecheck`、`npm run build` PASS（50 modules，index-BxF978od.js），`git diff --check` PASS。既有 React act warning 保留，没有隐藏失败或修改 test scripts。
- Diff 仅准许的3个前端源码/新增测试文件及 task/handoff；无 backend、Schema、依赖、锁文件、配置、凭据、Cloud 或正式数据变更。当前 root branch 与候选只读 merge-tree 无冲突，结果树 `13f123cc7eb4e8f8ce0c6c0c6fcddb82e5bc3ae4`，未实际合并。真实服务失败/恢复的 macOS GUI 验收仍由主控继续，不将 fixture 测试冒充实测。
