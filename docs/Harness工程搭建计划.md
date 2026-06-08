# Harness 工程搭建计划

更新时间：2026-06-08

## 1. 目标

把当前脚本 POC 升级成可运行的视频制作 harness。

核心要求：

- 用户需求可落成 `brief.yml`。
- 每次任务有独立 `runs/<run_id>`。
- 每个阶段有明确输入输出。
- 每个确认点有记录。
- 视频制作可断点续跑。
- 高风险动作不会自动执行。

## 2. P0 最小工程结构

```text
src/ai_video_maker/
  __init__.py
  cli.py
  models.py
  run_context.py
  approvals.py
  artifacts.py
  stages/
    brief.py
    plan.py
    script.py
    voice.py
    subtitle.py
    render.py
    qa.py
    package.py
  providers/
    edge_tts.py
    whisper.py
    auto_editor.py
    ffmpeg.py
  renderers/
    moviepy_renderer.py
    cards.py
    subtitle_drawer.py
```

P0 不做复杂录屏和上传，先把纯本地制作链路打通。

## 3. 数据模型

### 3.1 Brief

```yaml
goal: ""
audience: ""
platform: "youtube"
duration: 180
language: "zh-CN"
style: ""
source_material: []
must_show: []
must_avoid: []
upload:
  enabled: false
```

### 3.2 Approval

```yaml
gate: "plan"
status: "approved"
approved_at: ""
summary: ""
```

### 3.3 Artifact

```yaml
id: "final_video"
type: "video"
path: "render/final_16x9.mp4"
stage: "render"
created_at: ""
```

### 3.4 Run State

```json
{
  "run_id": "20260608-001",
  "status": "package_ready",
  "current_stage": "package"
}
```

## 4. CLI 阶段

### 4.0 P1 Pipeline 入口

P1 开始支持用 `pipeline.yml` 驱动 run。

创建 pipeline run：

```bash
ai-video-maker run \
  --pipeline pipeline.example.yml \
  --run-id p1-self-intro \
  --overwrite
```

查看状态：

```bash
ai-video-maker status --run runs/p1-self-intro
```

继续推进：

```bash
ai-video-maker run --run runs/p1-self-intro
```

当前推进规则：

```text
pipeline.yml -> brief.yml -> 等待 brief 确认
brief approved -> storyboard/asset_plan/narration -> 等待 plan 确认
plan approved -> voice/render/qa/package
GUI capability required -> 等待 execution 确认
upload/publish -> P1 不自动执行
```

### 4.1 初始化任务

```bash
ai-video-maker new --template general_demo
```

生成：

```text
runs/<run_id>/brief.yml
runs/<run_id>/approvals.yml
runs/<run_id>/state.json
```

### 4.2 生成方案

```bash
ai-video-maker plan --run runs/<run_id>
```

生成：

```text
plan/storyboard.yml
plan/asset_plan.yml
```

### 4.3 记录确认

```bash
ai-video-maker approve --run runs/<run_id> --gate plan
```

写入：

```text
approvals.yml
```

### 4.4 生成配音

```bash
ai-video-maker voice --run runs/<run_id>
```

生成：

```text
audio/narration.mp3
audio/voice_profile.yml
```

### 4.5 渲染视频

```bash
ai-video-maker render --run runs/<run_id>
```

生成：

```text
render/draft.mp4
render/final_16x9.mp4
```

### 4.6 质检

```bash
ai-video-maker qa --run runs/<run_id>
```

生成：

```text
qa/report.md
qa/ffprobe.json
qa/screenshots/
```

### 4.7 打包

```bash
ai-video-maker package --run runs/<run_id>
```

生成：

```text
package/video.mp4
package/title.txt
package/description.md
package/tags.txt
package/upload_checklist.md
```

## 5. 确认 Gate

| Gate | 进入前 | 确认内容 |
|---|---|---|
| `brief` | 生成方案前 | 视频目标、受众、平台、时长 |
| `plan` | 开始制作前 | 章节结构、素材需求、风险 |
| `execution` | GUI 操作前 | 需要打开的软件、网页、账号状态 |
| `upload` | 上传前 | 平台、账号、文件、标题、简介、可见性 |
| `publish` | 发布前 | 是否立即公开视频 |

`upload` 和 `publish` 永远不能默认通过。

## 6. Capability Adapter 接口

后续 adapter 统一暴露：

```python
class CapabilityAdapter:
    name: str

    def available(self) -> bool:
        ...

    def plan(self, task):
        ...

    def execute(self, task, run_context):
        ...
```

建议 adapter：

```text
browser
chrome
computer_use
youtube_api
```

## 7. 测试计划

P0 测试只测稳定逻辑：

- `brief.yml` 加载。
- `storyboard.yml` 加载。
- `approvals.yml` 写入。
- `state.json` 更新。
- SRT 解析。
- 字幕绘制。
- smoke render。
- QA 报告生成。

先不要在 CI 里测真实 GUI。GUI 测试后面单独做手动或本地集成测试。

## 8. 第一阶段完成标准

满足以下条件算 P0 完成：

```text
1. 可以通过 CLI 创建 run。
2. 可以生成并记录 brief/plan approval。
3. 可以用模板生成旁白稿。
4. 可以生成 TTS 音频和字幕。
5. 可以渲染一个 final_16x9.mp4。
6. 可以输出 qa/report.md。
7. 可以生成 package/ 上传包。
8. 不依赖 GUI 工具也能完成 smoke run。
```
