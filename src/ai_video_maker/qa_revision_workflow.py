from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_json, write_yaml
from .stages import bin_path, run_command


def generate_qa_revision(ctx: RunContext) -> dict[str, Any]:
    edit_handoff = read_yaml(ctx.path("render/handoff.edit-render.yml"))
    if edit_handoff.get("skill") != "edit-render":
        raise FileNotFoundError("render/handoff.edit-render.yml is required before qa-revision")
    if edit_handoff.get("status") not in {"ready_for_review", "done"}:
        raise PermissionError("edit-render handoff must be ready_for_review or done before qa-revision")

    video = ctx.path("render/final_16x9.mp4")
    captions = ctx.path("subtitles/captions.srt")
    ffprobe_json = ctx.path("qa/ffprobe.json")
    screenshot = ctx.path("qa/screenshots/frame_6s.png")
    report = ctx.path("qa/report.md")

    checks: list[dict[str, Any]] = []
    probe: dict[str, Any] = {}

    video_exists = video.exists() and video.stat().st_size > 0
    _add_check(checks, "video_file", video_exists, "render/final_16x9.mp4 exists and is non-empty")

    captions_text = captions.read_text(encoding="utf-8").strip() if captions.exists() else ""
    _add_check(checks, "captions_non_empty", bool(captions_text), "subtitles/captions.srt exists and has text")

    if video_exists:
        probe = _ffprobe(video)
        write_json(ffprobe_json, probe)
        streams = probe.get("streams", []) if isinstance(probe.get("streams"), list) else []
        has_video = any(item.get("codec_type") == "video" for item in streams if isinstance(item, dict))
        has_audio = any(item.get("codec_type") == "audio" for item in streams if isinstance(item, dict))
        _add_check(checks, "video_stream", has_video, "ffprobe found a video stream")
        _add_check(checks, "audio_stream", has_audio, "ffprobe found an audio stream")
        _add_check(checks, "keyframe_screenshot", _extract_screenshot(video, screenshot), "ffmpeg extracted frame_6s.png")
    else:
        write_json(ffprobe_json, {"error": "video file missing or empty", "streams": []})
        _add_check(checks, "video_stream", False, "ffprobe skipped because video is missing")
        _add_check(checks, "audio_stream", False, "ffprobe skipped because video is missing")
        _add_check(checks, "keyframe_screenshot", False, "screenshot skipped because video is missing")

    passed = all(item["passed"] for item in checks)
    revision_skill = _revision_skill(checks)
    handoff = _handoff(ctx, passed, revision_skill)

    report.write_text(_report(ctx, checks, probe, handoff, screenshot), encoding="utf-8")
    write_yaml(ctx.path("qa/handoff.qa-revision.yml"), handoff)

    record_artifact(ctx, "qa_report", "markdown", report, "qa-revision")
    record_artifact(ctx, "qa_ffprobe", "json", ffprobe_json, "qa-revision")
    if screenshot.exists():
        record_artifact(ctx, "qa_screenshot", "image", screenshot, "qa-revision")
    record_artifact(ctx, "qa_revision_handoff", "yaml", ctx.path("qa/handoff.qa-revision.yml"), "qa-revision")

    status = "qa_revision_ready" if passed else "qa_revision_needs_revision"
    next_action = "review QA; next skill: publish-package" if passed else f"review QA; revise with: {revision_skill}"
    ctx.update_state(status, "qa-revision", next_action=next_action)
    return handoff


def _ffprobe(video: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            bin_path("ffprobe"),
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
    return json.loads(result.stdout or "{}")


def _extract_screenshot(video: Path, screenshot: Path) -> bool:
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_command(
            [
                bin_path("ffmpeg"),
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
    except subprocess.CalledProcessError:
        return False
    return screenshot.exists() and screenshot.stat().st_size > 0


def _add_check(checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str) -> None:
    checks.append({"id": check_id, "passed": bool(passed), "detail": detail})


def _revision_skill(checks: list[dict[str, Any]]) -> str:
    failed = {item["id"] for item in checks if not item["passed"]}
    if "video_file" in failed or "video_stream" in failed or "keyframe_screenshot" in failed:
        return "edit-render"
    if failed & {"captions_non_empty", "audio_stream"}:
        return "voice-subtitle"
    return "edit-render"


def _handoff(ctx: RunContext, passed: bool, revision_skill: str) -> dict[str, Any]:
    return {
        "skill": "qa-revision",
        "run_id": ctx.run_id,
        "status": "ready_for_review" if passed else "needs_revision",
        "outputs": [
            "qa/report.md",
            "qa/ffprobe.json",
            "qa/screenshots/frame_6s.png",
            "qa/handoff.qa-revision.yml",
        ],
        "review_checklist": [
            "Confirm final video is playable",
            "Confirm QA report has video and audio streams",
            "Confirm subtitles are present and readable",
            "Confirm keyframe screenshot is not blank or misframed",
        ],
        "risks": [] if passed else ["QA checks failed; revise before packaging"],
        "next_gate": None,
        "next_skill_suggestion": "publish-package" if passed else revision_skill,
        "revision_skill_suggestion": revision_skill,
        "user_action_required": False,
        "user_message": (
            "Please review the QA report. If approved, the next recommended skill is publish-package."
            if passed
            else f"QA needs revision. The recommended revision skill is {revision_skill}."
        ),
    }


def _report(ctx: RunContext, checks: list[dict[str, Any]], probe: dict[str, Any], handoff: dict[str, Any], screenshot: Path) -> str:
    streams = probe.get("streams", []) if isinstance(probe.get("streams"), list) else []
    video_stream = next((item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"), {})
    lines = [
        "# QA Revision Report",
        "",
        f"- Run: `{ctx.run_id}`",
        f"- Status: `{handoff['status']}`",
        f"- Final video: `render/final_16x9.mp4`",
        f"- Screenshot: `qa/screenshots/{screenshot.name}`",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- [{marker}] `{item['id']}`: {item['detail']}")

    lines.extend(
        [
            "",
            "## Streams",
            "",
            f"- Video: `{video_stream.get('codec_name', 'missing')}` {video_stream.get('width', '?')}x{video_stream.get('height', '?')}",
            f"- Audio: `{audio_stream.get('codec_name', 'missing')}`",
            "",
            "## Next",
            "",
            f"- Next skill: `{handoff['next_skill_suggestion']}`",
            f"- Revision skill: `{handoff['revision_skill_suggestion']}`",
            "",
        ]
    )
    return "\n".join(lines)
