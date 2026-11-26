# TASK-READINESS-GUI-HARNESS-TRUTH

- Role: Implementer `/root/qa_launch_isolation`
- Date: 2026-11-04
- Base: `2c97703b40f79e22cbeb65bf54a243a26338f017`
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-gui-harness-truth`
- Branch: `codex/readiness-gui-harness-truth`
- Suggested status: IN_REVIEW; Root reviews only this tooling delta once.

## 修改

仅修改已有 `scripts/verify_gui_e2e.mjs`，新增一个 Node 内置测试及本交接。DIRECT 复用已安装 Playwright 1.62.1、Chrome、Node 标准库与既有应用路由；不修改依赖、锁文件、工具链、产品源码、前端或其他工作树。

修正原脚本的假成功：每个 required step 都须实际完成，缺少控件、备份被阻塞、HTTP/console/page 错误、超时、退出异常均失败，输出 failed receipt 并 exit 1。浏览器启动也在 try/finally 内，不能在结果文件写出之前静默中断。DOM 步骤使用实际控件/持久化状态和 networkidle，不再固定睡眠后置 true。

脚本默认 **HEADED**，可显式 `--headless`；结果写实际模式。范围明确为 **GUI_SETTINGS_AND_POPULATED_RESTORE**，不宣称完整普通用户链。新库 onboarding、模型质量、Native macOS/Picker/APFS、精确 SQLite schema 校验均明确 NOT_PERFORMED，删除无证据的 schema44Verified 假标志。恢复预览的 archiveSchemaVersion 只是实际读取版本，不能替代后端 exact-schema 测试。

目标必须为明确 127.0.0.1/::1、非特权端口、无 URL 凭据/跳转参数的 HTTP。启动前同时读取 frontend proxy 与 API 的 settings，两者都必须广告 `cloud_execution_enabled=false`。随后要求非空 Content 和真实 Evidence 视图；空库不能伪称恢复数据一致。HTTP route whitelist 拒绝外部请求和范围外 mutation，包括保存/删除凭据、执行模型等；密钥面板只填合成未保存草稿并验证清空，不输出密码值、响应正文或原始异常。诊断截图屏蔽 password inputs。

恢复必须取得真实 stage restore_id 与非零 Content/Evidence/DATA 文件预览、同 ID 的 pending/restart_required 确认，再有限轮询该 ID 的 APPLIED、非 pending、有效 completed_at，并观察界面成功反馈。只在已确认重启窗口对连接拒绝/重置作有界重连；代理 5xx 只有在直接 API 同时确实不可达时才可视为暂态，其他错误失败。恢复后重新验证费用门，并比较真实 Content/Evidence API 视图身份和全文投影 hash，原文不落诊断。它不是全 SQL/DATA 恢复证明，完整存储验收仍单独执行。

## 检查与证据

- `node --check scripts/verify_gui_e2e.mjs`：PASS。
- `node --check scripts/verify_gui_e2e.failure.test.mjs`：PASS。
- `node --test scripts/verify_gui_e2e.failure.test.mjs`：PASS，1 个回归中真实启动 4 个 runner 子进程，各自 **exit 1 + success=false + 精确失败码**。
- 四个反例：缺 QA 费用门、空 Content、空 Evidence、外网 URL；前三个仅访问任务自建 127.0.0.1 stub，最后一个在任何请求前拒绝。全部 **0 mutations**，不依赖浏览器/模型/钥匙串。
- 日志 `.var/gui-harness-truth/failure-check.log`；每个 runner 的失败 receipt 保留在本 WT `.var/gui-e2e/<timestamp>-<pid>/result.json`。
- 原测试 stub 第一次将 unsafe/disabled 布尔写反，导致期望失败码不匹配。修正 fixture 后通过；断言和产品门禁未弱化，原失败 receipt 保留。
- 一次原子 patch 因同路径 delete/add 被工具拒绝，另一次 `python` 命令不存在，均未改动脚本；随后用明确 quoted heredoc 写入并重新检查了实际新脚本语法，未把旧脚本的 syntax 通过冒充新检查。

## 正向验收与使用

**正向 GUI 验收 NOT_RUN**。等待 Root 冻结最终源码、准备有数据的安全隔离候选后执行一次；本任务没有启动真实凭据服务、读取真实 Keychain、打开用户浏览器或调用模型。也没有实际调用 Playwright，因本任务四项反例均在安全 preflight 拒绝；未声称任何 headed/Native 验收通过。此新 WT 未安装 node_modules，Root 最终候选应复用现有已安装 Playwright，禁止自动安装/下载。

```sh
node scripts/verify_gui_e2e.mjs --headed --base-url http://127.0.0.1:6379/ --api-url http://127.0.0.1:6378/
```

仅在 Root 验证的安全 QA launcher 与有数据隔离库上运行。结果、屏蔽截图和 ZIP 均进入当前工作树 `.var/gui-e2e/`，不覆盖旧报告、手册、截图或正式数据。不存在产品源码变更，因此未重复全后端、前端、TS/build/mypy；最终整套验收由 Root 统一执行。没有 merge/push/deploy。
