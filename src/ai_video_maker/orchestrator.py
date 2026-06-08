from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml


HARD_GATES = {"brief", "plan", "execution", "upload", "publish"}


HANDOFF_PATHS = [
    "script/handoff.video-script.yml",
    "assets/browser/handoff.browser-capture.yml",
    "assets/terminal/handoff.terminal-capture.yml",
    "assets/chrome/handoff.chrome-capture.yml",
    "assets/desktop/handoff.desktop-capture.yml",
    "subtitles/handoff.voice-subtitle.yml",
    "render/handoff.edit-render.yml",
    "qa/handoff.qa-revision.yml",
    "package/handoff.publish-package.yml",
    "upload/handoff.youtube-upload.yml",
]


def generate_next(ctx: RunContext) -> dict[str, Any]:
    result = determine_next(ctx)
    next_dir = ctx.path("orchestrator")
    next_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(next_dir / "next.yml", result)
    (next_dir / "next.md").write_text(_next_markdown(result), encoding="utf-8")
    record_artifact(ctx, "orchestrator_next_yml", "yaml", next_dir / "next.yml", "orchestrator")
    record_artifact(ctx, "orchestrator_next_md", "markdown", next_dir / "next.md", "orchestrator")
    ctx.update_state(str(result["status"]), "orchestrator", next_action=str(result["message"]))
    return result


def determine_next(ctx: RunContext) -> dict[str, Any]:
    approvals = read_yaml(ctx.approvals_path)
    if not ctx.path("brief.yml").exists():
        return _ready(ctx, "new", "video-brief", "尚未生成 brief。下一步建议调用 video-brief。")

    if _gate_status(approvals, "brief") != "approved":
        return _gate(ctx, "brief", "brief", "brief 已生成，请检阅后确认 brief gate。")

    if not ctx.path("plan/storyboard.yml").exists():
        return _ready(ctx, "brief", "video-plan", "brief 已确认。下一步建议调用 video-plan。")

    if _gate_status(approvals, "plan") != "approved":
        return _gate(ctx, "plan", "plan", "plan 已生成，请检阅 storyboard、asset plan 和 capability plan 后确认 plan gate。")

    if not ctx.path("script/handoff.video-script.yml").exists():
        return _ready(ctx, "plan", "video-script", "plan 已确认。下一步建议调用 video-script。")

    latest = _latest_handoff(ctx)
    if latest:
        routed = _route_handoff(ctx, latest, approvals)
        if routed:
            return routed

    if _needs_execution(ctx) and _gate_status(approvals, "execution") != "approved":
        return _gate(ctx, "execution", "execution", "检测到需要浏览器、Chrome、桌面或终端执行能力，请先确认 execution gate。")

    if _needs_browser_capture(ctx) and not ctx.path("assets/browser/handoff.browser-capture.yml").exists():
        return _ready(ctx, "browser-capture", "browser-capture", "需要网页演示素材。下一步建议调用 browser-capture。")

    if not ctx.path("subtitles/handoff.voice-subtitle.yml").exists():
        return _ready(ctx, "voice-subtitle", "voice-subtitle", "脚本已准备好。下一步建议调用 voice-subtitle。")

    if not ctx.path("render/handoff.edit-render.yml").exists():
        return _ready(ctx, "edit-render", "edit-render", "配音和字幕已准备好。下一步建议调用 edit-render。")

    if not ctx.path("qa/handoff.qa-revision.yml").exists():
        return _ready(ctx, "qa-revision", "qa-revision", "成片已生成。下一步建议调用 qa-revision。")

    if not ctx.path("package/handoff.publish-package.yml").exists():
        return _ready(ctx, "publish-package", "publish-package", "QA 已完成。下一步建议调用 publish-package。")

    if _gate_status(approvals, "upload") != "approved":
        return _gate(ctx, "upload", "upload", "发布包已准备好。上传前必须确认 upload gate。")

    if not ctx.path("upload/handoff.youtube-upload.yml").exists():
        return _ready(ctx, "youtube-upload", "youtube-upload", "upload gate 已确认。下一步建议调用 youtube-upload。")

    if _gate_status(approvals, "publish") != "approved":
        return _gate(ctx, "publish", "publish", "上传结果已记录。公开或改可见性前必须确认 publish gate。")

    return {
        "status": "done",
        "run_id": ctx.run_id,
        "current_stage": "complete",
        "next_skill_suggestion": None,
        "next_gate": None,
        "user_action_required": False,
        "message": "所有已规划阶段都已完成。",
    }


def _route_handoff(ctx: RunContext, handoff: dict[str, Any], approvals: dict[str, Any]) -> dict[str, Any] | None:
    status = str(handoff.get("status", ""))
    skill = str(handoff.get("skill", ""))
    next_gate = handoff.get("next_gate")
    if isinstance(next_gate, str) and next_gate in HARD_GATES and _gate_status(approvals, next_gate) != "approved":
        return _gate(ctx, next_gate, skill, str(handoff.get("user_message") or f"请确认 {next_gate} gate。"))

    if status == "needs_revision":
        revision_skill = str(handoff.get("revision_skill_suggestion") or handoff.get("next_skill_suggestion") or skill)
        return _ready(ctx, skill, revision_skill, str(handoff.get("user_message") or f"需要返修，建议调用 {revision_skill}。"), status="needs_revision")

    next_skill = handoff.get("next_skill_suggestion")
    if isinstance(next_skill, str) and next_skill:
        if next_skill in {"browser-capture", "chrome-capture", "desktop-capture", "terminal-capture"} and _gate_status(approvals, "execution") != "approved":
            return _gate(ctx, "execution", skill, "下一步需要执行或录制能力，请先确认 execution gate。")
        expected_handoff = _expected_handoff(next_skill)
        if expected_handoff and not ctx.path(expected_handoff).exists():
            return _ready(ctx, skill, next_skill, str(handoff.get("user_message") or f"下一步建议调用 {next_skill}。"))
    return None


def _latest_handoff(ctx: RunContext) -> dict[str, Any]:
    existing: list[tuple[float, Path]] = []
    for relative in HANDOFF_PATHS:
        path = ctx.path(relative)
        if path.exists():
            existing.append((path.stat().st_mtime, path))
    if not existing:
        return {}
    return read_yaml(sorted(existing)[-1][1])


def _expected_handoff(skill: str) -> str:
    mapping = {
        "browser-capture": "assets/browser/handoff.browser-capture.yml",
        "terminal-capture": "assets/terminal/handoff.terminal-capture.yml",
        "chrome-capture": "assets/chrome/handoff.chrome-capture.yml",
        "desktop-capture": "assets/desktop/handoff.desktop-capture.yml",
        "voice-subtitle": "subtitles/handoff.voice-subtitle.yml",
        "edit-render": "render/handoff.edit-render.yml",
        "qa-revision": "qa/handoff.qa-revision.yml",
        "publish-package": "package/handoff.publish-package.yml",
        "youtube-upload": "upload/handoff.youtube-upload.yml",
    }
    return mapping.get(skill, "")


def _needs_execution(ctx: RunContext) -> bool:
    if ctx.path("script/terminal_actions.yml").exists() or ctx.path("plan/browser_preflight.yml").exists():
        return True
    plan = read_yaml(ctx.path("plan/capability_plan.yml"))
    required = plan.get("required", [])
    return isinstance(required, list) and bool(required)


def _needs_browser_capture(ctx: RunContext) -> bool:
    script_handoff = read_yaml(ctx.path("script/handoff.video-script.yml"))
    if script_handoff.get("next_skill_suggestion") == "browser-capture":
        return True
    return ctx.path("script/screen_actions.yml").exists()


def _gate_status(approvals: dict[str, Any], gate: str) -> str:
    data = approvals.get(gate, {})
    return str(data.get("status", "pending")) if isinstance(data, dict) else "pending"


def _ready(ctx: RunContext, stage: str, skill: str, message: str, *, status: str = "ready") -> dict[str, Any]:
    return {
        "status": status,
        "run_id": ctx.run_id,
        "current_stage": stage,
        "next_skill_suggestion": skill,
        "next_gate": None,
        "user_action_required": False,
        "message": message,
    }


def _gate(ctx: RunContext, gate: str, stage: str, message: str) -> dict[str, Any]:
    return {
        "status": "waiting_for_gate",
        "run_id": ctx.run_id,
        "current_stage": stage,
        "next_skill_suggestion": None,
        "next_gate": gate,
        "user_action_required": True,
        "message": message,
    }


def _next_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Orchestrator Next",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Current stage: `{result.get('current_stage')}`",
        f"- Next skill: `{result.get('next_skill_suggestion')}`",
        f"- Next gate: `{result.get('next_gate')}`",
        f"- User action required: `{result.get('user_action_required')}`",
        "",
        str(result.get("message", "")),
        "",
    ]
    return "\n".join(lines)
