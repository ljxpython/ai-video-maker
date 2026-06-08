from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


GUI_CAPABILITIES = ("browser", "chrome", "computer_use")


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
        "notes": [
            "P0 capability adapters only produce a dry-run plan.",
            "No browser, Chrome, desktop app, upload, or account action is executed.",
            "Required GUI capabilities must pass the execution gate before real execution is allowed.",
        ],
    }


def required_capability_names(pipeline: dict[str, Any]) -> list[str]:
    plan = capability_plan_from_pipeline(pipeline)
    return list(plan["required"])
