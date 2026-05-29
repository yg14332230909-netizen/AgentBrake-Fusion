from __future__ import annotations

import json
from pathlib import Path

from reposhield.eval.agentdojo_firewall import AgentDojoToolTaxonomy


def main() -> None:
    taxonomy = AgentDojoToolTaxonomy()
    names = sorted(taxonomy.specs)
    out = {
        "count": len(names),
        "tools": names,
        "coverage": taxonomy.coverage(names),
    }
    path = Path("experiments/agentdojo_firewall/reports/tool_inventory.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
