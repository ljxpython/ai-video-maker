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
    narration = ctx.path("script/narration.zh.txt")
    audio = ctx.path("audio/narration.mp3")
    subtitles_vtt = ctx.path("subtitles/captions.vtt")
    subtitles_srt = ctx.path("subtitles/captions.srt")

    run_command(
        [
            bin_path("edge-tts"),
            "--file",
            str(narration),
            "--voice",
            "zh-CN-XiaoxiaoNeural",
            "--rate",
            "+0%",
            "--write-media",
            str(audio),
            "--write-subtitles",
            str(subtitles_vtt),
        ]
    )
    shutil.copyfile(subtitles_vtt, subtitles_srt)
    ctx.update_state("voice_ready", "voice")
    record_artifact(ctx, "voice", "audio", audio, "voice")
    record_artifact(ctx, "captions", "subtitle", subtitles_srt, "voice")


def render(ctx: RunContext) -> None:
    draft = ctx.path("render/draft.mp4")
    final_video = ctx.path("render/final_16x9.mp4")

    render_video(
        audio_path=ctx.path("audio/narration.mp3"),
        subtitles_path=ctx.path("subtitles/captions.srt"),
        output_path=draft,
        title="AI Video Maker",
        subtitle="需求对齐 -> 配音字幕 -> 横屏成片",
        footer="ai-video-maker p0 harness",
        fps=24,
    )

    run_command(
        [
            bin_path("auto-editor"),
            str(draft),
            "-o",
            str(final_video),
            "--no-open",
        ]
    )
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
