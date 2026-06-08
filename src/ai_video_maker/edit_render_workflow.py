from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .renderer import render_mixed_video
from .stages import bin_path, pipeline_config, run_command


def generate_edit_render(ctx: RunContext) -> dict[str, Any]:
    voice_handoff = read_yaml(ctx.path("subtitles/handoff.voice-subtitle.yml"))
    if voice_handoff.get("skill") != "voice-subtitle":
        raise FileNotFoundError("subtitles/handoff.voice-subtitle.yml is required before edit-render")
    if voice_handoff.get("status") not in {"ready_for_review", "done"}:
        raise PermissionError("voice-subtitle handoff must be ready_for_review or done before edit-render")

    pipeline = pipeline_config(ctx)
    render_config = pipeline.get("render", {})
    storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
    draft = ctx.path("render/draft.mp4")
    final_video = ctx.path("render/final_16x9.mp4")
    browser_recording = _browser_recording(ctx)

    render_mixed_video(
        audio_path=ctx.path("audio/narration.mp3"),
        subtitles_path=ctx.path("subtitles/captions.srt"),
        storyboard=storyboard,
        output_path=draft,
        browser_recording_path=browser_recording,
        fps=int(render_config.get("fps", 24)),
    )

    if render_config.get("auto_edit", True):
        run_command([bin_path("auto-editor"), str(draft), "-o", str(final_video), "--no-open"])
    else:
        shutil.copyfile(draft, final_video)

    handoff = _handoff(ctx, browser_recording)
    write_yaml(ctx.path("render/handoff.edit-render.yml"), handoff)
    record_artifact(ctx, "draft_video", "video", draft, "edit-render")
    record_artifact(ctx, "final_video", "video", final_video, "edit-render")
    record_artifact(ctx, "edit_render_handoff", "yaml", ctx.path("render/handoff.edit-render.yml"), "edit-render")
    ctx.update_state("edit_render_ready", "edit-render", next_action="review render; next skill: qa-revision")
    return handoff


def _browser_recording(ctx: RunContext) -> Path | None:
    handoff = read_yaml(ctx.path("assets/browser/handoff.browser-capture.yml"))
    outputs = handoff.get("outputs", [])
    if isinstance(outputs, list):
        for output in outputs:
            if isinstance(output, str) and output.endswith((".mp4", ".webm", ".mov")):
                candidate = ctx.path(output)
                if candidate.exists():
                    return candidate
    fallback = ctx.path("assets/browser/demo.webm")
    return fallback if fallback.exists() else None


def _handoff(ctx: RunContext, browser_recording: Path | None) -> dict[str, Any]:
    outputs = ["render/draft.mp4", "render/final_16x9.mp4"]
    risks = []
    if browser_recording:
        risks.append("browser recording was mixed into the final render")
    return {
        "skill": "edit-render",
        "run_id": ctx.run_id,
        "status": "ready_for_review",
        "outputs": outputs,
        "review_checklist": [
            "Confirm final video exists and is playable",
            "Confirm card sections match storyboard",
            "Confirm browser recording segment appears when available",
            "Confirm subtitles do not cover critical visuals",
        ],
        "risks": risks,
        "next_gate": None,
        "next_skill_suggestion": "qa-revision",
        "revision_skill_suggestion": "edit-render",
        "user_action_required": False,
        "user_message": "Please review the rendered video. If approved, the next recommended skill is qa-revision.",
    }
