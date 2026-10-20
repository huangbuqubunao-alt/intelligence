# Intelligence Goal 通用续作交接

2026-10-20（混合修复整合）。此文件是交接快照，后续执行者须更新；先核对真实Git/进程/文件证据，不能把本快照当实时状态。Goal尚未完成、候选未发布。主控保持唯一写入控制，旧会话不得并行恢复同一目录。

## 权威入口与持续授权

主控工作树 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness`，branch `codex/task-end-to-end-user-readiness`。本轮实际HEAD请现场git核验；mixed候选已整合后HEAD在merge df19d70附近。正式工作树 `/Users/hua/Documents/yia-worktrees/v1x-local-main`；最后已核验main/origin/main/served均73ee7e747b4461b9de8a201d6b47669eb3913d1a，正式URL http://127.0.0.1:5488/、API5489。此值须采用前重新核验，不得覆盖并行更新。正式owner/配置/凭据未读写或重置。

先读AGENTS.md、docs/COLLABORATION.md、docs/PROJECT_STATUS.md，随后按其引用读PRD/SYSTEM_DESIGN/PRODUCT_DECISIONS/REUSE_REGISTER、活动tasks和agent-prompts/handoffs。用户持续默认批准的准确记录：`CONTINUING_AUTHORIZATION_2026_10_15.md`。必要任务内代码/隔离安全持久化/兼容迁移/本地模型调整记录范围风险后直接实施，不再逐文件/方法申请；全部门禁满足后的安全采用已授权。禁止降低测试/证据/资格、付费Cloud、无关凭据、正式数据删除重置、force push。主控不写产品代码，独立作者/审查/整合按COLLABORATION；共享核心串行，最多2writer+1reviewer。没有Codex专用工具不构成阻塞，使用等价本地工具和文件记录，不能伪造独立审查。

## 已完成、不要重跑的最近证据

- 钟/捕获修复独立APPROVE并整合root（5dfadb9/f0a9ad5/2161dcc/b498ea4）；完整backend5334PASS；原OYp5j2RihPE真实Chrome重试SUCCEEDED，29cue/4Evidence/摘要，实际重启77表/37DATA全等（TRACKED_FIXED_REAL_GUI_2026_10_20.json）。
- 纯长request冻结已完成独立APPROVE并整合root：35eb95e/8137178/ebc7c2b/2670b43；候选799c625（core d990c41）。
- mixed字幕结清原候选d9226ff被独立审查REJECT（P1）；隔离作者修复ec6dabb（App.tsx effect拆分 + 4例测试）与delta硬化b8bceaf已经两次独立审查APPROVE并以96c9ffa/df19d70整合root；root整合复验968前端/TS/build/diff、compileall/strict116/Ruff/194后端closure全PASS（.var/mixed-integration日志，SHA见MIXED_DISPATCH_GUARD_FIX_IMPLEMENTER_2026_10_20.json）。
- 中文手册docs/validation/muse-final-audit/USER_MANUAL.md/html真截图65/65加载、0横溢；最终合格洞察/新恢复截图仍需补。

## 最新实际断点（必须优先处理）

1. **mixed候选最终真实macOS GUI完整恢复仍在OPEN。** 旧d9226ff候选上的GUI实验（mixed-real-gui-20261020目录、6139端口）在root整合（96c9ffa/df19d70）后已过期：候选App.tsx已变，须从root HEAD重新以独立完整frozen-stock副本启动普通服务与真实Chrome再验证。验证序列：readiness→创建/下载→macOS Native Picker→strict preview→明确RESTORE→普通服务实际重启→全部SQL表（含sqlite_sequence）所有行＋每个物理DATA路径/大小/SHA相等（不能只比条目数），全部旧历史保留。可用私有harness `mixed_real_gui_server_oct20.py` 模式（真实candidate src、YIA_API_BASE、真实维护worker，--no-worker仅限初始读取），print module origin。独立APPROVE已覆盖静态/测试面；此GUI是验收面，不是独立审查替代。
2. **真实无reload成功Evidence刷新复验**仍OPEN：可用独立原失败stock副本，保留新command与旧文件，不改已成功终态凑重试。
3. **长request真实冻结校验未跑**：`long_real_request_freeze_oct20.py`（root .var）须先核对实际API/候选身份后运行真实114Evidence/2406cue验证；0模型资格。
4. **mixed之后串行队列**：完整长输入inputproof/模型completionreceipt两表、合法全量来源factory、原子reserve/claim/complete、正反向current/history/NO_NEW/Save/Topic/Backup closure、capacity/native renderer/slot/registry/CODE_FILES与原入口接线；按LONG_CONTENT_READONLY_TOKENIZER_PROBE_PLAN.md，不重设计、不篡用旧39/20上限。

## 之后剩余关键路径

- long WAIT取消按已冻结设计：inputproof＋m037取消(inv0)或inputproof＋真实completionreceipt(inv1)两互斥；不伪造取消模型输出；PENDING须真实WAITING_MODEL零usage才能取消；历史验证不依当前资格/Summary。
- 当前所有模型资格关闭；失败8b/9b profiles保留STOP，协议成功≠语义合格；新profile按原语义四例+holdouts+LOCAL最多8例真实验收，首失败停止，不修补输出、不付费上云、不重跑相同失败profile。
- 资源门实际复查再定：旧快照RAM低于门值时保持关闭0load；磁盘充足。可以停止仅自己验证过的QA进程；不能降低门槛或关闭用户应用。
- acoustic tuple绑定source_authority等代码变化后，原17例真实Whisper旧PASSED不可复用；核心稳定后原17例同标准重验，再普通Native Import→转写→字幕/摘要/Evidence→等待取消/重启/恢复。
- 最终合格Intelligence完整生成→保存→主题→原Evidence跳转/刷新/重启/完整恢复；完成全入口失败矩阵后：完整Backend/Frontend/TS/build/Ruff/strictmypy/diff + 最新图文手册渲染。
- 全门同时满足、无P0/P1、正式数据保护、main/origin/candidate拓扑安全→可ff-only合main/push/launcher更新/核served。任一门失败不采用。

## 最终交付与会话纪律

输出 INTELLIGENCE_THREE_AGENT_FINAL_ADOPTION_REPORT（实际测试、真实链路、模型资格、数据恢复、剩余问题、main/origin/served、手册、访问地址）；成功THREE_AGENT_REMEDIATION_ADOPTED，否则THREE_AGENT_ADOPTION_BLOCKED并保留候选证据。没有真实完成不标complete；无外部硬阻塞不单方面标blocked。每轮精简更新此handoff、PROJECT_STATUS、READINESS_MATRIX，保留原失败/原材料。不重新开启三方完整审查，不开其他开发阶段。
