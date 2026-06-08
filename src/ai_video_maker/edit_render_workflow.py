from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .renderer import render_mixed_video
from .stages import bin_path, pipeline_config, run_command


DEFAULT_PROFILE = "youtube_16x9"


def generate_edit_render(ctx: RunContext, profiles: list[str] | None = None) -> dict[str, Any]:
    voice_handoff = read_yaml(ctx.path("subtitles/handoff.voice-subtitle.yml"))
    if voice_handoff.get("skill") != "voice-subtitle":
        raise FileNotFoundError("subtitles/handoff.voice-subtitle.yml is required before edit-render")
    if voice_handoff.get("status") not in {"ready_for_review", "done"}:
        raise PermissionError("voice-subtitle handoff must be ready_for_review or done before edit-render")

    pipeline = pipeline_config(ctx)
    render_config = pipeline.get("render", {})
    storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
    browser_recording = _browser_recording(ctx)
    terminal_cards = _terminal_cards(ctx)
    selected_profiles = profiles or [DEFAULT_PROFILE]
    profile_outputs: dict[str, dict[str, Any]] = {}

    for profile_id in selected_profiles:
        profile = _load_profile(ctx, profile_id)
        draft = ctx.path(str(profile["draft"]))
        final_video = ctx.path(str(profile["output"]))
        render_mixed_video(
            audio_path=ctx.path("audio/narration.mp3"),
            subtitles_path=ctx.path("subtitles/captions.srt"),
            storyboard=storyboard,
            output_path=draft,
            browser_recording_path=browser_recording,
            terminal_card_paths=terminal_cards,
            width=int(profile["width"]),
            height=int(profile["height"]),
            fps=int(render_config.get("fps", profile["fps"])),
        )

        if render_config.get("auto_edit", True):
            run_command([bin_path("auto-editor"), str(draft), "-o", str(final_video), "--no-open"])
        else:
            shutil.copyfile(draft, final_video)
        profile_outputs[profile_id] = {
            "draft": str(profile["draft"]),
            "output": str(profile["output"]),
            "resolution": f"{profile['width']}x{profile['height']}",
            "package_dir": str(profile["package_dir"]),
        }

    handoff = _handoff(ctx, browser_recording, terminal_cards, profile_outputs)
    write_yaml(ctx.path("render/handoff.edit-render.yml"), handoff)
    for profile_id, output in profile_outputs.items():
        record_artifact(ctx, f"draft_video_{profile_id}", "video", ctx.path(output["draft"]), "edit-render")
        record_artifact(ctx, f"final_video_{profile_id}", "video", ctx.path(output["output"]), "edit-render")
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


def _terminal_cards(ctx: RunContext) -> list[Path]:
    handoff = read_yaml(ctx.path("assets/terminal/handoff.terminal-capture.yml"))
    outputs = handoff.get("outputs", [])
    cards = []
    if isinstance(outputs, list):
        for output in outputs:
            if isinstance(output, str) and output.endswith(".png"):
                path = ctx.path(output)
                if path.exists():
                    cards.append(path)
    if cards:
        return cards
    return sorted(ctx.path("assets/terminal/cards").glob("*.png"))


def _load_profile(ctx: RunContext, profile_id: str) -> dict[str, Any]:
    path = ctx.project_root / "templates" / "render_profiles" / f"{profile_id}.yml"
    profile = read_yaml(path)
    if not profile:
        if profile_id == "youtube_16x9":
            profile = {"resolution": {"width": 1920, "height": 1080}, "fps": 24, "output": "render/final_16x9.mp4", "package_dir": "package/youtube"}
        elif profile_id == "shorts_9x16":
            profile = {"resolution": {"width": 1080, "height": 1920}, "fps": 24, "output": "render/final_9x16.mp4", "package_dir": "package/shorts"}
        else:
            raise ValueError(f"unknown render profile: {profile_id}")
    resolution = profile.get("resolution", {})
    if isinstance(resolution, str) and "x" in resolution:
        width_text, height_text = resolution.split("x", 1)
        width, height = int(width_text), int(height_text)
    elif isinstance(resolution, dict):
        width, height = int(resolution.get("width", 1920)), int(resolution.get("height", 1080))
    else:
        width, height = 1920, 1080
    output = str(profile.get("output") or ("render/final_9x16.mp4" if profile_id.endswith("9x16") else "render/final_16x9.mp4"))
    draft = "render/draft.mp4" if output == "render/final_16x9.mp4" else output.replace("final_", "draft_", 1)
    return {
        "id": profile_id,
        "width": width,
        "height": height,
        "fps": int(profile.get("fps", 24)),
        "output": output,
        "draft": draft,
        "package_dir": profile.get("package_dir", "package/youtube"),
    }


def _handoff(ctx: RunContext, browser_recording: Path | None, terminal_cards: list[Path], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    for profile in profiles.values():
        outputs.extend([profile["draft"], profile["output"]])
    risks = []
    if browser_recording:
        risks.append("browser recording was mixed into the final render")
    if terminal_cards:
        risks.append("terminal cards were mixed into the final render")
    return {
        "skill": "edit-render",
        "run_id": ctx.run_id,
        "status": "ready_for_review",
        "outputs": outputs,
        "profiles": profiles,
        "review_checklist": [
            "Confirm final video exists and is playable",
            "Confirm card sections match storyboard",
            "Confirm browser recording segment appears when available",
            "Confirm terminal cards appear when available",
            "Confirm subtitles do not cover critical visuals",
        ],
        "risks": risks,
        "next_gate": None,
        "next_skill_suggestion": "qa-revision",
        "revision_skill_suggestion": "edit-render",
        "user_action_required": False,
        "user_message": "Please review the rendered video. If approved, the next recommended skill is qa-revision.",
    }
