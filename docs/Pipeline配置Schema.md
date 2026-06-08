# Pipeline 配置 Schema

更新时间：2026-06-08

`pipeline.yml` 是 AI Video Maker 的任务入口。它描述一次视频制作任务的目标、来源、视频规格、配音、渲染、能力适配器和上传策略。

验证命令：

```bash
ai-video-maker validate --pipeline pipeline.example.yml
```

## 顶层结构

```yaml
project:
  name: "AI Video Maker"
  type: "general_demo"

source:
  type: "user_request"
  value: "介绍 AI Video Maker 项目自己"

video:
  platform: "youtube"
  aspect_ratio: "16:9"
  resolution: "1920x1080"
  target_duration: 60
  language: "zh-CN"
  style: "横屏技术讲解，AI 配音，字幕清晰"

capabilities:
  browser:
    required: false
  chrome:
    required: false
  computer_use:
    required: false

voice:
  provider: "edge-tts"
  voice: "zh-CN-XiaoxiaoNeural"
  rate: "+0%"
  pitch: "+0Hz"
  volume: "+0%"

render:
  fps: 24
  burn_subtitles: true
  auto_edit: true

upload:
  enabled: false
  platform: "youtube"
  confirmation: "required"
```

## 必填字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `project.name` | string | 项目或视频主题名称 |
| `project.type` | string | 模板类型，当前默认 `general_demo` |
| `source.type` | string | 输入来源，例如 `user_request` |
| `source.value` | string | 用户需求或视频任务描述 |
| `video.platform` | string | 目标平台，当前优先 `youtube` |
| `video.aspect_ratio` | string | 画幅，例如 `16:9` |
| `video.resolution` | string | 分辨率，例如 `1920x1080` |
| `video.target_duration` | integer | 目标时长，必须大于 0 |
| `video.language` | string | 视频语言，例如 `zh-CN` |

## 可选字段

### `voice`

当前默认使用 `edge-tts`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `voice.provider` | string | 配音提供方 |
| `voice.voice` | string | 声音 ID |
| `voice.rate` | string | 语速，例如 `+0%` |
| `voice.pitch` | string | 音高，例如 `+0Hz` |
| `voice.volume` | string | 音量，例如 `+0%` |

### `render`

| 字段 | 类型 | 说明 |
|---|---|---|
| `render.fps` | integer | 帧率，必须大于 0 |
| `render.burn_subtitles` | boolean | 是否烧录字幕 |
| `render.auto_edit` | boolean | 是否使用 `auto-editor` 自动剪辑 |

### `capabilities`

GUI 工具是能力适配器，不是核心依赖。

| 字段 | 类型 | 说明 |
|---|---|---|
| `capabilities.browser.required` | boolean | 是否需要 `$browser` |
| `capabilities.chrome.required` | boolean | 是否需要 `$chrome` |
| `capabilities.computer_use.required` | boolean | 是否需要 `$computer-use` |

如果任何 GUI capability 的 `required` 为 `true`，pipeline 会在制作前等待 `execution` gate 确认。

查看 capability dry-run：

```bash
ai-video-maker capabilities --pipeline pipeline.example.yml
```

在 plan 阶段会生成：

```text
runs/<run_id>/plan/capability_plan.yml
```

P0 阶段只生成 dry-run 计划，不会真正打开浏览器、Chrome 或桌面应用。

### `upload`

| 字段 | 类型 | 说明 |
|---|---|---|
| `upload.enabled` | boolean | 是否准备上传 |
| `upload.platform` | string | 上传平台 |
| `upload.confirmation` | string | 上传确认策略 |

当 `upload.enabled` 为 `true` 时，`upload.confirmation` 必须是 `required`。

P1 不会自动上传或发布视频。上传和发布必须分别通过 `upload`、`publish` gate。

## 当前校验规则

`validate` 会检查：

- 必填 mapping 是否存在。
- 必填字符串是否非空。
- 正整数是否大于 0。
- boolean 字段是否为 `true` 或 `false`。
- GUI capability 是否使用合法结构。
- 上传启用时是否强制要求确认。

示例：

```bash
ai-video-maker validate --pipeline pipeline.example.yml
```

成功输出：

```text
pipeline valid
```

失败输出：

```text
pipeline invalid
- project.name must be a non-empty string
- video.target_duration must be a positive integer
```

## P1 执行规则

```text
pipeline.yml -> brief.yml -> 等待 brief 确认
brief approved -> storyboard / asset_plan / capability_plan / narration -> 等待 plan 确认
plan approved -> voice / subtitles / render / QA / package
GUI capability required -> 等待 execution 确认
upload / publish -> 永不自动执行
```
