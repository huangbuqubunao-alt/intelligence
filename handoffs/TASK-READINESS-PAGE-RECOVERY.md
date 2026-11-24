# READINESS-PAGE-RECOVERY 交接报告

## 元数据

- Role: Implementer `/root/caption_resume`; reported 2026-10-13.
- Base: `1a401d7f688162adf5da01e6a30ab69d3e82ce52`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-page-recovery`.
- Branch: `codex/task-readiness-page-recovery`.
- Implementation: `1164bf4eaa2bfc26720f710886f908b17e1acc62`.
- 建议状态: `IN_REVIEW`; 本报告不宣称主控验收、正式采用或全链路完成。

## 目标、范围与复用

真实隔离 API 重启时 Content GET 返回空 HTTP500，旧客户端直接解析 JSON，
页面显示 `Unexpected end of JSON input`，服务恢复后没有普通读取恢复入口。
根因证据由主控保存于 root worktree 的
`docs/validation/end-to-end-user-readiness/screenshots/api-restart-transient-load-error.png`。

现有 `api` 仅为 GET/HEAD 的无法解析响应保留专用读取错误码；结构化 4xx
错误码、details 和 qualification/authorization 判定原样保留。现有 `useRemote`
提供本 loader 的手动 GET 重读；现有 `ErrorState` 显示中英文服务暂时不可用
说明及操作。Home、Following、Content、Intelligence、Topics、Settings 及已有
Content Evidence/Deep Analysis/发布状态读取面接入，多个读取失败只重读失败者。
发布状态 GET 错误不再被误认成真实写入失败，真正 POST outcome 仍保持。

DIRECT 复用现有 React state/effect、api/useRemote/ErrorState/router/UI tokens。
React `18.3.1` 为已有锁定依赖，来源 https://github.com/facebook/react，MIT；
未复制外部代码或添加/升级依赖。无新增设计样式，继续使用原设计参考。
主控已批准 `frontend/src/api/client.ts` 现有读取映射的额外限定范围。

## 验收证据

| 项目 | 结果 | 证据 |
|---|---|---|
| 空500/无法解析GET、HEAD有读取专用错误码，无自动重试 | PASS | client tests |
| 中英文Content服务仍离线再读失败，恢复再读成功，按用户点击计数 | PASS | App read recovery tests |
| 读取重试不重放POST/PATCH/PUT/DELETE、授权与资格码保留 | PASS | client及App tests |
| Following 未提交草稿保留，重读不重复既有 focus/check-stale 写操作 | PASS | App draft test |
| 路由切换移除旧错误 | PASS | App route test |
| 发布状态读取恢复不虚构WRITE_FAILED，也不发布笔记 | PASS | App publish read test |
| 真实 macOS 服务中断/恢复交互 | PENDING | 主控在独立 review/integration 后执行；本 worker 未操作真实服务/GUI |

## 检查结果

在 `frontend/`，使用已安装依赖的忽略 symlink，未安装依赖。原始日志保留于
本 tree `.var/readiness-page-recovery/`，非正式 owner 数据。

| 命令 | 结果 | 日志 |
|---|---|---|
| `npm test -- --run src/api/client.test.ts src/workspace/App.test.tsx -t 'empty 500\|unreadable successful\|empty restart\|page read reload\|failed page read'`，修改前 | 预期 RED，7 failed | `red.txt`，暴露 parse internals / 缺少操作 |
| 相同 focused 命令加 disconnected local service | 8 PASS | `green.txt`，过滤跳过141项，仅定向检查 |
| publish status read recovery 定向 | 1 PASS | `publish-green-final.txt`，过滤跳过140项 |
| `npm test` | **359 PASS /22 files，无跳过** | `frontend-full.txt` |
| `npm run typecheck` | PASS | `typecheck-final.txt` |
| `npm run build` | PASS，50 modules | `build.txt` |
| `git diff --check` | PASS | 提交前检查 |

完整测试保留已有 asynchronous `act(...)` warning 输出，没有静默或改配置。
新增发布读取测试最初使用未安装的 jest-dom matcher，TS2339，改为原生 disabled
属性断言；最初假设1次初始化读取，但既有 result-identity key 正常挂载2次，
fixture 断言改为明确2次初读、用户点击仅增加1次。两次初始失败日志
`publish-green.txt` 等未删除；所有新断言均在完整回归中通过。

## Diff 复核与风险

- 仅5个批准的 frontend 源码/测试文件 + task/handoff；无无关格式化。
- 无 backend、Schema、持久化 Evidence、凭据、正式配置、工具链或锁文件变化。
- 不调用模型、付费云或真实 Vault；客户端没有自动重试或 mutation replay。
- 窗口完整 reload 被读取 loader callback 替代，避免重挂载和清空输入。
- 完整 backend/Ruff/mypy 不在纯 frontend 切片重复运行，由主控整合阶段覆盖。
- `frontend/dist`、node_modules symlink、`.var` 日志均忽略，不提交生成文件。
- 仍需独立 reviewer 与主控真实 macOS 中断/恢复验收。
- 主控发现的 native fallback JSON3 raw 未索引、Backup/Restore DATA4→3 P1
  **仍未解决**；本任务未触碰 producer/Backup 或失败证据，不能据此宣称全链路通过。
- `DECISION NEEDED`: None for this authorized scope.

## Reviewer / 主控 / 整合

Pending independent review; worker stopped writing after this handoff commit.
不合并 main，不更新正式构建，不标记 DONE。
