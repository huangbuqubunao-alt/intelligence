# TASK-003 / TASK-004 Read-only Preflight Packet

## 身份

你是 `TASK-003` 与 `TASK-004` 的只读 Preflight/Scout。你只为主控识别两张后续并行任务的审批、接口和测试风险，不写代码、不修改仓库、不安装依赖。

## 运行边界

- Repository: `/Users/developer/Documents/youtubek agent`
- Branch: `main`
- Start condition: `TASK-002` assignment sync 已提交且 `git status --short` 无输出
- Sandbox: `read-only`
- Repository changes: 必须始终为 `None`

不要在 `/Users/developer/Documents/yia-worktrees/task-002` 中运行，避免读取 Implementer 正在变化的文件。只分析已批准规格和当前 `main`；不假设 TASK-002 实现已经完成。

## 必读上下文

按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md`
5. `docs/SYSTEM_DESIGN.md`
6. `docs/IMPLEMENTATION_ROADMAP.md`
7. `docs/PRODUCT_DECISIONS.md` 的 DEC-01、DEC-02、DEC-07
8. `docs/decisions/ADR-002-config-domain-contracts.md`
9. `tasks/TASK-003-state-store.md`
10. `tasks/TASK-004-discovery-metadata.md`

如文档冲突，只报告冲突，不自行选择一种解释。

## 分析内容

### TASK-003

1. 提取 SQLite 最终物理 Schema、迁移、事务、租约、唯一约束和 Artifact/Provider call 幂等要求。
2. 区分已批准逻辑方向与仍需产品负责人批准的最终 SQL Schema；列出最小决策清单。
3. 建议不跨入编排/Provider 的文件范围、Repository 接口和离线测试矩阵。
4. 标记 TASK-003 与 TASK-004 可能共享或竞争的领域类型、游标保存边界和事务接口。

### TASK-004

1. 提取 RSS 发现、yt-dlp 元数据/字幕清单、无登录态、游标推进和直播/不可用状态要求。
2. 核实正式开工仍需批准的 `yt-dlp` 精确版本范围、必要传递依赖、网络下载和锁文件动作；不得实际联网查询或安装。
3. 建议 RSS 使用标准库还是已批准依赖能力，并明确不得新增白名单外包。
4. 建议 Fake/fixture 契约测试、无网络默认测试和单独真实网络冒烟的边界。

### 并行兼容性

1. 输出 TASK-003 与 TASK-004 在 TASK-002 完成后能否真正并行的判定。
2. 列出开工前必须冻结的共享接口；不要提出超出 ADR-002 的新公共字段。
3. 给出两个独立 worktree、分支、Implementer/Reviewer 角色的建议，不创建它们。

## 禁止事项

- 不修改、创建、删除、暂存或格式化任何文件。
- 不安装、锁定、解析或下载依赖。
- 不运行会生成缓存、数据库、构建产物或网络请求的命令。
- 不创建分支、worktree 或 commit。
- 不把 TASK-003/TASK-004 设为 `READY`，不生成实现代码，不替主控做最终 Schema/依赖决定。

## 最终输出

```text
Preflight: TASK-003 / TASK-004
Role: Read-only Scout
Observed main commit:
Repository changes: None
TASK-003 spec consistency: PASS | DECISION NEEDED
TASK-003 schema approvals needed:
TASK-003 suggested scope/tests:
TASK-004 spec consistency: PASS | DECISION NEEDED
TASK-004 dependency approvals needed:
TASK-004 suggested scope/tests:
Shared interface risks:
Parallel verdict: SAFE AFTER TASK-002 | NOT SAFE
Risks/blockers:
Recommended next action:
```
