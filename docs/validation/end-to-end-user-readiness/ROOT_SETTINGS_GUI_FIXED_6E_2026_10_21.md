# 固定6e用户界面实测：取消通过，恢复重建拒绝采用

固定产品源码 `6e0f59e2f40fb62d371945cac0253346aa1616ce`，独立R4 WT。生产frontend构建、真实headful macOS Chrome155/CDP9341，前端6148、隔离正常worker API6149。QA harness仅使用完整旧stock、NoCredentials和正常production factory；AppConfig在重建循环外缓存，未手改route/任务/资格。正式owner未接触，零模型加载/生成/付费调用。

## 已真实通过的界面步骤

1. 旧8b配置的完整114Evidence/2406cue Content在正文前显示实际设置指引，不创建任务；实际Settings选择固定已安装9b/运行程序0.40.6，保存并应用，服务正常重建并回读实际route。选模型不授资格，所有资格仍关闭。全部79SQL表/19DATA与设置前相等，仅机器选择文件新增。
2. 原长内容 `#Content/0eMzc-WnBfQ` 和短内容 `#Content/IwglW_hIL_g` 分别由真实提炼按钮进入WAITING_MODEL。长任务checkpoint/usage inv0、actual_model与tokens均NULL、无completion receipt，完整来源不截断。
3. 两项等待时Backup禁用。取消长任务后，反馈明确本次无洞察且原Content/字幕/摘要/Evidence保留；短任务仍阻止Backup。取消短任务后才显示核心数据就绪并开放创建。
4. 实际终止并重启本任务API进程，同一选择仍应用、任务未复活；全79SQL表、19个物理DATA文件、机器选择逐项完全相等，SQLite integrity/FK通过。
5. 实际创建备份，浏览器保存链接下载1,217,812字节ZIP；真实macOS系统文件选择器选择该ZIP，正常上传并预览，准确显示5关注/4内容/4摘要/147Evidence/0洞察/0主题/19DATA。未用路径API或模拟上传绕过文件选择。

## 新P1：确认恢复后的服务重建失败

预览→恢复此备份→输入RESTORE→确认恢复并重启，界面停在“恢复待完成；应用将重启并验证恢复的数据”，随后“未能检查备份状态”。API进程退出。真实异常：

```text
runtime_composition.py:510 recover_and_apply_pending_restore
backup_restore.py:547 _protect_background
backup_restore.py:318 admission_lock(exclusive=True)
tracked_retry_context.py:93 RetryConflict: Content retry writer or Backup is still active
BackupRestoreError: Content retry is still writing; wait before Backup or Restore.
```

独立只读诊断：ThreadingHTTPServer的daemon请求不被server_close加入等待；恢复确认后前端立即读取readiness，readiness请求会在全量校验时持machine EX。结合实际栈，此正常请求重叠是已确认的可达冲突路径；未记录故障瞬间锁持有者，不能断言该次一定是此GET。仅停止worker不足以等待HTTP请求，新factory仍可能与旧请求锁冲突。需要产品HTTP请求停止准入/排空屏障，不能用任意sleep、盲目重试或修改QA harness掩盖；外部真实锁竞争仍必须安全拒绝。

失败后只读再次快照证明79SQL表/19DATA/机器选择与恢复前完全相等，integrity ok/FK空；保留待恢复现场，不人工清journal、不冒称恢复成功。最终新源码须从完整原stock建新副本复验。

## 外部证据与本轮完整检查

根私有证据目录 `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.var/local-settings-r4/`：01–11真实截图、settings-apply.har、two-waiting-tasks.har、cancel-and-readiness.har、restart-and-native-restore-failure.har、ZIP、api-restart.log、long-wait-zero-invocation.json。`09-native-restore-picker.png`是真实系统选择器截图。

完整数据快照目录 `.var/end-to-end-user-readiness/long-wait-gui-20261021-v3/`：before-apply/after-apply、after-both-cancel、after-process-restart、before-native-restore、after-native-restore-failure。快照包含每个SQL表所有行和每个物理DATA文件hash，不能仅以页面计数替代。

作者固定76文件/2168节点：2159PASS、9FAIL、1warning，1656.10秒；495源码/前端/测试hash全程一致，完整日志及settings-affected-result.json保留。6个失败是新增服务层wrong-model guard破坏既有LOCAL等待合同；3个是native/background阻塞原因退化。独立R4另确认metadata HTTPException外溢，报告25147d4已导入root787f741。前端980、TS/build、编译/Ruff/strict119/diff曾通过，不抵消后端和真实GUI失败。

当前结论：REJECT，不接受、不整合、不发布。由唯一接任writer集中修复，完整新检查、增量独审和新固定源码真实GUI通过后再决定接受；真实模型资格及正向保存/主题等Goal验收仍待。
