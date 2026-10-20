# Intelligence Goal 通用续作交接

2026-10-20。此文件是交接快照，后续执行者须更新；先核对真实Git/进程/文件证据，不能把本快照当实时状态。Goal尚未完成、候选未发布；本轮为用户请求交接，不新开开发阶段。本Codex已停止产品修改和自建GUI服务；新主控接管后保持唯一写入控制，旧会话不得并行恢复同一目录。

## 权威入口与持续授权

主控工作树 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness`，branch `codex/task-end-to-end-user-readiness`。交接前HEAD70d3ec46c205b008a8931c3ea25f4b726b5066d2，clean。本交接提交的实际新HEAD请现场git核验。
正式工作树 `/Users/hua/Documents/yia-worktrees/v1x-local-main`；最后已核验main/origin/main/served均73ee7e747b4461b9de8a201d6b47669eb3913d1a，正式URL http://127.0.0.1:5488/、API5489。此值须采用前重新核验，不得覆盖并行更新。正式owner/配置/凭据未读写或重置。

先读AGENTS.md、docs/COLLABORATION.md、docs/PROJECT_STATUS.md，随后按其引用读PRD/SYSTEM_DESIGN/PRODUCT_DECISIONS/REUSE_REGISTER、活动tasks和agent-prompts/handoffs。用户持续默认批准的准确记录：`docs/validation/end-to-end-user-readiness/CONTINUING_AUTHORIZATION_2026_10_15.md`。必要任务内代码/隔离安全持久化/兼容迁移/本地模型调整记录范围风险后直接实施，不再逐文件/方法申请；全部门禁满足后的安全采用已授权。禁止降低测试/证据/资格、付费Cloud、无关凭据、正式数据删除重置、force push。主控不写产品代码，独立作者/审查/整合按COLLABORATION；共享核心串行，最多2writer+1reviewer。没有Codex专用工具不构成阻塞，使用等价本地工具和文件记录，不能伪造独立审查。

## 已完成、不要重跑的最近证据

- 钟/捕获修复已独立APPROVE并整合至root：5dfadb9/f0a9ad5/2161dcc/b498ea4。固定QA ffcb3ed完整后端5334PASS、1既有o200k资产skip、2既有warning；407src/tests与root整合后字节全等，root60专项/strict115/Ruff/diff通过。原全量日志和SHA在CLOCK_FULL_BACKEND_2026_10_20.json及tracked-clock-capture-recovery/full-backend.log.gz。该结果不是未来新核心全量结果。
- 原失败内容OYp5j2RihPE经真实Chrome普通重试SUCCEEDED，29cue/4Evidence/确定性摘要；实际API重启全部77表/37DATA全等，原19DATA/所有原terminal及模型权威记录保留，0模型/Cloud。证据TRACKED_FIXED_REAL_GUI_2026_10_20.json。成功后Evidence直到reload才更新的UI缺口并入下面mixed修复，不能当作已经无刷新通过。
- 中文手册docs/validation/muse-final-audit/USER_MANUAL.md/html新增真截图；真实Chrome65/65图片加载、无横溢。最终合格洞察/新恢复截图还需补。

## 最新实际断点（必须优先处理）

1. **纯完整长request：已独立APPROVE，尚未接受整合。**
   作者WT `/Users/hua/Documents/yia-worktrees/readiness-long-request-freeze`；base25c7b015f253c9250e149a3ba52890a424343b23，core d990c4139d466ec1603b571e8cc59e993b58ac9b，最终799c62552c0a76b46e70f9ddba551df404c76f02，cleanSTOP。仅4个新增文件。
   Reviewer WT readiness-long-request-freeze-review，report-only SHA3d4bfff7a135d4e49400c31b0df37188a605a48c，APPROVE/cleanSTOP；424及13独立反例/strict116/Ruff/diff通过。审查复跑既有harness包含一例临时合成SQLite，已披露，不声称零DB；没有真实/frozen/owner/模型IO。
   先读task/package及两handoff，根控接受后顺序整合作者core/docs和独立report，不重复纯模块旧提交。profile local-grounding-qwen35-9b-lossless-rle-thinking-v1，ctx32768/output6144只是未验证候选，0模型资格。随后用根控私有`.var/end-to-end-user-readiness/long_real_request_freeze_oct20.py`校验真实114Evidence/2406cue完整request（脚本尚未运行，先核对实际API）。不得拿合成夹具替代真实源身份或容量。

2. **mixed字幕结清＋Backup提示＋无刷新Evidence：作者cleanSTOP，独立审查尚未执行。**
   作者WT `/Users/hua/Documents/yia-worktrees/readiness-mixed-subtitle-settlement`，base4e20793e08ce7c223e3e5dd03468e1f6424d1c8a。
   commits UI992732458bbf9c220e29adb14c2a2a621f04de53、core19d8107c8a583a28aa2d6d4fae3ccc24ec6e2bd4、handoff/evidence d9226ff607a211f2e7dc196e9f447fdaea31bca1。
   作者193+1distinct/198adjacent/19compatibility/964frontend、strict115/Ruff/TS/build通过。真正冻结74表19DATA的完整副本normalfactory→安全维护→备份恢复→正常重启，77表全部行/19DATA全等，原完整SQL/DB/WAL/SHM/文件不变；该实验离线socket OSError，不是真实GUI。
   独立包 `agent-prompts/TASK-READINESS-MIXED-SUBTITLE-SETTLEMENT-REVIEW.md` 已准备。原Reviewer刚触发此新任务即额度中断（提示05:51可恢复）；没有mixed APPROVE，mixed review WT亦尚未建立。不要将pure APPROVE当mixed APPROVE，也不要绕过审查直接合main。

3. **根控mixed真实GUI刚开始，未完成。**
   完整独立工作stock `.var/end-to-end-user-readiness/mixed-real-gui-20261020` 从原frozen74表19DATA逐项相等复制，clone-proof.json已存；原frozen未改。作者d922候选normalfactory以--no-worker初始化，正常迁移40；真实Chrome确认Google来源已暂停，Settings仅打开到加载状态。未启动正常worker维护、未创建备份、未stage/RESTORE，绝不能报通过。
   私有harness `mixed_real_gui_server_oct20.py` 采用此stock、NoCredentials、port6139；需从经审candidate的cwd、PYTHONPATH=src运行（务必打印module origin）。6138前端必须同一候选且YIA_API_BASE=http://127.0.0.1:6139。交接前已SIGTERM仅本轮自有两个进程，6138/6139均无监听。--no-worker仅初始读取，真实维护/恢复阶段必须正常运行worker，并明确区别。浏览器自建标签不保证留存，应重新选真实browser。
   独立APPROVE前允许隔离副本QA，不允许接受整合/正式采用。验证待做：真实readiness→创建/下载→macOS Native Picker→strict preview→明确RESTORE→普通服务实际重启→全部SQL表（含sqlite_sequence）所有行＋每个物理DATA路径/大小/SHA相等，所有旧历史保留；任何其他任务仍阻塞，不绕过Backup。还要真实无reload成功Evidence刷新复验，可用独立原失败stock副本、保留新command与旧文件，不改已成功终态凑重试。

## 之后剩余关键路径

- shared核心mixed审查/整合和真实GUI通过后，串行实现完整长输入inputproof/模型completionreceipt两表、合法全量来源factory、原子reserve/claim/complete、正反向current/history/NO_NEW/Save/Topic/Backup closure、capacity/native renderer/slot/registry/CODE_FILES与原入口接线。精确设计现有LONG_CONTENT_READONLY_TOKENIZER_PROBE_PLAN.md、任务和纯handoff，不重设计或借旧LOCAL39/20上限冒充长协议。
- 已记录long WAIT取消设计：inputproof＋m037取消(inv0)，或inputproof＋真实completionreceipt(inv1)，两互斥；不伪造取消模型输出。PENDING先真实WAITING_MODEL零usage才可取消；Cloud/WAITING_BUDGET/未知inv1不借此开放。历史验证不依当前资格/当前Summary。
- 当前所有模型资格关闭。旧8b/9b失败profiles保留STOP，协议成功≠语义合格。新profile完整代码/输入/政策冻结后按原语义四例/holdouts和既定LOCAL最多8例真实验收，首失败停止，不修补输出、不降低标准、不付费上云。不能反复重跑相同失败profile。
- 最近用户释放后内存复查5.479GiB，低于当前8.101GiB最低加载门，磁盘192.948GiB足够；0load/生成。此是旧快照，实际重查；新32k还需真实容量门，不能降低门槛或关闭用户应用。可停止仅自己验证过的QA进程。
- acoustic tuple绑定source_authority等代码，原17例真实Whisper PASSED不能直接授权新tuple。所有核心稳定后同原17例/原标准真实重验，再普通Native Import→转写→字幕/摘要/Evidence→等待取消/重启/恢复。只复用原2GiB APFS证据若对应实现确实未变。
- 最终合格Intelligence实际生成→保存→主题→原Evidence跳转/刷新/重启/完整恢复；完成全部普通用户入口和失败反馈矩阵。最后完整Backend/Frontend、TS/Production build/Ruff/strictmypy/diffcheck（有新核心必须新完整运行），最新图文手册实际渲染。
- 全门同时满足、无P0/P1、正式数据保护、实际main/origin/candidate拓扑安全才ff-only合main、push、不force、不reset；用既有owner_launcher更新正式构建，核served SHA/正常启动/访问地址。任一门失败不采用、不宣称全部可用。

## 最终交付与会话纪律

输出 INTELLIGENCE_THREE_AGENT_FINAL_ADOPTION_REPORT，含实际起止Git/main/origin/served、取消与恢复/Backup/真实macOS/完整测试/模型门禁/D2/手册/剩余问题/正式URL；成功THREE_AGENT_REMEDIATION_ADOPTED，无法满足采用条件则THREE_AGENT_ADOPTION_BLOCKED并保留候选与证据。没有真实完成不要把Goal标complete；没有外部硬阻塞不要因困难或额度单方面标blocked。

每轮把最新事实精简更新此handoff、PROJECT_STATUS和READINESS_MATRIX，保留原失败/原材料，避免继续增大历史叙事。下一执行者可用handoff、git-workflow、code-review、browser-testing等已有技能；缺Codex工具用同等工具，不把工具名称当必需依赖。不重新开启三方完整审查，不开其他开发阶段。
