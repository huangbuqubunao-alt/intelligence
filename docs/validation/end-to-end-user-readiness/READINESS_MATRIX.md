# 普通用户链路验收矩阵（候选，未发布）

2026-10-14 当前结论：**未完成，暂不交用户作为全部可用版本测试。** 正式main/真实远端仍73ee7e7，本轮未改owner数据、配置或凭据。当前审查记录c56e9ad（未完成候选）；下方历史检查点保留，不代表当前任务状态。

| 用户操作 | 当前外部证据 | 剩余门禁 |
|---|---|---|
| 首次使用及跳过后设置 | 真实macOS引导可到设置；最新ZH/EN明确安装身份≠洞察资格、Cloud可选逐次授权 | 合格能力正式配置/最终回跳采用仍待 |
| 多文件导入及过长视频 | 前轮已发布真实Native Picker/D2-01/D2-02/2GiB APFS通过；本轮实现不变，失败当时反馈可关闭、不跨页面残留 | 最终完整回归，复用未变实现证据 |
| 本地视频/音频转写与声学负控 | 普通factory隔离固定tuple PASSED，真实UI转写4cue/Summary5Evidence；17任务14正向、3静音噪声负控失败无假文本 | 正式配置另批；不保证任意录音准确率 |
| 本地转写后取消等待 | 真实WAITING_MODEL0→明确用户取消→无洞察，全部78DATA及authority保持，Backup重新ready | 新合格模型正向仍未通过 |
| 公开频道关注/暂停/恢复/自动检查 | 真正HEALTHY与后来NOT_FOUND保留；新真实关注后发布OYp5j2RihPE由following-auto持久ENROLLED/单video单link、SourceRun完成，GUI可读 | 一例真实新发现PASS；该内容TRANSCRIPT目录INVALID_RESPONSE/FAILED_FINAL，没有字幕/Summary/Evidence；当前来源NOT_FOUND风险保留 |
| 原生字幕与已有plain补全 | 同源原生VTT补全、字幕/摘要/Evidence真实可读；firstplain/winner持久capture独立接受；fresh RAW真实恢复71表4DATA精确PASS | 老DATA4→3FAIL保留；另旧失败derived归档仍OPEN |
| 旧失败请求+成功child安全归档 | Schema38第三独立ff43 APPROVE已整合74ac5c2；root176专项/静态PASS，普通Schema38真实GUI恢复72表78DATA精确PASS | 23字段保持；genuine失败derived归档真实GUI仍待网络条件，不用空表38恢复冒充；最终完整回归待 |
| 当前Content转写/深度分析读取 | 真实有限GET延迟复现假待转写/假尚未运行；作者fff9bf中性加载430全前端自测 | 047/ba524返修独立接受整合；root441/TSbuild及真实ZH/EN loading、abort禁用、GET恢复/lateID隔离PASS；旧REJECT留存 |
| 本地洞察真实资格 | 8b停止；9b nonthinking首例4语义P1 FAIL，native thinking首例4096length正文空FAIL，后3及LOCAL8未调用 | 6144原EN唯一调用完成，native stop/912输入4638输出/218.923s；协议PASS但独立fbd1035语义REJECT/P1，18DATA/输入hash不变；全部调用STOP、正式资格false |
| LOCAL TXT/MD提炼与真实字符来源 | 主体LOCAL_TEXT及可信reader补充均已获具体批准；只读设计保留码点范围/NULL时间/旧YT协议 | 核心已接受，新独立作者LOCAL_TEXT实施含具体获批read_current验证入口，等待提交与独立review；模型实际0调用 |
| 已生成洞察收藏/主题/原证据回跳 | 既有逻辑回归保留，没有合格模型正向GUI支撑 | 真正admitted Intelligence后全链路操作/恢复，不用fixture冒充 |
| 本地资料研究 | 真实已转写Content收集3Evidence/0Intelligence、回读/初次定位原文、重新收集/两版本无实质变化对比PASS；明确无模型结论 | 刷新丢Evidence定位OPEN，纳入已批LOCAL深链UI |
| 研究后的备份/恢复 | 真实创建/下载/选择ZIP/预览/RESTORE/重启；71表全部行和78DATA精确SHA6bf70daa…，当前与历史研究可读/readinessready | 不覆盖Schema38归档验收；旧恢复成功提示在新预览仍展示P2待UI最小修复 |
| 页面读失败与窄窗 | 实际自有API暂停→GET重试恢复、Source neutral loading/失败单GET重试、四宽六导航正反Tab/Enter/鼠标PASS | 最终候选复核，未知状态仍不得误放行 |
| 关注继承兴趣配置 | ExistingSourceForm失败GET/重试/草稿保护组件通过；tracked creator普通详情没有编辑入口 | 专用interest-only CAS及入口已具体获批；待LOCAL_TEXT state/App接受后串行，未实测采用 |
| 旧v1明确429取消阻塞 | 独立返修接受/真正idle worker持久终止并保留错误/history；另一WAIT0仍正确阻塞，用户取消后ready | 不扩大到当前未知/活跃执行 |
| Deep Analysis/Cloud/Bilibili | 未合格Deep保持禁用，Cloud0调用无凭据；Bilibili Creator明确不可用、公开单视频原路径保留 | 不造资格、不以付费云替代本地，不绕Cookie或安全规则 |
| 长内容/rolling字幕 | Sasha114Evidence真实422、单长cue需完整token预算准入；原生rolling重复真实可读但质量不佳 | OPEN新精确政策；不截20项/扩大窗口/改历史Evidence，未实施 |
| 最终回归/采用 | 最新已接受root frontend418/TSbuild PASS；backend4220+1既有skip只是此前检查点 | 新core/UI接受后完整backend/front/TS/build/Ruff/mypy/diff；无P0/P1、真实恢复与另批正式采用 |

![真正隔离设置：本地转写就绪](screenshots/asr-real-qualified-settings.png)
![真正本地转写完成](screenshots/asr-real-ui-complete.png)
![恢复并重启后通过数据检查](screenshots/asr-real-ui-after-restore.png)

本轮 Native Picker 不可用新的电脑控制工具，未改实现的前次真实原生选择器与2GiB APFS验收证据复用。新转写样本经普通导入API建立，再从实际UI点击转写；两者明确区分。没有通过截图或fixture宣称真实模型合格。

2026-10-13续作：ASR文案与最小CSS均独立审查整合，真实中英文反馈/Retry Tab及四窗口document几何PASS；完整backend4220 PASS/1既有skip/2warning，frontend386 PASS/TS/build。六导航完整可见键盘检查另发现部分遮挡，NARROW_WINDOW_GUI_EVIDENCE.json如实PARTIAL/FAIL，独立返修中；不能说小屏全通过。LOCAL_TIMED候选39新专项等通过独立审查中未整合，真实LOCAL新资格仍因9b原语义FAIL而BLOCKED，不复制旧YTreceipt或授普通factory权力。Schema38旧失败归档仅精确待批提案，未实施。fresh RAW GUI恢复71表/4物理DATA精确PASS不覆盖旧失败恢复OPEN。

夜间最新状态优先：键盘返修已独立整合且四宽六项正反Tab/Enter/鼠标真实PASS（新NARROW_KEYBOARD_GUI_EVIDENCE，旧FAIL留存）。LOCAL_TIMED已独立整合/root78PASS，真实Whisper视频WAIT0→取消→Backupready与全部78DATA/authority保持PASS，正向模型仍BLOCKED。Source详情中性加载/失败GET重试独立整合，406前端/TS/build以及真实1GET/0命令重放PASS，见SOURCE_DETAIL_GUI_EVIDENCE。Schema38和同固定9b新thinking模式均已获精确隔离批准，但尚未完成实现/独立验收；不能将批准当PASS。当前4220后端只是此前RAW/UI检查点，最终候选完整回归仍等待核心新变更。
