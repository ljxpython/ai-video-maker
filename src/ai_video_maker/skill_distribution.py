from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml


def load_manifest(project_root: Path) -> dict[str, Any]:
    path = project_root / "skills" / "manifest.yml"
    if not path.exists():
        raise FileNotFoundError("skills/manifest.yml is required")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("skills manifest must be a mapping")
    return data


def list_skills(project_root: Path) -> list[dict[str, Any]]:
    manifest = load_manifest(project_root)
    skills = manifest.get("skills", [])
    return [item for item in skills if isinstance(item, dict)]


def validate_skills(project_root: Path) -> dict[str, Any]:
    skills = list_skills(project_root)
    errors: list[str] = []
    names: set[str] = set()
    for item in skills:
        name = str(item.get("name", "")).strip()
        relative = str(item.get("path", "")).strip()
        if not name:
            errors.append("skill name is required")
            continue
        if name in names:
            errors.append(f"duplicate skill name: {name}")
        names.add(name)
        skill_dir = project_root / relative
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"SKILL.md missing for {name}: {relative}")
            continue
        frontmatter = _frontmatter(skill_md)
        if frontmatter.get("name") != name:
            errors.append(f"frontmatter name mismatch for {name}")
        if not str(frontmatter.get("description", "")).strip():
            errors.append(f"description missing for {name}")
        text = skill_md.read_text(encoding="utf-8")
        if _contains_private_marker(text):
            errors.append(f"private marker found in {relative}/SKILL.md")
    return {"status": "passed" if not errors else "failed", "count": len(skills), "errors": errors, "skills": skills}


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1]) or {}
    return data if isinstance(data, dict) else {}


def _contains_private_marker(text: str) -> bool:
    home = str(Path.home())
    patterns = [
        re.escape(home),
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        r"(?i)\btoken\s*=",
        r"(?i)\bsecret\s*=",
    ]
    return any(re.search(pattern, text) for pattern in patterns)
