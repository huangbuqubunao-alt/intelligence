# 本地 Content→洞察→保存/主题的精确隔离补全提案

2026-10-13，用户已明确批准“批准该精确隔离补全与验收范围”。尚未实施，不授权发布；模型新调用仍依赖9b原资格通过。

## 已证实的缺口

现有真实本地文件可形成 canonical、Summary 与 Evidence，但 local_api._manual_content_source 与 distillation._manual_content_ready 均限定 YOUTUBE；LOCAL 内容无法通过普通提炼入口。仅移除限定会让 Cloud review 复用的 helper扩大授权，且 NO_NEW 成功事务仅允许启用来源或明确 YOUTUBE manual。文本 Evidence 使用既有 TEXT_RANGE（真实字符范围、时间为 NULL）；当前 provider 输入和引用 wire 未绑定 locator/offset，不能伪造0毫秒让它冒充视频。此缺口涉及授权及可信 Evidence 边界，不能用界面解禁代替。

## 申请的两个串行切片

1. LOCAL_TIMED：只允许明确用户手动提交、绑定 LOCAL_LIBRARY 来源与实际 Content、已有 verified timed transcript及当前可信Summary、未取消且通过既有模型/预算/执行校验的 LOCAL 内容，走本地模型提炼。不得启用整个资料库的自动执行。Cloud入口、service与transport在读取凭据、组装payload、claim invocation前统一拒绝LOCAL；原YouTube云授权行为保留。NO_NEW事务仅添加满足同一 manual/来源/当前Summary和Evidence CAS的LOCAL分支；原历史记录不改写。
2. LOCAL_TEXT：使用已有TEXT_RANGE与source_authority resolver，明确绑定locator、真实字符/行范围、snapshot/canonical hash与excerpt hash；时间保持NULL。为该输入新增独立版本化prompt/schema/资格profile与严格解析，不改变既有YouTube v5协议/资格身份。所有引用、NO_NEW完整coverage、保存/主题与Content来源深链均按真实locator校验；拒绝混用时间与字符范围、缺范围、越界、假时间、外部/损坏Evidence。UI显示真实行范围或时间，LOCAL来源打开自身Content，不造外部链接。

两切片只在独立worktree/数据库实施；LOCAL_TEXT依赖LOCAL_TIMED独立审查通过。已批准9b原四例真实语义验收通过是任何新真实LOCAL模型调用的前提；未通过则停止LOCAL模型验收，不重复生成择优。

## 文件范围与复用

允许最小改动：src/youtube_intel/distillation.py（manual admission、sealed locator输入、新local-text wire/profile/parser），local_api.py（LOCAL readiness、明确Cloud拒绝、locator DTO），state.py（精确manual LOCAL NO_NEW事务校验），runtime_composition.py仅如确有必要接入新的独立版本资格reader。frontend/src/workspace/App.tsx、uiLanguage.tsx及既有Evidence显示组件只补入口/正确locator/来源回跳/Cloud不可用说明；对应单元、integration与前端测试、独立研究harness/freeze、任务/交接/手册。

DIRECT既有模型transport、EvidenceResolver、source_authority、预算/ledger/checkpoint/cancellation、Summaryproducer、Intelligence保存/主题、Backup。优先复用既有read projection，不新增平行存储。源规范为Phase7/8既有本地资料链路、SYSTEM_DESIGN来源与Evidence契约；不是新增产品功能。现有Schema37已支持TEXT_RANGE，不申请Schema、依赖或正式配置变更。若不能在上述边界内完成，先停并给具体增补提案。

## 验收与调用边界

先冻结输入/code/profile/模型精确digest/原语义门槛并独立预输出审查，再按固定顺序验收：真实Whisper timed内容、真实TXT、真实MD分别中英正向（共6例）、LOCAL完整NO_NEW与source injection各1例；每例最多1次真实已批准9b本地调用，总最多8次，任何决定性失败即停，不reroll、修补输出或降低门槛，不调用云。夹具覆盖反例不产生模型调用。新profile通过全部真实资格、独立语义审查后才允许隔离普通factory持正确版本receipt运行；不得复制production_qualified布尔值。

同时验证错来源/损坏hash/过期Summary/非法范围/未知执行拒绝，LOCAL所有云路径0读取凭据/0payload/0invocation/0费用；双击与并发仅一次，取消/重启不复活，WAITING_BUDGET及原YT/NO_NEW无回归。真实GUI提炼→读取原证据→保存→主题→Content范围回跳→Backup/Restore/重启全表全DATA一致。完整backend/frontend/TS/build/Ruff/strict mypy/diff与独立审查仍为最终门禁。长内容分批、滚动字幕归一化不包含本提案。

## 风险、回退与批准依据

新增LOCAL manual资格分支和TEXT引用协议可能错误扩大来源/Cloud权力，必须在三层Cloud拒绝、真实resolver与事务CAS下验证。没有迁移或历史回写；失败候选保留独立分支，正式main及owner数据保持原样。模型receipt按新版本独立建立，旧通过记录不继承新资格。

用户全局AGENTS.md“Ask before touching: Authentication, authorization … security-sensitive code”适用于上述manual准入、NO_NEW持久化及Evidence绑定；此前字幕捕获和模型研究批准未覆盖本地内容准入。本提案请求仅上述精确隔离实施/真实验收，不请求正式采用。
