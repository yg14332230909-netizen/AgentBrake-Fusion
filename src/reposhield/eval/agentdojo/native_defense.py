"""Native AgentDojo defense registration helpers."""

from __future__ import annotations

from typing import Any

from .inspect_adapter import reposhield_agentdojo


def register_native_defense() -> dict[str, Any]:
    return {"defense_name": "reposhield_toolgate", "load": reposhield_agentdojo}

