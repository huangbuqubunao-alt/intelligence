# HANDOFF STATUS — Intelligence User Pilot（豆包接管 · 最终快照）

> 供下一个接手的 AI Agent 快速恢复现场。最后更新：2026-10-10（豆包最终交付轮次）。

## 当前 HEAD 与分支

- 工作树：`/Users/hua/Documents/yia-worktrees/opencode-user-pilot`
- 分支：`opencode/user-pilot`
- 接管时 HEAD：`fad25e6109d02650b25ae777f2f7557dd478309d`（与任务参考 HEAD 一致；未对 main 做任何回退/覆盖/重置）
- 最终 HEAD：**本次任务全部成果已提交到 `opencode/user-pilot`**（提交信息见 git log；未合并 main、未 push）

## 独立测试环境（禁止触碰正式 5488/5489）

- Frontend：http://127.0.0.1:5588/（OpenCode 遗留进程，沿用中）
- Backend：http://127.0.0.1:5589/（豆包最终重启 PID 58253，加载全部修复）
- 数据：`/Users/hua/Documents/yia-worktrees/opencode-user-pilot/.var/user-pilot`
- 启动器：`docs/dogfood/opencode-user-pilot/harness/pilot_launcher.py`（--restart-api 依赖 launcher.json 的 pids；若 pid 失真先 kill 端口占用进程）
- 浏览器 harness：`harness/browser.mjs`（open/shot/BASE/PROFILE）+ `p*.mjs`（p13/p13b/p13c/p14/p15/p16/p17/p17b/p18 为豆包新增验证脚本）
- Ollama：127.0.0.1:11434，qwen3:8b（digest sha256:500a1f06…，与 settings.yaml 期望一致）
- 本地转写（mlx-whisper）：模型未配置（capability=UNSUPPORTED / EXECUTOR_INCOMPATIBLE / model_present=false），隔离与正式环境均无 whisper 模型文件

## 测试数据状态（.var/user-pilot/state.sqlite3）

- 视频/内容：aircAruvnKk（3Blue1Brown，ORGANIZED，字幕+摘要+20 条 Evidence 汇总）；note.txt / note.md（READY）；sample.m4a / sample.mp4（TRANSCRIPTION_UNAVAILABLE）；bilibili-BV1GJ411x7h7（CAPTION_UNAVAILABLE）
- 关注：Veritasium（enabled，DISCOVER_ONLY）+ 备份测试生成的关注记录，共 3 条
- 洞察：手动提炼已修复并验证，结果 SUCCEEDED_NO_NEW_INTELLIGENCE（模型判定无新洞察，正常）；0 条洞察（正常）
- Topics：0 条（无洞察可关联，主题空状态已 GUI 验证）
- 备份：已实际创建成功（backup_id ef7f2dee98d2451cb9e88aa998bde644，Intelligence-Backup-2026-10-10.zip，372589 B）
- OpenCode 遗留 4 条历史 checkpoint（2 个 WAITING_MODEL inv0、2 个 PENDING inv1 + no-new 结果）——修复版备份检查已正确豁免，保留作证据

## 已完成事项（豆包轮次）

1. 恢复现场：核验工作树、数据库、服务进程、截图唯一性（MD5）；识别 OpenCode 截图重复/串页（勿复用）
2. **Bug 1 修复 — 前端路由**：hashchange 只处理深链接 → 前进/后退/地址栏 hash 不切换视图。修复 `App.tsx` + 2 个回归测试；110 tests passed；GUI 验证（30-topics-real.png）
3. **Bug 2 修复 — 本地提炼永远 WAITING_MODEL**：runtime_composition 硬编码 production_qualified=False 且无授予路径。修复：本地 transport 授予资格（digest 绑定保留）+ 回归测试；runtime composition 10 passed；GUI 验证（34/35，ollama 实际执行）
4. **Bug 3 修复 — 提炼后备份永久阻止**：no-new 结果已记录但 checkpoint 保持 PENDING，备份把 PENDING 视为活动任务。修复 `backup_restore.py` 豁免两类已完结死 checkpoint + 2 个回归测试；backup 28 passed；端到端：ready:true + 实际备份成功
5. 真实路径验证：本地 TXT/MD/音频/视频、暂停/恢复关注（38/39）、语言 zh↔en（41/42/43）、Bilibili 导入（API 201）、首页/列表/详情/字幕/摘要（44/45/46/47）
6. 交付文档全部完成并校验：USER_MANUAL.md（17 章）、USER_MANUAL.html（31 图真实渲染 0 缺失）、ISSUES_FOUND.md、UNRESOLVED_ISSUES.md（U1–U6）、EXPLORATION_REPORT.md、FINAL_REPORT.md、HANDOFF_STATUS.md、build_manual_html.py

## 测试结果（豆包轮次）

- 前端：`npx vitest run src/workspace/App.test.tsx` → **110 passed**
- 后端全量：`PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` → **3976 passed, 2 failed, 1 skipped**
  - 2 个失败为既有环境敏感测试（与本次修改无交集，修复前基线同样失败）：
    - `tests/integration/test_background_following.py::test_serve_api_sigterm_drains_active_tracking_before_exit`
    - `tests/unit/test_offline_transcription.py::test_task_owned_child_stops_when_application_parent_dies`
- runtime composition：10 passed；backup：28 passed；`npm run build`：成功

## 交付文档清单（docs/dogfood/opencode-user-pilot/）

| 文件 | 内容 |
|------|------|
| USER_MANUAL.md | 17 章完整中文图文用户手册 |
| USER_MANUAL.html | 自包含 HTML 手册（浏览器打开，31 张真实截图） |
| build_manual_html.py | HTML 生成脚本 |
| ISSUES_FOUND.md | 3 个 Bug 完整记录（发现/根因/修复/验证）+ 产品正确行为 |
| UNRESOLVED_ISSUES.md | U1–U6 未解决问题与限制 |
| EXPLORATION_REPORT.md | 19 条路径体验报告 |
| FINAL_REPORT.md | 最终交付报告（15 要素 + DOUBAO_USER_PILOT_COMPLETE） |
| HANDOFF_STATUS.md | 本文件 |
| screenshots/ | 49 个 PNG（手册引用 31 张，全部真实有效） |
| harness/ | 全部验证脚本与启动器 |

## 未完成事项 / 下一步（供后续 Agent 参考）

- 本任务已交付，未强制项遗留。可选后续：
  1. U1：配置 mlx-whisper 模型后补验音频/视频转写链路
  2. U2：网络可访问 Bilibili 字幕接口后补验字幕
  3. U3：磁盘充足环境补验 2 GiB 大文件导入
  4. U4：产生真实洞察后补验主题详情
  5. U5：低负载环境重跑两个环境敏感测试确认

## 已知阻塞 / 风险

- 转写模型缺失（U1）；Bilibili 字幕源站限制（U2）；磁盘仅 23 GiB（U3，2 GiB 测试 BLOCKED）
- 正式产品（5488/5489）与本测试完全隔离，禁止触碰
- 浏览器 harness 需串行使用同一 profile（并发 SingletonLock 冲突）

## 交接提醒（给下一个 Agent）

- 所有操作限定在 `opencode-user-pilot` 工作树与 `opencode/user-pilot` 分支
- 禁止：merge main / push main / force push / 修改正式 worktree / 重置正式数据库 / 覆盖截图与测试记录
- 测试命令：后端 `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`（直接用 pytest 会模块找不到）；前端 `npx vitest run src/workspace/App.test.tsx`
- 备份/提炼行为确认：先 `curl http://127.0.0.1:5589/api/v1/system` 按实际状态操作，勿凭文档假设
- 交付截图在 `screenshots/`，直接 Read 本地 PNG 取用
