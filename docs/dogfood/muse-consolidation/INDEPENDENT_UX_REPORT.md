# 独立体验报告（INDEPENDENT_UX_REPORT）— Muse 评审轮

> **方法边界（诚实声明）**：本环境无浏览器自动化能力，**未做任何真实 GUI 点击、未实际运行产品界面**。本报告全部结论基于：① `frontend/src/workspace/*.tsx` 源码阅读；② `src/youtube_intel/*.py` 后端代码阅读；③ 后端自动化测试实测。凡涉及界面实际渲染、点击交互、截图的内容，本轮均未验证。
>
> 每条路径结论均标注 **[CODE REVIEW ONLY]**。豆包轮次的真实 GUI 验证记录保留在其分支 `docs/dogfood/opencode-user-pilot/`（EXPLORATION_REPORT.md + 截图），本报告不复制、不冒充为本轮验证。

---

## A. 首次使用 [CODE REVIEW ONLY]

- 引导流程代码存在（`Onboarding.tsx`）：共 3 步（`step + 1 / 3` 进度指示），第 1–2 步按钮为"继续"（Continue），第 3 步按钮为"添加内容"（Add something → zh-CN "添加内容"），另有"稍后再说"（Skip for now）跳过入口。
- 引导文案包含"本地优先""关注→内容→洞察""证据可追溯"等定位说明（`Onboarding.tsx:24-36`）。
- 首页标题文案存在："最近 7 天发生了什么变化？"（`uiLanguage.tsx:532`），空状态"最近 7 天没有明显的知识变化。"（`:536`）。
- 未验证：真实渲染效果、引导→首页的实际跳转、重开后状态保留。

## B. 添加来源 [CODE REVIEW ONLY]

- 添加对话框引导文案存在："粘贴 YouTube 或 Bilibili 视频链接，持续关注 YouTube 频道，或导入本地文件。"（`uiLanguage.tsx:30`）—— 注意文案明确限定"持续关注 YouTube 频道"。
- Bilibili 单次导入入口存在（`BilibiliImport.tsx`）；Bilibili UP 主持续关注在代码层关闭（`providers/bilibili.py: CREATOR_FOLLOWING_AVAILABLE = False`），`CreatorFollowing.tsx` 在能力关闭时显示"Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos."—— 与手册"不支持持续关注 Bilibili UP 主"一致。
- 未验证：粘贴链接后的真实识别、添加成功提示的实际展示。

## C. 本地文件处理 [CODE REVIEW ONLY]

- 两套导入路径代码存在：macOS 原生选择器（`NativeLocalImport.tsx`，经后端 `/local/native/picks` 打开系统对话框，仅 `sys.platform == "darwin"` 可用）；其他平台走浏览器 `<input type="file">` 上传（`LocalImport.tsx:124`，`accept=".txt,.md,.mp3,.m4a,.wav,.mp4,.mov,.m4v"`）。
- 大小限制文案存在且与手册一致："TXT／MD：UTF-8，最大 2 MiB。音频／视频：最大 2 GiB。媒体时长：最长两小时。所有内容都保留在本机。"（`uiLanguage.tsx:311`）。
- 未验证：真实文件选择、上传进度、超限拒绝提示、2 GiB 边界。

## D. Following（关注） [CODE REVIEW ONLY]

- "暂停关注"/"持续关注"按钮文案存在（`uiLanguage.tsx`）；自动检查机制代码存在（`App.tsx:2505` `check-stale`，文案"应用运行时检查更新，两次检查至少间隔 15 分钟。"`uiLanguage.tsx:195`）。
- 未验证：暂停/恢复的真实状态切换、自动检查的实际触发。

## E. Content（内容） [CODE REVIEW ONLY]

- 详情页关键入口文案存在："打开原始来源"（`uiLanguage.tsx:910/925`）、"关注此频道"（`:124`）、"原始字幕"相关文案；时间戳溯源与证据哈希展示代码存在。
- 状态文案存在："已完成""待转写""字幕不可用"等；无字幕时"不会根据缺失的结果编造摘要"的诚实反馈文案存在。
- 未验证：列表/详情的真实渲染、字幕时间戳跳转。

## F. Intelligence（洞察） [CODE REVIEW ONLY]

- "提炼为洞察"按钮文案存在（`uiLanguage.tsx`）；两种结果文案存在："已完成，未产生新洞察"（`:77`）；未配置模型时"云端洞察需要配置凭据并授权。内容整理仍可使用。"（`:55`）。
- 后端提炼链路已用自动化测试覆盖（`test_runtime_composition.py` 10 passed，含本地 transport 生产授权回归测试）—— 但这是授权逻辑测试，非端到端"点击提炼→模型执行"验证。
- 未验证：真实点击提炼、ollama 实际执行、无新洞察的 UI 展示。

## G. Topic（主题） [CODE REVIEW ONLY]

- 主题页面路由存在（`App.test.tsx` 新增测试覆盖 `#Topics` 切换到"主题"标题）；空状态文案"暂无主题。"存在（`uiLanguage.tsx:829`）。
- 主题详情依赖先有洞察；本轮无洞察数据，详情页未验证（NOT TESTED）。

## H. Settings（设置） [CODE REVIEW ONLY]

- 语言：区域标题与"编辑语言"按钮文案存在；"界面语言"/"默认输出语言"选项文案存在（`uiLanguage.tsx:611/617`）；"保存语言"按钮存在。
- 模型："模型与处理准备"（`:47`）、"云端配置与模型详情"（`:57`）分区存在；本地模型状态"已安装，可使用"（`:51`）文案存在；digest 绑定校验在后端逐次执行（`distillation.py` `available`）。
- 备份："创建备份"/"选择备份"按钮文案存在；备份范围说明"备份包含洞察核心数据和已保存设置，不包含外部资料库、凭据和模型文件。"（`:669`）与手册一致；备份被阻止提示"以下工作尚未结束，暂时无法备份："（`:161`）存在。
- 隐私："凭据值永不显示"相关文案与后端行为（`credential_status` 不返回值）一致。
- 未验证：语言切换真实生效、备份文件真实生成、恢复流程。

## 总体结论（代码审查口径）

1. 八条路径的前端入口、按钮文案、状态反馈文案在源码中**均存在且与手册描述一致**（已逐项核对 `uiLanguage.tsx` 与各组件，详见 USER_MANUAL.md 整改记录）。
2. 产品的"诚实反馈"设计在文案层得到贯彻：不可用能力（Bilibili 字幕/UP 主关注、未配置模型、备份被占用）均有明确的不可用提示文案，而非静默失败。
3. 三处 Bug 修复中，Bug2/Bug3 的后端逻辑有自动化测试实测覆盖；Bug1 的前端路由修复有新增回归测试（待 npm 环境执行），本轮未做真实浏览器前进/后退验证。
4. **本轮未发现与豆包 GUI 结论矛盾的代码证据**；但所有"界面实际可用"的结论仍以豆包轮次的真实验证记录为准，本轮不重复背书。
