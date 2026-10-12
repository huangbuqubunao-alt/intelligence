# USER_JOURNEY_REMEDIATION_REPORT

日期：2026-10-12。针对用户截图反馈，在隔离 macOS 服务和独立数据库完成普通用户流程整改。候选代码已验收，正式采用待本次发布批准；不能把此前一次性主线采用授权重复使用。

起始 main / origin/main：`fa906148aef506bb19ae7036d2309f3cdd7b47ca`。
代码提交：`8a14cd247f43937a14073d893945d0870d35c128`、`47b4eb2234f955411131f61eee4cff7bf0618fc7`。
候选分支：`codex/task-user-journey-remediation`。工作树：`/Users/hua/Documents/yia-worktrees/user-journey-remediation`。

## 已解决的问题

- 旧导入结果被全局重放：只提示本次操作；导入窗口展示的结果不在各页重复。后台终态可关闭，15 秒后自动消失，切页清除终态。仍在运行的导入继续显示，历史与文件不删除。
- 转写不可用缺少解释和引导：首次使用、跳过之后的导入窗口、音视频详情均提供设置入口。设置解释运行组件、媒体工具、模型目录及质量验证，保留错误输入，支持重查和返回原内容。
- 检查中断后无法重试：断网时提供 GET-only 状态重试；执行状态未知时保持模型修改禁用，不启动新的检查或转写。
- 内容列表打开详情没有持久地址：统一 canonical Content URL，刷新、后退、前进与返回列表验证通过。
- 语言取消仍保存、恢复错误被 readiness 刷新抹去、中文泄漏底层英文：取消不写配置；操作失败与状态读取失败分开保留；断网、无效备份给出中文恢复指导。

## 普通用户验收矩阵

| 流程 | 实测结果与边界 |
|---|---|
| 首次使用 | 三步、返回、跳过、设置入口均通过真实浏览器操作；不创建虚假内容 |
| 本地导入 | 原生 AppKit 选择及取消；TXT/MD 成功，空文件拒绝；同批短视频成功、超两小时 WAV 拒绝；成功内容打开、关闭提示、跨页和刷新不重放 |
| 后台导入 | 最终候选在可见 macOS Chrome 与原生 Picker 中，确认导入→在后台继续→内容页显示真实失败→自动消失→切页/刷新不复现；截图 `screenshots/background-result.png` |
| 转写 | 真实 MODEL_MISSING，详情→设置→返回同一内容→刷新通过；无效目录可修改；能力检查中连接故障以受控 fixture 验证，最终返回真实服务状态，不伪造资格 |
| 关注 | 真实公开 YouTube 视频字幕处理完成；频道添加、暂停和继续关注通过，保留已存内容；RSS 网络失败保留原因及冷却，未声称来源检查成功；Bilibili UP 主暂不可用提示保留 |
| 内容 | 原文、双语、摘要摘录、Evidence 阅读；详情深链接与浏览器导航通过；真实提炼 WAITING_MODEL→取消→刷新不复活；Deep Analysis 无合格模型时关闭 |
| Research | 真实文本问题/范围校验、三条证据、来源回跳、返回研究、刷新、重做与历史通过；没有调用生成模型 |
| 洞察/主题 | 真实空态及导航通过。已保存洞察、反馈、创建/关联主题、Deep Analysis 丰富结果属于已有离线前端契约测试；真实机器缺合格模型，不制造洞察作生产验证 |
| 设置 | 界面/输出语言保存与取消、兴趣规则保存与取消、语音设置通过；凭据与云模型操作仅隔离契约测试，未访问正式凭据或调用付费服务 |
| Backup/Restore | 真实 WAITING_MODEL 阻塞，取消后开放；下载、错误扩展名/损坏 ZIP、预览取消、RESTORE 确认、恢复与重启通过；两次全表及所有 DATA 文件哈希完全一致 |
| 全局 | 中英两种语言 × 四种宽度 320/768/1024/1440 × 六导航，共 48 次可达与横向溢出检查通过；真实服务断开→中文重试→连接恢复通过；记录的 pageerror 为零 |

没有声称所有模型能力都成功执行：本地 ASR 正向转写、合格本地 Intelligence、付费云生成和依赖这些输出的真实丰富结果无法在当前资格/授权条件下实测。其状态及配置路径已验证，正向界面由隔离 fixture 契约覆盖。此产品能力限制继续显式展示，不能通过配置或测试夹具放行。

## 自动检查

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest -q` | 4008 passed，1 既有 skip，2 warnings，954.51s |
| 后端相关导入、转写、Backup、owner launcher 契约 | 161 passed |
| `npm test -- --run` | 22 文件 / 332 passed，较基线增加 40 项 |
| `npm run typecheck` | PASS |
| `npm run build` | PASS，默认 API 构建 `index-DQad5eL2.js`；隔离 API 5889 构建及实测资源 `index-QjXrTOO8.js` |
| `.venv/bin/ruff check src tests` | PASS |
| `.venv/bin/mypy --strict src` | PASS，101 source files |
| `git diff --check` | PASS |

原始日志在隔离工作树 `.var/user-journey-remediation/` 中。后端 skip 是未提供 canonical o200k tokenizer 资产的既有测试；warnings 来自重复 ZIP 与故意无效枚举 fixture。前端存在测试环境 act 警告，未隐藏日志。未修改 CI、依赖、锁文件、覆盖率或生产配置。

## 数据保护与复用

独立 API/UI 端口 5889/5888；独立 DB/DATA/config/Vault，隔离凭据提供器。正式 owner 数据只读诊断，不用于测试、导入、取消或恢复。没有 Schema/后端变更。

取消前后仅 `distillation_waiting_model_cancellations` 表变化，其他表和 DATA 完整相等。两次真实恢复均 71 张表、10 个数据文件完全相等，SQLite integrity=ok。证据：[DATA_CONSISTENCY.json](DATA_CONSISTENCY.json)。原始全表快照留在私有忽略目录，不提交仓库。

D2-01 原生导入正向与错误批次重新实测；D2-02 native_import/local_content/native_picker/build 后端及既有 2 GiB APFS 验收文件 SHA256 完全不变，复用已有大文件证明。前端通知/引导已改变，另行真实 GUI 与全量回归，不把旧前端证据当新实现验收。

复用：DIRECT React、现有 API/原生 AppKit Picker、model/refresh 端点和手册 renderer；ADAPT 现有诊断为普通用户配置引导；没有新依赖或第三方拷贝。拒绝删历史、配置即资格、自动云回退。

## 独立审查与失败记录

有界审查首次发现 P1（SELECTED 提前确认通知，后台完成被吞）和 P2（checking 状态断网后重试永久禁用），均已修复并加入复现用例。Reviewer 最终对 `47b4eb2234f955411131f61eee4cff7bf0618fc7` 给出 APPROVE，无未解决 P0/P1/P2；独立运行 TypeScript、3 文件 / 36 测试、diff check。没有重新启动三方全审。

[GUI_RESULTS.json](GUI_RESULTS.json) 保留早期失败与成功重试。原生多选选错、定位文字不符等 harness 失败保留；真实 Content 路由、备份错误消失等缺陷已修复。后台最终测试先用了错误按钮名“关闭通知”，更正为“关闭导入提示”时通知已按 15 秒规则消失；最终记录自动消失，通过此前混合批次操作与单元测试验证关闭。原先缺 PYTHONPATH 的契约启动、测试假时钟/act harness 失败日志均保留，未反复采用失败方案或隐藏断言。

## 图文手册与采用门禁

统一中文手册：[USER_MANUAL.md](../muse-final-audit/USER_MANUAL.md)、[USER_MANUAL.html](../muse-final-audit/USER_MANUAL.html)。四张新增真实截图；本地 HTML 渲染 43 张图片全部载入。

正式 main / origin/main / served revision 当前仍为 `fa906148aef506bb19ae7036d2309f3cdd7b47ca`，正式地址 http://127.0.0.1:5488/。候选为其后代，未覆盖其他 Agent 成果。正式采用必须再次核对远端/工作树/祖先关系，并获本次精确发布批准后才 ff-only、push、通过既有 owner launcher 构建重启及核验 served revision。不会重置正式数据。
