# 已关注频道兴趣入口：精确隔离CAS提案

2026-10-14，待具体批准。真实tracked详情没有兴趣编辑入口；现全量PUT省略数量字段会重置为继承，回填effective会固化继承，且无expected版本CAS会覆盖并行设置。直接挂旧表单还会修改processing和DAILY automation，不采用。

申请只在隔离候选新增专用interest-only写入口：local_api.py精确路由/DTO、source_policy.py最小应用方法、state.py同一BEGIN IMMEDIATE下校验expected_source_policy_revision_id（明确允许null）、从原raw revision复制initial_history_count/per_run_max_new_videos的nullable值，仅更新focus/ignore mode+rules与style mode+value，追加既有不可变revision并CAS当前pointer。请求只接受command_id/expected版本/上述兴趣字段，不接受数量、enabled、processing、schedule、identity或tracking字段。旧全量PUT合同保持。

command重复只有相同完整输入幂等，不回退已移动pointer；并发版本冲突409、保留草稿、明确GET重读，无自动重放。不存在raw revision时保留既有inherit默认。复用已有GET source_policy_revision_id/policy_modes，无新Schema/原表改写/新raw读字段；只使用现合法模式和规则限制。不得通过兴趣修改授预算/执行/资格权限。

前端App.tsx CreatorFollowingDetail最小专用编辑入口与uiLanguage中英文/测试，避免Generic ExistingSourceForm submit；读取未知/失败/lateSource不得保存，关闭重开/键盘/窄窗、继承/空override真实语义明确。除了必要policy revision/pointer，Source/enabled/processing/tracking/health、automation/SourceRun/job/provider/模型和费用全部零变化。

先TDD raw NULL及非默认数值保留、并行数量/兴趣写入冲突/幂等不回退、未知字段拒绝、模式合法性、事务回滚、旧API回归、全表DATA BackupRestore。独立writer/reviewer且待LOCAL_TEXT state作者STOP后串行；真实GUI保存/重载/继承与范围内全回归。无配置/凭据/依赖/Schema/正式数据/模型网络变化，正式采用另行批准。DIRECT既有SQLite/revision/domain/GET/React/API，不新组件。

批准依据：全局AGENTS要求安全敏感持久化和新增文件范围具体批准；普通UI整改不包含这个并发持久化边界。此提案只修现有兴趣承诺可达性，不扩大自动处理功能。

## 2026-10-14 用户具体批准

用户明确回复“批准该精确隔离整改范围”。只上述精确隔离范围获批，无正式采用/模型执行或其他扩围。
