# 独立终端验收窗口

这一步用于解除Codex前台占用带来的内存阻塞，验证已安装官方9B文本模型的固定单例。它不是产品发布，也不代表模型合格。原输入、证据、采样、300秒生成上限、7,776,604,301B内存和10GiB磁盘门均保持；仅更新当前隔离服务归属与外部等待入口。

在主控确认“独立验收窗口已打开”后：

1. 确认Terminal窗口正在显示“等待您手动退出Codex/ChatGPT”。
2. 用⌘Q退出Codex/ChatGPT应用；保留Terminal与Jimmm。只关闭聊天或最小化窗口不足以释放应用占用。
3. 等Terminal提示“诊断窗口已停止。请重新打开Codex，独立审查结果”。等待期间不要重开Codex或重复打开验收入口。
4. 重新打开本对话，发送“读取独立验收结果继续”。主控先查实际marker/raw/cleanup，不能重新调用模型。

没有命令需要用户输入，也不需要修改模型或正式配置。程序不会关闭任何应用；只在Codex主进程已退出且原资源门满足时，调用一次原固定验收。重复打开不会重复执行。等待最多30分钟；子任务有原生成截止和总时限，失败不重试。所有结果仍需独立内容审查；模型返回JSON或终端结束不表示通过。正式数据库、资格、main与产品版本均不由此入口改动，没有付费云调用。

若终端报错、资源仍不足或未知状态，保留窗口与记录并重新打开Codex，不自行重启验收。主控必须读取已有证据并保持fail-closed。

## 留给接续Agent的固定位置

- 控制器与测试：`/Users/developer/Documents/yia-worktrees/readiness-q4-standalone-window/.var/q4-standalone-window/`，作者提交64065313dcd8e83dd2e40352188f60ae208669fa。
- 控制器启动记录：同目录`launch-start.json`；结果目录`run-20261025/`（wait-observations.jsonl、child-stdout.log、child-stderr.log、controller-result.json、可选cleanup-slots.json）。
- 唯一实际模型输出：`/Users/developer/Documents/yia-worktrees/readiness-q4km-text-diagnostic/.var/model-diagnostic-q4km-text/real-once-terminal-window-20261025/`；全局`generation-start.json`在其父目录。先查它们，严禁重复生成。
- 未改动实际执行harness：同父目录`diagnostic.py`，SHAd510aef83346bf1706f69a14fc7e9e10148d2e0614591f6b333c24a28f91e1ef。
- 新固定包：root`.var/end-to-end-user-readiness/qwen35-9b-text-q4km-20261025/diagnostic-freeze-q4km-text-terminal-v2.json`，SHA4c324a55fae37bac56f54c778e75be9b4492f0d1cf97080a9d6cd5a79dd99a92。
- Terminal元数据/进程归属：上述Q4root`terminal-window-20261025/`。旧3a107…包、旧资源拒绝、全部旧模型FAIL/raw和marker保留。
- 终止后先独立检查原source-case expectation与精确两Evidence、归因/猜测/比较/验证边界。任何语义或引用错误停止；成功也仅诊断PASS，不能自动颁资格、执行后续案例或合main。必须继续原范围完整资格和真实用户正向链路。

本文件为操作说明；实际启动以独立复核通过的包、控制器与具体launcher哈希及当前Terminal进程归属为准。产品源码仍与a2076db、完整后端6003/前端1026的已验收实现一致；没有另启开发阶段。
