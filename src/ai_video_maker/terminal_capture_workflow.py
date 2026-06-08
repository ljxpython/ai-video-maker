from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .artifacts import record_artifact
from .browser_adapter import ensure_execution_approved
from .context import RunContext
from .io import write_json, write_yaml
from .renderer import DEFAULT_FONT, wrapped_lines
from .terminal_actions import load_terminal_actions


CARD_SIZE = (1280, 720)


def generate_terminal_capture(ctx: RunContext) -> dict[str, Any]:
    plan = load_terminal_actions(ctx)
    if plan.get("requires_gate", "execution") == "execution":
        ensure_execution_approved(ctx)

    logs_dir = ctx.path("assets/terminal/logs")
    cards_dir = ctx.path("assets/terminal/cards")
    logs_dir.mkdir(parents=True, exist_ok=True)
    cards_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for command in plan["commands"]:
        result = _run_terminal_command(ctx, command, Path(plan["cwd"]), logs_dir, cards_dir)
        results.append(result)
        if result["status"] == "failed" and not result["allow_failure"]:
            break

    passed = all(item["status"] == "passed" or item["allow_failure"] for item in results)
    status = "ready_for_review" if passed else "needs_revision"
    report = ctx.path("qa/terminal_capture.md")
    result_json = ctx.path("qa/terminal_capture.json")
    handoff_path = ctx.path("assets/terminal/handoff.terminal-capture.yml")
    report.write_text(_report(ctx, status, results), encoding="utf-8")
    write_json(result_json, {"status": "passed" if passed else "failed", "commands": results})
    handoff = _handoff(ctx, status, results)
    write_yaml(handoff_path, handoff)

    record_artifact(ctx, "terminal_capture_report", "markdown", report, "terminal-capture")
    record_artifact(ctx, "terminal_capture_json", "json", result_json, "terminal-capture")
    record_artifact(ctx, "terminal_capture_handoff", "yaml", handoff_path, "terminal-capture")
    for result in results:
        record_artifact(ctx, f"terminal_card_{result['id']}", "image", ctx.path(result["card"]), "terminal-capture")

    ctx.update_state(
        "terminal_capture_ready" if passed else "terminal_capture_needs_revision",
        "terminal-capture",
        next_action="review terminal capture; next skill: edit-render" if passed else "review terminal capture; revise with: terminal-capture",
    )
    return handoff


def _run_terminal_command(
    ctx: RunContext,
    command: dict[str, Any],
    cwd: Path,
    logs_dir: Path,
    cards_dir: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(command["argv"], cwd=cwd, text=True, capture_output=True, check=False)
    elapsed = round(time.monotonic() - started, 3)
    stdout = _redact(ctx, completed.stdout)
    stderr = _redact(ctx, completed.stderr)
    command_id = str(command["id"])
    stdout_path = logs_dir / f"{command_id}.stdout.txt"
    stderr_path = logs_dir / f"{command_id}.stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    passed = completed.returncode == 0
    status = "passed" if passed else "failed"
    card_path = cards_dir / f"{command_id}.png"
    _render_card(card_path, command, stdout, stderr, status, completed.returncode, elapsed)
    return {
        "id": command_id,
        "title": command["title"],
        "command": command["command"],
        "status": status,
        "allow_failure": bool(command.get("allow_failure", False)),
        "exit_code": completed.returncode,
        "duration_seconds": elapsed,
        "stdout_log": stdout_path.relative_to(ctx.run_dir).as_posix(),
        "stderr_log": stderr_path.relative_to(ctx.run_dir).as_posix(),
        "card": card_path.relative_to(ctx.run_dir).as_posix(),
    }


def _render_card(
    path: Path,
    command: dict[str, Any],
    stdout: str,
    stderr: str,
    status: str,
    exit_code: int,
    elapsed: float,
) -> None:
    image = Image.new("RGB", CARD_SIZE, (18, 26, 36))
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(DEFAULT_FONT), 48)
    mono_font = ImageFont.truetype(str(DEFAULT_FONT), 30)
    small_font = ImageFont.truetype(str(DEFAULT_FONT), 24)
    draw.text((64, 48), str(command["title"]), font=title_font, fill=(255, 255, 255))
    status_color = (117, 210, 163) if status == "passed" else (255, 107, 107)
    draw.text((64, 125), f"{status.upper()}  exit={exit_code}  {elapsed}s", font=small_font, fill=status_color)
    draw.rounded_rectangle((64, 180, 1216, 255), radius=12, fill=(7, 12, 20))
    draw.text((88, 202), f"$ {command['command']}", font=mono_font, fill=(255, 209, 102))
    output = (stdout or stderr or "<no output>").strip()
    y = 300
    for line in _output_lines(draw, output, mono_font, 1050)[:10]:
        draw.text((88, y), line, font=mono_font, fill=(210, 222, 235))
        y += 36
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _output_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        lines.extend(wrapped_lines(draw, raw[:220], font, max_width) or [""])
    return lines


def _redact(ctx: RunContext, text: str) -> str:
    value = text.replace(ctx.project_root.as_posix(), "<project-root>")
    value = value.replace(str(Path.home()), "<home>")
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", value)
    value = re.sub(r"(?i)(token|secret|password|cookie)=\S+", r"\1=<redacted>", value)
    return value


def _report(ctx: RunContext, status: str, results: list[dict[str, Any]]) -> str:
    lines = ["# Terminal Capture Report", "", f"- Run: `{ctx.run_id}`", f"- Status: `{status}`", "", "## Commands", ""]
    for result in results:
        marker = "PASS" if result["status"] == "passed" else "FAIL"
        lines.append(f"- [{marker}] `{result['id']}` `{result['command']}` -> `{result['exit_code']}`")
    lines.extend(["", "## Cards", ""])
    for result in results:
        lines.append(f"- `{result['card']}`")
    return "\n".join(lines).rstrip() + "\n"


def _handoff(ctx: RunContext, status: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    next_skill = "edit-render" if ctx.path("audio/narration.mp3").exists() and ctx.path("subtitles/captions.srt").exists() else "voice-subtitle"
    return {
        "skill": "terminal-capture",
        "run_id": ctx.run_id,
        "status": status,
        "outputs": [
            "qa/terminal_capture.md",
            "qa/terminal_capture.json",
            "assets/terminal/handoff.terminal-capture.yml",
            *[result["card"] for result in results],
        ],
        "review_checklist": [
            "Confirm command outputs are safe to show",
            "Confirm cards explain the terminal steps clearly",
            "Confirm no local paths, emails, tokens, or cookies appear",
        ],
        "risks": [] if status == "ready_for_review" else ["One or more terminal commands failed"],
        "next_gate": None,
        "next_skill_suggestion": next_skill if status == "ready_for_review" else "terminal-capture",
        "revision_skill_suggestion": "terminal-capture",
        "user_action_required": False,
        "user_message": (
            f"Please review terminal cards. If approved, the next recommended skill is {next_skill}."
            if status == "ready_for_review"
            else "Terminal capture needs revision before continuing."
        ),
    }
