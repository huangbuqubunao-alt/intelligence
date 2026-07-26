# ADR-012：本地转写持续处理契约

- 状态：`Accepted`
- 日期：2026-07-24
- 决策人：产品负责人
- 对应任务：`TASK-013A`

## 背景

ADR-007 与 TASK-006 已提供本地 Whisper 的离线策略、缓存键、资源门禁和 Adapter，但不负责把成功转写持久化为可供评分阶段消费的 Transcript Artifact。TASK-013 的独立验收因此确认：无字幕内容可以得到本地文本，却不能作为完整知识流程继续进入评分、分析、笔记和周报。

产品负责人已批准补齐该真实能力，拒绝仅在端到端测试中直接推进 SQLite 状态的替代方案。

## 决策

### C-01：以独立应用服务衔接本地转写

新增一个 Repository-backed 本地转写应用服务。它调用既有 MLX Whisper Adapter，并在同一既有 `complete_stage` 事务中完成：验证后的规范转写 Artifact、Provider-call 完成、TRANSCRIPT Job 成功和 `METADATA_READY -> TRANSCRIPT_READY`。Adapter 保持只负责本地转写与安全错误映射；Repository/Schema 契约不改变。

### C-02：只接受受控、已登记的音频输入

服务只处理 DATA 根内、已登记、未删除、哈希匹配的音频 Artifact。路径逃逸、符号链接、缺失/篡改文件、Artifact 身份不匹配、失效 Job 或状态 CAS 冲突必须失败关闭，且不得推进 Pipeline。

### C-03：转写身份与恢复

Provider-call 的稳定身份至少绑定音频内容哈希、Whisper Provider/模型/版本、语言提示和参数策略版本；成功缓存必须同时验证 Provider-call、规范转写 Artifact、文件哈希和视频/Job/Pipeline 绑定。命中时不得再次调用本地 Executor。

### C-04：失败、原子性与清理

转写文本先在 DATA 根以安全临时文件写入并验证；只有数据库阶段完成成功后才能将其作为已完成结果。数据库失败时清理本次新文件并保留可重试状态。音频清理复用既有受控 cleanup 规则，仅在成功持久化后执行；清理失败不撤销成功转写。

外部本地 Executor 成功与 SQLite 提交之间仍只能提供 at-most-once best effort：若进程在二者之间中断，恢复可重试或复用已验证缓存，但不声称严格 exactly-once。

### C-05：不改变运行资源与 CLI 边界

本决定不下载/加载模型，不调用 ffmpeg、媒体/YouTube、网络、云端或真实 Vault，也不为 CLI 添加 production composition。TASK-013A 只通过 Fake Whisper executor、临时 SQLite/DATA 和固定文本验证能力；真实运行路径继续等待各项资源与 composition 的独立批准。

## 后果

- 无字幕内容在未来受控运行时可进入与字幕相同的后续评分和知识产出路径。
- TASK-013 必须等待 TASK-013A 整合后，以新服务重新建立离线 E2E 证据；旧的直接状态推进测试不能作为验收依据。
- 不新增依赖、Schema、migration、状态转换或公共领域模型；复用既有 `mlx-whisper` Adapter、SQLite `complete_stage`、Artifact/Provider-call、临时文件安全模式和 pytest 临时目录。

## 不采用的方案

- 在 TASK-013 测试内手写 `complete_stage`：会制造产品没有的链路，不能作为验收依据。
- 修改 CLI 以临时拼装生产服务：会扩大生产运行面和真实资源风险，留待单独任务。
- 将 Whisper 降级为仅 Adapter 测试：不能满足 V1 无字幕后仍形成知识产物的产品目标。
