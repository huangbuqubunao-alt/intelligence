# 普通用户完整流程整改

用户授权：2026-10-12 截图反馈，修复跨页历史导入通知、解释并引导转写配置，并从普通用户视角跑通前端完整流程。
基线 main/origin/main：fa906148aef506bb19ae7036d2309f3cdd7b47ca。
工作树：user-journey-remediation；分支 codex/task-user-journey-remediation。

完成标准：所有现有产品入口按用户操作验证；成功可达，失败可恢复/取消/退出，阻塞说明真实条件与下一步。前端完整测试、类型检查、构建和相关后端契约检查通过；真实 macOS UI 验证及截图可复查。不得把接口 stub 或 fixture 成功写成真实模型/云/网络能力。

修复范围：NativeLocalImport、LocalTranscription、Settings、Onboarding、App 导航、双语文案及相应用例。沿用 DESIGN.md；不改变模型资格、云授权、预算、数据库 Schema、数据历史或依赖。

复用：DIRECT React/现有 API/SQLite/原生 AppKit Picker/既有转写 model+refresh 端点；ADAPT 现有转写能力诊断为普通用户设置引导；REJECT 历史终态任务全局永久提示、删历史、配置即授予资格、自动云回退。

真实状态：正式 capability 为 MODEL_MISSING、runtime_available=true、media_tools_available=true、production_eligible=false。此前已测 acoustic candidate FAILED；设置目录只触发能力与资格检查，不授予资格。隔离服务禁止访问凭据、付费模型及真实 Vault。

用例矩阵（每项记录 PASS / 真实阻塞与下一步 / 尚未验证）：
1. 首次使用：三步、返回、跳过、配置入口、刷新、已有资料库。
2. 导入：原生选择/取消、TXT/MD、音视频、混合有效无效批次、超两小时、格式/空文件、重复、后台、终态关闭、跨页/刷新不重放、持续任务保留。
3. 转写：缺模型、运行时/工具不足、目录无效、保存并检查、未测试/失败/过期、等待与繁忙、完成/中断/重试（fixture 契约与真实能力明确分开）；内容与设置往返。
4. 关注：添加视频/频道、无效/离线错误重试、暂停/恢复、立即检查、策略保存、Bilibili 能力提示。
5. 内容：列表/筛选/空态、详情/深链接/后退刷新、字幕/摘要/Evidence、缺字幕及重试、提炼等待/取消、不可用 Deep Analysis。
6. 洞察/主题/Research：空态、保存/取消保存/反馈、来源回跳、主题创建/关注与取消、Research 内容选择/问题/验证/无命中/历史/比较。
7. 设置：界面/输出语言编辑保存与取消、兴趣规则、候选模型与云凭据纯离线契约、转写引导、诊断可读、数据隐私。
8. Backup/Restore：真实 readiness、其他任务阻塞、创建下载、无效备份、确认取消、有效恢复+重启、已取消任务与数据一致。
9. 全局：六导航、dialog 关闭/键盘、错误加载重试、中文/英文、320/768/1024/1440、console/network、API 重启。

所有测试使用独立 DB/DATA/config/Vault。正式数据仅只读诊断，不用于导入、重置或恢复。验收完成前不将候选当成正式完成。
