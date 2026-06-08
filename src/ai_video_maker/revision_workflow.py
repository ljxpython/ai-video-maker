from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml


def generate_revision_plan(ctx: RunContext, issue_id: str) -> dict[str, Any]:
    issues = read_yaml(ctx.path("qa/issues.yml")).get("issues", [])
    issue = next((item for item in issues if isinstance(item, dict) and item.get("id") == issue_id), None)
    if not issue:
        raise ValueError(f"issue not found: {issue_id}")
    revision_skill = str(issue.get("revision_skill_suggestion") or "edit-render")
    revision_id = f"rev_{issue_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    plan = {
        "version": 1,
        "revision_id": revision_id,
        "issue_ids": [issue_id],
        "status": "planned",
        "revision_skill": revision_skill,
        "reason": str(issue.get("message", "")),
        "rerun_from": revision_skill,
        "rerun_after": _rerun_after(revision_skill),
        "blocked_by_gate": None,
        "user_action_required": True,
        "message": f"建议回到 {revision_skill} 处理 `{issue_id}`，确认后再执行返修。",
    }
    yml_path = ctx.path(f"revisions/{revision_id}.yml")
    md_path = ctx.path(f"revisions/{revision_id}.md")
    write_yaml(yml_path, plan)
    md_path.write_text(_plan_markdown(plan), encoding="utf-8")
    record_artifact(ctx, f"revision_plan_{revision_id}", "yaml", yml_path, "revise")
    record_artifact(ctx, f"revision_plan_md_{revision_id}", "markdown", md_path, "revise")
    ctx.update_state("revision_planned", "revise", next_action=plan["message"])
    return plan


def _rerun_after(skill: str) -> list[str]:
    if skill == "voice-subtitle":
        return ["edit-render", "qa-revision", "publish-package"]
    if skill == "edit-render":
        return ["qa-revision", "publish-package"]
    if skill == "publish-package":
        return ["publish-package"]
    return ["qa-revision", "publish-package"]


def _plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Revision Plan",
        "",
        f"- Revision ID: `{plan['revision_id']}`",
        f"- Status: `{plan['status']}`",
        f"- Revision skill: `{plan['revision_skill']}`",
        f"- Issue IDs: `{', '.join(plan['issue_ids'])}`",
        "",
        str(plan["message"]),
        "",
    ]
    return "\n".join(lines)
