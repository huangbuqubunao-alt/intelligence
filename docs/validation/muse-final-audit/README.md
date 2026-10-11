# 审核交付入口

最终结论在 [REPORT.md](REPORT.md)，逐项来源与裁决在 [ADOPTION_MATRIX.md](ADOPTION_MATRIX.md)。普通用户入口是 [中文图文手册](USER_MANUAL.html)，Markdown 源为 [USER_MANUAL.md](USER_MANUAL.md)。历史报告和图片保持原字节，不能把其中已拒绝的能力承诺当成当前产品说明。

产品代码固定于 `fad9eaead4036eb39013a5d5fba3e53f14ecbd43`。全部回归/JUnit位于 checks；raw日志在审核工作树 `.var/muse-final-audit/`，只为发布副本规范化尾部空白，原失败仍保留，hash见 manifest。artifact-manifest排除自身，固定其他已发布文件内容；final-head回执在提交后写入 `.var`，避免提交哈希自指。

## 本轮可重现环境

- macOS、已有 main venv / frontend node_modules、Google Chrome、System Events权限、既有 ffmpeg及本地Ollama身份检查。没有安装新依赖。
- 审核 `.venv` 链接现有解释器。frontend/node_modules的临时链接在验收退出时移除；要重跑需要在这个独立工作树重新链接已安装依赖，不改变 lockfile。
- 只使用 `.var/muse-final-audit/gui` 的新配置、state.sqlite3、DATA、fixtures和独立browser Profiles；所有harness都只指向5688/5689。不得改为owner数据。配置取公开settings.example.yaml，把外部vault指向隔离fixture，禁用placeholder频道，不配置云凭据。
- API入口 `PYTHONPATH=src:. .venv/bin/python -m youtube_intel --project-root .var/muse-final-audit/gui serve-api --database .var/muse-final-audit/gui/state.sqlite3 --port 5689 --native-import-origin http://127.0.0.1:5688 --native-import-origin http://localhost:5688 --native-picker-executable <审核根内prepare_native_picker构建的App可执行文件>`。
- frontend以 `YIA_API_BASE=http://127.0.0.1:5689` 运行既有Vite入口，host127.0.0.1/port5688/strictPort。启动入口不代替生产launcher验收；UI恢复确认后本轮手动重启自己API进程。
- 从审核根执行 `node docs/validation/muse-final-audit/harness/gui-native.mjs` 等；AppKit选文件由真实System Events完成，不是fake_picker。gui-media是未通过的自动选择尝试，不能算APFS验收；重跑需人工确认真实文件选择，不能把diagnostic变成PASS。first-open应使用全新Profile。
- gui-settings创建/恢复隔离备份；gui-youtube联网添加公开视频及频道；gui-completion暂停/恢复、查看Content、尝试可选提炼并验证等待阻挡。无付费请求，cloud凭据不可用。harness是审核脚本，不是产品代码或CI。
- `python3 docs/validation/muse-final-audit/harness/build_manual.py` 生成HTML。复用了原豆包CSS/table renderer，修正figure、列表及中文锚点；未改原始renderer。

## 证据边界

真实本地TXT选择、YouTube、路由、中英文、备份恢复与等待阻挡通过。真实合格模型no-new生成、非空Topic、完整ASR和fresh媒体APFS未通过本轮新增验收。既有正式D2-02的真实2GiB/APFS证据仅在核心代码逐文件hash相同且回归通过时复用。报告不以截图或合成fixture冒充模型资格。
