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

## 独立 Reviewer — REJECT（2026-10-14）

Reviewer `/root/intel_bounded_review`，固定 base
`2d167d8afa4d09b030fde4b3f1ea4f0c78721a7f` → candidate
`fff9bf0607b81794064f13d5827df624de3bc0a0`。作者 STOP/clean 后开始，额度中断后
核对同一 SHA 与原日志继续，没有重新申请批准或写业务。只有本交接追加。graph-first
定位组件/useRemote，再按实际候选核对较旧索引；两份 DESIGN、任务和完整六文件 diff
已读。未触 Schema树、研究freeze、服务配置、owner数据或任何 provider/model。

### 已验证的正确部分

Local读状态绑定 Content/revision，首次/重读中性文案，GET错误与action错误分开；
cleanup忽略旧响应/清 timer，READY按Content一次通知，草稿保持，顺序两秒轮询与
失败停轮询合理。真正PENDING/RUNNING/READY/FAILED与NOT_REQUESTED既有分支保留。
Deep null/缺availability与GET错误清楚显示加载或本地化仅GET恢复，原Content可信
字幕仍可读；ContentDetail key+useRemote alive隔离晚旧响应。失败数据不用于运行/
发布。新文案中英完整，没有样式/导航/请求结构/后端契约改动。

独立从 git show base 和候选提取比较：Local `const action = async` 的完整处理器、
Deep `async function run(authorized?: DeepAnalysisPreflight)` 的整个执行/preflight/
逐次同意/费用/未知dispatch逻辑、整个 `DeepAnalysisPublishAction` 函数均 byte-equal。
本次改动只收紧读取/呈现条件，没有重放命令或修改这些敏感处理器。

### P2-1：非空未知 availability 仍被当已知读取并启用运行

`App.tsx:2117–2119` 的 `statusRead` 仅检测 string/length，不检测既有明确状态集合。
独立真实组件负控返回正常JSON，但status为
`{ availability: "UNKNOWN_FUTURE", qualified: true, production_eligible: true, ... }`。
实际 Run Deep Analysis 按钮 enabled，而预期未知/不完整投影必须 READ_RESPONSE_INVALID/
仅GET恢复且不能执行；未知枚举还会作为原始状态标签显示。这遗漏了任务要求的
“未知或错误不能运行/发布”与partial read边界。不是仅missing availability的测试。

只在私有 `/private/tmp/content-status-review-9ugv490i/review.test.tsx` 加独立负控，
原新App测试六项照跑：**6 PASS /1 FAIL**，关键行
`expected false to be true`（button.disabled预期true实际false）。没有点击该按钮，
没有发模型/provider请求；没有证据表明后端授权可绕过或真实收费，故不夸大为P0/P1。
应在允许App读取分支使用既有明确availability集合验证，unknown/nonstring/blank/
partial均只提供read error+手动GET恢复，补对应负控并保持已知真实资格/Cloud同意/
NOT_REQUESTED原行为。处理器与后端无需修改，仍在原精确UI任务范围。

独立探针最早用 `/tmp`词法路径外部Vitest文件，Vite解析`/private/tmp`路径 collection
失败，未执行任何测试。保留 `/tmp/content-status-review-unknown.txt`；改为真实
canonical临时root/现node_modules链接后正常执行，最终有效输出
`/tmp/content-status-review-unknown-resolved.txt`。未安装依赖、改工具链/config仓库文件
或改候选tests。该独立Fail不能被完整430 PASS抵消。

### 独立检查与限制

| 检查 | 结果 |
|---|---|
| `npm run typecheck`，先类型再测试 | PASS；`/tmp/content-status-review-ts.txt` |
| `npm test -- src/workspace/LocalTranscription.test.tsx src/workspace/App.content-status-load.test.tsx` | **21 PASS /455ms**；`/tmp/content-status-review-focused.txt` |
| `npm test` | **430 PASS /27files /11.44s**；`/tmp/content-status-review-full.txt` |
| `npm run build` | PASS /486ms；`/tmp/content-status-review-build.txt`；assets与作者同hash |
| 独立未知availability负控 | **1 FAIL /6 PASS /217ms**；有效输出上述路径 |
| git diffcheck/六文件范围/原tests完整/处理器byte比较 | PASS；没有业务修复或新增skip/ignore |

前端完整既有act warnings保留。后端/Ruff/mypy未重复：本slice无Python改动。
核验root7b119f58包含该base，新增root工作未进入本固定候选；此次不整合。
没有进行真macOS GUI验收，controlled React/Vitest不得当真实普通用户实测；root真实
延迟/错误/重读/切ID与四宽键盘验收仍需独立接受后执行。Schema38 REJECT、本地模型
真实FAIL与资格门禁不变，不声明全用户链路通过。

**Verdict REJECT：P0=0、P1=0、P2=1。** 精确补足未知状态边界后由原作者提交返修再
独立审查；当前不整合。Reviewer审查交接提交后STOP，不改业务、不自领后续任务。
