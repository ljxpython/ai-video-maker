from pathlib import Path

from .context import RunContext
from .io import read_yaml, write_yaml


def record_artifact(ctx: RunContext, artifact_id: str, artifact_type: str, path: Path, stage: str) -> None:
    data = read_yaml(ctx.artifacts_path) or {"run_id": ctx.run_id, "artifacts": []}
    relative = path.relative_to(ctx.run_dir).as_posix()
    items = [item for item in data.get("artifacts", []) if item.get("id") != artifact_id]
    items.append(
        {
            "id": artifact_id,
            "type": artifact_type,
            "path": relative,
            "stage": stage,
        }
    )
    data["artifacts"] = items
    write_yaml(ctx.artifacts_path, data)
