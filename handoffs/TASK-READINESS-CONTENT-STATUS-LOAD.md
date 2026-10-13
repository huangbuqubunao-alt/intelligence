# TASK-READINESS-CONTENT-STATUS-LOAD 交接

2026-10-14。Implementer `/root/caption_resume`，独立 Reviewer `/root/intel_bounded_review`。
Base `2d167d8afa4d09b030fde4b3f1ea4f0c78721a7f`；tree
`/Users/hua/Documents/yia-worktrees/readiness-content-status-load`；branch
`codex/task-readiness-content-status-load`。本交接所属提交完成后 STOP，建议 IN_REVIEW。
原 Schema 工作树停止写入，未在此 UI 夹带其返修。

## 修改与复用

DIRECT 既有 React、useRemote、API GET、语言字典、Panel/ErrorState/原生按钮与状态
提示，参考两份 DESIGN.md；graph 定位已有 LocalTranscription/DeepAnalysisPanel，
随后按本树实际代码核对（索引的 useRemote 较旧）。没有新的库/样式/控件系统。

实际六文件：LocalTranscription.tsx、App.tsx、uiLanguage.tsx、原 LocalTranscription
test只追加案例/必要测试 import、新 App.content-status-load.test.tsx、本交接。

- Local 初读、对应 Content/revision 未到达时明确中性“正在读取转写状态…”，不回退
  为 PENDING、无 runtime、缺模型或未测试；尚无 capability时不捏造 diagnostics。
- 读取结果绑定 Content ID/revision，effect cleanup 忽略旧响应/旧 timer；ID切换立即
  隐藏其它 Content状态，真实 READY仅对应当前 Content通知完成一次。PENDING/RUNNING
  的原顺序轮询条件/两秒间隔保留，GET失败停止轮询并清晰反馈，不冒充旧状态成功。
- 读取失败的按钮仅增加 read revision重新原 GET，没有 availability POST、模型PUT、
  转写POST或自动命令重放。未知/读取失败时原配置及执行按钮禁用，modelPath草稿保留。
  原 action错误与读取错误分开，成功GET不会擦掉仍应可读的命令失败。
- Deep Analysis原 useRemote null明确中性读取；失败保留原本地化 ErrorState+手动
  原GET恢复，partial status不再当 NOT_REQUESTED。只有真正收到已知 availability才
  呈现其原状态/原因/路线，未知或错误不能运行/发布。当前 ContentDetail已有ID key与
  useRemote取消旧请求，实测组件契约覆盖切路由后 late旧资格响应不得放行新Content。
- Local start/refresh/model action及 Deep run/preflight/consent handler **原 bytes完整
  相同**，分别用 git show base与本树自动提取比较 PASS。没有修改 Deep发布处理器、
  云端逐次授权/费用参数/credentials API、执行参数、任何后端或模型资格。
- 新五项字典中英文对应；保留现有 aria-live/原生按钮、Panel、details与正文布局。
  Content原可信字幕、Summary/Evidence读取组件未改，不因小面板加载阻止读取正文。

## 检查

- baseline与新增测试后先 `npm run typecheck` PASS。
- TDD `/tmp/content-status-load-tdd-red-exact-copy.log`：**9 FAIL / 10 PASS**，主要缺
  中性读取/只读恢复以及错误地展示未运行状态。第一次新测试误写既有英文
  NOT_REQUESTED显示文字为“Not requested”、中文 qualification hint误写，核对现有
  字典后修正新测试预期，保留首 `/tmp/content-status-load-tdd-red.log`，没有改旧断言。
- 最终 `npm test -- src/workspace/LocalTranscription.test.tsx
  src/workspace/App.content-status-load.test.tsx`：**21 PASS / 454ms**，
  `/tmp/content-status-load-final-focused.log`。12新增案例涵盖双语延迟/GET失败恢复/
  diagnostics未知无命令、late ID response与READY逐Content一次、轮询失败不可用旧
  RUNNING且草稿保留、Deep late旧资格隔离、partial投影手动GET回真实NOT_REQUESTED。
- 完整 `npm test`：**430 PASS / 27 files / 11.42s**，
  `/tmp/content-status-load-full.log`，既有 React act warnings保留。旧141项 App等
  完整保留，云端同意/参数/不明执行阻塞、发布与路由旧用例仍通过，无 skip或删断言。
- 最终 TS PASS（`/tmp/content-status-load-final-ts.log`）；build PASS（50 modules /
  492ms），`/tmp/content-status-load-build.log`；assets `index-LXHjlWTz.js` /
  `index-DmN6_wU_.css`；diff check PASS。ignored dist未提交、不更新正式 build。
- 未运行后端/Ruff/mypy：只前端/测试/交接，无 Python变更。没有模型、Cloud、下载、
  credential、owner数据、配置/Schema/依赖/lockfile/toolchain或实际服务写操作。

## 证据限制与交接

没有将 controlled component测试当真实 macOS GUI。真实红证据见 root原
CONTENT_CAPABILITY_LOADING_REPRODUCTION.json / content-capability-loading-before.png，
保持不变；主控须独立 review后在真实已完成ASR Content作有限GET延迟/故障/重读/
切ID测试，并在320/768/1024/1440与键盘核验普通正文持续可读、无未知执行放行。

本切片不宣称整个用户链路、字幕归档迁移或模型资格通过。原 Schema REJECT与 V2
真实 FAIL均不改，最终接受整合后的完整后端及正式采用门禁仍需主控处理。
提交后 STOP，不自行审查或合并 main。

## Reviewer / 主控

待独立审查和主控真实 GUI；实现者不填写 APPROVE/ACCEPT。
