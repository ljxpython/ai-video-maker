# AI 视频制作助手项目定位与工程方案

更新时间：2026-06-08

## 1. 项目定位

AI Video Maker 当前名字保留，但项目定位不能只停在“开源仓库解说”。真正要做的是一个 AI 驱动的视频制作助手：

```text
输入一个视频需求
-> AI 对齐目标和受众
-> 拆解内容结构
-> 规划镜头、素材和旁白
-> 调用录屏、浏览器、桌面、TTS、字幕、剪辑工具
-> 生成可发布的视频产物和上传包
```

仓库讲解只是第一个试点场景。后续还要支持：

- 开源仓库/软件工具介绍。
- 产品功能演示。
- 操作教程和 SOP。
- Bug 复现和修复说明。
- API/SDK 使用演示。
- 课程片段和技术培训。
- 发布说明、版本更新、功能对比。
- 内部项目汇报或方案演示。

项目核心不是“某个剪辑软件替代品”，而是把 AI、录屏、配音、字幕、剪辑、质检和发布包装成一条可复用的视频生产流水线。

## 2. 产品原则

### 2.1 AI 做决策，工具做执行

AI 负责：

- 问清楚视频目标、受众、时长、平台和风格。
- 把需求拆成故事线、章节、镜头和素材清单。
- 生成旁白、字幕、标题、简介和标签。
- 选择合适的录制/剪辑策略。
- 检查成片是否满足质量标准。

工具负责：

- 录制浏览器、终端和桌面操作。
- 生成 AI 配音。
- 生成字幕或转写。
- 合成视频、音频和字幕。
- 自动剪掉停顿和无效片段。
- 导出横屏/竖屏版本。
- 准备上传包或执行上传。

### 2.2 先可复现，再好看

第一阶段不要追求复杂视觉包装。先保证：

- 每次运行能产出完整视频。
- 每一步输入输出可追踪。
- 脚本、字幕、音频、画面都能复用和重新生成。
- 失败时能定位是哪一步坏了。

视觉模板、动效、封面和多平台适配放在第二阶段升级。别一上来做花活，最后主流程跑不起来，那就是典型憨批工程。

### 2.3 人类确认高风险动作

下面动作必须确认：

- 上传或发布 YouTube/抖音/B 站视频。
- 使用 Chrome 登录态操作账号。
- 上传本地文件到第三方平台。
- 创建 OAuth/API 凭据。
- 创建公开仓库或公开发布内容。
- 删除、覆盖或批量移动重要素材。

AI 可以把内容准备好，但不能悄悄替用户发布。

## 3. 支持场景

### 3.1 仓库/工具介绍

输入：

- GitHub URL 或本地仓库路径。
- 目标平台和时长。
- 是否需要实操演示。

输出：

- 项目价值介绍。
- 安装和启动演示。
- 核心功能演示。
- 架构或代码亮点。
- 总结和适用人群。

典型结构：

```text
00:00 hook：这个项目能解决什么问题
00:10 效果预览
00:30 安装启动
01:00 核心功能实操
02:00 代码/架构亮点
02:40 总结
```

### 3.2 产品功能演示

输入：

- 产品 URL 或本地 Demo。
- 需要展示的功能列表。
- 目标用户角色。

输出：

- 功能演示视频。
- 分步骤旁白。
- UI 重点区域放大或标注。
- 平台发布包。

### 3.3 SOP/操作教程

输入：

- 操作目标。
- 操作路径。
- 注意事项。

输出：

- 分步骤教程视频。
- 字幕和章节卡。
- 错误操作提醒。
- 可复用培训素材。

### 3.4 Bug 复现和修复说明

输入：

- Bug 描述。
- 复现步骤。
- 修复前后对比。

输出：

- 复现视频。
- 修复说明视频。
- 对比字幕和关键帧截图。

## 4. 核心流水线

完整流水线分为 9 个阶段：

```text
brief -> ingest -> plan -> script -> capture -> voice -> subtitle -> render -> qa -> package
```

### 4.1 brief：需求对齐

目标：把一句模糊需求变成可执行视频 brief。

输入：

```yaml
goal: "介绍一个开源项目"
audience: "开发者"
platform: "youtube"
duration: 180
style: "技术讲解，AI 配音，节奏清晰"
source:
  type: "github_repo"
  value: "https://github.com/example/project"
```

输出：

```text
runs/<run_id>/brief.yml
```

需要明确：

- 视频目的：教学、推广、汇报、说明、复盘。
- 目标观众：开发者、产品、运营、管理者、新员工。
- 平台比例：YouTube 横屏、Shorts/抖音竖屏、内部培训。
- 时长范围。
- 是否需要真人/AI 配音。
- 是否需要上传。

### 4.2 ingest：资料读取

目标：读取和理解输入资料。

可读取对象：

- Git 仓库。
- README、文档、配置文件。
- 本地网页或线上 URL。
- PDF/Markdown/文本需求。
- 用户提供的操作步骤。

输出：

```text
runs/<run_id>/analysis/source_summary.md
runs/<run_id>/analysis/key_points.yml
runs/<run_id>/analysis/demo_candidates.yml
```

### 4.3 plan：视频结构规划

目标：生成视频结构、镜头计划和素材清单。

输出：

```text
runs/<run_id>/plan/storyboard.yml
runs/<run_id>/plan/asset_plan.yml
runs/<run_id>/plan/risk_notes.md
```

`storyboard.yml` 示例：

```yaml
title: "AI Video Maker：用 AI 自动做技术视频"
target_duration: 180
aspect_ratio: "16:9"
sections:
  - id: "hook"
    duration: 10
    purpose: "展示最终效果，快速说明价值"
    visual: "成片预览和工具链标题卡"
    narration: "这个项目能把一个技术需求变成一条带配音和字幕的视频。"
  - id: "workflow"
    duration: 40
    purpose: "解释流水线"
    visual: "流程图或终端命令"
    narration: "流程从需求对齐开始，然后生成脚本、录屏、配音、字幕和剪辑。"
```

### 4.4 script：旁白和字幕稿

目标：把视频结构变成可配音文本。

输出：

```text
runs/<run_id>/script/narration.zh.txt
runs/<run_id>/script/captions.srt
runs/<run_id>/script/scene_notes.md
```

规则：

- 优先先写旁白，再生成字幕。
- 不优先用 Whisper 猜 AI 配音内容。
- 技术视频旁白要短句多，少长难句。
- 命令、变量名、项目名要保留原文。
- 每段旁白必须能对应一个视觉画面。

### 4.5 capture：素材采集

目标：录制浏览器、终端、桌面或截图素材。

素材类型：

```text
browser_video
terminal_video
desktop_video
screenshot
image
audio
```

工具策略：

| 场景 | 首选工具 | 兜底 |
|---|---|---|
| 网页 Demo | `$browser` / Playwright | `$chrome` |
| 已登录网站 | `$chrome` | `$computer-use` |
| 终端操作 | VHS / asciinema | FFmpeg 录屏 |
| 桌面 GUI | OBS | `$computer-use` |
| 静态图 | Pillow / 截图 | FFmpeg |

输出：

```text
runs/<run_id>/assets/
runs/<run_id>/assets/manifest.yml
```

### 4.6 voice：AI 配音

目标：把旁白稿生成音频。

当前首选：

```text
edge-tts
```

输出：

```text
runs/<run_id>/audio/narration.mp3
runs/<run_id>/audio/voice_profile.yml
```

`voice_profile.yml` 示例：

```yaml
provider: "edge-tts"
voice: "zh-CN-XiaoxiaoNeural"
rate: "+0%"
pitch: "+0Hz"
volume: "+0%"
```

### 4.7 subtitle：字幕

目标：生成可烧录字幕和可外挂字幕。

优先级：

1. 已知旁白稿：根据旁白稿和 TTS 时间生成字幕。
2. 真人录音或实录音频：用 Whisper 转写。
3. Whisper 结果必须校对。

输出：

```text
runs/<run_id>/subtitles/captions.srt
runs/<run_id>/subtitles/captions.vtt
```

### 4.8 render：剪辑和合成

目标：把素材、配音、字幕、章节卡合成视频。

当前策略：

```text
Pillow 画标题/字幕/卡片 -> MoviePy 组合画面和音频 -> FFmpeg 编码 -> Auto-Editor 剪停顿
```

输出：

```text
runs/<run_id>/render/draft.mp4
runs/<run_id>/render/final_16x9.mp4
runs/<run_id>/render/final_9x16.mp4
```

### 4.9 qa：质量检查

目标：自动检查视频是否可发布。

检查项：

- 视频存在且非 0 字节。
- 时长在目标范围内。
- 有视频流和音频流。
- 字幕不为空。
- 关键帧截图非黑屏。
- 旁白和字幕数量匹配。
- 横屏/竖屏比例正确。
- 文件名和导出目录正确。

输出：

```text
runs/<run_id>/qa/report.md
runs/<run_id>/qa/ffprobe.json
runs/<run_id>/qa/screenshots/
```

### 4.10 package：发布包

目标：准备平台发布所需内容。

输出：

```text
runs/<run_id>/package/video.mp4
runs/<run_id>/package/thumbnail.png
runs/<run_id>/package/title.txt
runs/<run_id>/package/description.md
runs/<run_id>/package/tags.txt
```

上传不默认执行。真正上传或发布前必须确认。

## 5. 工程 Harness 设计

### 5.1 目录结构

建议后续演进成：

```text
ai-video-maker/
  src/ai_video_maker/
    __init__.py
    cli.py
    config.py
    pipeline.py
    artifacts.py
    stages/
      brief.py
      ingest.py
      plan.py
      script.py
      capture.py
      voice.py
      subtitle.py
      render.py
      qa.py
      package.py
    renderers/
      moviepy_renderer.py
      cards.py
      subtitles.py
    providers/
      edge_tts.py
      whisper.py
      ffmpeg.py
      auto_editor.py
    templates/
  templates/
    briefs/
    storyboards/
    scripts/
    render_profiles/
    upload_profiles/
  skills/
    ai-video-maker/
      SKILL.md
  examples/
    repo_explainer/
    product_demo/
    sop_tutorial/
  runs/
```

### 5.2 CLI 入口

建议提供统一命令：

```bash
ai-video-maker init
ai-video-maker brief --source "https://github.com/user/repo" --type repo_explainer
ai-video-maker plan --run "runs/20260608-001"
ai-video-maker script --run "runs/20260608-001"
ai-video-maker voice --run "runs/20260608-001"
ai-video-maker render --run "runs/20260608-001"
ai-video-maker qa --run "runs/20260608-001"
ai-video-maker package --run "runs/20260608-001"
```

组合命令：

```bash
ai-video-maker run --config "pipeline.yml"
```

### 5.3 pipeline.yml

每个任务用一个配置文件描述：

```yaml
project:
  name: "ai-video-maker demo"
  type: "repo_explainer"

source:
  type: "local_path"
  value: "."

video:
  platform: "youtube"
  aspect_ratio: "16:9"
  target_duration: 180
  language: "zh-CN"
  style: "技术讲解，清晰直接"

voice:
  provider: "edge-tts"
  voice: "zh-CN-XiaoxiaoNeural"
  rate: "+0%"

render:
  resolution: "1920x1080"
  fps: 24
  burn_subtitles: true
  auto_edit: true

upload:
  enabled: false
```

### 5.4 Artifact Manifest

每一步都写入 manifest，方便断点续跑：

```yaml
run_id: "20260608-001"
status: "rendered"
artifacts:
  brief: "brief.yml"
  storyboard: "plan/storyboard.yml"
  narration: "script/narration.zh.txt"
  voice: "audio/narration.mp3"
  subtitles: "subtitles/captions.srt"
  final_video: "render/final_16x9.mp4"
```

## 6. 模板体系

模板不是装饰，是稳定产出的关键。没有模板，每次都靠 AI 临场发挥，质量会飘。

### 6.1 Brief 模板

```text
你要做什么视频？
给谁看？
看完希望观众做什么？
目标平台是什么？
目标时长是多少？
是否需要实操录屏？
是否需要 AI 配音？
是否需要上传？
```

### 6.2 场景模板

建议先支持：

| 模板 | 用途 |
|---|---|
| `repo_explainer` | 仓库/工具介绍 |
| `product_demo` | 产品功能演示 |
| `sop_tutorial` | 操作教程 |
| `bug_repro` | Bug 复现说明 |
| `release_note` | 版本更新说明 |
| `api_tutorial` | API/SDK 教程 |

### 6.3 渲染模板

基础模板：

- 标题卡。
- 章节卡。
- 字幕条。
- 终端画面容器。
- 浏览器画面容器。
- 总结卡。
- 竖屏裁切和放大规则。

## 7. Skill 设计

后续需要沉淀 Codex Skill，让 AI 知道遇到视频制作需求时怎么工作。

建议路径：

```text
skills/ai-video-maker/SKILL.md
```

Skill 职责：

- 识别视频制作需求。
- 对齐 brief。
- 选择模板。
- 调用项目 CLI。
- 使用 `$browser`、`$chrome`、`$computer-use` 录制或操作。
- 生成发布包。
- 在上传/发布前请求确认。

Skill 骨架：

```markdown
---
name: ai-video-maker
description: Use when the user wants AI-assisted technical/product/demo video creation, including planning, narration, recording, subtitles, editing, rendering, and upload packaging.
---

# AI Video Maker Skill

## Workflow

1. Align brief.
2. Select video template.
3. Ingest source material.
4. Generate storyboard and narration.
5. Capture required assets.
6. Generate voice and subtitles.
7. Render draft.
8. Run QA.
9. Package for upload.

## Safety

Always confirm before uploading files, publishing videos, using account login state, or creating public resources.
```

## 8. 质量标准

每条视频至少满足：

- 开头 10 秒说明价值或展示效果。
- 每个章节都有对应视觉画面。
- 字幕不遮挡关键 UI。
- 旁白没有大段废话。
- 音频响度稳定，无明显爆音。
- 终端命令和网页操作已经提前验证。
- 成片有音轨、有画面、非黑屏。
- 输出文件可被 FFmpeg/ffprobe 正常读取。
- 发布包包含标题、简介、标签和封面建议。

## 9. 里程碑

### P0：从 POC 到可用 Harness

- [ ] 建 `src/ai_video_maker/` Python 包。
- [ ] 实现 `pipeline.yml` 加载。
- [ ] 实现 `runs/<run_id>` 目录和 artifact manifest。
- [ ] 把 smoke test 接入 CLI。
- [ ] 把当前 MoviePy/Pillow 渲染脚本改造成 renderer。
- [ ] 补基础 pytest。

### P1：支持第一个真实主题试点

- [ ] 选一个真实视频主题。
- [ ] 生成 brief。
- [ ] 生成 storyboard。
- [ ] 生成旁白和字幕。
- [ ] 录制浏览器或终端素材。
- [ ] 输出横屏 1080p 成片。
- [ ] 输出 YouTube 发布包。

### P2：模板和 Skill

- [ ] 增加 `templates/`。
- [ ] 增加 `skills/ai-video-maker/SKILL.md`。
- [ ] 增加 repo/product/sop 三种模板。
- [ ] 增加 QA 截图和 ffprobe 报告。
- [ ] 增加竖屏导出。

### P3：上传和多平台

- [ ] 接 YouTube Data API 上传。
- [ ] 接 `$chrome` + YouTube Studio 半自动上传。
- [ ] 生成 Shorts/抖音/B 站发布包。
- [ ] 上传和发布前统一确认。

## 10. 下一步建议

下一步不要急着做上传。先做工程 harness：

```text
pipeline.yml -> runs/<run_id> -> manifest -> render -> qa
```

然后拿一个具体主题打磨。

建议第一个主题：

```text
“用 AI Video Maker 把一个需求变成一条 AI 配音技术视频”
```

这个主题正好用项目介绍项目，能同时验证：

- 需求对齐。
- 旁白生成。
- 字幕生成。
- 标题卡渲染。
- 自动剪辑。
- 质量检查。
- 发布包生成。

