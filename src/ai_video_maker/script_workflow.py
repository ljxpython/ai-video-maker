from __future__ import annotations

from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .stages import pipeline_config


def generate_video_script(ctx: RunContext) -> dict[str, Any]:
    if _approval_status(ctx, "plan") != "approved":
        raise PermissionError("plan gate must be approved before video-script outputs can be generated")

    pipeline = pipeline_config(ctx)
    storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
    capability_plan = read_yaml(ctx.path("plan/capability_plan.yml"))
    narration = ctx.path("script/narration.zh.txt").read_text(encoding="utf-8").strip()
    terminal_actions = _terminal_actions_yaml(pipeline, capability_plan)
    if terminal_actions:
        write_yaml(ctx.path("script/terminal_actions.yml"), terminal_actions)
    screen_actions = _screen_actions_yaml(ctx, capability_plan)
    if screen_actions:
        write_yaml(ctx.path("script/screen_actions.yml"), screen_actions)
    next_skill = _next_skill_from_context(pipeline, capability_plan, bool(screen_actions), bool(terminal_actions))

    ctx.path("script/screen_actions.md").write_text(_screen_actions_markdown(storyboard), encoding="utf-8")
    if terminal_actions:
        ctx.path("script/terminal_actions.md").write_text(_terminal_actions_markdown(terminal_actions), encoding="utf-8")
    ctx.path("script/subtitle_draft.srt").write_text(_subtitle_draft(narration, storyboard), encoding="utf-8")
    ctx.path("script/shot_notes.md").write_text(_shot_notes_markdown(storyboard), encoding="utf-8")
    handoff = _handoff(ctx, next_skill, capability_plan)
    write_yaml(ctx.path("script/handoff.video-script.yml"), handoff)

    record_artifact(ctx, "screen_actions", "markdown", ctx.path("script/screen_actions.md"), "script")
    if screen_actions:
        record_artifact(ctx, "screen_actions_yml", "yaml", ctx.path("script/screen_actions.yml"), "script")
    if terminal_actions:
        record_artifact(ctx, "terminal_actions", "markdown", ctx.path("script/terminal_actions.md"), "script")
        record_artifact(ctx, "terminal_actions_yml", "yaml", ctx.path("script/terminal_actions.yml"), "script")
    record_artifact(ctx, "subtitle_draft", "subtitle", ctx.path("script/subtitle_draft.srt"), "script")
    record_artifact(ctx, "shot_notes", "markdown", ctx.path("script/shot_notes.md"), "script")
    record_artifact(ctx, "video_script_handoff", "yaml", ctx.path("script/handoff.video-script.yml"), "script")
    ctx.update_state("script_ready", "script", next_action=f"review script; next skill: {next_skill}")
    return handoff


def _approval_status(ctx: RunContext, gate: str) -> str:
    approvals = read_yaml(ctx.approvals_path)
    return str(approvals.get(gate, {}).get("status", "pending"))


def _next_skill_from_context(pipeline: dict[str, Any], capability_plan: dict[str, Any], has_screen_actions: bool, has_terminal_actions: bool) -> str:
    required = capability_plan.get("required", [])
    required_list = [str(item) for item in required] if isinstance(required, list) else []
    if "browser" in required_list:
        return "browser-capture"
    if "chrome" in required_list:
        return "chrome-capture"
    if "computer_use" in required_list:
        return "desktop-capture"
    if has_terminal_actions or str(pipeline.get("source", {}).get("type", "")) == "repository":
        return "terminal-capture"
    if has_screen_actions:
        return "browser-capture"
    return "voice-subtitle"


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


def _terminal_actions_yaml(pipeline: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    source = pipeline.get("source", {})
    source_type = str(source.get("type", "")).strip()
    if source_type != "repository":
        return {}

    return {
        "version": 1,
        "working_directory": ".",
        "requires_gate": "execution",
        "commands": [
            {
                "id": "check_python",
                "title": "检查 Python 版本",
                "command": "python --version",
                "allow_failure": False,
                "highlight": ["Python"],
            },
            {
                "id": "git_status",
                "title": "查看 Git 状态",
                "command": "git status",
                "allow_failure": False,
                "highlight": ["working tree"],
            },
            {
                "id": "run_tests",
                "title": "运行测试",
                "command": ".venv/bin/python -m unittest discover -s tests",
                "allow_failure": False,
                "highlight": ["OK"],
            },
        ],
    }


def _terminal_actions_markdown(terminal_actions: dict[str, Any]) -> str:
    lines = ["# Terminal Actions", ""]
    for command in terminal_actions.get("commands", []):
        if not isinstance(command, dict):
            continue
        lines.extend(
            [
                f"## {command.get('id', '')}",
                f"- Title: {command.get('title', '')}",
                f"- Command: `{command.get('command', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _screen_actions_yaml(ctx: RunContext, capability_plan: dict[str, Any]) -> dict[str, Any]:
    required = capability_plan.get("required", [])
    if not isinstance(required, list) or "browser" not in required:
        return {}

    preflight = read_yaml(ctx.path("plan/browser_preflight.yml"))
    target_url = str(preflight.get("target_url", "")).strip()
    if not target_url:
        return {}
    viewport = preflight.get("viewport", {})
    recording = preflight.get("recording", {})
    return {
        "version": 1,
        "target_url": target_url,
        "viewport": viewport if isinstance(viewport, dict) else {"width": 1920, "height": 1080},
        "recording": {
            "enabled": True,
            "output": "assets/browser/demo.webm",
            "duration_seconds": int(recording.get("duration_seconds", 5)) if isinstance(recording, dict) else 5,
        },
        "actions": [
            {"id": "open_target", "type": "goto", "url": target_url},
            {"id": "wait_loaded", "type": "wait", "duration_ms": 1000},
            {"id": "screenshot_loaded", "type": "screenshot", "output": "assets/browser/steps/003_screenshot_loaded.png"},
            {"id": "record_overview", "type": "record_segment", "duration_ms": 3000},
        ],
    }


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
            "script/screen_actions.yml",
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
