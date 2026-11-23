# 内部运营与发布资产储备库（Internal Ops & Growth Assets — Drafts Only）

> **⚠️ 阶段冻结声明（Section 二 红线）**：本文档中的全部文案、教程、落地页结构与渠道分发计划均为 **内部自主迭代阶段储备资产（Internal Drafts Only）**。在创始人未正式下达进入“真实用户验证/公开推广”阶段指令之前，**严禁向外部社群、真实用户私信、GitHub Discussions 或媒体渠道发送任何内容**。

---

## 一、产品核心定位文案（已对照源码实现，绝不夸大）

### 一句话版本（中文）
> **把 YouTube 英文原讲、B 站中文拆解和你的本地 Markdown 笔记放在一台电脑里互相对照——每句结论都有点击可核查的时间轴原话，缺证据直接诚实拒答，研究完连同跳转链接带回 Obsidian。**

### One-Liner（English · GitHub / HN）
> **Local-first, fail-closed bilingual research workbench: cross-check YouTube talks, Bilibili videos, and local Markdown notes under one SQLite evidence ledger, refuse unsupported claims cleanly, and export portable Obsidian notes with timestamp deep links.**

### 三条刚性事实背书（不允许写成“永久全自动万能”）
1. **本地优先与零静默花费**：默认运行本机免费 Ollama（如 `qwen3.5:9b`）或仅在显式保存 Key 后按日上限调用自带云端 API（Keychain 隔离），后台任务严格禁止发起付费云请求。
2. **Fail-Closed 透明拒答**：所有核心结论引用由后端真实字幕切片或段落字节偏移 `TEXT_RANGE` 签发，无证据支点直接标记 `REFUSED_INSUFFICIENT_EVIDENCE`，把相似片段隔离放在“仅供参考”区。
3. **带走即用的普通文件**：导出到 Obsidian 的 `.md` 与 `.zip` 包内含可点击 `https://...?t=` 原片时间戳链接、段落范围与 `ev:` 出处指纹，脱离本应用仍可持续验证。

---

## 二、用户引导教程：5 分钟本地体验脚本（待授权对外时随附）

1. **启动工作台（单命令免手动改配置）**
   ```bash
   git clone https://github.com/huangbuqubunao-alt/intelligence.git && cd intelligence
   cd frontend && npm ci && npm run build && cd ..
   uv sync --dev
   uv run youtube-intel start --check-only   # 先检查 Ollama / yt-dlp / ffmpeg 就绪状态
   uv run youtube-intel start                # 打开 http://127.0.0.1:8765/
   ```
   *(若仅先快速看交互而不导入私库：`uv run youtube-intel demo` 启动隔离离线样例展示，支持对抗拒答核验)*
2. **放入 2 份异构资料（2 分钟）**
   - 点右上或侧边栏 `+ 导入`：贴入 1 个公开带字幕 B 站 `BV` 或 YouTube 链接；
   - 再切换「本地文件」→ 若从命令行在 macOS 浏览器访问，点击「使用浏览器本地上传（`.md / .txt / 音视频`）」选中自己的一份研究 `.md` 笔记确认导入（HTTP `201`，数据仅留本机）。
3. **验证一次“有依据作答” + 一次“有理由拒答”（2 分钟）**
   - 进入 `AI 跨视频问答` 提出核心分歧问题，点开引用旁的 `原片 01:15 ↗` 或段落位置核对；
   - 故意提出资料库绝未提及的领域外诡计问题（例如虚构物理实验数值或未发表财务数字），确认应用显式返回 `证据不足 · 已诚实拒答` 且引用条数为 `0`。
4. **带走研究成果（1 分钟）**
   - 点 `下载 .md` 或 `设置 → 导出 Obsidian 知识库包 (.zip)`，在任意 Markdown 编辑器里点击外链跳转核对原片对应秒数。

---

## 三、常见问题 FAQ（诚实披露能力边界）

- **Q1：没有英伟达显卡或不想买 API Key 能跑吗？**
  可以。`8GB–16GB` 内存的 Apple Silicon Mac 或常规电脑搭配本机 Ollama（`qwen3.5:9b`）即可完全 `$0` 本地跑通总结、打分与跨源问答（不触发任何付费云调用）。若电脑配置有限，也可在设置里显式填入 DeepSeek / Kimi / 智谱 / OpenAI 自带 Key 并设每日调用上限。
- **Q2：遇到没有官方字幕的 YouTube 或 B 站视频怎么办？**
  系统**不会偷跑黑盒语音转写或在缺字情况下编造摘要**。无字幕视频会明确标示为 `仅元信息`；若你在 Apple Silicon Mac 上有音频/视频原文件，可在配置好本地 `mac-whisper` 后本地离线转写，或者直接导入手头已有的 `.txt` / `.md` 文字整理稿（同样支持严谨 `TEXT_RANGE` 溯源）。
- **Q3：支持 Windows 原生运行吗？**
  支持通过 **Windows WSL2 (Ubuntu)** 按 POSIX 环境完整运行；原生 Windows 因缺少 `fcntl` 文件锁，启动时会直接报错拦截并引导切换 WSL2。
- **Q4：我的笔记和 API Key 安全吗？会上传分析统计吗？**
  全系统严格 Zero-Telemetry。所有材料保存在本地工作区 SQLite；BYOK 密钥存入系统钥匙串且永不随 `.zip` 备份或 `.json` 恢复快照导出。

---

## 四、落地页（Landing Page）内容框架草稿

- **Hero 主标题**：把跨平台视频和笔记里的判断，核回原话再带进 Obsidian
- **副标题**：面向中文双语研究者与深度创作者的本地优先 AI 研究工作台——YouTube + B 站 + 本地 Markdown 同场比对，缺证据诚实拒答，零云端数据锁死。
- **主 CTA**：`5 分钟本地运行（Apache-2.0 开源）` / `查看离线 Demo 说明`（均待授权公开宣传时启用，当前不上线外部落地页）
- **三段式视觉模块（对应真实能力，禁止虚构数字徽章）**：
  1. **对比验证**：左右并列视频时间轴切片与本地 Markdown 段落定位；
  2. **透明拒答**：真实展示“证据不足 · 已诚实拒答”与分离“相关片段”防幻觉机制；
  3. **知识主权**：一键导出通用 `.md` 与 Obsidian `[[wikilinks]]` 知识包。

---

## 五、未来渠道投放储备草稿（Strictly Frozen — 待未来阶段解锁后由创始人审发）

| 拟选渠道 | 切入重点与标题方向（仅内部存稿） | 发布时机（必须等创始人授权） |
|---|---|---|
| **V2EX / 少数派 / Obsidian 中文社区** | 《做了一个专治大模型幻觉与笔记割裂的本地研究工具：YouTube + B 站 + Markdown 同库对照、敢拒答、能直接导进 Obsidian》 | 完成真人内测验证 `W1 >=30%` 且冷启动卡点修清后 |
| **B 站技术/工具向演示短片（2–3 分钟真机一镜到底）** | 全程录屏本机 `$0` Ollama 对一对真实中英长视频抓分歧 + 故意问假问题触发诚实拒答 + 导进 Obsidian 点开跳转外链 | 同上（避免未打磨先曝光流量浪费） |
| **GitHub Showcase / Show HN / `r/LocalLLaMA` & `r/ObsidianMD`** | *Show HN: Local-first bilingual video & Markdown research bench with fail-closed citations and Obsidian deep-link export (Apache-2.0)* | 双语 README、英文 Demo 录屏与跨平台安装说明就绪后 |
