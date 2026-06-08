from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / "pipeline.example.yml").exists() and (path / "templates").exists():
            return path
        if (path / ".git").exists() and (path / "requirements.txt").exists():
            return path
    return current
