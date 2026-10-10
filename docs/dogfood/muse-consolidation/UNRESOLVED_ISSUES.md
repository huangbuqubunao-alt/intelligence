# 未解决问题（UNRESOLVED_ISSUES）— Muse 评审轮

> 基线：豆包 UNRESOLVED_ISSUES（U1–U6）经复核基本成立，本文件在其基础上更新本轮状态。凡未实际验证的一律如实标注，不写成已确认。

## 环境性限制（产品行为正确，待环境/外部条件）

### U1. 本地音频/视频转写不可用（模型未配置）—— 未变化
- 表现：导入的音频/视频保持"待转写"；能力 API 如实报告不可用。产品行为正确（不编造）。
- 恢复条件：配置约 1.6 GB 的 mlx-whisper 本地转写模型。
- 验证级别：转写执行 NOT TESTED（本轮未验证）。

### U2. Bilibili 视频字幕不可用 —— 未变化
- 表现：公开 Bilibili 视频可导入（元数据保留），字幕显示"字幕不可用"。
- 根因：源站字幕接口限制 / 无公开网页字幕；后端能力表明确标记 `public_captions.available = False`（`local_api.py` `_BILIBILI_CAPABILITY`），前端如实展示。
- 另：Bilibili UP 主持续关注在代码层明确关闭（`providers/bilibili.py: CREATOR_FOLLOWING_AVAILABLE = False`），添加对话框仅提供"YouTube 频道持续关注"，Bilibili 仅支持单次公开视频导入。手册已按此如实描述。
- 验证级别：本轮未重新验证，沿用豆包结论。

### U3. 2 GiB 大文件导入未实测 —— 未变化
- 表现：对话框标注"TXT/MD 最大 2 MiB、音频/视频最大 2 GiB、媒体时长最长两小时"（源码 `LocalImport.tsx:123` / `uiLanguage.tsx:311` 核验一致），但 2 GiB 边界未实际导入验证。
- 验证级别：NOT TESTED。

### U4. 主题详情无真实数据 —— 未变化
- 主题归档的是已提炼洞察；无洞察时主题页为空是正常现象。主题详情页未验证。
- 验证级别：NOT TESTED。

## macOS 特有能力 —— 未验证（本轮新增明确项）

### U7. macOS 原生能力在本环境未验证
- Keychain 凭据存储、APFS `clonefile`、macOS 原生文件选择器（`native_picker.m` / `macos_pick`，仅 `sys.platform == "darwin"` 生效）均为 macOS 特有路径。
- 本评审环境为 Linux：原生选择器分支不可达（前端 `navigator.platform.includes("Mac")` 为 false 时走浏览器 `<input type="file">` 上传；后端 `macos_pick` 在非 darwin 直接拒绝）。
- 验证级别：NOT TESTED。手册中已按"macOS 可用、非 Mac 环境走浏览器文件选择"如实区分，不写成全平台可用。

## GUI 未实际运行验证（本轮方法边界）

### U8. 本轮未做真实 GUI 点击验证
- 本环境无浏览器自动化能力。`INDEPENDENT_UX_REPORT.md` 的 A–H 路径结论全部为 CODE REVIEW ONLY（代码阅读 + 静态分析），未声称做过真实操作。
- 豆包轮次的 GUI 验证记录（19 条路径、截图）保留在豆包分支 `docs/dogfood/opencode-user-pilot/` 备查，不复制、不冒充为本轮验证。

## 既有测试失败 —— 已确认环境敏感（2026-10-11 更新）

### U5. 两个环境敏感的后端测试 —— 已确认非本次改动引入
- `tests/integration/test_background_following.py::test_serve_api_sigterm_drains_active_tracking_before_exit`（SIGTERM 后子进程 10 秒未退出）
- `tests/unit/test_offline_transcription.py::test_task_owned_child_stops_when_application_parent_dies`（子进程心跳 3 秒超时）
- **本轮复核结论**：两测试在 muse-work 分支单独运行时均通过（2.3s / 5.7s）；后端全量套件（muse-work 与 main 基线）中均未出现 FAILED，确认为进程生命周期/信号时序类环境敏感测试（与系统负载相关），与本次修改的代码路径（路由、提炼、备份）无交集。豆包"既有环境问题"的判断成立。

## 本轮已知但未修复的小问题

### M-2 / M-3（见 ISSUES_FOUND.md）
- Research 详情后退到 `#Research` 时视图不重置；`openDelta` 内容深链 hash 信息丢失。均为 pre-existing、低严重程度，待 GUI 验证。

## 遗留说明

### U6. 历史 checkpoint 数据（测试环境，非缺陷）
- 沿用豆包结论：修复前产生的历史 checkpoint 在修复版代码下被正确豁免，不再阻止备份；记录本身保留。如正式环境存在同类遗留数据，行为一致。
