from __future__ import annotations

import os

from experiments.agentdojo.scripts._common import run_eval


def main() -> None:
    os.environ.setdefault("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8765/v1"))
    os.environ.setdefault("OPENAI_API_KEY", os.getenv("REPOSHIELD_GATEWAY_API_KEY", "reposhield-local"))
    for suite in ("banking", "slack", "workspace", "travel"):
        run_eval(
            suite=suite, defense="gateway_only", attack="important_instructions", run_name=f"{suite}_reposhield_gateway_only_fast_attack"
        )


if __name__ == "__main__":
    main()



