# AI Video Maker

AI Video Maker 是一套免费、可自动化的 AI 视频制作工具链实验项目。目标是让用户通过 `ai-video-maker` skill 提出一个视频需求，再由 AI 串联多个工作流 skill，完成目标对齐、内容拆解、脚本生成、素材录制、AI 配音、字幕、剪辑、质检和最终 MP4 导出。

仓库讲解是第一个试点场景，但项目不只服务开源仓库。它还面向产品演示、操作教程、SOP 培训、Bug 复现、API/SDK 教程、版本更新说明等技术和业务演示视频。

这个项目不做 AI 漫剧，不做素材混剪，专注结构化说明类视频生产。

## 当前能力

- 使用 `edge-tts` 生成 AI 旁白和字幕。
- 使用 `MoviePy` + `Pillow` 生成带中文标题和烧录字幕的视频。
- 使用 `auto-editor` 自动剪掉静音和停顿片段。
- 使用 `Whisper` 作为真实录音转写的备用方案。
- 使用 FFmpeg 作为底层音视频编码工具。
- 已实现 `video-script`、`voice-subtitle`、`edit-render`、`qa-revision`、`publish-package` 子工作流。
- 已实现 `browser-capture` 第一版：基于 Playwright 打开本地或公开网页、截图、短录屏，必须经过 `execution` gate。
- 预留 `$chrome` / `$computer-use` 用于需要登录态的网页、YouTube Studio 和桌面工具操作。
- 已沉淀项目定位、工程 harness、模板体系和 skill 设计方案。

## 为什么是 Skills + Harness

剪映、CapCut、Kdenlive 这类工具适合人工剪一条视频，但不适合批量、稳定、可复现地生成技术和业务演示视频。

本项目的用户入口是 skills，执行底座是 harness：

```text
用户需求 -> ai-video-maker orchestrator -> 子 workflow skills -> gate 确认 -> harness 执行 -> 视频包
```

CLI、pipeline 和 run 目录用于让 skill 的每一步可复现、可检查、可继续，不要求普通用户把 CLI 当成主路径。

## 环境要求

当前已验证环境：

- macOS arm64
- Python 3.12
- FFmpeg 8.0.1
- `edge-tts` 7.2.8
- `moviepy` 2.2.1
- `auto-editor` 29.3.1
- `openai-whisper` 20250625
- `torch` 2.12.0

注意：当前机器默认 `python3` 是 3.14.0，太新了，容易让 Whisper/Torch 依赖出兼容性问题。建议使用 Python 3.12 创建虚拟环境。

## 快速开始

进入项目目录：

```bash
cd "<project-root>"
```

创建虚拟环境：

```bash
/opt/homebrew/bin/python3.12 -m venv ".venv"
```

安装依赖：

```bash
".venv/bin/python" -m pip install --upgrade pip setuptools wheel
".venv/bin/python" -m pip install -r "requirements.txt"
".venv/bin/python" -m pip install -e "."
```

如果需要使用 `browser-capture` 录制网页，再安装 Playwright 浏览器运行时：

```bash
".venv/bin/python" -m playwright install chromium
```

## 使用者入口

在 Codex 或支持 skills 的 AI agent 中，推荐这样使用：

```text
请使用 ai-video-maker skill 帮我制作一个横屏 YouTube 视频。

需求：介绍 AI Video Maker 这个项目自己，演示它如何把一句视频需求变成视频包。
要求：先给 brief 和 plan，我确认后再执行录制、剪辑、配音、字幕和打包；不要自动上传。
```

AI 会在 `brief`、`plan`、`execution`、`upload`、`publish` 等 gate 暂停等待确认。

## 开发验证

下面命令用于开发者验证 harness，不是普通用户主路径。

验证依赖和 CLI：

```bash
".venv/bin/edge-tts" --version
".venv/bin/auto-editor" --version
".venv/bin/whisper" --help
".venv/bin/python" -c "import moviepy, torch, whisper, edge_tts; print('ok')"
".venv/bin/ai-video-maker" validate --pipeline "pipeline.example.yml"
".venv/bin/ai-video-maker" capabilities --pipeline "pipeline.example.yml"
".venv/bin/ai-video-maker" capabilities --pipeline "templates/pipelines/browser_local_demo.yml"
```

运行 P1 pipeline harness：

```bash
".venv/bin/ai-video-maker" run \
  --pipeline "pipeline.example.yml" \
  --run-id p1-self-intro \
  --overwrite

".venv/bin/ai-video-maker" approve \
  --run "runs/p1-self-intro" \
  --gate brief \
  --summary "确认 brief"

".venv/bin/ai-video-maker" run \
  --run "runs/p1-self-intro"

".venv/bin/ai-video-maker" approve \
  --run "runs/p1-self-intro" \
  --gate plan \
  --summary "确认 storyboard、素材计划和旁白稿"

".venv/bin/ai-video-maker" run \
  --run "runs/p1-self-intro"

".venv/bin/ai-video-maker" status \
  --run "runs/p1-self-intro"
```

运行 skills-first 主链的内部 harness 命令：

```bash
".venv/bin/ai-video-maker" script --run "runs/<run_id>"
".venv/bin/ai-video-maker" voice-subtitle --run "runs/<run_id>"
".venv/bin/ai-video-maker" edit-render --run "runs/<run_id>"
".venv/bin/ai-video-maker" qa-revision --run "runs/<run_id>"
".venv/bin/ai-video-maker" publish-package --run "runs/<run_id>"
```

运行 P0 harness demo：

```bash
".venv/bin/ai-video-maker" run-demo \
  --run-id p0-self-intro \
  --overwrite
```

运行单元测试：

```bash
".venv/bin/python" -m unittest discover -s "tests"
```

## 最小验证

生成 AI 配音和字幕：

```bash
mkdir -p "output/smoke"
".venv/bin/edge-tts" \
  --file "samples/demo_narration.txt" \
  --voice "zh-CN-XiaoxiaoNeural" \
  --rate "+0%" \
  --write-media "output/smoke/demo_narration.mp3" \
  --write-subtitles "output/smoke/demo_narration.vtt"
cp "output/smoke/demo_narration.vtt" "output/smoke/demo_narration.srt"
```

渲染测试视频：

```bash
".venv/bin/python" "scripts/render_smoke_video.py"
```

自动剪辑：

```bash
".venv/bin/auto-editor" \
  "output/smoke/demo_video.mp4" \
  -o "output/smoke/demo_video_auto.mp4" \
  --no-open
```

## 已知限制

当前 Homebrew FFmpeg 构建缺少 `drawtext` 和 `subtitles` 滤镜，所以本项目没有直接依赖 FFmpeg 画中文标题或烧字幕。

当前处理方式：

```text
用 Pillow 生成画面和字幕帧，用 MoviePy 组合音频和视频，最后让 FFmpeg 只负责编码。
```

这条路线更稳，也更方便后续做标题卡、章节卡和竖屏版本。

## 文档

- [使用指南](./docs/使用指南.md)
- [Skills 工作流架构](./docs/Skills工作流架构.md)
- [AI 视频制作助手项目定位与工程方案](./docs/AI视频制作助手项目定位与工程方案.md)
- [需求对齐到视频发布工作流](./docs/需求对齐到视频发布工作流.md)
- [能力适配器与 GUI 工具策略](./docs/能力适配器与GUI工具策略.md)
- [Harness 工程搭建计划](./docs/Harness工程搭建计划.md)
- [Pipeline 配置 Schema](./docs/Pipeline配置Schema.md)
- [Capability Adapter P0](./docs/CapabilityAdapterP0.md)
- [实操记录：AI Video Maker 自我介绍横屏 Demo](./docs/实操记录-AIVideoMaker自我介绍横屏Demo.md)
- [实操记录：P0 Harness 自我介绍 Demo](./docs/实操记录-P0Harness自我介绍Demo.md)
- [实操记录：P1 Pipeline Harness 自我介绍 Demo](./docs/实操记录-P1PipelineHarness自我介绍Demo.md)
- [实操记录：Skills-First 自我介绍 Demo](./docs/实操记录-SkillsFirst自我介绍Demo.md)
- [实操记录：Browser Adapter P1 本地页面检查](./docs/实操记录-BrowserAdapterP1本地页面检查.md)
- [TODO：功能实现路线图](./docs/TODO-功能实现路线图.md)
- [视频制作工具链调研与执行方案](./视频制作工具链调研与执行方案.md)
- [方案 A 安装配置记录](./docs/方案A安装配置记录.md)
- [AI Video Maker Skill](./skills/ai-video-maker/SKILL.md)
- [Video Brief Skill](./skills/video-brief/SKILL.md)
- [Video Plan Skill](./skills/video-plan/SKILL.md)
- [Video Script Skill](./skills/video-script/SKILL.md)
- [Voice Subtitle Skill](./skills/voice-subtitle/SKILL.md)
- [Browser Capture Skill](./skills/browser-capture/SKILL.md)
- [Edit Render Skill](./skills/edit-render/SKILL.md)
- [QA Revision Skill](./skills/qa-revision/SKILL.md)
- [Publish Package Skill](./skills/publish-package/SKILL.md)

## 路线图

- [x] 建立 `runs/<run_id>` 的 P0 工程 harness。
- [x] 实现需求 brief、storyboard、artifact manifest。
- [x] 实现 brief/plan/execution/upload/publish 分阶段确认记录。
- [x] 实现 `pipeline.yml` 驱动的 P1 run/status 流程。
- [x] 实现 `pipeline.yml` validate 命令和 schema 文档。
- [x] 实现 `$browser` / `$chrome` / `$computer-use` dry-run capability adapter。
- [x] 实现 `$browser` 本地 Web Demo 预检模板和 `browser_preflight.yml`。
- [x] 实现 Browser Adapter P1 本地页面截图和非空 QA 记录。
- [x] 支持仓库讲解、项目介绍、产品演示三类模板。
- [x] 生成视频脚本、旁白稿和字幕。
- [x] 使用 Playwright browser-capture 录制普通网页 Demo。
- [ ] 使用 `$chrome` 辅助需要登录态的网页和 YouTube Studio。
- [ ] 使用 `$computer-use` 辅助桌面 GUI 软件和文件选择器。
- [ ] 使用终端录制工具生成安装和运行演示片段。
- [x] 使用 MoviePy/Pillow/FFmpeg 渲染横屏视频。
- [x] 增加自动 QA：音轨、画面、字幕、关键帧截图。
- [ ] 自动生成横屏 YouTube 版和竖屏 Shorts/抖音版。
- [ ] 自动生成封面图、标题、简介和标签。
- [x] 沉淀 `skills/ai-video-maker/SKILL.md` 作为 orchestrator skill。
- [x] 拆分 `video-brief`、`video-plan`、`video-script` 子 skills。
- [x] 拆分 `voice-subtitle` 子 skill。
- [x] 拆分 `browser-capture`、`edit-render`、`qa-revision`、`publish-package` 子 skills。
- [x] 生成 YouTube 本地发布包：视频、标题、简介、标签和上传清单。
- [ ] 通过 YouTube Data API 或 YouTube Studio 辅助上传。

## 安全边界

以下动作不会自动执行，必须在操作前确认：

- 创建 GitHub 远程仓库。
- 上传或发布 YouTube 视频。
- 使用 Chrome 登录态操作账号。
- 上传本地文件到第三方平台。
- 创建 OAuth/API 凭据。

## License

MIT
