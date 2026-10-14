# 原生字幕目录有界扫描 v2：必要隔离整改

2026-10-15；用户持续默认授权，先隔离实现/独立验收，不改变正式数据/配置/依赖。固定yt-dlp2026.07.04。真正OYp5j2RihPE单metadata读取4.124s：23086raw=301native+22785tlang，原生支持129，目录canonical UTF8 10966987B、估算Python对象14273551B。原raw4096关闭了合法目录；不是native1024太小。原FAIL和单次hash证据保留，统计不是字幕正文成功。0body/model/credentials。

已装官方skip=['translated_subs']只影响manual，automatic循环不读flag；源码AST8场景无网络证明，现默认False本已关闭manual翻译。不能把无效flag当修复，不修改yt-dlp代码或升级依赖。

v2明确调整总raw策略4096→32768（实测1.42倍余量），同时新增完整目录16MiB UTF8结构字节、映射5秒monotonic deadline、depth8/累计节点524288硬限；manual+automatic共享同budget。现native支持1024/buckets512及所有lang/ext/name/url/HTTPS/host/no-userinfo/no-fragment安全验证保持；tlang必须完成原安全检查才排除，native candidate内存≤1024，provider_position/选择身份/请求次数不改。新32k不是原4k不变，旧4097政策测试须明确升级为32769负控并保留新4097兼容正控及原历史红证据；其它安全断言不得削弱。总量耗尽整目录reject，无partial/slice/成功Artifact。

先有界遍历计费，不能json.dumps整个不可信对象后检查。未知字段也入完整预算，未知非JSON/循环/过深拒绝，防隐藏巨字段；标点/键/字符串与多字节预算边界准确。预算仅限制Adapter后置扫描/复制/retention，不声称限制yt-dlp预解析峰值；实测上游约14.27MB，socket_timeout30及现网络边界不改。新字节/节点/时间防护比旧只按4k计数更直接限制资源，仍由独立安全Reviewer验证。

精确允许providers/subtitles.py私有budget/mapping/enumeration、既有subtitle_limits/provider unit与必要native capture integration测试、任务/handoff/docs。无state/Schema/App/Cloud/model/正式配置/依赖/其他source metadata改变。先TDD 23086合成结构（明确fixture，不冒真实signed replay）、32768/32769跨两来源、16MiB/UTF8/unknown巨字段/depth/cycle/node/5s边界、恶意translated在4096后仍拒、native1025/buckets513、全既有请求次数/位置/normalization/integrity/零partial测试；Ruff/mypy/相关全tests/diff。

作者STOP→独立APPROVE→root整合后，单个private VIDEO_URL普通UI一次retry/import，真实字幕→Summary→Evidence→Backup验证。若body429/未知/新硬上限失败，保留并停止重复网络；另行用记录事实继续必要不同修复。旧tracked FAILED_FINAL没retry是独立生命周期，不能在此借capacity复活。此方案不放模型资格、不重置正式或删历史。
