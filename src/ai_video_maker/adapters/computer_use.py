from __future__ import annotations

from typing import Any


def plan_operation(request: dict[str, Any]) -> dict[str, Any]:
    return {"adapter": "computer_use", "mode": "plan", "request": request}


def record_result(result: dict[str, Any]) -> dict[str, Any]:
    return {"adapter": "computer_use", "mode": "record_result", "result": result}
