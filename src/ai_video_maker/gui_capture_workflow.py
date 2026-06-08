from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .browser_adapter import ensure_execution_approved
from .context import RunContext
from .io import read_yaml, write_json, write_yaml


def generate_chrome_operation_plan(ctx: RunContext) -> dict[str, Any]:
    pipeline = read_yaml(ctx.path("pipeline.yml"))
    config = _capability_config(pipeline, "chrome")
    plan = {
        "version": 1,
        "tool": "$chrome",
        "requires_gate": "execution",
        "target": {"kind": "authenticated_web", "url": str(config.get("target_url", "https://studio.youtube.com"))},
        "allowed_actions": ["inspect_visible_page", "click_visible_control", "type_user_approved_text", "screenshot_visible_page"],
        "forbidden_actions": ["read_cookies", "read_local_storage", "read_passwords", "upload_without_gate", "publish_without_gate"],
        "steps": [
            {
                "id": "inspect_page",
                "instruction": "打开目标页面并截取用户可见页面。",
                "evidence_required": ["screenshot"],
            }
        ],
    }
    write_yaml(ctx.path("plan/chrome_operation.yml"), plan)
    record_artifact(ctx, "chrome_operation_plan", "yaml", ctx.path("plan/chrome_operation.yml"), "chrome-capture")
    ctx.update_state("chrome_operation_planned", "chrome-capture", next_action="approve execution gate before recording Chrome result")
    return plan


def generate_desktop_operation_plan(ctx: RunContext) -> dict[str, Any]:
    pipeline = read_yaml(ctx.path("pipeline.yml"))
    config = _capability_config(pipeline, "computer_use")
    plan = {
        "version": 1,
        "tool": "$computer-use",
        "requires_gate": "execution",
        "target": {"kind": "desktop_app", "app_name": str(config.get("app_name", "desktop app"))},
        "allowed_actions": ["open_app", "click_visible_control", "type_user_approved_text", "screenshot_window"],
        "forbidden_actions": ["delete_files_without_confirmation", "change_system_settings_without_confirmation", "upload_without_gate", "publish_without_gate"],
        "steps": [
            {
                "id": "inspect_app",
                "instruction": "打开目标桌面应用并截取当前窗口。",
                "evidence_required": ["screenshot"],
            }
        ],
    }
    write_yaml(ctx.path("plan/desktop_operation.yml"), plan)
    record_artifact(ctx, "desktop_operation_plan", "yaml", ctx.path("plan/desktop_operation.yml"), "desktop-capture")
    ctx.update_state("desktop_operation_planned", "desktop-capture", next_action="approve execution gate before recording desktop result")
    return plan


def record_chrome_operation_result(ctx: RunContext, *, screenshot: Path, note: str = "", url: str = "", title: str = "", action: str = "inspect") -> dict[str, Any]:
    return _record_result(ctx, tool="$chrome", channel="chrome", screenshot=screenshot, note=note, url=url, title=title, action=action)


def record_desktop_operation_result(ctx: RunContext, *, screenshot: Path, note: str = "", app_name: str = "", action: str = "inspect") -> dict[str, Any]:
    return _record_result(ctx, tool="$computer-use", channel="desktop", screenshot=screenshot, note=note, app_name=app_name, action=action)


def _record_result(ctx: RunContext, *, tool: str, channel: str, screenshot: Path, note: str, action: str, **extra: str) -> dict[str, Any]:
    _check_side_effect_gate(ctx, action)
    ensure_execution_approved(ctx)
    target_dir = ctx.path(f"assets/{channel}")
    target_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dest = target_dir / f"{action}.png"
    shutil.copyfile(screenshot, screenshot_dest)
    status = "blocked" if action in {"upload", "publish"} else "passed"
    result = {
        "status": status,
        "tool": tool,
        "steps": [
            {
                "id": action,
                "status": status,
                "evidence": [screenshot_dest.relative_to(ctx.run_dir).as_posix()],
                "note": note or "Recorded user-visible result only; sensitive storage was not accessed.",
                **{key: value for key, value in extra.items() if value},
            }
        ],
        "safety": {
            "sensitive_storage_accessed": False,
            "upload_performed": False,
            "publish_performed": False,
        },
    }
    report = ctx.path(f"qa/{channel}_operation.md")
    result_json = ctx.path(f"qa/{channel}_operation.json")
    handoff_path = ctx.path(f"assets/{channel}/handoff.{channel}-capture.yml")
    report.write_text(_report(channel, result), encoding="utf-8")
    write_json(result_json, result)
    handoff = _handoff(ctx, channel, status, report)
    write_yaml(handoff_path, handoff)
    record_artifact(ctx, f"{channel}_operation_report", "markdown", report, f"{channel}-capture")
    record_artifact(ctx, f"{channel}_operation_json", "json", result_json, f"{channel}-capture")
    record_artifact(ctx, f"{channel}_operation_screenshot", "image", screenshot_dest, f"{channel}-capture")
    record_artifact(ctx, f"{channel}_capture_handoff", "yaml", handoff_path, f"{channel}-capture")
    ctx.update_state(f"{channel}_operation_{status}", f"{channel}-capture", next_action=f"review {channel} operation result")
    return handoff


def _check_side_effect_gate(ctx: RunContext, action: str) -> None:
    approvals = read_yaml(ctx.approvals_path)
    if action == "upload" and approvals.get("upload", {}).get("status") != "approved":
        raise PermissionError("upload gate must be approved before upload-side GUI actions")
    if action == "publish" and approvals.get("publish", {}).get("status") != "approved":
        raise PermissionError("publish gate must be approved before publish-side GUI actions")


def _capability_config(pipeline: dict[str, Any], name: str) -> dict[str, Any]:
    capabilities = pipeline.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return {}
    value = capabilities.get(name, {})
    return value if isinstance(value, dict) else {}


def _report(channel: str, result: dict[str, Any]) -> str:
    step = result["steps"][0]
    return "\n".join(
        [
            f"# {channel.title()} Operation Report",
            "",
            f"- Status: `{result['status']}`",
            f"- Tool: `{result['tool']}`",
            f"- Evidence: `{step['evidence'][0]}`",
            f"- Note: {step['note']}",
            "",
            "No cookies, localStorage, passwords, or tokens were read.",
            "",
        ]
    )


def _handoff(ctx: RunContext, channel: str, status: str, report: Path) -> dict[str, Any]:
    return {
        "skill": f"{channel}-capture",
        "run_id": ctx.run_id,
        "status": "ready_for_review" if status == "passed" else "blocked",
        "outputs": [report.relative_to(ctx.run_dir).as_posix(), f"assets/{channel}/handoff.{channel}-capture.yml"],
        "review_checklist": ["Confirm screenshot shows the intended user-visible state", "Confirm no private data is exposed"],
        "risks": [] if status == "passed" else ["Requested action remains blocked by gate policy"],
        "next_gate": None,
        "next_skill_suggestion": "edit-render" if status == "passed" else None,
        "revision_skill_suggestion": f"{channel}-capture",
        "user_action_required": False,
        "safety": {
            "sensitive_storage_accessed": False,
            "upload_performed": False,
            "publish_performed": False,
        },
        "user_message": f"Please review the {channel} capture result.",
    }
