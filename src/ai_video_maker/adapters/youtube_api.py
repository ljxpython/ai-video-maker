from __future__ import annotations

from typing import Any


def dry_run_upload(plan: dict[str, Any]) -> dict[str, Any]:
    return {"adapter": "youtube_api", "mode": "dry_run", "network_requests_performed": False, "plan": plan}
