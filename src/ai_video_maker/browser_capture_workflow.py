from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .browser_adapter import ensure_execution_approved, load_browser_preflight
from .browser_actions import load_screen_actions
from .context import RunContext
from .io import write_json, write_yaml


def generate_browser_capture(ctx: RunContext) -> dict[str, Any]:
    ensure_execution_approved(ctx)
    actions_plan = load_screen_actions(ctx)
    plan = actions_plan or load_browser_preflight(ctx)
    target_url = str(plan.get("target_url", "")).strip()
    if not target_url:
        raise ValueError("plan/browser_preflight.yml must include target_url before browser-capture")

    screenshot = ctx.path("assets/browser/screenshot.png")
    recording = ctx.path("assets/browser/demo.webm")
    report = ctx.path("qa/browser_capture.md")
    result_json = ctx.path("qa/browser_capture.json")
    actions_json = ctx.path("qa/browser_actions.json")
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    recording.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    if actions_plan:
        capture_result = _capture_actions_with_playwright(ctx, actions_plan, screenshot, recording)
    else:
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
    write_json(result_json, capture_result)
    write_json(actions_json, {"status": "passed" if capture_result["passed"] else "failed", "actions": capture_result.get("actions", [])})
    write_yaml(ctx.path("assets/browser/handoff.browser-capture.yml"), handoff)

    record_artifact(ctx, "browser_capture_video", "video", recording, "browser-capture")
    record_artifact(ctx, "browser_capture_screenshot", "image", screenshot, "browser-capture")
    record_artifact(ctx, "browser_capture_report", "markdown", report, "browser-capture")
    record_artifact(ctx, "browser_capture_json", "json", result_json, "browser-capture")
    record_artifact(ctx, "browser_actions_json", "json", actions_json, "browser-capture")
    record_artifact(ctx, "browser_capture_handoff", "yaml", ctx.path("assets/browser/handoff.browser-capture.yml"), "browser-capture")

    next_action = "review browser capture; next skill: voice-subtitle" if status == "ready_for_review" else "review browser capture; revise with: browser-capture"
    ctx.update_state("browser_capture_ready" if status == "ready_for_review" else "browser_capture_needs_revision", "browser-capture", next_action=next_action)
    return handoff


def _capture_actions_with_playwright(ctx: RunContext, plan: dict[str, Any], screenshot: Path, recording: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    viewport = plan.get("viewport", {})
    recording_config = plan.get("recording", {})
    width = _positive_int(viewport.get("width") if isinstance(viewport, dict) else None, 1920)
    height = _positive_int(viewport.get("height") if isinstance(viewport, dict) else None, 1080)
    duration_seconds = _positive_int(recording_config.get("duration_seconds") if isinstance(recording_config, dict) else None, 5)
    step_results: list[dict[str, Any]] = []
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    recording.parent.mkdir(parents=True, exist_ok=True)
    steps_dir = ctx.path("assets/browser/steps")
    steps_dir.mkdir(parents=True, exist_ok=True)

    current_url = str(plan["target_url"])
    title = ""
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
            for index, action in enumerate(plan.get("actions", []), start=1):
                result = _run_action(page, action, index, steps_dir)
                step_results.append(result)
                if result["status"] != "passed":
                    break
            page.screenshot(path=str(screenshot), full_page=True)
            page.wait_for_timeout(duration_seconds * 1000)
            title = page.title()
            current_url = page.url
            context.close()
            browser.close()

        videos = sorted(video_dir.glob("*.webm"), key=lambda item: item.stat().st_mtime)
        if videos:
            shutil.copyfile(videos[-1], recording)

    screenshot_ok = screenshot.exists() and screenshot.stat().st_size > 0
    recording_ok = recording.exists() and recording.stat().st_size > 0
    actions_ok = bool(step_results) and all(item["status"] == "passed" for item in step_results)
    return {
        "passed": screenshot_ok and recording_ok and actions_ok,
        "target_url": plan["target_url"],
        "current_url": current_url,
        "title": title,
        "duration_seconds": duration_seconds,
        "screenshot_non_blank": screenshot_ok,
        "recording_non_empty": recording_ok,
        "actions": step_results,
    }


def _run_action(page: Any, action: dict[str, Any], index: int, steps_dir: Path) -> dict[str, Any]:
    action_id = str(action["id"])
    action_type = str(action["type"])
    result: dict[str, Any] = {"id": action_id, "type": action_type, "status": "passed"}
    try:
        if action_type == "goto":
            page.goto(str(action["url"]), wait_until="networkidle", timeout=30_000)
        elif action_type == "click":
            page.click(str(action["selector"]), timeout=10_000)
        elif action_type == "fill":
            page.fill(str(action["selector"]), str(action.get("value", "")), timeout=10_000)
        elif action_type == "press":
            page.keyboard.press(str(action["key"]))
        elif action_type == "scroll":
            page.mouse.wheel(0, int(action.get("delta_y", 700)))
        elif action_type == "wait_for_selector":
            page.wait_for_selector(str(action["selector"]), timeout=int(action.get("timeout_ms", 10_000)))
        elif action_type == "wait":
            page.wait_for_timeout(int(action.get("duration_ms", 1000)))
        elif action_type == "screenshot":
            output = Path(str(action.get("output", "")))
            shot = output if output.is_absolute() else steps_dir.parent.parent.parent / output
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True)
            result["screenshot"] = shot.as_posix()
        elif action_type == "record_segment":
            page.wait_for_timeout(int(action.get("duration_ms", 1000)))
        step_shot = steps_dir / f"{index:03}_{action_id}.png"
        page.screenshot(path=str(step_shot), full_page=True)
        result["step_screenshot"] = step_shot.as_posix()
    except Exception as exc:  # Playwright exceptions vary by version.
        result["status"] = "failed"
        result["error"] = str(exc)
    return result


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
    next_skill = "edit-render" if ctx.path("audio/narration.mp3").exists() and ctx.path("subtitles/captions.srt").exists() else "voice-subtitle"
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
        "next_skill_suggestion": next_skill if status == "ready_for_review" else "browser-capture",
        "revision_skill_suggestion": "browser-capture",
        "user_action_required": False,
        "browser": {
            "target_url": capture_result.get("target_url", ""),
            "current_url": capture_result.get("current_url", ""),
            "title": capture_result.get("title", ""),
        },
        "user_message": (
            f"Please review the browser capture. If approved, the next recommended skill is {next_skill}."
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
