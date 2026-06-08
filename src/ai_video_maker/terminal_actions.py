from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any

from .context import RunContext
from .io import read_yaml


BLOCKED_TOKENS = {
    "rm",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "open",
    "osascript",
}

BLOCKED_PHRASES = {
    "curl | sh",
    "wget | sh",
    "pip install",
    "npm install",
    "npm publish",
    "git push",
    "git reset",
    "git clean",
    ".env",
    "cookie",
    "token",
    "secret",
}


def load_terminal_actions(ctx: RunContext) -> dict[str, Any]:
    path = ctx.path("script/terminal_actions.yml")
    if not path.exists():
        raise FileNotFoundError("script/terminal_actions.yml is required before terminal-capture")
    return normalize_terminal_actions(ctx, read_yaml(path))


def normalize_terminal_actions(ctx: RunContext, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("version") != 1:
        raise ValueError("terminal actions version must be 1")
    working_directory = str(data.get("working_directory", ".")).strip() or "."
    cwd = _safe_working_directory(ctx, working_directory)
    commands = data.get("commands", [])
    if not isinstance(commands, list) or not commands:
        raise ValueError("terminal actions commands must be a non-empty list")

    seen: set[str] = set()
    normalized = []
    for item in commands:
        if not isinstance(item, dict):
            raise ValueError("each terminal command must be a mapping")
        command_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        command = str(item.get("command", "")).strip()
        if not command_id:
            raise ValueError("terminal command id is required")
        if command_id in seen:
            raise ValueError(f"duplicate terminal command id: {command_id}")
        if not title:
            raise ValueError(f"terminal command {command_id} requires title")
        argv = validate_safe_command(command)
        if Path(argv[0]).name in {"python", "python3"}:
            argv[0] = sys.executable
        seen.add(command_id)
        normalized.append(
            {
                "id": command_id,
                "title": title,
                "command": command,
                "argv": argv,
                "allow_failure": bool(item.get("allow_failure", False)),
                "highlight": [str(value) for value in item.get("highlight", [])] if isinstance(item.get("highlight", []), list) else [],
            }
        )
    return {
        "version": 1,
        "working_directory": working_directory,
        "cwd": cwd.as_posix(),
        "requires_gate": str(data.get("requires_gate", "execution")),
        "commands": normalized,
    }


def validate_safe_command(command: str) -> list[str]:
    if not command:
        raise ValueError("terminal command is required")
    lowered = command.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in lowered:
            raise ValueError(f"blocked terminal command phrase: {phrase}")
    argv = shlex.split(command)
    if not argv:
        raise ValueError("terminal command is required")
    executable = Path(argv[0]).name
    if executable in BLOCKED_TOKENS:
        raise ValueError(f"blocked terminal command: {executable}")
    if executable == "git":
        _require_prefix(argv, {("git", "status"), ("git", "log"), ("git", "show")})
    elif executable in {"python", "python3"} or argv[0].endswith("/python"):
        _validate_python(argv)
    elif executable in {"pytest", "node", "npm", "pip"}:
        _validate_tool(argv)
    else:
        raise ValueError(f"terminal command is not in allowlist: {argv[0]}")
    return argv


def _validate_python(argv: list[str]) -> None:
    if len(argv) == 2 and argv[1] == "--version":
        return
    if len(argv) >= 4 and argv[1] == "-m" and argv[2] in {"unittest", "pytest"}:
        return
    raise ValueError("python command is not in allowlist")


def _validate_tool(argv: list[str]) -> None:
    if argv[0] in {"pytest"}:
        return
    if argv[0] in {"node", "npm", "pip"} and len(argv) == 2 and argv[1] == "--version":
        return
    if argv[0] == "npm" and argv[1:] in (["test"], ["run", "build"], ["run", "lint"]):
        return
    raise ValueError(f"{argv[0]} command is not in allowlist")


def _require_prefix(argv: list[str], allowed: set[tuple[str, str]]) -> None:
    if len(argv) < 2 or (argv[0], argv[1]) not in allowed:
        raise ValueError("git command is not in allowlist")


def _safe_working_directory(ctx: RunContext, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise ValueError("terminal working_directory must be relative")
    candidate = (ctx.project_root / raw).resolve()
    root = ctx.project_root.resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError("terminal working_directory must stay inside project")
    return candidate
