from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .browser_adapter import ensure_execution_approved, load_browser_preflight
from .context import RunContext
from .io import write_yaml


def generate_browser_capture(ctx: RunContext) -> dict[str, Any]:
    ensure_execution_approved(ctx)
    plan = load_browser_preflight(ctx)
    target_url = str(plan.get("target_url", "")).strip()
    if not target_url:
        raise ValueError("plan/browser_preflight.yml must include target_url before browser-capture")

    screenshot = ctx.path("assets/browser/screenshot.png")
    recording = ctx.path("assets/browser/demo.webm")
    report = ctx.path("qa/browser_capture.md")
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    recording.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    capture_result = _capture_with_playwright(
        target_url=target_url,
        screenshot=screenshot,
        recording=recording,
        viewport=plan.get("viewport", {}),
        duration_seconds=_recording_duration(plan),
    )
    status = "ready_for_review" if capture_result["passed"] else "needs_revision"
    handoff = _handoff(ctx, status, capture_result)

    report.write_text(_report(ctx, plan, capture_result, handoff), encoding="utf-8")
    write_yaml(ctx.path("assets/browser/handoff.browser-capture.yml"), handoff)

    record_artifact(ctx, "browser_capture_video", "video", recording, "browser-capture")
    record_artifact(ctx, "browser_capture_screenshot", "image", screenshot, "browser-capture")
    record_artifact(ctx, "browser_capture_report", "markdown", report, "browser-capture")
    record_artifact(ctx, "browser_capture_handoff", "yaml", ctx.path("assets/browser/handoff.browser-capture.yml"), "browser-capture")

    next_action = "review browser capture; next skill: voice-subtitle" if status == "ready_for_review" else "review browser capture; revise with: browser-capture"
    ctx.update_state("browser_capture_ready" if status == "ready_for_review" else "browser_capture_needs_revision", "browser-capture", next_action=next_action)
    return handoff


def _capture_with_playwright(
    *,
    target_url: str,
    screenshot: Path,
    recording: Path,
    viewport: Any,
    duration_seconds: int,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    screenshot.parent.mkdir(parents=True, exist_ok=True)
    recording.parent.mkdir(parents=True, exist_ok=True)
    width = _positive_int(viewport.get("width") if isinstance(viewport, dict) else None, 1920)
    height = _positive_int(viewport.get("height") if isinstance(viewport, dict) else None, 1080)

    with tempfile.TemporaryDirectory() as tmp:
        video_dir = Path(tmp)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=str(video_dir),
                record_video_size={"width": width, "height": height},
            )
            page = context.new_page()
            page.goto(target_url, wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(1_000)
            page.screenshot(path=str(screenshot), full_page=True)
            page.wait_for_timeout(duration_seconds * 1000)
            title = page.title()
            current_url = page.url
            context.close()
            browser.close()

        videos = sorted(video_dir.glob("*.webm"), key=lambda item: item.stat().st_mtime)
        if not videos:
            raise RuntimeError("Playwright did not produce a browser recording")
        shutil.copyfile(videos[-1], recording)

    screenshot_ok = screenshot.exists() and screenshot.stat().st_size > 0
    recording_ok = recording.exists() and recording.stat().st_size > 0
    return {
        "passed": screenshot_ok and recording_ok,
        "target_url": target_url,
        "current_url": current_url,
        "title": title,
        "duration_seconds": duration_seconds,
        "screenshot_non_blank": screenshot_ok,
        "recording_non_empty": recording_ok,
    }


def _recording_duration(plan: dict[str, Any]) -> int:
    recording = plan.get("recording", {})
    duration = recording.get("duration_seconds") if isinstance(recording, dict) else None
    return _positive_int(duration, 5)


def _positive_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


def _handoff(ctx: RunContext, status: str, capture_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": "browser-capture",
        "run_id": ctx.run_id,
        "status": status,
        "outputs": [
            "assets/browser/demo.webm",
            "assets/browser/screenshot.png",
            "qa/browser_capture.md",
            "assets/browser/handoff.browser-capture.yml",
        ],
        "review_checklist": [
            "Confirm screenshot shows the intended page state",
            "Confirm browser recording is playable",
            "Confirm no private account data or local secrets appear in the capture",
        ],
        "risks": [] if status == "ready_for_review" else ["Browser capture did not produce all expected artifacts"],
        "next_gate": None,
        "next_skill_suggestion": "voice-subtitle" if status == "ready_for_review" else "browser-capture",
        "revision_skill_suggestion": "browser-capture",
        "user_action_required": False,
        "browser": {
            "target_url": capture_result.get("target_url", ""),
            "current_url": capture_result.get("current_url", ""),
            "title": capture_result.get("title", ""),
        },
        "user_message": (
            "Please review the browser capture. If approved, the next recommended skill is voice-subtitle."
            if status == "ready_for_review"
            else "Browser capture needs revision before continuing."
        ),
    }


def _report(ctx: RunContext, plan: dict[str, Any], capture_result: dict[str, Any], handoff: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Browser Capture Report",
            "",
            f"- Run: `{ctx.run_id}`",
            f"- Status: `{handoff['status']}`",
            f"- Target URL: `{plan.get('target_url', '')}`",
            f"- Current URL: `{capture_result.get('current_url', '')}`",
            f"- Page title: `{capture_result.get('title', '')}`",
            f"- Duration: `{capture_result.get('duration_seconds', '')}` seconds",
            "",
            "## Checks",
            "",
            f"- Screenshot non-empty: `{capture_result.get('screenshot_non_blank', False)}`",
            f"- Recording non-empty: `{capture_result.get('recording_non_empty', False)}`",
            "",
            "## Outputs",
            "",
            "- `assets/browser/demo.webm`",
            "- `assets/browser/screenshot.png`",
            "- `assets/browser/handoff.browser-capture.yml`",
            "",
        ]
    )
