from __future__ import annotations

from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml


def generate_video_script(ctx: RunContext) -> dict[str, Any]:
    if _approval_status(ctx, "plan") != "approved":
        raise PermissionError("plan gate must be approved before video-script outputs can be generated")

    storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
    capability_plan = read_yaml(ctx.path("plan/capability_plan.yml"))
    narration = ctx.path("script/narration.zh.txt").read_text(encoding="utf-8").strip()
    next_skill = _next_skill_from_capabilities(capability_plan)

    ctx.path("script/screen_actions.md").write_text(_screen_actions_markdown(storyboard), encoding="utf-8")
    ctx.path("script/subtitle_draft.srt").write_text(_subtitle_draft(narration, storyboard), encoding="utf-8")
    ctx.path("script/shot_notes.md").write_text(_shot_notes_markdown(storyboard), encoding="utf-8")
    handoff = _handoff(ctx, next_skill, capability_plan)
    write_yaml(ctx.path("script/handoff.video-script.yml"), handoff)

    record_artifact(ctx, "screen_actions", "markdown", ctx.path("script/screen_actions.md"), "script")
    record_artifact(ctx, "subtitle_draft", "subtitle", ctx.path("script/subtitle_draft.srt"), "script")
    record_artifact(ctx, "shot_notes", "markdown", ctx.path("script/shot_notes.md"), "script")
    record_artifact(ctx, "video_script_handoff", "yaml", ctx.path("script/handoff.video-script.yml"), "script")
    ctx.update_state("script_ready", "script", next_action=f"review script; next skill: {next_skill}")
    return handoff


def _approval_status(ctx: RunContext, gate: str) -> str:
    approvals = read_yaml(ctx.approvals_path)
    return str(approvals.get(gate, {}).get("status", "pending"))


def _next_skill_from_capabilities(capability_plan: dict[str, Any]) -> str:
    required = capability_plan.get("required", [])
    return "browser-capture" if isinstance(required, list) and required else "voice-subtitle"


def _screen_actions_markdown(storyboard: dict[str, Any]) -> str:
    lines = ["# Screen Actions", ""]
    for section in _sections(storyboard):
        lines.extend(
            [
                f"## {section['id']} ({section['duration']}s)",
                f"- Purpose: {section['purpose']}",
                f"- Visual: {section['visual']}",
                f"- Narration intent: {section['narration']}",
                "- Action: prepare generated visual or captured clip that matches the visual line.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _shot_notes_markdown(storyboard: dict[str, Any]) -> str:
    lines = [
        "# Shot Notes",
        "",
        f"- Title: {storyboard.get('title', '')}",
        f"- Aspect ratio: {storyboard.get('aspect_ratio', '16:9')}",
        f"- Target duration: {storyboard.get('target_duration', 0)}s",
        "",
    ]
    for section in _sections(storyboard):
        lines.append(f"- {section['id']}: keep the visual readable for {section['duration']}s; avoid covering UI with subtitles.")
    return "\n".join(lines).rstrip() + "\n"


def _subtitle_draft(narration: str, storyboard: dict[str, Any]) -> str:
    lines = [line.strip() for line in narration.splitlines() if line.strip()]
    if not lines:
        return ""

    duration = _target_duration(storyboard)
    segment = duration / len(lines)
    blocks = []
    for index, line in enumerate(lines, start=1):
        start = (index - 1) * segment
        end = index * segment
        subtitle_text = "\n".join(_wrap_subtitle_line(line))
        blocks.append(f"{index}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{subtitle_text}\n")
    return "\n".join(blocks).rstrip() + "\n"


def _wrap_subtitle_line(line: str, max_chars: int = 36) -> list[str]:
    if len(line) <= max_chars:
        return [line]

    chunks = []
    current = ""
    for token in _subtitle_tokens(line):
        if current and token in "，。；：、,.!?！？":
            current += token
            if len(current) >= max_chars * 0.6:
                chunks.append(current.strip())
                current = ""
            continue
        candidate = current + token
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = token
        else:
            current = candidate
        if current and len(current) >= max_chars and current[-1] in "，。；：、,.!?！？":
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _subtitle_tokens(line: str) -> list[str]:
    tokens = []
    current = ""
    for char in line:
        if char.isascii() and (char.isalnum() or char in "_-"):
            current += char
            continue
        if current:
            tokens.append(current)
            current = ""
        tokens.append(char)
    if current:
        tokens.append(current)
    return tokens


def _handoff(ctx: RunContext, next_skill: str, capability_plan: dict[str, Any]) -> dict[str, Any]:
    required = capability_plan.get("required", [])
    risks = []
    if isinstance(required, list) and required:
        risks.append("execution gate is required before browser, Chrome, or desktop capture")

    return {
        "skill": "video-script",
        "run_id": ctx.run_id,
        "status": "ready_for_review",
        "outputs": [
            "script/narration.zh.txt",
            "script/screen_actions.md",
            "script/subtitle_draft.srt",
            "script/shot_notes.md",
        ],
        "review_checklist": [
            "Confirm narration tone",
            "Confirm subtitle readability",
            "Confirm screen action order",
        ],
        "risks": risks,
        "next_gate": None,
        "next_skill_suggestion": next_skill,
        "revision_skill_suggestion": "video-script",
        "user_action_required": False,
        "user_message": f"Please review the narration and screen actions. If approved, the next recommended skill is {next_skill}.",
    }


def _sections(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sections = storyboard.get("sections", [])
    return [section for section in raw_sections if isinstance(section, dict)]


def _target_duration(storyboard: dict[str, Any]) -> float:
    value = storyboard.get("target_duration", 60)
    return float(value if isinstance(value, int) and value > 0 else 60)


def _format_srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    whole_seconds = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"
