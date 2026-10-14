# 已关注频道兴趣入口：精确隔离CAS提案

2026-10-14，待具体批准。真实tracked详情没有兴趣编辑入口；现全量PUT省略数量字段会重置为继承，回填effective会固化继承，且无expected版本CAS会覆盖并行设置。直接挂旧表单还会修改processing和DAILY automation，不采用。

申请只在隔离候选新增专用interest-only写入口：local_api.py精确路由/DTO、source_policy.py最小应用方法、state.py同一BEGIN IMMEDIATE下校验expected_source_policy_revision_id（明确允许null）、从原raw revision复制initial_history_count/per_run_max_new_videos的nullable值，仅更新focus/ignore mode+rules与style mode+value，追加既有不可变revision并CAS当前pointer。请求只接受command_id/expected版本/上述兴趣字段，不接受数量、enabled、processing、schedule、identity或tracking字段。旧全量PUT合同保持。

command重复只有相同完整输入幂等，不回退已移动pointer；并发版本冲突409、保留草稿、明确GET重读，无自动重放。不存在raw revision时保留既有inherit默认。复用已有GET source_policy_revision_id/policy_modes，无新Schema/原表改写/新raw读字段；只使用现合法模式和规则限制。不得通过兴趣修改授预算/执行/资格权限。

前端App.tsx CreatorFollowingDetail最小专用编辑入口与uiLanguage中英文/测试，避免Generic ExistingSourceForm submit；读取未知/失败/lateSource不得保存，关闭重开/键盘/窄窗、继承/空override真实语义明确。除了必要policy revision/pointer，Source/enabled/processing/tracking/health、automation/SourceRun/job/provider/模型和费用全部零变化。

先TDD raw NULL及非默认数值保留、并行数量/兴趣写入冲突/幂等不回退、未知字段拒绝、模式合法性、事务回滚、旧API回归、全表DATA BackupRestore。独立writer/reviewer且待LOCAL_TEXT state作者STOP后串行；真实GUI保存/重载/继承与范围内全回归。无配置/凭据/依赖/Schema/正式数据/模型网络变化，正式采用另行批准。DIRECT既有SQLite/revision/domain/GET/React/API，不新组件。

批准依据：全局AGENTS要求安全敏感持久化和新增文件范围具体批准；普通UI整改不包含这个并发持久化边界。此提案只修现有兴趣承诺可达性，不扩大自动处理功能。

## 2026-10-14 用户具体批准

用户明确回复“批准该精确隔离整改范围”。只上述精确隔离范围获批，无正式采用/模型执行或其他扩围。

## 2026-10-15 必要并发合同补充（持续授权，未实施）

只给新兴趣入口CAS不足：新兴趣先写R1后，旧无expected全量PUT仍可带R0兴趣覆盖。保留旧路径/领域字段，但新增明确版本前置条件：正常全部编辑器发送捕获expected；新写已有raw revision却没expected则409，不猜当前版本；首次真实无raw revision可按旧初始化null兼容，历史同命令同字段重放仍允许但不移pointer。新全量PUT的完整持久command identity也绑定expected，不能只比最终字段。此安全版本要求是原“旧全量PUT合同保持”的必要澄清，旧无版本盲写不再保证成功；非兴趣数量编辑仍可正常操作并能感知冲突。

无需Schema。使用明确server-generated版本revision identity source-policy:source-interest:v1:<canonical operation/source/command SHA>:<完整typed request含explicit expected/null SHA>，≤512字符。事务内主键prefix的有界范围查询LIMIT2（非全表猜hash、非默认case-insensitive LIKE），先历史command一致性再当前pointer CAS；同完整输入才幂等，同command改expected或任字段拒绝，重复旧command绝不回退head。历史重放若applied已非current，响应显式区分applied/current，UI保留草稿提示已处理但有后续更新，不能假称当前已保存。新raw数量从同事务真实row复制NULL/值。

GET现字段够但原2217 raw modes与2221 effective两次读存在R0/R1混版；必须在同read snapshot取得global+raw source，并从同row生成effective/expected/modes，无新raw数量DTO。编辑轮询/晚source响应不可覆盖草稿；缺版本、坏enum、未知读取均禁止保存并有GET重试。

实际允许加入CreatorFollowing.tsx（tracked详情在该文件）及对应tests；App SourcePolicy revision类型/专用最小兴趣编辑/旧ExistingSourceForm必要expected兼容。旧完整编辑器先处理policyCAS，再做其原有PATCH/automation，避免冲突已发生却先改Source；失败须如实区分已完成步骤，重试使用同输入持久幂等不得自动重放或重置DAILY。兴趣专用保存始终仅一interest请求，Source/enabled/processing/tracking/health/automation/SourceRun/jobs/model/费用0变化。schema、依赖、正式数据/配置均不改。

新增验收：两种旧数量/新兴趣竞争顺序均不丢更新；samecommand不同expected/fields拒、历史replay不回退、explicit null与missing区分；GET快照混版负控；专用入口只1命令+显式重读，409草稿保留，旧全量正常flow与所有现UI回归。原任务继续等待39核心独立接受，root指定最新base后串行实施；不逐文件再问批准。
