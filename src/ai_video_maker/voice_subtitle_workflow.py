from __future__ import annotations

from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .stages import generate_voice


def generate_voice_subtitle(ctx: RunContext) -> dict[str, Any]:
    script_handoff = read_yaml(ctx.path("script/handoff.video-script.yml"))
    if script_handoff.get("skill") != "video-script":
        raise FileNotFoundError("script/handoff.video-script.yml is required before voice-subtitle")
    if script_handoff.get("status") not in {"ready_for_review", "done"}:
        raise PermissionError("video-script handoff must be ready_for_review or done before voice-subtitle")

    generate_voice(ctx)
    handoff = _handoff(ctx)
    write_yaml(ctx.path("subtitles/handoff.voice-subtitle.yml"), handoff)
    record_artifact(ctx, "voice_subtitle_handoff", "yaml", ctx.path("subtitles/handoff.voice-subtitle.yml"), "voice")
    ctx.update_state("voice_subtitle_ready", "voice-subtitle", next_action="review voice/subtitles; next skill: edit-render")
    return handoff


def _handoff(ctx: RunContext) -> dict[str, Any]:
    return {
        "skill": "voice-subtitle",
        "run_id": ctx.run_id,
        "status": "ready_for_review",
        "outputs": [
            "audio/narration.mp3",
            "subtitles/captions.srt",
        ],
        "review_checklist": [
            "Confirm narration audio exists and is playable",
            "Confirm subtitle timing exists",
            "Confirm subtitle text is readable before render",
        ],
        "risks": [],
        "next_gate": None,
        "next_skill_suggestion": "edit-render",
        "revision_skill_suggestion": "voice-subtitle",
        "user_action_required": False,
        "user_message": "Please review the generated voice and captions. If approved, the next recommended skill is edit-render.",
    }
