# 智谱首个真实公开诊断：工程完成，语义不合格

仅一次实际请求，随后停止；没有后续样例、重试、输出修补或资格授予。正式main仍为73ee7e747b4461b9de8a201d6b47669eb3913d1a，未发布。用户已自行注册且未充值，并在隔离页保存密钥；本次只发送预先审核的公开视频内容及合成兴趣，不含个人资料。

## 固定范围与独立预审

作者14565034+测试自足性修复7e7d4d6d；独审原4ce8728 REJECT保留，修复后4292cac16e07ba46fa2c87c6ecd20c6af84e766e明确APPROVE_ONE_PUBLIC_DIAGNOSTIC。Root核对实际已提交报告后接受，并整合52489c3/7b94c12/6510fe5。具体prepared SHA `d31ae035ab3f8f7b012e48eb35e8d780a63a7d4455a994f9d64a04960e4dcd14`，脚本、公开输入、请求与原oracle未变。

诊断为real-deepthink-en，公开视频QoXRfTb7ves，18条真实字幕、全部2条canonical Evidence、英文输出。投影4224B/真实wire4132B；semantic hash `4d4b30739519803c87fecd23b991b3f221a508512ecf2f63520f45c617c0150e`。使用固定glm-4.7-flash thinking JSON profile，16384输出上限、300秒、零重试。外部O_EXCL/fsync一次标记在dispatch前落盘且不随数据库恢复；未删除或重置。

Oct28官方快照只对该精确型号标价免费；账号权益、最终实际账单仍未知，不能据此证明永久免费或零账单。不使用付费变体或自动回退。[官方定价](https://www.bigmodel.cn/pricing)。真实密钥只在执行进程由既有固定QA Keychain读取，没有进入聊天、argv、env、SQL、DATA或报告。

## 实际结果与质量边界

实际执行成功返回一次HTTP200，持久化工程状态SUCCEEDED、invocation_count=1；provider/model为zhipu_bigmodel/glm-4.7-flash，耗时56196ms。服务方报告input_tokens=1120/output_tokens=2927，cost_microunits=null；实际账单UNKNOWN。见不可改写的[原始公开结果](BIGMODEL_PUBLIC_FIRST_CASE_REAL_RESULT_2026_10_28.json)，SHA `6fba749db539fffdc0dc12586289b979cf63ad229b02e1425e2b7bd8093311dd`。该文件的NOT_REVIEWED是执行当时值，不能用来覆盖后续独立语义结论。

Root读到明显失真后立即停止。独立语义复核f329e218（Root整合0553f99）正式REJECT/FAIL_STOP，2P1/2P2：把受访者暂定的证明经验提升为确定已解决；把maybe3/20or100的估计写为数量区间及数量级比较；额外加入数十年前、混淆产品用户与公开受访者角色。双Evidence ID及时间范围确实匹配，但不能支持放大的断言。输出保留了similar与towards的措辞，因此不额外指控它声称两个模式完全相同或已经实现人类智能。正式结论见独立[语义报告](../../../handoffs/REVIEW-READINESS-BIGMODEL-PUBLIC-FIRST-CASE-SEMANTIC.md)。

结构化结果通过不等于质量通过；本例不能建立合格的超Summary洞察路径。不得把已入库的隔离诊断卡当作生产合格证明；保留原记录和错误证据，不改写原文制造成功。模型资格与正常预算继续关闭。

## 真实备份恢复与持久化

针对真实请求后的独立case数据库执行Backup→下载→stage→confirm→recover，未再访问key或网络。恢复前后全部81张表每行/Schema与19个DATA逐字相同，工程SUCCEEDED及单次调用记录仍在，一次标记和原结果hash完全相同，readiness前后均true/reasons空。实际ZIP880026B，SHA `e66852dc511d5fdcbe069d3ab12bea49b05a0ef49975a750ec10ac27f2ceb6da`；restore APPLIED，完成于2026-10-28T00:13:03Z。见[完整核对记录](BIGMODEL_PUBLIC_FIRST_CASE_REAL_BACKUP_2026_10_28.json)。这是隔离服务层真实恢复，不冒充普通用户GUI或正式数据验收；没有再次execute来“验证”幂等。

## 工程检查及剩余范围

Root整合后124文件内存编译、strict mypy123、Ruff和diff检查通过；3个完整相关测试文件107PASS58.77s。作者干净导出107PASS58.87s、独审干净导出107PASS59.28s为分别独立的证据，不相加为覆盖量。初次绝对临时目录依赖和SQL dump遗漏user_version42的失败均保留；修复没有跳过或削弱断言。当前不是全后端最终回归；前端沿用未变源码的1084PASS/TS/build证明。

后续仅先做零调用诊断，区分模型能力与通用指令的来源归属、模态、数字及用户角色约束缺口，选最小必要路线；不重复本例、不批量试模型、不大规模重开发。免费可用路径、完整资格矩阵、普通Content→洞察→保存/主题/Evidence、当前完整回归及main安全采用仍未完成。付费路径未经授权不调用，本地未合格洞察模型保持关闭。整个Goal尚未达成。
