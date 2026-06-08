from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_json


def load_browser_preflight(ctx: RunContext) -> dict[str, Any]:
    plan = read_yaml(ctx.path("plan/browser_preflight.yml"))
    if not plan:
        raise FileNotFoundError(f"browser preflight plan not found: {ctx.path('plan/browser_preflight.yml')}")
    return plan


def ensure_execution_approved(ctx: RunContext) -> None:
    approvals = read_yaml(ctx.approvals_path)
    status = approvals.get("execution", {}).get("status", "pending")
    if status != "approved":
        raise PermissionError("execution gate must be approved before browser preflight results can be recorded")


def record_browser_preflight_result(
    ctx: RunContext,
    *,
    screenshot: Path,
    current_url: str,
    title: str,
    non_blank: bool,
) -> dict[str, Any]:
    ensure_execution_approved(ctx)
    plan = load_browser_preflight(ctx)

    screenshot_dest = ctx.path("assets/browser/preflight_screenshot.png")
    screenshot_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(screenshot, screenshot_dest)

    status = "passed" if non_blank and bool(title.strip()) else "failed"
    result = {
        "status": status,
        "current_url": current_url,
        "title": title,
        "non_blank": non_blank,
        "target_url": plan.get("target_url", ""),
        "target_kind": plan.get("target_kind", ""),
        "screenshot": screenshot_dest.relative_to(ctx.run_dir).as_posix(),
        "checks": {
            "page_load": bool(current_url),
            "title_present": bool(title.strip()),
            "screenshot_non_blank": non_blank,
        },
    }

    result_path = ctx.path("qa/browser_preflight.json")
    report_path = ctx.path("qa/browser_preflight.md")
    write_json(result_path, result)
    report_path.write_text(_browser_preflight_report(result), encoding="utf-8")

    record_artifact(ctx, "browser_preflight_result", "json", result_path, "browser_preflight")
    record_artifact(ctx, "browser_preflight_report", "markdown", report_path, "browser_preflight")
    record_artifact(ctx, "browser_preflight_screenshot", "image", screenshot_dest, "browser_preflight")
    ctx.update_state("browser_preflight_ready", "browser_preflight", next_action="")
    return result


def _browser_preflight_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join(
        [
            "# Browser Preflight Report",
            "",
            f"- Status: `{result['status']}`",
            f"- Target URL: `{result['target_url']}`",
            f"- Current URL: `{result['current_url']}`",
            f"- Target kind: `{result['target_kind']}`",
            f"- Title: `{result['title']}`",
            f"- Screenshot: `{result['screenshot']}`",
            "",
            "## Checks",
            "",
            f"- Page load: `{checks['page_load']}`",
            f"- Title present: `{checks['title_present']}`",
            f"- Screenshot non blank: `{checks['screenshot_non_blank']}`",
            "",
        ]
    )
