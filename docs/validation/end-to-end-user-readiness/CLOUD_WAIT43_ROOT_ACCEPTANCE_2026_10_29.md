# 云端WAIT0取消：Root工程整合与真实Mac浏览器验收

作者706b165+af71317，经同一2094414独审累计APPROVE，Root2c16c47/460f022/a8b413f整合。仅一次新增安全逻辑审查；唯一P2是云等待误指本地模型，已按真实任务provider与can_cancel证明修复，未重跑已绿629。

根因：旧037取消证明仅Ollama，BigModel合法零调用WAITING_MODEL仍永远阻塞Backup。43追加12字段不可变云取消receipt与六字段有限429观察，旧001–042不变；不删除checkpoint/usage/同意/证据，不伪造成功/0费用。可信身份、零执行、有限前置失败、budget、同意、SourceRun、并发事务和SQL护栏共同保护；未知/已执行/PENDING/RUNNING/BUDGET仍closed。429观察无权授权或改变readiness。

真实Mac headed Chrome在新公开QA副本完成：旧42两笔真实service USER_CONFIRMATION/default资格关闭/零key-wire调用WAIT0，UI不可取消→正常43迁移（81旧表仅登记改变、19DATA不变）→取消一项反馈清楚、另一项仍阻塞→正常重启前项不复活→修正cloud提示/设置深链往返内容进度保留→取消另一项ready→UI创建881824字节ZIP→同浏览器file input选择→检查预览/输入RESTORE确认→实际服务重启恢复APPLIED。83表schema及全部行、19DATA精确一致，两取消不复活，真实旧429/inv1拒绝及未知业务码保留、不允许取消或回填。选择文件通过真实浏览器input，不冒充一次新的Native Picker/APFS验收；D2实现不变，既有证据沿用。

Root整合检查：46新后端PASS/33.11s；完整前端1102PASS/42文件21.80s；TS、production build565ms、strict mypy124、compile124、Ruff、diff PASS，src/frontend/src/tests逐字等已审af71317。作者受影响14完整文件629PASS/268.99s及后增精确检查保留；独审83关键、原反证与修后精确UI/API检查见handoff。6003完整后端是更早历史，此处不宣称当前全仓6000已重跑。最终采用前仍需最终全回归及合格洞察正向。

图文手册已补本轮原始截图；三图均经目检，不改图。私有源Q= .var/end-to-end-user-readiness/cloud-wait43-gui-20261028。GUI QA服务全NoCredentials/出站拒绝/no worker；无Keychain、模型调用、正式owner/配置/凭据变更。实际模型诊断在另一个隔离副本，不把两者混为一次验收。机器证明见CLOUD_WAIT43_REAL_GUI_RESTORE_2026_10_28.json。

辅助准备错误保留：相对URI、缺自有vault目录、错误Settings深链和schema tuple/list表示，均按实际接口修正，没有放宽断言；原全部行与DATA已全等。跨用户中断后测试服务被停止，页面清楚报本地连接问题；仅重启测试服务，不重复ZIP或数据恢复。main未采用，整个Goal尚未完成。
