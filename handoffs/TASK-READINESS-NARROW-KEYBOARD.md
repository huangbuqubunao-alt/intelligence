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

独立 Reviewer `/root/intel_bounded_review`：**APPROVE（限定代码审查），P0/P1 = 0**。实现 SHA `9bdcce33f316de1c6378087e73a2fbefeb84b09a`；基线 `142f16bd26747c8bc3584c4e681620c26d89f4d7`。作者 STOP，接手时工作树 clean。

- 完整三文件 diff 核对：业务只有既有 sidebar button 的六行 focus handler。父节点就是 sidebar-nav；仅横向内容超过可用宽度时请求 nearest 滚动，未修改 tab 顺序/键盘事件、preventDefault、激活、路由、状态、ARIA、CSS 或宽屏布局。保持鼠标 onClick；聚焦本身不调用 navigate 或提交请求。
- 独立 focused：`npm test --prefix frontend -- --cache=false src/workspace/SidebarKeyboard.test.tsx`，**3 PASS / 1.29 秒**。两种语言覆盖六个目的地正反 Tab、正确目标滚动且不激活、Enter 激活；宽屏不额外滚动且鼠标行为保留。测试替身没有布局能力，不能用它证明像素完整可见。
- 独立 `npm run typecheck --prefix frontend`、`npm run build --prefix frontend`、范围 diff check：PASS；50 modules，CSS `index-DmN6_wU_.css` / JS `index-nAg-FfKj.js`。实现者完整日志 389 / 24 PASS 已核对，按主控有界要求未重复全套。未运行 backend/Ruff/mypy：没有 Python 改动。
- 与 root `c90406e4f6d8e681afc0df3f9052ea0ce8963fc3` 的只读 merge-tree 无冲突，结果树 `b211dacfcc4a26f309e104ec137ff6221cc738fe`。未实际整合。一次读取实现者日志使用了 root 而非候选 cwd，返回 No such file；随后在候选正确目录读取原日志，没有修改或伪造证据。
- **真实 GUI 尚待主控验收**：320/768/1024/1440px、六个按钮正反 Tab、完整可见、document 无横向滚动与 Enter 激活都须真实重放。scrollIntoView 会按 nearest 对可滚动祖先请求可见性；本代码不构造 document 溢出，也未通过隐藏内容规避问题，但 jsdom 无法证明实际祖先滚动位置。
- Reviewer 只补交接。无业务修改、资格/模型调用、正式配置/数据、Schema 或 main 操作；本批准不代表模型资格或整体普通用户链路已通过。

## 主控验收与整合

待主控决定。
