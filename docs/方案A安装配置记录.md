# 方案 A 安装配置记录

更新时间：2026-06-08

## 1. 本次目标

按“方案 A”搭建一个免费、可自动化的视频制作最小工具链：

```text
Playwright/$browser + edge-tts + Whisper + MoviePy + FFmpeg + Auto-Editor
```

本次先完成本地可验证能力：

- AI 配音：`edge-tts`
- 字幕生成：`edge-tts` 输出字幕；`Whisper` 备用转写
- 视频合成：`MoviePy` + `Pillow` + FFmpeg 编码
- 自动剪辑：`auto-editor`
- 浏览器录制：后续使用当前环境的 `$browser` / `$chrome`，本次不额外安装本地 Playwright

## 2. 当前目录结构

当前工作目录：

```text
/Users/bytedance/Downloads/movie_make
```

已创建目录：

```text
docs/
output/
output/smoke/
samples/
scripts/
```

关键文件：

| 文件 | 说明 |
|---|---|
| `requirements.txt` | Python 依赖清单 |
| `samples/demo_narration.txt` | 最小验证旁白稿 |
| `scripts/create_smoke_frame.py` | 生成测试标题帧 |
| `scripts/render_smoke_video.py` | 用 MoviePy/Pillow 渲染烧字幕视频 |
| `output/smoke/demo_video.mp4` | 最小验证视频 |
| `output/smoke/demo_video_auto.mp4` | auto-editor 处理后的测试视频 |

## 3. 已确认的基础环境

本机已有：

```bash
rtk which ffmpeg
rtk ffmpeg -version
rtk which python3
rtk python3 --version
rtk which python3.12
rtk which brew
rtk which pipx
```

结果摘要：

| 工具 | 状态 |
|---|---|
| FFmpeg | 已安装，版本 8.0.1 |
| Python 默认版本 | 3.14.0 |
| Python 3.12 | 已安装，版本 3.12.12 |
| Node/npm | 已安装 |
| brew | 已安装 |
| pipx/pip3 | 已安装 |

注意：默认 `python3` 是 3.14.0，太新了，容易让 Torch/Whisper 这类依赖出兼容性妖蛾子。所以本次使用 `python3.12` 创建虚拟环境。

## 4. 虚拟环境与依赖安装

创建本地虚拟环境：

```bash
rtk /opt/homebrew/bin/python3.12 -m venv "/Users/bytedance/Downloads/movie_make/.venv"
```

升级打包工具：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
```

安装依赖：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/python" -m pip install -r "/Users/bytedance/Downloads/movie_make/requirements.txt"
```

`requirements.txt` 内容：

```text
edge-tts
moviepy
auto-editor
openai-whisper
```

已安装关键版本：

```text
auto-editor==29.3.1
edge-tts==7.2.8
moviepy==2.2.1
numpy==2.4.6
openai-whisper==20250625
pillow==11.3.0
torch==2.12.0
```

## 5. CLI 验证

验证命令：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/edge-tts" --version
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/auto-editor" --version
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/whisper" --help
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/python" -c "import moviepy, torch, whisper, edge_tts; print('ok')"
```

结果：

| 工具 | 验证结果 |
|---|---|
| `edge-tts` | 通过，版本 7.2.8 |
| `auto-editor` | 通过，版本 29.3.1 |
| `whisper` | 通过，CLI 可用 |
| `moviepy` / `torch` / `whisper` / `edge_tts` import | 通过 |

`auto-editor` 首次运行时下载了 macOS arm64 二进制：

```text
https://github.com/WyattBlue/auto-editor/releases/download/29.3.1/auto-editor-macos-arm64
```

## 6. AI 配音验证

列出中文音色：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/edge-tts" --list-voices | rtk rg "zh-CN.*(Xiaoxiao|Yunxi|Yunjian|Xiaoyi|Xiaochen)"
```

可用音色摘要：

```text
zh-CN-XiaoxiaoNeural    Female    Warm
zh-CN-XiaoyiNeural      Female    Lively
zh-CN-YunjianNeural     Male      Passion
zh-CN-YunxiNeural       Male      Lively, Sunshine
zh-CN-YunxiaNeural      Male      Cute
```

本次使用音色：

```text
zh-CN-XiaoxiaoNeural
```

生成配音和字幕：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/edge-tts" \
  --file "/Users/bytedance/Downloads/movie_make/samples/demo_narration.txt" \
  --voice "zh-CN-XiaoxiaoNeural" \
  --rate "+0%" \
  --write-media "/Users/bytedance/Downloads/movie_make/output/smoke/demo_narration.mp3" \
  --write-subtitles "/Users/bytedance/Downloads/movie_make/output/smoke/demo_narration.vtt"
```

结果：

| 文件 | 说明 |
|---|---|
| `output/smoke/demo_narration.mp3` | 102.7 KB，时长 17.52 秒 |
| `output/smoke/demo_narration.vtt` | 331 B |
| `output/smoke/demo_narration.srt` | 从上面的字幕复制得到 |

注意：`edge-tts` 写出的字幕内容更像 SRT，但文件名用了 `.vtt`。为了避免后续工具误判，本次复制为 `.srt` 使用。

## 7. FFmpeg 坑点与处理

本机 FFmpeg 可用，但当前构建缺少两个常用视频滤镜：

```text
drawtext
subtitles
```

验证命令：

```bash
rtk /opt/homebrew/bin/ffmpeg -filters | rtk rg " drawtext| subtitles"
```

结果没有匹配项。

影响：

- 不能直接用 FFmpeg `drawtext` 画中文标题。
- 不能直接用 FFmpeg `subtitles` 烧录字幕。

处理方案：

```text
用 Pillow 生成画面，用 MoviePy 按字幕时间把字幕画进帧里，最后让 FFmpeg 只负责编码。
```

这个方案更稳，也更适合后续做复杂标题卡、章节卡和竖屏排版。

## 8. 最小视频合成验证

生成测试标题帧：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/python" \
  "/Users/bytedance/Downloads/movie_make/scripts/create_smoke_frame.py"
```

生成烧字幕 MP4：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/python" \
  "/Users/bytedance/Downloads/movie_make/scripts/render_smoke_video.py"
```

结果：

| 文件 | 说明 |
|---|---|
| `output/smoke/demo_video.mp4` | 17.52 秒，539388 字节 |
| `output/smoke/demo_video_frame_5s.png` | 5 秒处截图，确认字幕已烧入画面 |

截图人工检查结论：

```text
画面非黑屏，标题正常，中文字幕正常显示。
```

## 9. 自动剪辑验证

运行：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/auto-editor" \
  "/Users/bytedance/Downloads/movie_make/output/smoke/demo_video.mp4" \
  -o "/Users/bytedance/Downloads/movie_make/output/smoke/demo_video_auto.mp4" \
  --no-open
```

结果：

| 文件 | 时长 | 大小 |
|---|---:|---:|
| `demo_video.mp4` | 17.52 秒 | 539388 字节 |
| `demo_video_auto.mp4` | 16.50 秒 | 402261 字节 |

结论：`auto-editor` 能正常处理我们生成的视频。

## 10. Whisper 验证

运行：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/whisper" \
  "/Users/bytedance/Downloads/movie_make/output/smoke/demo_narration.mp3" \
  --model "tiny" \
  --language "zh" \
  --output_format "srt" \
  --output_dir "/Users/bytedance/Downloads/movie_make/output/smoke/whisper" \
  --fp16 "False"
```

首次运行下载了 `tiny` 模型，大小约 72.1 MB。

结果：

```text
Whisper CLI 可用，能生成 SRT。
```

但 `tiny` 模型识别质量一般，例如把“方案 A”识别错，并出现繁体和错字。正式视频建议：

- 如果旁白稿已知：优先使用 `edge-tts` 同步输出字幕。
- 如果要从真实录音转写：使用 `small` 或更高模型，并人工校对。

## 11. 如何激活环境

进入项目目录：

```bash
cd "/Users/bytedance/Downloads/movie_make"
```

激活虚拟环境：

```bash
source "/Users/bytedance/Downloads/movie_make/.venv/bin/activate"
```

不激活也可以直接调用绝对路径：

```bash
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/edge-tts" --version
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/auto-editor" --version
rtk "/Users/bytedance/Downloads/movie_make/.venv/bin/whisper" --help
```

## 12. 需要用户手动设置的事项

当前本地视频制作最小链路已经跑通，不需要你手动设置。

后续进入真实仓库介绍和上传 YouTube 时，需要你手动处理或确认这些事：

| 场景 | 是否需要你手动处理 | 原因 |
|---|---:|---|
| YouTube Data API OAuth | 需要 | 要创建/选择 Google Cloud 项目、OAuth 客户端、授权频道 |
| YouTube API 项目审核 | 可能需要 | 未审核项目上传的视频可能被限制为 private |
| Chrome 登录 YouTube | 需要 | 如果走 `$chrome` + YouTube Studio，需要你的账号登录态 |
| 上传/发布视频 | 需要确认 | 上传文件、设置公开、发布都会影响外部账号 |
| macOS 屏幕录制权限 | 可能需要 | 如果用 OBS 或桌面录制，需要系统授权 |
| 下载 Whisper 更大模型 | 可能需要等待 | `small`、`medium`、`large` 模型体积更大 |
| 使用在线 TTS | 默认可用 | `edge-tts` 会把旁白文本发送到 Microsoft Edge 在线 TTS 服务 |

## 13. 当前结论

方案 A 的核心链路已经跑通：

```text
文本稿 -> edge-tts 配音/字幕 -> MoviePy/Pillow 烧字幕合成 -> auto-editor 自动剪辑 -> MP4 输出
```

已验证产物：

```text
/Users/bytedance/Downloads/movie_make/output/smoke/demo_video.mp4
/Users/bytedance/Downloads/movie_make/output/smoke/demo_video_auto.mp4
```

下一步可以拿一个真实开源仓库做试点：

```text
1. 分析 README 和代码结构
2. 启动项目或跑示例
3. 生成讲解脚本
4. 用 $browser 录制网页实操
5. 用 edge-tts 配音
6. 用 MoviePy/Pillow/Auto-Editor 合成
7. 生成 YouTube 标题、简介、标签
8. 经确认后上传
```

