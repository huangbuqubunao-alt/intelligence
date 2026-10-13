# TASK-READINESS-SOURCE-DETAIL-LOADING

2026-10-13，READY。Root主控；Implementer /root/intel_bounded_review（本任务角色切换，非审自己的变更）；Reviewer /root/caption_resume（其独立迁移任务结束后只读审查）。最新基线为本任务卡提交。

真实普通入口：5898 Following→Google for Developers行按钮→SourceDetail→CreatorFollowingDetail。fetch pending时瞬间显示“UP主关注／UP主持续关注当前暂不可用”，然后正确Google YouTube详情；没有source却用 source?.provider!==YOUTUBE 与全局Bilibili withdrawn 判off造成错误。现unknown标题也猜Bilibili。加载/失败不能先给其他provider能力结论。

目标：来源身份未取得或切换ID时显示中性加载，不冒充YouTube/Bilibili或给错误withdrawn结论；身份取得后保留真正Bilibili能力拒绝和YouTube原行为。详情GET失败提供明确GET重试，已有内容/来源状态不改写、不重放PATCH/check。用户关闭不再更新已卸载组件。

允许最小frontend/src/workspace/CreatorFollowing.tsx、uiLanguage.tsx仅必要新文案、相应focused tests、本task/handoff。不改App/sidebar/路由/API/backend/权限/capability判定/真实生产配置/model/依赖。不要把未知当available；fetch未完成时禁止依赖unknown source的操作。旧身份不得在新ID下显示/提交命令，错误保留到明确成功。

Reuse DIRECT已有api/React effect-dispose/状态、Error/Retry样式/国际化字典；REFERENCE DESIGN.md和既有page-read-recovery。新增文案先复用既有中性Following/LoadingSource/Retry，不能更改后端能力政策。

TDD：真实deferred GET baseline错误provider通知/ID切换旧身份；初读failure→明确Retry只GET→恢复正确provider；polling暂时GET失败保留既有身份并提供恢复，不重发check/PATCH；真正Bilibiliwithdrawn继续禁check/新follow，YouTube即使Bilibiliwithdrawn不受影响；close/dispose延迟响应无更新。frontend full389+、focused、TS/build/diff；不得weakentest/skip/改scripts。Root真GUI可用浏览器route仅隔离GET延迟/abort诱发故障，不造模型资格或后端数据。

提交通用有界SHA/handoff后STOP待独立审查。本任务ordinary UI恢复无需新敏感批准。可并行：caption在独立tree做已获批subtitle migration后端，无product重叠；本任务写完后intel可切换独立review其migration，caption只review本UI，不审自己。
