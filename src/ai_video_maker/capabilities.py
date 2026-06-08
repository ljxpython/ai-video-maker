from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


GUI_CAPABILITIES = ("browser", "chrome", "computer_use")
DEFAULT_BROWSER_CHECKS = ["page_load", "title_present", "screenshot_non_blank"]
DEFAULT_BROWSER_VIEWPORT = {"width": 1920, "height": 1080}


@dataclass(frozen=True)
class CapabilityDefinition:
    name: str
    label: str
    gate: str
    purpose: str


@dataclass(frozen=True)
class CapabilityDryRun:
    name: str
    label: str
    required: bool
    gate: str
    status: str
    action: str
    purpose: str


CAPABILITY_DEFINITIONS = {
    "browser": CapabilityDefinition(
        name="browser",
        label="$browser",
        gate="execution",
        purpose="record or inspect regular web pages and local web demos",
    ),
    "chrome": CapabilityDefinition(
        name="chrome",
        label="$chrome",
        gate="execution",
        purpose="operate authenticated browser sessions after explicit approval",
    ),
    "computer_use": CapabilityDefinition(
        name="computer_use",
        label="$computer-use",
        gate="execution",
        purpose="operate desktop apps, file pickers, and native GUI workflows",
    ),
}


def capability_plan_from_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    capabilities = pipeline.get("capabilities", {})
    items = []
    required = []
    for name in GUI_CAPABILITIES:
        definition = CAPABILITY_DEFINITIONS[name]
        config = capabilities.get(name, {}) if isinstance(capabilities, dict) else {}
        is_required = bool(config.get("required") is True) if isinstance(config, dict) else False
        status = "requires_execution_approval" if is_required else "optional"
        action = "dry_run_only"
        item = CapabilityDryRun(
            name=name,
            label=definition.label,
            required=is_required,
            gate=definition.gate,
            status=status,
            action=action,
            purpose=definition.purpose,
        )
        items.append(asdict(item))
        if is_required:
            required.append(name)

    return {
        "mode": "dry_run",
        "required": required,
        "capabilities": items,
        "browser_preflight": browser_preflight_plan_from_pipeline(pipeline),
        "notes": [
            "P0 capability adapters only produce a dry-run plan.",
            "No browser, Chrome, desktop app, upload, or account action is executed.",
            "Required GUI capabilities must pass the execution gate before real execution is allowed.",
        ],
    }


def required_capability_names(pipeline: dict[str, Any]) -> list[str]:
    plan = capability_plan_from_pipeline(pipeline)
    return list(plan["required"])


def browser_preflight_plan_from_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    config = _capability_config(pipeline, "browser")
    recording = config.get("recording", {}) if isinstance(config.get("recording", {}), dict) else {}
    target_url = str(config.get("target_url", "")).strip()
    required = bool(config.get("required") is True)
    recording_enabled = bool(recording.get("enabled") is True)
    enabled = required or bool(target_url) or recording_enabled

    checks = config.get("checks", DEFAULT_BROWSER_CHECKS)
    if not isinstance(checks, list) or not checks:
        checks = DEFAULT_BROWSER_CHECKS

    viewport = config.get("viewport", DEFAULT_BROWSER_VIEWPORT)
    if not isinstance(viewport, dict):
        viewport = DEFAULT_BROWSER_VIEWPORT

    status = "disabled"
    if enabled:
        status = "missing_target_url" if not target_url else "ready_for_execution_gate"

    return {
        "mode": "dry_run",
        "adapter": "browser",
        "enabled": enabled,
        "required": required,
        "gate": "execution",
        "status": status,
        "target_url": target_url,
        "target_kind": _target_kind(target_url),
        "viewport": {
            "width": _positive_int(viewport.get("width"), DEFAULT_BROWSER_VIEWPORT["width"]),
            "height": _positive_int(viewport.get("height"), DEFAULT_BROWSER_VIEWPORT["height"]),
        },
        "checks": [str(item) for item in checks],
        "recording": {
            "enabled": recording_enabled,
            "duration_seconds": _positive_int(recording.get("duration_seconds"), 0),
            "output": str(recording.get("output", "assets/browser_recording.mp4")),
        },
        "actions": [
            "open_target_url",
            "wait_for_page_load",
            "capture_screenshot",
            "verify_non_blank_frame",
        ],
        "notes": [
            "This is a preflight plan only.",
            "The adapter does not open Browser or record video in P0.",
        ],
    }


def _capability_config(pipeline: dict[str, Any], name: str) -> dict[str, Any]:
    capabilities = pipeline.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return {}
    config = capabilities.get(name, {})
    return config if isinstance(config, dict) else {}


def _target_kind(target_url: str) -> str:
    if not target_url:
        return "none"
    local_prefixes = ("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1", "http://[::1]", "https://[::1]")
    return "local_web" if target_url.startswith(local_prefixes) else "web"


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default
