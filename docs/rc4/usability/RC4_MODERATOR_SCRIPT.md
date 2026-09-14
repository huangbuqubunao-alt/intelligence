# RC4 Five-Person Moderator Script

## Use of this script

Status: `BLANK PROTOCOL — NO SESSION RESULTS`.

Use the same core prompts for all five real participants. Text marked **READ
VERBATIM** is participant-facing. Text marked **MODERATOR ONLY** must not be
read unless it is a neutral follow-up. Do not expose architecture, repository
details, secret values, or prior hypotheses.

Recommended pacing is 35–50 minutes total:

- introduction and consent: 3–5 minutes;
- Tasks 1–6: 15–20 minutes;
- Tasks 7–11: 15–20 minutes;
- fixed post-session questions: 5–8 minutes.

## Before the participant joins — MODERATOR ONLY

1. Confirm build SHA
   `9d0d5425e740004f4c4c056f9a55df185bf00c00`.
2. Open the isolated participant workspace at the agreed starting state.
3. Confirm no previous participant information or private account is present.
4. Confirm prepared states are available without an uncontrolled provider call.
5. Confirm observation and result templates are blank.
6. If recording, obtain consent before recording begins.
7. Record environment transitions and fixture changes separately from observed
   behavior.

## Opening — READ VERBATIM

> 谢谢你参加这次测试。今天我们测试的是产品，不是你；没有正确或错误的答案。
> 请尽量把你的想法说出来，包括你在看什么、期待什么，以及哪里让你犹豫。我有时
> 会保持安静，让你按自己的方式完成任务，这不代表你做错了。你可以随时暂停或结束
> 测试。请不要输入任何个人信息、私人账号或真实凭据。如果界面要求这类信息，请先
> 停下来告诉我。请尽量坦率，你的困惑和批评对我们最有帮助。开始前，你有什么问题吗？

If the participant asks what the product does, say:

> 我想先听听你从界面中得到的理解；完成这一部分后我可以补充背景。

## Think-aloud reminder — READ VERBATIM

> 接下来请一边操作，一边告诉我你在想什么。遇到不确定的地方也请直接说出来。

## Task 1 — First impression

**READ VERBATIM**

> 请看一下这个产品。先不要点击，告诉我你觉得它是做什么的，以及你第一步会做什么。

**MODERATOR ONLY — observe before probing**

- Start `TIME_TO_CORE_VALUE_UNDERSTANDING` when the unobstructed product appears.
- Record the participant's value explanation and intended first action.
- Note whether they instead describe a downloader, player, chat tool, channel
  manager, developer console, or scheduler.

Neutral probe after the initial answer:

> 界面里的哪些信息让你这样理解？

Close timing when they sufficiently express that AI monitors relevant YouTube
and turns it into useful Intelligence, or mark `NOT_REACHED` when Task 1 closes.

## Task 2 — Determine readiness

**READ VERBATIM**

> 你希望这个产品开始为你分析一个 YouTube 来源。请判断现在是否已经具备所需条件。

Do not name Settings, readiness, credential, provider, model, budget, or Source
before the participant encounters them.

After the participant states a conclusion, ask these neutral questions:

> 你为什么认为现在可以，或者不可以开始？

> 如果不能开始，你认为下一步该做什么？

**MODERATOR ONLY**

Record whether the participant finds and distinguishes application connection,
Video Distillation/provider availability, credential availability, usage limit,
and Source readiness. Record technical terms they repeat without understanding.
Use the preassigned controlled-state order; do not add a blocker because of the
participant's response.

## Task 3 — Add first Source

**READ VERBATIM**

> 请选择一个你可能愿意持续关注的 YouTube 来源，把它添加到产品中。

If personal choice would expose data, add:

> 请使用我提供的安全测试来源，不要使用你的私人账号或私人内容。

Do not explain fields or recommended values. Start `TIME_TO_FIRST_SOURCE` at the
prompt and stop when the product confirms the Source was saved.

**MODERATOR ONLY**

Record completion, hesitation, fields read or ignored, whether every field seems
mandatory, searches for defaults/recommendations, and anxiety or confidence.
Do not ask whether progressive disclosure would help.

### Controlled validation subtask

After the first Source attempt is closed, provide the prepared malformed safe
test Source value. Do not say which field is wrong or how to fix it.

**READ VERBATIM**

> 这是另一个安全测试来源。请尝试把它添加到产品中，并根据产品提供的信息处理过程
> 中遇到的问题。

**MODERATOR ONLY**

Record whether the participant identifies the affected field, understands the
message, and corrects the value using the paired safe corrected Source. Do not
ask whether field-level validation should be redesigned. After the task closes,
tell the participant that the malformed value was intentionally prepared for
the study.

## Task 4 — Configuration comprehension

Ask only after the participant has naturally encountered the configuration.

**READ VERBATIM**

> 你觉得 Initial History 会改变什么？

> 你觉得 Per-run Limit 会改变什么？它们有什么区别？

> 你觉得 Focus 和 Ignore 分别会做什么？

> 你觉得 Distillation Style 会改变什么？

**MODERATOR ONLY**

For each concept code `CORRECT / PARTIAL / WRONG_MENTAL_MODEL /
CANNOT_EXPLAIN` and capture the words that support the code. Do not correct
answers until the task is closed.

## Keyboard-only overlay — at least two preselected participants

**READ VERBATIM**

> 接下来这一小段请不要使用鼠标或触控板。请只用键盘打开这个 Source 的编辑配置，
> 浏览控件，关闭它，再重新打开并完成一个不会破坏数据的小修改。

**MODERATOR ONLY**

Observe opening, initial focus, Tab, Shift+Tab, inability to move into background
controls, Escape, focus restoration, reopening, editing, and keyboard submit.
Do not coach key order. This is bounded Source-flow evidence, not accessibility
certification.

## Task 5 — Check Now

**READ VERBATIM**

> 现在你希望系统立刻检查一次这个来源。请自己完成。

Before they activate an action, ask:

> 你预计执行这个操作后会发生什么？

**MODERATOR ONLY**

Record whether they expect one video, all videos, new videos, historical videos,
a page refresh, or an immediate AI answer. After activation, remain silent long
enough to observe whether they understand acceptance, current state, and what
they can do while waiting.

Then ask:

> 现在发生了什么？你接下来会做什么？

## Task 6 — Leave and return

Once the run is active, ask the participant to navigate elsewhere without
naming a destination. Continue with a short unrelated browsing action, then say:

**READ VERBATIM**

> 你刚才启动的检查现在怎么样了？

**MODERATOR ONLY**

Do not point to Source Detail. Record whether they find the latest run, explain
its current or terminal status, and identify any required action. Record if they
rely on memory rather than durable UI evidence.

If the environment moves from active to terminal using a prepared state, record
the transition as a moderator environment event and do not imply that the
participant caused it.

Then present the prepared terminal state with no important new result and ask:

> 这次检查发生了什么？你认为它成功了、失败了，还是其他情况？

Record whether the participant understands that completed with no important new
result is distinct from failure. Do not explain the distinction until this
subtask is closed.

## Task 7 — Read Intelligence

Present the prepared state containing produced Intelligence.

**READ VERBATIM**

> 请告诉我，这条内容最重要的信息是什么？

> 为什么这对你有价值？

> 这里哪些是事实，哪些可能只是观点或判断？

**MODERATOR ONLY**

Observe use of Conclusion, Why this matters, What's new, details, claim kind,
state, and information density. Record whether the participant treats
Intelligence as product output or merely as a processed video card.

## Task 8 — Verify a claim

**READ VERBATIM**

> 假设这里有一条信息对你的工作很重要，你想确认它不是 AI 编的。你会怎么验证？

Do not mention Evidence, Source, Video, timestamp, excerpt, or Open Source until
the participant ends their attempt.

If they stop without succeeding, ask once:

> 你还会去哪里找支持这条信息的依据？

**MODERATOR ONLY**

Success requires reaching original-source evidence and explaining the
relationship among the claim, excerpt or timestamp, video, and Source. Technical
provenance terminology is not required.

## Task 9 — Needs Attention

Every participant receives both controlled parts. Rotate the actionable blocker
according to the preassigned order.

### Part A — actionable blocker

Present credential missing or budget blocked.

**READ VERBATIM**

> 系统现在不能继续。你会怎么办？

**MODERATOR ONLY**

Observe whether the participant identifies what happened, why it matters, the
safe action, and what the product will not do automatically. Do not teach the
recovery path.

### Part B — external result unconfirmed

Present AMBIGUOUS.

**READ VERBATIM**

> 你看到这个状态后会怎么处理？

Then ask:

> 你认为系统接下来会自动做什么，或者不会做什么？

**MODERATOR ONLY — critical safety observation**

Record whether the participant expects Retry, Resume, waiting, a distinct new
future action, or settings/contact support. The participant must not be led to
retry the protected execution. If the UI exposes or dispatches such a retry,
stop this scenario and record `POTENTIAL_P0`.

## Task 10 — Return to Dashboard

Present the representative Dashboard with multiple Intelligence cards, Topic
change, Weekly, and appropriate blocking or non-blocking Attention.

**READ VERBATIM**

> 如果你几天没打开这个产品，现在回来，你先看哪里？为什么？

**MODERATOR ONLY**

Record first fixation, first click, scrolling, missed Attention, perceived card
dominance, Weekly discovery, and whether the participant can explain what
changed. Do not ask whether Needs Attention should move or whether the Dashboard
is too long.

## Task 11 — Resource Usage

**READ VERBATIM**

> 如果你想知道这个产品用了多少模型资源或者可能产生多少成本，你会去哪里看？

After they reach or abandon the relevant view, ask:

> 如果这里显示 cost unknown，你觉得是什么意思？

**MODERATOR ONLY**

Record discoverability and understanding of calls, tokens, provider/model, and
unknown cost. Code the interpretation: `FREE / ZERO / NOT_CHARGED /
NOT_MEASURABLE / NOT_YET_AVAILABLE / OTHER`. Ask for explanation; do not correct
until the task closes.

## Fixed post-session questions — READ VERBATIM

Ask all ten, in this order, after tasks are closed:

1. 如果你用一句话介绍这个产品，你会怎么说？
2. 刚才最让你困惑的三个地方是什么？
3. 有没有哪个设置你不知道为什么需要？
4. 你什么时候会相信一条 Intelligence？
5. 如果系统几天自动运行，你回来最想先看到什么？
6. 有没有哪个页面的信息太多？
7. 有没有哪个重要信息你找不到？
8. 如果今天让你自己使用，你觉得还需要别人教你什么？
9. 哪些功能你会真的用？
10. 哪些东西你觉得可以删掉或先隐藏？

## Neutral intervention ladder — MODERATOR ONLY

Use the smallest intervention needed and record each substantive intervention:

1. **Silence:** allow time to inspect and think.
2. **Think-aloud reminder:** “请告诉我你现在在想什么。”
3. **Restate goal:** repeat the original task without naming a control.
4. **General continuation:** “如果这是你自己使用，你接下来会尝试什么？”
5. **Close as failed/partial:** record the result before teaching enough context
   to continue subsequent tasks.

Never say “click,” “go to Settings,” “look at Needs Attention,” “open Evidence,”
or name the expected solution while the task is active.

## Safety stop script

If a stop condition appears, say:

> 我们先停止这个场景。你没有做错任何事情；我需要记录产品当前的行为。我们不会
> 在这次测试里继续这个操作。

Then stop interaction, preserve only non-sensitive evidence, mark
`POTENTIAL_P0`, and notify the Product Owner. Do not reproduce, fix, retry, or
continue the unsafe path.

## Closing — READ VERBATIM

> 谢谢。今天的反馈会和另外四位真实参与者的观察一起分析。我们不会把你的回答当作
> 所有用户的统计结论，也不会在研究完成前假定某个设计一定需要改变。你还有什么想
> 补充的吗？

After the participant leaves, complete the observation and session-result
templates while memory is fresh. Do not add words the participant did not say.
