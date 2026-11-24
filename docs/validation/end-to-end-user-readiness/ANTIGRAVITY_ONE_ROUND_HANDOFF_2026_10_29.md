# Antigravity 一轮实施交接：交付可真实测试候选，由 Codex 验收

交接日2026-10-29。用户最新要求：所有剩余问题继续解决，交付普通用户可实际操作测试的版本；本轮交给Antigravity，在独立分支完成后由Codex校验，不直接修改/合并/发布main。以下是续作，不从头开发，不重启完整三方审查。

## 1. Git 与隔离

- 已验收主候选目录 R=/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness，记录时HEAD d33c5d437fec7b0d9d55271cd5810fd3be19312b，branch codex/task-end-to-end-user-readiness，clean。已接受的新增产品代码为65220b6da74f184116b7beff83d5b92f659ee4af。交接提交只增加本文档。
- 正式目录 /Users/developer/Documents/yia-worktrees/v1x-local-main，main/tracking/真实origin-main均73ee7e747b4461b9de8a201d6b47669eb3913d1a，clean。本轮只读；原/Users/developer/youtube-intel及所有其他worktree只读保留。
- Antigravity工作树：/Users/developer/Documents/yia-worktrees/antigravity-user-testable；分支antigravity/user-testable-delivery。已由Codex从本交接提交创建。用户复制提示词会给出确切起始SHA；先核验，不在R或正式目录checkout/编辑。
- 本轮可以在自己的分支做范围明确的commit；禁止merge main、push、force/reset/clean、删旧分支或工作树、更新正式构建/配置/数据。由Codex读取最终SHA、独立验证后再处理采用。

## 2. 实际剩余缺口

A. 新Kimi系统分析协议只有pure组件接通，还没有正常产品垂直链路。runtime_composition目前仍硬编码老K2.6；不能把K3.1实际调用冒名为K2.6或继承旧资格。
B. 普通提炼输入过去未发送真实已有Summary，现已新增完整、同源、hash绑定、十字段lossless Summary比较组件，但尚未正常runtime接线。
C. 原八字段输出依赖模型自报整卡claim_kind，实际结果混合来源事实和系统建议。两份真实输出均保留REJECT，不能改标签制造通过。已接受的新system-synthesis-v1在调用前声明“系统分析”，新模型wire正向恰七字段、禁止返回claim_kind；系统元数据由请求类型固定，来源事实须在正文归因、原Evidence独立回跳。它是受限新合同，旧输出仍严格拒绝，不是事后修补。
D. Schema44持久化/授权费用/原始结果证明/零调用取消/可信读取/旧备份兼容尚未完成。
E. 模型选择、明确外发和费用同意、失败引导、保存→主题→证据回跳、重启/恢复，尚未在这条新路径真实跑通。
F. 新profile尚无真实模型资格。完整最终回归与macOS GUI/恢复/可访问隔离版本尚未交付；main不允许采用。

## 3. 已通过的成果：保留与复用

- 原用户旅程：导入结果提示生命周期、配置/转写引导、轮询草稿保护、Content深链接与重试、兴趣CAS、no-new、字幕原始捕获/归档、LOCAL文字输入证明等成果均在基线，勿从头重写。
- Schema43云WAIT0安全取消、另一任务仍阻塞、重启不复活、实际Backup/Restore83SQL表每行+19DATA全等。真实1305繁忙流程也完成GUI恢复。037本地取消与已有安全门禁保留。
- 完整后端在50abfbc产品基线6438PASS/1SKIP/2warnings，约47分钟；唯一词表skip随后用既有asset补跑完整文件8PASS。完整前端1112PASS/42files，TS/build通过。这不是新增44/最终版本的全绿证据。
- 新pure系统合同：770abb3e+b0fc1ad→Root原子65220b6；85相关unit/0.38s、全src127严格mypy、Ruff通过。实际readonly草包4messages20613B、完整Summary重建精确、256源文件不变；两个旧失败raw被新解码器拒绝。无新模型/密钥调用。
- D2-01真实本地导入与路由证据保留；D2-02 Native Picker/APFS2GiB实现未改可复用原证据。浏览器input-file操作不能冒充Native Picker新实测。
- ASR已有17真实案例证据，只证明转写；不等于本地Intelligence或所有摘要模型合格。本地Intelligence资格仍关闭，不继续追逐新本地权重/反复内存试验。

## 4. 先读这些现有材料，不复制重写规格

在自己的工作树读AGENTS.md及其要求的协作/PRD/SystemDesign/Reuse等权威规范，再读：
- docs/validation/end-to-end-user-readiness/CURRENT_RESUME_STATUS_2026_10_29.md（按末尾最新记录，前文是历史）
- SYSTEM_SYNTHESIS_CONTRACT_DECISION_2026_10_29.md
- SYSTEM_SYNTHESIS_ROOT_ACCEPTANCE_2026_10_29.json
- SYSTEM_SYNTHESIS_RUNTIME_INTEGRATION_PLAN_2026_10_29.md
- USER_TESTABLE_VERSION_ACCEPTANCE_PLAN_2026_10_29.md
（上四个同在docs/validation/end-to-end-user-readiness/）
- tasks/TASK-READINESS-SYNTHESIS-PERSISTENCE44.md及对应agent-prompts文件
- handoffs/TASK-READINESS-SYSTEM-SYNTHESIS-CONTRACT.md：包含完整projection→同一factory重建→精确wire/origin比较的recipe。
- KIMI_SUMMARY_AWARE_FINAL_TRIAL_REPORT_2026_10_29.json及handoffs/REVIEW-READINESS-KIMI-SUMMARY-AWARE-SEMANTIC.md。不要重审旧输出一遍或修改旧判定。

## 5. 中断的44草稿：参考可续，不是已验收代码

原位置 /Users/developer/Documents/yia-worktrees/readiness-synthesis-persistence44（只读，HEAD也是d33c5d4，未提交）。已封存到 R/.var/antigravity-handoff-20261029/persistence44-draft；manifest.json列全部文件/hash，tracked.patch只有原tracked差异，另有未跟踪新文件，不能只套patch漏文件。

草稿8文件：backup_restore.py、intelligence_read.py、state.py；新增044 migration、system_synthesis_persistence.py、system_synthesis_profile.py、test_system_synthesis_persistence.py和精确迁移提案。Agent额度中断，没有最终类型/测试/审查结论。先读实际内容和提案，选择性移入自己的分支并完成，不覆盖原工作树、不把草稿自述当通过。

提案方向：在既有checkpoint下追加四种不可变sidecar（完整inputproof、授权+费用预留、rawpublic-final/resultreceipt、WAIT0取消），不另造执行生命周期；44只有限替换相关guard保留旧分支，001–043不改写，42/43精确DDL验证按版本，34–43及44备份明确兼容。精确字段/保护/恢复风险先记录，再隔离实施。新家族PENDING显式abandon只在严格证明新proof-bound、从未授权/claim/执行时适用；不得放行旧PENDING、RUNNING、WAITING_BUDGET或未知/部分执行。

## 6. 建议实施顺序与边界

1. 完成44持久化/严格replay/取消/预算竞态及兼容恢复，相关测试先通过。集中有限profile描述，不让每换一个同服务模型就复制执行系统；未知/未验模型不因此获得资格。
2. 接新typed请求与transport到原compose/reserve/preview/confirm/claim/dispatch/admit；Summary当前快照、完整proof、actualmodel/参数、最终wire都进入identity，确认时重验。新Reader重放raw+proof后沿用原Save/Topic/Evidence。避免重写整个distillation/state框架。
3. 接设置/模型选择/费用和外发预览/明确用户确认/取消及清晰反馈。当前费用政策缺失默认拒绝；不要默认日常付费或自动换付费模型。
4. 第一真实云能力是publicYOUTUBE/TIMED_MEDIA。当前LOCAL云路径服务/API双拒绝，不能偷偷取消保护。若为本地视频/文字链路增加云选项，必须是独立的手动逐次明确外发同意、数据预览与能力证明；自动测试仅用公开/合成材料，严禁默认上传私人内容。没有实现/验收的scope如实标未支持，不宣传全部输入都已可用。
5. 新资格与正常费用保持关闭直到新profile真实质量验收。可做FakeTransport的正常链路/错误/并发验证，但必须标模拟。禁止用环境变量/布尔常量强行资格true，禁止旧Kimi或本地资格冒名放行。
6. 完整测试、真实GUI/重启/备份恢复后，启动自己的隔离服务供Codex校验，记录真实revision/端口/数据目录。全部条件未满足时仅交工程候选与阻塞，不能称已交付可正式使用。

## 7. 模型、费用和凭据红线（重要）

- 目前Kimi实际累计2次。第一次缺Summary，第二次事实/引用/新增价值通过但1P2分类不符；旧raw/result/reservation/reject永远保留。实际账单UNKNOWN，累计1.943326元预留未释放。最近一次明确授权只有一次，已经耗尽；本轮交接不授权新收费或提高调用次数。
- Kimi fixed kimi-k3.1-pro/low/5888/JSON/nonstream/cache5m；当日官方价格快照与固定参数在R/.var/kimi-summary-aware-diagnostic/package和原脚本可只读参考。输入价格最坏26、输出68微元/token；UTF8bytes+2048仅保守估计，不是厂商账单保证。
- R/.var/system-synthesis-20261029/eight-case-draft-NOT-APPROVED.json是后续8例草案（4真实公开输入：2来源×中英；4合成NO_NEW/注入防护）。合计含旧预留估计7.498514元；若执行将累计10次生成，超过原8次调用数，需要新的明确一次批次授权。合成源尚未在44正常repository落地，正常runtime/proof和最终语义冻结仍待完成。不能直接运行这些草包或自造ownerreceipt。
- 本轮先完成工程、离线与GUI/恢复；真实模型新费用如仍未准，准备完整可审查请求/范围/预算/停止条件，集中交Codex处理，不逐文件或方法问用户。
- 用户已有Kimi API付费余额并已自行存QA钥匙串。唯一授权QA namespace：service com.huangbuqubunao.intelligence.qa.kimi-public-20261029 / account api-key。不得手工读取/打印key、查别的namespace、导出环境变量或带key进入命令行/日志/截图。只查配置状态即可。历史智谱密钥曾泄露已轮换；不能宣称历史从未泄露。
- 不接管用户Chrome、不要--auto-connect或全局AX检查含key页面；另起agent-owned会话，只截图无秘密的产品流程。不要杀Root的6278/6279服务、修改VPN、重置正式owner数据。
- 免费GLM4.7路径已5次失败并停止，不自动重启；GLM5.3未调用。本轮不要新增模型下载/依赖/试其他收费服务来绕开当前问题。

## 8. 验证与交付

使用独立临时DB/DATA/Vault。可复用R/.venv，但所有Python命令明确PYTHONPATH=<你的worktree>/src、MYPYPATH同路径、PYTHONDONTWRITEBYTECODE=1，避免editable指向/Users/developer/youtube-intel跑错代码。依赖版本保持原lock，不修改共享依赖/工具链来掩盖失败。

先相关语法/类型/测试，再在最终产品代码冻结时执行一次后端完整pytest、前端npm test、npm run typecheck、npm run build、Ruff、strict mypy、git diff --check。真实报告基线失败/新失败/跳过和原因，不删测试、改断言或减覆盖让它绿。完整后端约47分钟，不能当卡住随意杀掉后写全绿。相关新改动修后仅复核delta，不反复开旧三方完整审查。

真实macOSGUI流程及截屏：首次/跳过设置→导入失败瞬时提示可关闭且不跨路由残留→成功导入/转写/摘要→模型设置与预览/同意/拒绝→提炼/NO_NEW→保存/主题→Evidence回跳→取消WAIT0/另一任务仍阻塞→重启不复活→Backup readiness→创建/恢复→全部SQL逐行和DATA路径/hash相等。真实模型未授权的步骤如实UNVERIFIED或SIMULATED，不用Fake冒充real。

更新统一中文手册docs/validation/muse-final-audit/USER_MANUAL.md、同步HTML及真实无秘密截图；已有91图不丢失。自己的开发端口可用6378/6379（先查冲突；占用则另选，不杀未知服务）。必须记录启动/停止方式、访问地址、真实served revision、数据隔离路径和截图路径；未部署不能填虚假revision/地址。

最终仅提交本分支，输出ANTIGRAVITY_ONE_ROUND_IMPLEMENTATION_REPORT：起止SHA/分支/worktree、每项实际改动、复用/迁移范围、测试命令与结果、真实/模拟/未验矩阵、完整恢复比较、模型资格/费用/隐私状态、可访问隔离地址与revision、手册位置、剩余P0/P1/P2和阻塞。不merge/push/main/正式发布。Codex收到SHA后审查实际diff并复核必要证据，才决定下一步。

建议技能：git-workflow-and-versioning、incremental-implementation、security-and-hardening、相关接口/前端与真实browser-testing技能；按实际可用性使用，不安装一套新工具或反复全量review。
