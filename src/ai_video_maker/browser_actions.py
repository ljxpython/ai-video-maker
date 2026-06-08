from __future__ import annotations

from typing import Any

from .context import RunContext
from .io import read_yaml


ACTION_TYPES = {"goto", "click", "fill", "press", "scroll", "wait_for_selector", "wait", "screenshot", "record_segment"}


def load_screen_actions(ctx: RunContext) -> dict[str, Any]:
    path = ctx.path("script/screen_actions.yml")
    if not path.exists():
        return {}
    return normalize_screen_actions(read_yaml(path))


def normalize_screen_actions(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        raise ValueError("screen actions file is empty")
    if data.get("version") != 1:
        raise ValueError("screen actions version must be 1")
    target_url = str(data.get("target_url", "")).strip()
    if not target_url:
        raise ValueError("screen actions target_url is required")

    viewport = data.get("viewport", {})
    if not isinstance(viewport, dict):
        viewport = {}
    recording = data.get("recording", {})
    if not isinstance(recording, dict):
        recording = {}

    actions = data.get("actions", [])
    if not isinstance(actions, list):
        raise ValueError("screen actions actions must be a list")
    seen: set[str] = set()
    normalized_actions = []
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("each screen action must be a mapping")
        action_id = str(action.get("id", "")).strip()
        action_type = str(action.get("type", "")).strip()
        if not action_id:
            raise ValueError("screen action id is required")
        if action_id in seen:
            raise ValueError(f"duplicate screen action id: {action_id}")
        if action_type not in ACTION_TYPES:
            raise ValueError(f"unsupported screen action type: {action_type}")
        _validate_action(action_id, action_type, action)
        seen.add(action_id)
        normalized_actions.append(dict(action, id=action_id, type=action_type))

    return {
        "version": 1,
        "target_url": target_url,
        "viewport": {
            "width": _positive_int(viewport.get("width"), 1920),
            "height": _positive_int(viewport.get("height"), 1080),
        },
        "recording": {
            "enabled": bool(recording.get("enabled", True)),
            "output": str(recording.get("output", "assets/browser/demo.webm")),
            "duration_seconds": _positive_int(recording.get("duration_seconds"), 5),
        },
        "actions": normalized_actions,
    }


def _validate_action(action_id: str, action_type: str, action: dict[str, Any]) -> None:
    if action_type == "goto" and not str(action.get("url", "")).strip():
        raise ValueError(f"screen action {action_id} requires url")
    if action_type in {"click", "wait_for_selector"} and not str(action.get("selector", "")).strip():
        raise ValueError(f"screen action {action_id} requires selector")
    if action_type == "fill":
        if not str(action.get("selector", "")).strip():
            raise ValueError(f"screen action {action_id} requires selector")
        if "value" not in action:
            raise ValueError(f"screen action {action_id} requires value")
    if action_type == "press" and not str(action.get("key", "")).strip():
        raise ValueError(f"screen action {action_id} requires key")


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default
