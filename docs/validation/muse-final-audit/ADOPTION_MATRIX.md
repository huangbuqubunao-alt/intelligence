# 三方成果采用矩阵

基线 main `fad25e6`；OpenCode/豆包 `8d63bbf`；Muse `1cc146b`。
每项均基于独立源代码、当前规范与复测；原始报告不构成采用授权。

| 成果 | main 基线 | OpenCode / 豆包 | Muse | 裁决与最终来源 | 修改与验证 / 风险 |
|---|---|---|---|---|---|
| 普通 hash、Back/Forward | 仅处理 Content 深链，普通页不恢复 | 补普通页，但 marker 缺 `#` | 修 `#` | MODIFY；豆包方向 + Muse 修正 + Codex 事件处理 | main 冻结源复现 Settings 失败；豆包导入提示复现失败；候选真实 Chrome Back/Forward 通过 |
| 导入成功反馈、D2-01 | 正常保留；chooser/in-flight 测试已存在 | 新 hash handler 清除反馈与详情 | 单 marker 在连续导航仍丢详情 | MODIFY；Codex 最小补齐 stale-event/no-op 处理 | 两实验 full frontend 的既有 D2-01 均失败；Muse 独立单测仍失败；候选原断言通过，真实 AppKit 文本导入反馈通过 |
| Content 深链接 / 刷新 | openContent/openDelta 只写 `#Content` | 未修 | 记录 M-3，未修 | REIMPLEMENT；Codex 用现有 Content/id 解析器 | 当前 URL 含编码 content id，真实刷新/Back/Forward 通过；未扩展其他对象路由 |
| Research 返回列表 M-2 | 旧详情不清理 | 未改 | 发现，未修 | REIMPLEMENT；Codex 局部状态清理 | 新 Back 测试；同时保护 detail→New Research 表单，原有 Research 全套通过 |
| 本地 Intelligence production_qualified=True | False；有意保留资格门禁 | 无条件 True | ACCEPT True | REJECT；最终保留 main | NOT_YET_QUALIFIED；M5/M12 证据仅 Summary/Scoring，无合格 admitted Intelligence；无本地/云资格绕过 |
| 生产组成新增 True 测试 | 既有测试区分两能力 | 合成输入断言 True | 原样采用 | REIMPLEMENT；Codex 能力边界测试 | identity/input valid 仍不能授权 Intelligence；零生成请求；既有资格测试保留 |
| no-new 裸 checkpoint 备份 | repository 已投影完成，原本可备份 | helper + 主循环豁免 | 保留 helper | REJECT 冗余 helper；原测试 MODIFY | 豆包/Muse新增裸 checkpoint 测试在 main 已通过，不能复现报告的主循环缺陷 |
| no-new + settled source run | SQL 把 raw PENDING 当未结束 | SQL 排除有结果行 | 保留排除 | MODIFY；豆包/Muse方向 + Codex最小SQL | 增加 invocation_count=1；真实 repository继续验证完整绑定；main复现SOURCE_RUN_ACTIVE，候选备份/恢复及损坏拒绝通过 |
| WAITING_MODEL inv=0 自动备份豁免 | 必须阻止，保留精确用户授权云完成例外 | 放宽 | M-5 回退 | REJECT 豆包豁免；ACCEPT Muse回退；最终main规则 | 同macOS：豆包3个task022失败，Muse3个通过；候选179 focused通过；现有等待任务无完整安全取消，P1未解决 |
| WAITING_MODEL 豁免测试 | 既有断言要求阻止 | 新测试要求放行 | 移除其新增测试 | REJECT；仅拒绝实验新增测试，main测试全保留 | 不删除、不弱化任何main测试；原实验测试和diff在历史分支可追溯 |
| D2-01 本地文本/媒体导入 | 已验收功能 | 未改核心导入但路由引入回归 | 回归仍存在 | ACCEPT main + MODIFY 路由 | 原有LocalImportFlow原断言通过；当前实际文本AppKit导入，媒体自动选择失败如实保留 |
| D2-02 Picker/APFS/2 GiB | main完整native和2GiB证据 | 核心未改 | 核心未改；未做macOS | ACCEPT main，复用原验收 | 当前真实AppKit文本选择已过；新小媒体自动化两次失败，不算APFS新验收；2GiB原证据/核心代码保持不变，全量native/import回归 |
| Following→Content | 默认ORGANIZE_CONTENT，洞察可选 | 实际YouTube试点 | 静态复核 | ACCEPT main 基础闭环；豆包体验证据参考 | 当前真实YouTube单视频+频道成功、暂停/恢复、原文摘录/Evidence可读，见GUI证据；不自动云执行，不重新开放Bilibili creator |
| Content→Intelligence | 合格模型及同意门禁 | 打开未合格本地生产 | 承认错误资格 | ACCEPT main 边界；REJECT两方生产放行 | 真实提炼进入WAITING_MODEL、invocation_count=0；备份真实阻挡；no-new真实模型执行未冒认已验收 |
| 17章中文手册 | 技术/功能说明 | 17章31处图示，含错误资格承诺 | 改文案但仍错误资格承诺，去除图示 | MODIFY；豆包结构+可用原图+Codex重写与新截图 | 统一手册USER_MANUAL.md；补RESTORE步骤、模型边界、等待备份限制；普通正文不包含技术审核结论 |
| 原始49 PNG / 31图路径 | main有D2-02原图 | 有真实产品画面，部分重复串页 | 不复制，截图空 | ACCEPT保留原物；MODIFY最终选图 | Git blob/SHA256全保留；路径0缺失；逐图联系表审阅；错标题图、空白串页、未合格提炼图不用于最终可用性证明 |
| 豆包harness | 无此试点脚本 | 独立端口但脚本硬编码旧worktree | 仅参考，未交付复制 | ACCEPT作历史证据，不能当本轮runner | 原样保存未执行；本轮runner/端口/DB/Profile独立，历史runner不指向审核实例 |
| Muse审查报告与测试归因 | 正式规范与原验收 | GUI+局部/后端报告 | Linux full对比及M-5回退 | MODIFY结论，保留原始文件 | 不接受“资格安全未降低”；U6仍称WAITING豁免，和M-5回退矛盾；Linux回退后未重跑full不能声称最终full证实无回归 |

| 本地Intelligence能力正向资格 / 新媒体native补验 | 有历史边界与2GiB证据 | 无充分资格产物；媒体范围有限 | 无GUI且无资格补证 | NEEDS_MORE_EVIDENCE；不开放或声称新验收 | 当前真实等待门禁通过；完整能力资格、fresh媒体选择/ASR与非空Topic须后续有证据补验 |

最终采用为逐项局部落实，没有合并、cherry-pick或整体移植任何实验分支。
