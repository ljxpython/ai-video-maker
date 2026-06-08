from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_json, write_yaml
from .renderer import render_video


DEFAULT_NARRATION = """这是 AI Video Maker 的第一条自我介绍 Demo。
它的目标是让用户只说一个视频需求，AI 就能完成需求对齐、方案拆解、脚本生成、配音、字幕、剪辑和质检。
当前版本先验证横屏 YouTube 视频链路：从文本旁白生成音频和字幕，再渲染成带字幕的 MP4。
后续我们会继续接入浏览器、Chrome 登录态和桌面操作能力，用来录制真实演示并准备发布包。
"""


def bin_path(command: str) -> str:
    candidate = Path(sys.executable).absolute().parent / command
    return str(candidate) if candidate.exists() else command


def run_command(args: list[str]) -> None:
    subprocess.run(args, check=True)


def pipeline_config(ctx: RunContext) -> dict:
    path = ctx.path("pipeline.yml")
    return read_yaml(path) if path.exists() else {}


def initialize_run_files(ctx: RunContext, template: str = "general_demo") -> None:
    project_root = ctx.project_root
    brief_template = read_yaml(project_root / "templates" / "briefs" / f"{template}.yml")
    storyboard_template = read_yaml(project_root / "templates" / "storyboards" / f"{template}.yml")

    brief_template.update(
        {
            "goal": "介绍 AI Video Maker 项目自己",
            "audience": "想用 AI 制作技术和演示视频的用户",
            "platform": "youtube",
            "duration": 60,
            "style": "横屏技术讲解，AI 配音，字幕清晰",
        }
    )
    write_yaml(ctx.path("brief.yml"), brief_template)
    write_yaml(ctx.path("plan/storyboard.yml"), storyboard_template)
    write_yaml(
        ctx.path("plan/asset_plan.yml"),
        {
            "assets": [
                {"id": "narration", "type": "text", "path": "script/narration.zh.txt"},
                {"id": "voice", "type": "audio", "path": "audio/narration.mp3"},
                {"id": "captions", "type": "subtitle", "path": "subtitles/captions.srt"},
            ]
        },
    )
    ctx.path("script/narration.zh.txt").write_text(DEFAULT_NARRATION, encoding="utf-8")
    ctx.update_state("brief_ready", "new")

    record_artifact(ctx, "brief", "yaml", ctx.path("brief.yml"), "new")
    record_artifact(ctx, "storyboard", "yaml", ctx.path("plan/storyboard.yml"), "new")
    record_artifact(ctx, "narration_script", "text", ctx.path("script/narration.zh.txt"), "new")


def approve_gate(ctx: RunContext, gate: str, summary: str = "approved for P0 harness run") -> None:
    approvals = read_yaml(ctx.approvals_path)
    approvals[gate] = {"status": "approved", "summary": summary}
    write_yaml(ctx.approvals_path, approvals)
    ctx.update_state(f"{gate}_approved", "approve")


def generate_voice(ctx: RunContext) -> None:
    pipeline = pipeline_config(ctx)
    voice_config = pipeline.get("voice", {})
    narration = ctx.path("script/narration.zh.txt")
    audio = ctx.path("audio/narration.mp3")
    subtitles_vtt = ctx.path("subtitles/captions.vtt")
    subtitles_srt = ctx.path("subtitles/captions.srt")

    command = [
        bin_path("edge-tts"),
        "--file",
        str(narration),
        "--voice",
        str(voice_config.get("voice", "zh-CN-XiaoxiaoNeural")),
        "--rate",
        str(voice_config.get("rate", "+0%")),
        "--write-media",
        str(audio),
        "--write-subtitles",
        str(subtitles_vtt),
    ]
    for key, option in [("pitch", "--pitch"), ("volume", "--volume")]:
        value = voice_config.get(key)
        if value:
            command.extend([option, str(value)])

    run_command(command)
    subtitles_srt.write_text(vtt_to_srt(subtitles_vtt.read_text(encoding="utf-8")), encoding="utf-8")
    subtitle_draft = ctx.path("script/subtitle_draft.srt")
    if subtitles_srt.stat().st_size == 0 and subtitle_draft.exists():
        shutil.copyfile(subtitle_draft, subtitles_srt)
    ctx.update_state("voice_ready", "voice")
    record_artifact(ctx, "voice", "audio", audio, "voice")
    record_artifact(ctx, "captions", "subtitle", subtitles_srt, "voice")


def vtt_to_srt(text: str) -> str:
    blocks = []
    cue_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or line.startswith("NOTE"):
            if cue_lines:
                blocks.append(cue_lines)
                cue_lines = []
            continue
        cue_lines.append(line)
    if cue_lines:
        blocks.append(cue_lines)

    cues = []
    for block in blocks:
        if not block:
            continue
        timing_index = 0 if "-->" in block[0] else 1
        if len(block) <= timing_index:
            continue
        timing = block[timing_index]
        caption_lines = block[timing_index + 1 :]
        if "-->" not in timing:
            continue
        start, end = _vtt_timing_to_milliseconds(timing)
        cues.append({"start": start, "end": end, "caption_lines": caption_lines})

    for index in range(1, len(cues)):
        previous = cues[index - 1]
        current = cues[index]
        if previous["end"] > current["start"]:
            previous["end"] = current["start"]

    srt_blocks = []
    for index, cue in enumerate(cues, start=1):
        timing = f"{_milliseconds_to_srt(cue['start'])} --> {_milliseconds_to_srt(cue['end'])}"
        srt_blocks.append("\n".join([str(index), timing, *cue["caption_lines"]]))
    return "\n\n".join(srt_blocks).rstrip() + ("\n" if srt_blocks else "")


def _vtt_timing_to_milliseconds(timing: str) -> tuple[int, int]:
    parts = timing.split(" --> ")
    if len(parts) != 2:
        raise ValueError(f"invalid VTT timing: {timing}")
    return _vtt_timestamp_to_milliseconds(parts[0]), _vtt_timestamp_to_milliseconds(parts[1])


def _vtt_timestamp_to_milliseconds(value: str) -> int:
    timestamp = value.split()[0]
    parts = timestamp.split(":")
    if len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds_part = parts[1]
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_part = parts[2]
    else:
        raise ValueError(f"invalid VTT timestamp: {value}")

    separator = "." if "." in seconds_part else "," if "," in seconds_part else ""
    if separator:
        seconds_text, milliseconds_text = seconds_part.split(separator, 1)
        milliseconds = int(milliseconds_text[:3].ljust(3, "0"))
    else:
        seconds_text = seconds_part
        milliseconds = 0
    seconds = int(seconds_text)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def _milliseconds_to_srt(value: int) -> str:
    hours = value // 3_600_000
    value %= 3_600_000
    minutes = value // 60_000
    value %= 60_000
    seconds = value // 1000
    milliseconds = value % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def render(ctx: RunContext) -> None:
    pipeline = pipeline_config(ctx)
    project = pipeline.get("project", {})
    video_config = pipeline.get("video", {})
    render_config = pipeline.get("render", {})
    draft = ctx.path("render/draft.mp4")
    final_video = ctx.path("render/final_16x9.mp4")

    render_video(
        audio_path=ctx.path("audio/narration.mp3"),
        subtitles_path=ctx.path("subtitles/captions.srt"),
        output_path=draft,
        title=str(project.get("name", "AI Video Maker")),
        subtitle=str(video_config.get("style", "需求对齐 -> 配音字幕 -> 横屏成片")),
        footer="ai-video-maker pipeline harness" if pipeline else "ai-video-maker p0 harness",
        fps=int(render_config.get("fps", 24)),
    )

    if render_config.get("auto_edit", True):
        run_command(
            [
                bin_path("auto-editor"),
                str(draft),
                "-o",
                str(final_video),
                "--no-open",
            ]
        )
    else:
        shutil.copyfile(draft, final_video)
    ctx.update_state("render_ready", "render")
    record_artifact(ctx, "draft_video", "video", draft, "render")
    record_artifact(ctx, "final_video", "video", final_video, "render")


def qa(ctx: RunContext) -> None:
    video = ctx.path("render/final_16x9.mp4")
    ffprobe_json = ctx.path("qa/ffprobe.json")
    screenshot = ctx.path("qa/screenshots/frame_6s.png")
    report = ctx.path("qa/report.md")

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    ffprobe_json.write_text(result.stdout, encoding="utf-8")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "6",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(screenshot),
        ]
    )

    report.write_text(
        "\n".join(
            [
                "# QA Report",
                "",
                f"- Video: `{video.relative_to(ctx.run_dir).as_posix()}`",
                "- Aspect: 16:9",
                "- Resolution target: 1920x1080",
                "- Checks:",
                "  - ffprobe completed",
                "  - keyframe screenshot extracted",
                "  - audio/video streams are present if ffprobe lists both streams",
                "",
                f"Screenshot: `qa/screenshots/{screenshot.name}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ctx.update_state("qa_ready", "qa")
    record_artifact(ctx, "qa_report", "markdown", report, "qa")
    record_artifact(ctx, "qa_screenshot", "image", screenshot, "qa")


def package(ctx: RunContext) -> None:
    package_dir = ctx.path("package")
    package_video = package_dir / "video.mp4"
    shutil.copyfile(ctx.path("render/final_16x9.mp4"), package_video)

    (package_dir / "title.txt").write_text("AI Video Maker：让 AI 完成技术视频制作流程\n", encoding="utf-8")
    (package_dir / "description.md").write_text(
        "\n".join(
            [
                "AI Video Maker 是一个实验性工具链，用于把视频需求拆解成脚本、配音、字幕、剪辑、QA 和发布包。",
                "",
                "本视频是 P0 harness 的横屏 YouTube demo。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (package_dir / "tags.txt").write_text("AI video,technical demo,automation,Python,MoviePy\n", encoding="utf-8")
    (package_dir / "upload_checklist.md").write_text(
        "\n".join(
            [
                "# Upload Checklist",
                "",
                "- [ ] Confirm target YouTube account",
                "- [ ] Confirm title and description",
                "- [ ] Confirm visibility",
                "- [ ] Confirm upload action",
                "",
                "Upload and publish are not automatic in P0.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    ctx.update_state("package_ready", "package")
    record_artifact(ctx, "package_video", "video", package_video, "package")
    record_artifact(ctx, "upload_checklist", "markdown", package_dir / "upload_checklist.md", "package")
