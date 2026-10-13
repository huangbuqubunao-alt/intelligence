# TASK-READINESS-NARROW-KEYBOARD 交接报告

## 元数据

- Task: `TASK-READINESS-NARROW-KEYBOARD`
- Role: Implementer; Agent/session: `/root/caption_resume`
- Base: `142f16bd26747c8bc3584c4e681620c26d89f4d7`
- Branch: `codex/task-readiness-narrow-keyboard`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-narrow-keyboard`
- Reported: 2026-10-13
- Head: 此交接所属提交，提交后回传精确 SHA。

## 目标、复现和范围

主控真实 5908/macOS Chrome 320px 窗口，body 宽度修复之后 document client/scroll 都为 305，仍发现 Tab 聚焦 Intelligence 的 right=335.672 超出 document，nav client277/scroll467/scrollLeft0，等待 2 秒未完整显示。此前 body CSS 修复不算本键盘边界通过。

原 FAIL 图片保持在 root 的 `.var/end-to-end-user-readiness/narrow-keyboard-navigation-failure.png`，本 worker 未改。

实际 product 仅 App.tsx 的 sidebar 既有按钮增加六行 onFocus：当 parent nav 的 scrollWidth 大于 clientWidth 时，以浏览器标准 `scrollIntoView({block:"nearest",inline:"nearest"})` 显示聚焦项。非溢出宽屏不干预滚动；不处理键盘事件、不 preventDefault，也不执行 navigate。原 onClick、route、状态与焦点顺序完整保留。未改 CSS、body 宽度、overflow、导航文案或拆分 App。

DIRECT 复用现有 nav/button、浏览器标准滚动 API、既有 Testing Library/user-event/Vitest；REFERENCE DESIGN.md。无新外部组件、依赖、许可证义务、权限、模型、后端、Schema、配置、正式数据或调度变更。

## 行为测试

新增 `frontend/src/workspace/SidebarKeyboard.test.tsx` 三例：

- 中英文各一例：真实用户 Tab/Shift+Tab traverses 六个目的地（以根复现的 nav277/467 几何条件提供浏览器 API 合同），每次滚动请求属于正确聚焦按钮；键盘聚焦保留原 Content route，没有提交请求；Enter 之后才正常进入 Following。
- 非溢出 nav：聚焦不请求额外滚动，鼠标仍正常激活 Following。

没有建立复述 CSS 常量的测试，也不把 jsdom（无真实布局）当作浏览器几何证明。scrollIntoView 的测试替身只记录标准 API 调用与目标；主控仍需真实 320/768/1024/1440 Tab/Shift+Tab、按钮完整显示、doc 无溢出与正常激活验收。

## 检查结果

独立忽略日志 `.var/readiness-narrow-keyboard/`，全部 Vitest 命令使用 `--cache=false`。

| 检查 | 结果 | 证据 |
|---|---|---|
| 改 product 前 `npm run typecheck --prefix frontend` | PASS | `typecheck-red.txt` |
| 改 product 前 `npm test --prefix frontend -- --run --cache=false src/workspace/SidebarKeyboard.test.tsx` | RED：2 fail / 1 pass | `red.txt`；英文确认缺少聚焦项滚动请求，中文夹具查询用了旧空文案，按现有词典更正后保留同等查询断言 |
| 同一 focused 命令（修复后） | PASS：3 / 3 | `focused.txt` |
| `npm run typecheck --prefix frontend` | PASS | `typecheck.txt` |
| `npm test --prefix frontend -- --cache=false` | PASS：389 tests / 24 files | `frontend-full.txt`，原 App/ContentStatusLocalization act 警告未隐藏 |
| `npm run build --prefix frontend` | PASS | `build.txt` |
| `git diff --check` | PASS | scoped diff |
| 真实 macOS GUI | 待主控验收 | worker 未触发模型/ASR/Cloud/正式服务，也未假称 mock 证明像素布局 |

## Diff、限制和交接

Product 仅 App.tsx 六行；新增 focused 行为 tests 和本交接。原 task 卡与其范围保留。无重构、无 generated 文件、无测试删除/skip/断言弱化、无生产依赖安装。忽略 node_modules 符号链接复用原工具；不改共享配置。

Backend/Ruff/mypy 未跑：没有 Python/backend 变化。原 9B 真实 FAIL 未重做或改结论，0 模型调用。本切片未解决或声称完成整体 LOCAL 链路/模型资格。

提交后停写，建议 `IN_REVIEW`，Reviewer `/root/intel_bounded_review`；独立审查后 root 真实 GUI 复核。Worker 不设 DONE，不合并 main，不进行正式产品发布。

## Reviewer 结论

待独立审查。

## 主控验收与整合

待主控决定。
