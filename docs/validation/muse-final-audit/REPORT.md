# Intelligence 三方统一审核与 macOS 验收报告

最终状态：**CODEX_MUSE_AUDIT_BLOCKED**。

独立审核、局部整改、macOS 回归和交付已完成；不建议现在整体合入 main。候选没有新增归因 P0/P1 或测试失败，但正式基线仍有可重现的 P1：未调用模型的 WAITING_MODEL 任务没有完整、安全的取消/终止生命周期，会持续阻止备份。qwen3:8b 的本地 Intelligence 资格结论为 **NOT_YET_QUALIFIED**；两实验分支的直接生产放行被拒绝，候选保持原有门禁。没有合并 main、没有 push main、没有调用付费云模型。

## 1. 固定版本与审核环境

| 对象 | 独立核验的版本 |
|---|---|
| A：正式 main 起始 HEAD | `fad25e6109d02650b25ae777f2f7557dd478309d` |
| origin/main 与远端 main | 同上；不是按报告假设 |
| B：OpenCode / 豆包 opencode/user-pilot | `8d63bbfeb5a764a0dc2cee8aa540e102a22ed6f4` |
| C：Muse muse/user-pilot-consolidation | `1cc146b17760be4de0c8613cb03787d75dbf5fa9`；远端验证后仅 fetch 远端跟踪引用 |
| 审核代码及测试最终提交 HEAD | `fad9eaead4036eb39013a5d5fba3e53f14ecbd43` |
| 包含本报告与原始证据的最终交付 HEAD | `refs/heads/codex/muse-final-audit` 的最终提交；其完整 SHA 在交付消息及本地 `.var/muse-final-audit/final-head.json` 回执中记录 |

报告属于最终提交本身，不能在其内容中嵌入自身提交的哈希；因此明确区分已固定的代码 HEAD 与提交后生成的完整交付 HEAD 回执。最终文档提交不会改变产品代码。

权威工作树 `/Users/developer/Documents/yia-worktrees/v1x-local-main`；独立工作树 `/Users/developer/Documents/yia-worktrees/muse-final-audit`，分支 `codex/muse-final-audit`，从核验后的 main 创建。没有在 A/B/C 工作树改代码，没有覆盖任何历史工作树，也没有清理既有 worktree topology。证据：[Git 核验记录](git-evidence.json)。最终再次核验保护分支及工作树状态。

macOS 26.3.1，Python 3.12.11，pytest 9.1.1，pydantic 2.13.4；真实 Google Chrome + Playwright，真实 AppKit picker + System Events。沿用已安装的 main venv / frontend node_modules，不安装或升级依赖，不改锁文件或工具链。A 的测试在 audit 内的 byte-identical Git archive 源快照执行，避免写正式工作树。B/C 也使用各自固定 SHA 的隔离源快照。

UI 5688 / API 5689，项目根 `.var/muse-final-audit/gui`，数据库、DATA、配置和每个浏览器 Profile 均在此审核工作树；未读取、连接或恢复正式 owner 数据库。配置来自公开 example，仅调整隔离路径；没有凭据、云授权或生产配置修改。

## 2. 三方采用矩阵与完整审查范围

详细逐项裁决见 [ADOPTION_MATRIX.md](ADOPTION_MATRIX.md)。该矩阵覆盖代码、全部新增测试、报告、手册、harness、截图及未解决问题，明确 ACCEPT / MODIFY / REIMPLEMENT / REJECT 与证据不足的边界。没有整体 merge 或 cherry-pick 实验分支。

A 先建立可信基线：当前规范、资格契约、生产门禁、备份生命周期、main 全量测试和原 D2 验收。B 独立审核 3 个生产代码文件、3 个测试文件和 81 个交付文件，再评 C 的相同代码及 9 个文档；没有先接受 C 对 B 的结论。

最终采用：

- 豆包普通 hash 导航方向，经 Muse `#` marker 修正及 Codex queued-event/no-op 修正；原有 D2-01 断言保持。
- Codex 用现有 Content/id 解析器补 openContent/openDelta 的内容深链接；局部修 Research 返回列表，并保护 New Research 表单。
- 豆包/Muse 对 no-new source-run SQL 的修复方向，经 Codex 限缩到 PENDING + invocation_count=1 + durable result，继续使用原 repository 的完整绑定验证。
- main 的模型生产资格、安全、语言、Evidence、预算、隐私、授权及 WAITING_MODEL 备份阻挡规则。
- 豆包 17 章手册结构与兼容原图，Codex 校正资格及备份步骤、替换错图和变化页面。

拒绝：两方 `production_qualified=True`；豆包 WAITING_MODEL inv=0 自动备份豁免及相应实验新增放行测试；两方冗余 no-new 主循环 helper；没有足够能力证据的本地 Intelligence 可用承诺。Muse M-5 回退方向采用，但不把其 40 个定向测试当成最终全量和 GUI 验收。

## 3. 路由修复与状态验证

真实缺陷：B 的 marker 保存裸 `Content`，listener 比较 `#Content`，程序导航被误判为用户导航，导入提示被清除。C 的 `#` 修正有效，但单 marker 仍会在连续 hash assignments 排队时被旧事件消费，丢失导入详情。

独立反证：

- A 固定源运行 B 的新增普通导航测试：无法找到 Settings 标题，复现普通 hash/Back 不恢复。[日志](checks/main-route-reproduction.txt)
- B 固定源运行 C 原始导入提示测试：`File imported. Its processing status appears below.` 消失。[日志](checks/opencode-notice-reproduction.txt)
- B/C frontend 全量都在既有 `LocalImportFlow.test.tsx` in-flight view-switch 测试失败：丢失保存详情中的 `Local model is missing.`。C 单独重跑也失败，排除仅为 full-suite 互扰。[B](checks/opencode-frontend.txt)、[C](checks/muse-frontend.txt)、[C 单独复测](checks/muse-import-focused.txt)

候选只让当前 URL 对应事件消费 marker；no-op 不创建新 marker；普通用户导航清理上一页临时状态。openContent/openDelta 内容目标写入编码 ID；现有 parser 恢复刷新和深链。Research `#Research` 恢复列表；新建用已有 History API 保留表单状态。没有加入第三方路由库或重构其他对象路由。

候选 frontend 288 个测试通过，新增测试覆盖 stale queued event、导入提示、普通 hash、深链与 Research 状态。实际 Chrome 本地文本导入后提示仍在；URL 为 `#Content/local-…`，刷新、Settings→Back→Forward 均通过，详情保留。[真实操作记录](gui-native.json)

D2 历史 native/HTTP browser runner 的成功 URL 断言更新为含 ID 的新契约，并新增与持久化 video_id 完全一致的断言，没有删断言或扩大允许结果；本轮未重复执行历史 2 GiB runner。

## 4. 本地模型资格：NOT_YET_QUALIFIED

裁决依次依据产品权威规范、原始历史证据、真实代码和独立测试：

1. [PRODUCT_CONSTITUTION](../../PRODUCT_CONSTITUTION.md) 约第 123 行：配置、安装模型不自动赋予生产权力。
2. [V1_PRODUCT_SPEC](../../V1_PRODUCT_SPEC.md) 约第 213 行：qwen3:8b 仅 Scoring/Summary 资格，V1 本地 Intelligence 尚未合格。
3. [M12_GOLDEN_UI_ACCEPTANCE](../../M12_GOLDEN_UI_ACCEPTANCE.md) 104–105 行：3Blue/GPT-4 的真实正向零结果；CNN 三次 Evidence binding 失败；没有经语义审核、可接受的本地 Intelligence 产物。
4. [Day1 真实验证](../dogfood-day1/live-validation.json)：`INTELLIGENCE_UNQUALIFIED`、production false、`SCORING_SUMMARY_ONLY`。
5. Git 历史 M5 `355f22d` / merge `6ed0f11` 曾开放早期本地路由；M12 `bfda6c5` 随后明确引入独立资格 seam 并设置 false。这不是忘记开启的布尔值，也不能用早期/M5 范围替代当前能力契约。

六个层次分别核验：已安装（本机 READY）、可连接（实际设置响应）、digest 匹配（现有 identity guard）、Schema/封闭输出契约（既有测试）、Intelligence 能力资格（缺足够正向产物及资格证据）、生产执行门禁（必须 false）。身份匹配不等于能力资格。

B/C 新增 composition 测试只用合成 VerifiedDistillationInput 断言 True；没有真实模型能力验证。候选改为“Summary identity valid 不授予 Intelligence production”的独立边界测试，既有 unqualified pause/no-generation、语言封闭、错误模型、授权与预算测试全部保留。

候选 runtime_composition 与 main 字节一致。实际 UI 点击提炼后是 WAITING_MODEL，invocation_count=0、actual_provider/model=null、`MODEL_UNAVAILABLE_BEFORE_TRANSPORT`；三类 cloud authorization 行数均为 0。resource_usage 有一条等待元数据，不是生成请求或收费记录。[实际 ledger](gui-waiting-ledger.json)、[实际等待截图](screenshots/23-waiting-model.png)

**结论：NOT_YET_QUALIFIED。** 没有伪造资格记录，没有以 digest、Schema 或可达性替代 Intelligence 能力审核，没有调用付费云补证，也没有将历史未合格提炼截图当作可用性证明。

## 5. Backup/Restore 安全结论

**候选的局部 no-new 修复符合现有安全边界；WAITING_MODEL 生命周期 P1 未解决。**

main 的 repository 已验证 no-new result 的执行身份、Evidence 集合与哈希，并投影 `SUCCEEDED_NO_NEW_INTELLIGENCE`；不可变 raw checkpoint 仍 PENDING。B/C 裸 checkpoint 新测试在 main 本已通过，所以不能证明主循环修复需要 helper。

独立定位到真正遗漏：settled NEEDS_ATTENTION parent 的 quiescence SQL 仍把 raw PENDING child 看作活跃任务。[冻结 main 复现](main-no-new-reproduction.json) 返回 `SOURCE_RUN_ACTIVE`。候选仅修改此查询，要求 invocation_count=1 且有结果；主循环继续让 repository 验证完整绑定。没有扩大等待豁免。

新增测试创建真实 Evidence、执行预约及 durable no-new row，child COMPLETED / parent NEEDS_ATTENTION，执行 create→download→stage→confirm→recover；恢复后 checkpoint、Evidence、resource_usage 与备份前快照一致，不能再次 claim，防重复执行/付费。另一参数只在隔离 fixture 中移除 immutable-update trigger 并损坏 evidence_set_hash，备份必须 fail closed；未修改生产 migration、trigger 或数据库。

B 的 WAITING_MODEL inv=0 豁免在同一 macOS 环境触发 task022 三个安全断言失败；C 固定最终 SHA 的三例通过。[B XML](checks/opencode-critical.xml)、[C XML](checks/muse-critical.xml)。候选现有 PENDING/RUNNING/WAITING_MODEL/WAITING_BUDGET、中断/不明执行及用户授权云完成的精确规则保留；定向 179 全过。

实际备份 ZIP 创建、下载、选择、预检、RESTORE 确认均从真实 UI 操作。serve-api 调试入口不自行重新启动进程，审核 harness 只重启自己已核验的 API PID以应用恢复；没有碰 owner。之后 last_restore=APPLIED、integrity_check=ok，Content/Evidence/source 数量、artifact 与全部 DATA hash 与恢复前完全相同。[前](gui-restore-before.json)、[后](gui-restore-after.json)、[操作](gui-settings.json)

之后实际手动提炼产生 WAITING_MODEL，UI 创建备份 disabled，API readiness=false/DISTILLATION_ACTIVE。[截图](screenshots/24-backup-blocked.png)。没有删除或篡改任务以清空阻挡。

未解决原因：现有不可变 checkpoint trigger 使 WAITING_MODEL 终态不能直接改；`_continue_reserved_distillation` 只继续 PENDING，source-run 取消也不终结 checkpoint。当前没有完整安全取消/放弃接口。既有唯一精确豁免需要同一执行上合格且用户授权的成功云结果，本轮没有凭据或调用授权。扩大豁免会把未完成伪装成完成；改变生命周期需要先明确规范、持久化终止记录与恢复/重试契约，不能在一次审核中绕过或伪造。

## 6. macOS 测试对比与失败归因

完整原始 pytest JUnit、日志与差集见 [checks](checks/)、[test-comparison.json](test-comparison.json)。A 与候选使用同一已安装 venv 和 macOS；两个 basetemp 隔离；不使用正式 DB。

| 检查 | A：main | 最终候选 |
|---|---:|---:|
| Backend full `PYTHONPATH=src:. .venv/bin/python -m pytest tests -p no:cacheprovider --basetemp=<isolated> --junitxml=<evidence>` | 3978 passed / 1 skipped，926.73s | 3981 passed / 1 skipped，892.39s |
| Frontend full `npm test -- --run` | 282 passed / 19 files | 288 passed / 19 files |
| 相关 Backup/Composition/task022/Ollama focused | 基线已包含在 full | 最终 179 passed，83.56s |
| TypeScript `npx tsc --noEmit` | baseline build 既有证据 | pass |
| Production `npm run build`（含 tsc -b） | baseline 既有证据 | pass，49 modules |
| Ruff `ruff check src tests` + 新手册 renderer | — | pass |
| Strict mypy `mypy --strict src/youtube_intel` | — | pass，100 source files |
| node syntax：两 D2 browser runners | — | pass |
| `git diff --check` / staged check | — | pass |

main 3979 collected，候选 3982；增加一个能力边界 composition 测试和两个 no-new 参数案例。Frontend 增加 6 例：B 2 + C 1 + Codex App 1 / Research 2。没有减少基线测试。唯一两侧相同 skip 是既有 canonical-o200k 外部资产未 provision 的测试，未新增 skip；两个相同 pydantic warning 是既有故意破坏 enum 的 fixture。损坏 ZIP focused 有既有 duplicate-member warning。

候选 full 的实现与最终代码提交一致；full 结束后仅强化新增测试的备份前后快照/禁止重 claim 断言、调整测试 act 包装及 docstring；强化版 179 focused 和最终 frontend full 均重跑通过，没有用修改测试期待来掩盖失败。

B/C frontend 完整独立复跑分别 283 passed/1 failed 与 284 passed/1 failed，都是原有 D2-01 in-flight 状态损失；C 独立 focused 3 passed/1 failed。B/C 后端本轮只定向复核争议安全断言，没有声称跑过其全部 backend。所有候选相关主题、Following、Content、导入、Intelligence、语言、资格、Day1、D2-01/02、离线、进程环境敏感测试均在完整 `tests` 收集中，无遗漏候选模块。

Muse Linux 报告 main 3264/702/1 与临时 Muse 3265/704/1，分别合计 3967/3970；那是不同平台/收集状态与回退前版本。M-5 回退后只有 40 个 targeted，不足以声称最终 full 失败集合已一致。报告的约 701 个环境失败没有原始日志/每例独立复测证据可供本轮追溯，不能统称“全部无关”。本次实际 macOS A/候选失败集合均为空，明确消除了候选归因问题；包括此前提到的进程时序测试和原生组件测试。没有降低任何生产契约。

开发/driver 失败如实保留：初始 no-new fixture 把 child 放在不明状态，修为正规已完成 child；一个补跑命令写错不存在的 task022 文件，0 collected/exit4，纠正真实文件后179通过；新增 renderer 的 import-order lint 修复后通过。GUI 首个 driver 错把成功对话框“完成”当自动关闭、等待文案选错，纠正 selector 后成功，并保留旧日志；不将其冒认为产品失败。媒体 picker 两次自动选择未完成，停止重复，不宣称 APFS 新验收。

## 7. 真实 GUI 与 D2-01 / D2-02 范围

| 操作 | 实际结果与范围 |
|---|---|
| 首次进入 / 三步引导 | 新独立 Profile，真实界面；01–03 |
| YouTube 单视频 | 实际 3Blue1Brown aircAruvnKk 导入 202；Content ORGANIZED，字幕、原文摘录与 Evidence 可读 |
| YouTube 频道 | @Veritasium 实际解析为 channel ID；200，HEALTHY / COMPLETE baseline，没有导入旧视频 |
| Following 暂停/恢复 | 真实 UI 成功；18/19；见 gui-completion.json |
| 本地 TXT | 真正 AppKit picker 选明确文件，native control `{}`，无需 HTTP 文件体；保存 READY，提示/详情/刷新通过 |
| Content 与浏览器前进后退 | 真实已保存 local id 深链、刷新、Back/Forward 通过；不是 mocked browser API |
| 模型就绪/等待 | 设置实际 READY 不授予 Intelligence；手动真实提炼进入等待，零 invocation；23 |
| no-new Intelligence | 合法终结及恢复由真实 repository 测试验证；未运行合格模型的真实 no-new UI，不能冒认生产验收 |
| Backup/Restore | UI create/download/stage/confirm 与 owned API restart 后恢复通过；12–14；真实等待任务随后阻挡备份 |
| 中英文 | 设置保存切换及实际画面通过；10/11；原内容保持原文，未跑云翻译 |
| Topic | 实际空状态25；无已合格洞察，因此非空详情 NOT TESTED |
| 本地媒体/ASR | 小 MP4 native 自动选择两次未完成，保留日志；完整 ASR NOT TESTED，模型未 provision |

[gui-native.json](gui-native.json)、[gui-youtube.json](gui-youtube.json)、[gui-completion.json](gui-completion.json) 与 [screenshot-manifest.json](screenshot-manifest.json) 是本次证据。浏览器 pageerror 为空。原生 panel 截图07来自真实 macOS screencapture，但截取时仍加载中；以04已选TXT和05成功保存配合证明，不冒充媒体选择成功。

D2-01：B/C 的路由改动确实引入现有回归，本候选在保持 chooser/focus/in-flight 原断言下通过，并补真实 TXT 操作。D2-02：native_import、local_content、native_picker.m、native_picker_build、LocalImport/NativeLocalImport 的 SHA256 在 A/B/C 与候选完全一致，[兼容性逐文件 pins](d2-native-compatibility.json)。本轮变化只在路由壳、source-run quiescence，历史 2 GiB native / APFS 原证据逐字节相同。

因此按用户授权复用 [正式 main D2-02 原验收](../dogfood-day2-d2-02/README.md)：真实 2,147,483,648 bytes AppKit→APFS clone→校验→普通 Content，零 HTTP 文件字节；原始修改/移动/删除仍独立，ZIP64 restore/hash一致。未无意义重复生成 2 GiB；没有用 Linux mock 冒充本轮 macOS。当前 fresh APFS/2GiB/完整 ASR 非新增验收，范围界线清楚。

## 8. 用户手册与截图真实性

统一中文图文手册：[USER_MANUAL.md](USER_MANUAL.md)、[浏览器 HTML](USER_MANUAL.html)。17章、35处配图；全部图片存在且浏览器 naturalWidth>0，17个目录锚点有效：[manual-validation.json](manual-validation.json)。[manual-preview.png](manual-preview.png) 是手册渲染预览，明确不是产品截图。

B 原始 81 个文件、49 个 PNG（其中1个手册预览，48个产品/诊断画面）、31处原手册配图引用完整原字节保存于 `docs/dogfood/opencode-user-pilot/`；C 原始9个文档同样保存于 `docs/dogfood/muse-consolidation/`。原始 Git blob与SHA256清单：[original-evidence-manifest.json](original-evidence-manifest.json)。没有覆写原报告来“修正历史”。

对49张原图用联系表及具体画面独立审阅，路径0缺失，但不接受“49张就是49个独立路径验收”：多组完全重复串页；09是添加错误而非频道成功；12显示浏览器导入页而非真正 OS picker；21空主题实际同20洞察页；23主题同24设置；25四个窄屏同设置；后端故障四图同Following；47命名summary其实是字幕位置；34未合格生产flag下提炼不能证明资格。重复组已用 hash列出，原图保留，最终错误步骤换成对应真实新图。

未变化的 onboarding后空状态、字幕、Evidence、媒体不可用/语言对话框可兼容复用；有变化的 YouTube识别成功、Following、内容、模型等待、备份恢复、模型设置等重截图。当前30张新PNG包含失败driver诊断画面，所有均为真实截图，未生成或修补产品图。原图源码/harness与Git只证明来源和完整性，不能单凭hash证明当时每一步成功，所以相应成功以本轮API/UI复测裁决。

手册正文只讲操作与实际限制，不包含三方技术审查。没有把未资格本地 Intelligence写成可用；no-new仅解释有合格模型时的合法结果；等待模型可能长期阻挡备份明确披露。云提炼、完整ASR、真实非空Topic未验证，不写成已验收。

## 9. 自审与剩余风险

按照 code-review skill 的两个独立只读轴复核：spec_review 以权威能力边界裁决拒绝生产True，standards_review 复核最终实现并独立运行 no-new损坏/恢复、等待阻挡、Research Back/New、资格零生成等测试。先前快照自比较弱点已强化；新建表单回归已修复；act包装已修正。最终没有发现新增候选归因 P0/P1；根 agent最后复核实际diff与完整checks。

| 等级 | 剩余问题 | 归属与处理 |
|---|---|---|
| P0 | 没有已确认项 | 两实验的未资格生产放行已拒绝，不在候选 |
| **P1** | **WAITING_MODEL 没有完整安全终止，持续阻止备份** | main继承；真实UI/API/ledger复现；本轮不绕过。需要规范化取消/恢复设计、持久化证明与安全审查 |
| P2 | 本地 Intelligence 无足够能力资格证据 | 正确保持禁用；要真实、多语言、正向入库/零结果/Evidence能力验证后才讨论启用 |
| P2 | Fresh媒体 native/APFS与完整ASR、非空Topic未补验 | 历史2GiB证据可复用，但新媒体driver未完成；明确范围，不冒认为PASS |
| P2 | 来源摘录 note 的语言标签 en-US 与本次繁中字幕内容不一致 | 隔离实测发现的main既有表示问题；方法明确SOURCE_EXCERPTS，不是生成/翻译结果，不触碰语言门禁；需独立来源语言展示校正 |
| P3 | 恢复成功 persisted message 在中文界面仍为英文 | main既有展示；实际恢复成功与数据一致性不受影响 |
| P3 | 非Content对象完整深链/Delta目标刷新恢复未扩展 | 本轮聚焦Content和Research，非通用路由重构；不得扩大本轮“全部路由状态均修复”的承诺 |

上线风险：有P1的完整体验不能标为 READY_FOR_ADOPTION。路由/settled no-new局部代码证据充分且无新增回归，但不能把它与“本地Intelligence已合格/全备份生命周期已完成”绑定发布。主机权限/媒体自动化失败也不能隐藏为产品完成。

## 10. 采用建议与下一步

**现在不建议整体合入 main。** 审核分支保留所有已审查修复、原始物证及报告供用户批准，main保持原状。

下一步应先处理WAITING_MODEL的正规取消/终止生命周期：先确定终止与不可重复执行的权威契约，再审查是否需要持久化/migration变更，补 interruption、restore、预算/授权与零重复付费测试并在macOS重验备份。未经用户对所需敏感变更的具体授权，本轮没有变更schema或终止账本。

本地 Intelligence资格应作为独立能力验收，不能改布尔值代替：固定模型/digest与契约，采集真实正向与零结果、多语言及Evidence绑定产物，人工评审admitted Intelligence，留真实资格记录后再提出生产资格变更。无授权云请求不可用于补验。

用户可审阅采用矩阵和当前局部修复，明确批准后再决定正式采用范围。本轮到此停止，不合并 main、不 push main、不 force push，不启动Phase14。
