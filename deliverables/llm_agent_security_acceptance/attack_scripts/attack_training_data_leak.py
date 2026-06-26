from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_case import run_case  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(run_case("SCN-03"), ensure_ascii=False, indent=2))
