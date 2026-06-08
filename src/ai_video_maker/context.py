from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .io import read_json, write_json, write_yaml


RUN_DIRS = [
    "plan",
    "script",
    "assets",
    "audio",
    "subtitles",
    "render",
    "qa/screenshots",
    "package",
]


@dataclass(frozen=True)
class RunContext:
    project_root: Path
    run_dir: Path

    @property
    def run_id(self) -> str:
        return self.run_dir.name

    @property
    def state_path(self) -> Path:
        return self.run_dir / "state.json"

    @property
    def approvals_path(self) -> Path:
        return self.run_dir / "approvals.yml"

    @property
    def artifacts_path(self) -> Path:
        return self.run_dir / "artifacts.yml"

    def path(self, relative: str) -> Path:
        return self.run_dir / relative

    def state(self) -> dict:
        return read_json(self.state_path)

    def update_state(self, status: str, stage: str, **extra: object) -> None:
        state = self.state()
        state.update(
            {
                "run_id": self.run_id,
                "status": status,
                "current_stage": stage,
                "updated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
        state.update(extra)
        write_json(self.state_path, state)


def default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def create_run(project_root: Path, run_id: str | None = None, overwrite: bool = False) -> RunContext:
    run_dir = project_root / "runs" / (run_id or default_run_id())
    if run_dir.exists() and not overwrite:
        raise FileExistsError(f"run already exists: {run_dir}")
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)

    for item in RUN_DIRS:
        (run_dir / item).mkdir(parents=True, exist_ok=True)

    ctx = RunContext(project_root=project_root, run_dir=run_dir)
    ctx.update_state("created", "new")
    write_yaml(
        ctx.approvals_path,
        {
            "brief": {"status": "pending"},
            "plan": {"status": "pending"},
            "execution": {"status": "pending"},
            "upload": {"status": "pending"},
            "publish": {"status": "pending"},
        },
    )
    write_yaml(ctx.artifacts_path, {"run_id": ctx.run_id, "artifacts": []})
    return ctx


def load_run(project_root: Path, run: str) -> RunContext:
    run_path = Path(run)
    if not run_path.is_absolute():
        run_path = project_root / run_path
    if not run_path.exists():
        raise FileNotFoundError(f"run not found: {run_path}")
    return RunContext(project_root=project_root, run_dir=run_path)
