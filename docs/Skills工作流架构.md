# Skills 工作流架构

更新时间：2026-06-08

AI Video Maker 的产品定位不是“让用户学习一堆 CLI 命令”，而是“用户提出视频需求，AI 通过 skills 串联完整制作流程”。

CLI、pipeline、run harness、capability adapter 都是执行底座。用户入口应该是 skill。

## 1. 架构目标

```text
用户一句需求
-> orchestrator skill 理解和追问
-> 子 skill 拆解任务
-> gate 确认
-> harness 执行可复现步骤
-> adapter 调用浏览器/桌面/API
-> 产出视频包
-> gate 确认后上传或发布
```

设计目标：

- 用户只需要调用 skill，不需要先理解 CLI。
- 每个 skill 是一个明确 workflow。
- 每个 workflow 都有输入、输出、gate 和交接契约。
- Orchestrator 每一步都要告诉用户当前完成了什么、需要检阅什么、下一步建议调用哪个 skill。
- 子 skill 完成后也必须输出下一步建议，不能把用户晾在中间状态。
- 所有中间产物落到 run 目录，方便恢复、复查和修订。
- 有账号、副作用、上传、发布的步骤必须显式确认。

## 2. 总体分层

```text
User
  |
  v
Skills Layer
  ai-video-maker orchestrator
  video-brief
  video-plan
  video-script
  browser-capture
  voice-subtitle
  edit-render
  qa-revision
  publish-package
  |
  v
Harness Layer
  pipeline loader
  run state
  approvals
  artifact manifest
  QA records
  |
  v
Capability Adapters
  script / ffmpeg / moviepy / edge-tts
  browser
  chrome
  computer-use
  youtube api or youtube studio
```

## 3. 引导和检阅模型

AI Video Maker 采用“主控引导 + 子 skill 交接建议 + 用户检阅”的设计。

```text
orchestrator 告诉用户下一步建议调用哪个 skill
-> 子 skill 完成一个 workflow
-> 子 skill 输出产物、检阅清单、风险和 next_skill_suggestion
-> 用户检阅
-> orchestrator 根据 handoff 和用户反馈决定继续、返修或暂停
```

### 3.1 硬 Gate

硬 gate 是安全和需求边界，必须等用户明确确认：

| Gate | 必须确认的原因 |
|---|---|
| `brief` | 防止视频目标、受众、平台和风格理解错 |
| `plan` | 防止章节、镜头、执行步骤和素材计划跑偏 |
| `execution` | 防止未经允许操作浏览器、Chrome 登录态或桌面 GUI |
| `upload` | 防止未经允许上传本地文件到第三方平台 |
| `publish` | 防止未经允许发布公开视频或执行账号侧动作 |

### 3.2 软 Review

软 review 是质量检阅，不一定要求用户每次都手动确认。

适用阶段：

- `video-script`
- `voice-subtitle`
- `edit-render`
- `qa-revision`
- `publish-package`

软 review 的输出应该包含：

- 已完成内容。
- 用户应该看什么。
- 如果不满意应该回到哪个 skill 修改。
- 如果满意下一步建议调用哪个 skill。

## 4. Skill 清单

### 4.1 `ai-video-maker` / `ai-video-orchestrator`

定位：总入口和总调度。

`ai-video-orchestrator` 是职责名，表示总调度 agent。当前仓库的实际 skill 名称是 `ai-video-maker`，文件是 `skills/ai-video-maker/SKILL.md`。

职责：

- 接收用户视频需求。
- 判断视频类型：项目介绍、产品演示、教程、SOP、Bug 复现、API/SDK 教程、版本更新说明等。
- 调用后续子 skill。
- 管理 `brief`、`plan`、`execution`、`upload`、`publish` gate。
- 在需要浏览器、Chrome 登录态或桌面 GUI 时，先解释动作和风险，再等待确认。

不做：

- 不直接绕过 gate 执行上传或发布。
- 不要求用户把 CLI 当成主入口。

### 4.2 `video-brief`

定位：需求对齐 workflow。

输入：

- 用户原始需求。
- 目标平台、比例、时长、受众、风格、语言、限制。

输出：

```text
runs/<run_id>/brief.yml
```

成功标准：

- 目标明确。
- 受众明确。
- 视频类型明确。
- 平台和比例明确。
- 用户知道下一步会生成什么 plan。

Gate：

```text
brief
```

### 4.3 `video-plan`

定位：制作方案 workflow。

输入：

- `brief.yml`
- 用户补充要求。

输出：

```text
runs/<run_id>/plan/storyboard.yml
runs/<run_id>/plan/asset_plan.yml
runs/<run_id>/plan/capability_plan.yml
```

成功标准：

- 每个章节有画面目标。
- 每段旁白能映射到画面。
- 明确哪些素材来自脚本生成、浏览器录制、Chrome 登录态或桌面操作。
- 明确是否需要 execution gate。

Gate：

```text
plan
```

### 4.4 `video-script`

定位：脚本和台本 workflow。

输入：

- `brief.yml`
- `plan/storyboard.yml`
- 用户确认后的修改意见。

输出：

```text
runs/<run_id>/script/narration.zh.txt
runs/<run_id>/script/screen_actions.md
runs/<run_id>/script/subtitle_draft.srt
```

成功标准：

- 旁白自然，适合 AI 配音。
- 字幕短句清晰。
- 操作台本能指导录屏。
- 开头 10 秒能说明价值或展示结果。

### 4.5 `browser-capture`

定位：网页、Chrome 和必要 GUI 捕获 workflow。

输入：

- `plan/capability_plan.yml`
- `script/screen_actions.md`
- 用户对 execution gate 的确认。

输出：

```text
runs/<run_id>/assets/browser/demo.webm
runs/<run_id>/assets/browser/screenshot.png
runs/<run_id>/qa/browser_capture.md
runs/<run_id>/assets/browser/handoff.browser-capture.yml
```

能力选择：

| 能力 | 使用场景 |
|---|---|
| `$browser` | 本地网页、普通网页、DOM 检查、截图、录屏 |
| `$chrome` | 需要用户现有登录态的网站，比如 YouTube Studio |
| `$computer-use` | 桌面软件、文件选择器、OBS、剪辑软件、系统对话框 |

Gate：

```text
execution
```

### 4.6 `voice-subtitle`

定位：配音和字幕 workflow。

输入：

- `script/narration.zh.txt`
- 视频目标时长。
- 声音风格。

输出：

```text
runs/<run_id>/audio/narration.mp3
runs/<run_id>/subtitles/captions.srt
```

成功标准：

- 有可播放音频。
- 字幕和旁白大致对齐。
- 字幕不宜过长，不遮挡关键 UI。

### 4.7 `edit-render`

定位：剪辑和渲染 workflow。

输入：

- 录屏片段或画面素材。
- 配音。
- 字幕。
- storyboard。

输出：

```text
runs/<run_id>/render/final_16x9.mp4
runs/<run_id>/render/handoff.edit-render.yml
```

成功标准：

- 横屏 YouTube 版优先，默认 16:9。
- 视频有画面流和音频流。
- 字幕清晰。
- 不出现明显空白、错位、遮挡或音画脱节。

### 4.8 `qa-revision`

定位：质检和返修 workflow。

输入：

- `render/final_16x9.mp4`
- storyboard。
- 发布目标。

输出：

```text
runs/<run_id>/qa/report.md
runs/<run_id>/qa/ffprobe.json
runs/<run_id>/qa/screenshots/frame_6s.png
runs/<run_id>/qa/handoff.qa-revision.yml
```

成功标准：

- 检查时长、分辨率、音轨、字幕、关键帧、开头信息密度。
- 如果失败，给出具体返修项并路由回对应 skill。

### 4.9 `publish-package`

定位：发布包 workflow。

输入：

- 通过 QA 的视频。
- 用户确认的平台策略。

输出：

```text
runs/<run_id>/package/video.mp4
runs/<run_id>/package/title.txt
runs/<run_id>/package/description.md
runs/<run_id>/package/tags.txt
runs/<run_id>/package/upload_checklist.md
```

Gate：

```text
upload
publish
```

## 5. Skill 交接契约

每个 skill 完成后都应该返回结构化交接信息，供 orchestrator 决定下一步。

建议格式：

```yaml
skill: video-plan
run_id: demo
status: ready_for_gate
inputs:
  - brief.yml
outputs:
  - plan/storyboard.yml
  - plan/asset_plan.yml
  - plan/capability_plan.yml
decisions:
  - platform: youtube
  - aspect_ratio: "16:9"
review_checklist:
  - 章节结构是否符合预期
  - 每段旁白是否能映射到画面
  - 是否接受浏览器录制和本地页面检查
risks:
  - browser capture requires execution approval
next_gate: plan
next_skill_suggestion: video-script
user_action_required: true
user_message: "请检阅章节结构、素材计划和执行步骤。确认后建议调用 video-script。"
```

最低要求：

- `skill`：当前 skill 名称。
- `run_id`：关联 run；如果还没有 run，应说明原因。
- `status`：`done`、`ready_for_review`、`ready_for_gate`、`blocked`、`needs_revision`。
- `outputs`：写入的产物路径。
- `review_checklist`：用户应该检阅的项目。
- `next_gate`：如果需要用户确认，写 gate 名称。
- `next_skill_suggestion`：建议下一步调用的 skill。
- `user_action_required`：是否需要用户明确动作。
- `risks`：涉及 GUI、账号、上传、发布等风险必须写明。
- `user_message`：面向用户的下一步说明。

## 6. Orchestrator 决策规则

Orchestrator 根据子 skill 的 handoff 做决策：

| Handoff 状态 | Orchestrator 动作 |
|---|---|
| `ready_for_gate` | 向用户展示产物、风险和确认请求，等待明确确认 |
| `ready_for_review` | 向用户展示检阅项，说明可修改或继续 |
| `needs_revision` | 说明失败点，建议回到对应 skill 返修 |
| `blocked` | 说明阻塞原因和需要用户补充的信息 |
| `done` | 说明已完成内容，并推荐下一步 skill |

Orchestrator 不应该机械地一条路走到底。它需要根据用户反馈决定：

- 继续调用 `next_skill_suggestion`。
- 回退到前一个 skill 返修。
- 暂停等待用户补充素材、账号确认或平台策略。
- 在有上传、发布、账号侧动作前强制进入 gate。

## 7. Harness 与 Skill 的关系

Skill 负责判断和编排：

```text
应该问什么
应该等哪个 gate
应该调用哪个 workflow
应该如何解释风险
应该如何处理返修
```

Harness 负责执行和留痕：

```text
创建 run
保存状态
记录 approvals
写 artifact manifest
调用渲染/配音/QA 工具
记录 capability adapter 结果
```

因此文档和产品入口应该写成：

```text
请使用 ai-video-maker skill 帮我制作视频
```

而不是：

```text
请手动运行一串 ai-video-maker CLI 命令
```

CLI 命令只应该出现在开发调试、实操记录和内部实现说明中。

## 8. Gate 规则

| Gate | 触发时机 | 必须确认的内容 |
|---|---|---|
| `brief` | 需求整理完成后 | 目标、受众、平台、时长、风格、边界 |
| `plan` | storyboard 和素材计划完成后 | 章节、镜头、旁白方向、执行步骤 |
| `execution` | 需要浏览器、Chrome 或桌面操作前 | 打开什么、录什么、是否使用登录态 |
| `upload` | 上传到第三方平台前 | 文件、平台、账号、隐私状态 |
| `publish` | 发布或公开前 | 标题、简介、标签、可见性、发布时间 |

## 9. 当前落地顺序

P0 已完成：

- run harness。
- gate 记录。
- 基础视频包目录结构。
- `ai-video-maker` 总入口 skill。
- 主控引导、子 skill 交接建议和用户检阅模型文档。

P1 已完成或正在完成：

- pipeline run/status/validate/capabilities。
- capability dry-run。
- browser preflight plan。
- browser result 写回 run。
- 使用文档改为 skills-first。
- `video-brief`、`video-plan`、`video-script` 子 skill P0 定义。
- `video-script` P0 harness：生成 screen actions、字幕草稿、shot notes 和 handoff。
- `voice-subtitle` 子 skill P0 定义。
- `voice-subtitle` P0 harness：生成 AI 配音、正式字幕和 handoff。
- `edit-render` 子 skill 和 harness：生成 `render/draft.mp4`、`render/final_16x9.mp4` 和 handoff。
- `qa-revision` 子 skill 和 harness：生成 QA 报告、ffprobe、关键帧截图和 handoff。
- `publish-package` 子 skill 和 harness：生成本地发布包，并停在 `upload` gate。
- `browser-capture` 子 skill 和 harness：第一版使用 Playwright 打开网页、截图和录短视频，必须经过 `execution` gate。
- 仓库讲解、项目介绍、产品演示三类 pipeline 模板。

P2 建议下一步：

1. 用更多真实主题打磨 `repository_demo`、`project_intro`、`product_demo`。
2. 增加返修闭环，让 `qa-revision` 可以驱动局部重做。
3. 增加封面图、章节描述、多平台版本和竖屏模板。
4. 接入需要登录态的 `$chrome` 和桌面 GUI 的 `$computer-use`。
5. 最后接 YouTube 上传，但继续保留 `upload` 和 `publish` gate。
