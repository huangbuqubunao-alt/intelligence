# Unresolved Issues — Intelligence User Pilot

> 尚未解决的问题与限制，均基于 2026-10-10 实测。

## 环境性限制（产品行为正确，等待环境/外部条件变化）

### U1. 本地音频/视频转写不可用（模型未配置）
- **表现**：导入的 `.m4a`/`.mp4` 保持"待转写"（`TRANSCRIPTION_UNAVAILABLE`）；详情页显示"正在检查本地转写能力"，能力 API 返回 `state: UNSUPPORTED / reason_code: EXECUTOR_INCOMPATIBLE / model_present: false`。
- **根因**：转写依赖 mlx-whisper 模型（约 1.6 GB），隔离环境与正式环境均未配置模型文件（`.local-transcription/model.json` 不存在）。
- **影响**：本地音频/视频的"转写 → 摘要"链路无法完整验证；产品行为正确（诚实反馈，不编造）。
- **恢复条件**：下载并配置 `mlx-community/whisper-large-v3-turbo`（settings.yaml 已配置模型名与 digest）。
- **验证级别**：API VERIFIED（导入与状态反馈）；转写执行 NOT TESTED。

### U2. Bilibili 视频字幕不可用
- **表现**：导入公开 Bilibili 视频成功（201），处理状态为 `CAPTION_UNAVAILABLE`。
- **根因**：Bilibili 源站字幕接口受访问限制（实测 Bilibili API 返回 HTML 风控页），或该视频无公开网页字幕。
- **影响**：Bilibili 视频可导入并保留元数据，但字幕/摘要链路不可用。
- **恢复条件**：网络环境可正常访问 Bilibili 字幕接口。
- **验证级别**：API VERIFIED（导入链路）；字幕抓取 BLOCKED（网络）。

### U3. 2 GiB 大文件导入未实测
- **表现**：产品对话框明确标注"音频/视频最大 2 GiB"限制，但未实际导入 2 GiB 文件验证。
- **根因**：本机磁盘仅剩约 23 GiB（使用率 98%），生成 2 GiB 测试文件会进一步耗尽磁盘。
- **影响**：大文件导入的边界行为（进度、超时、上限拒绝）未完整实测。
- **验证级别**：BLOCKED（磁盘限制）。

### U4. 主题详情无真实数据可验证
- **表现**：主题列表空状态已 GUI 验证（截图 `30-topics-real.png`）；但无真实主题详情截图。
- **根因**：主题归档"已提炼的洞察"，而本环境提炼结果均为"无新洞察"（模型判断合理），未产生可关联的洞察。
- **影响**：主题详情页、洞察→主题关联的用户路径未完整 GUI 验证。
- **验证级别**：主题列表 GUI VERIFIED；主题详情 NOT TESTED（依赖洞察产生）。

## 既有测试失败（与本次修改无关）

### U5. 两个环境敏感的后端测试持续失败
- `tests/integration/test_background_following.py::test_serve_api_sigterm_drains_active_tracking_before_exit`
  - 失败：SIGTERM 后子进程 10 秒未退出（`TimeoutExpired`）。
- `tests/unit/test_offline_transcription.py::test_task_owned_child_stops_when_application_parent_dies`
  - 失败：子进程心跳 3 秒超时（`TimeoutExpired`）。
- **分析**：两者均为进程生命周期/信号时序测试，与本任务修改的代码路径（路由、提炼、备份）无任何交集；在本次修改前的完整测试运行中同样失败；孤立重跑仍失败。
- **推测**：macOS 本机负载/进程调度下的时序敏感（子进程未及时响应信号）。
- **建议**：在低负载环境重跑确认；如仍失败需由维护者评估是否调整测试时序容差。

## 遗留数据状态（测试环境，非缺陷）

### U6. OpenCode 遗留的 4 个历史提炼 checkpoint
- 数据库中存在 4 个修复前产生的 checkpoint（2 个 `WAITING_MODEL` inv 0、2 个 `PENDING` inv 1 + no-new 结果）。
- 备份检查修复后已正确豁免（不再阻止备份）；checkpoint 记录本身保留作为修复前行为的证据。
- 正式环境若存在同类遗留数据，修复版代码同样会正确豁免；如需清理可考虑后续提供维护入口（未实现，不在本次范围）。
