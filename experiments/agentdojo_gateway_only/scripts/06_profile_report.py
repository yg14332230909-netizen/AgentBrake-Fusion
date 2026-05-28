"""Generate a compact profile report from RepoShield audit JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_log", type=Path)
    args = parser.parse_args()
    rows = load_timings(args.audit_log)
    print(render_markdown(rows))


def load_timings(path: Path) -> dict[str, list[float]]:
    timings: dict[str, list[float]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event.get("event_type") != "performance_trace":
                continue
            for key, value in ((event.get("payload") or {}).get("timings_ms") or {}).items():
                if isinstance(value, (int, float)):
                    timings.setdefault(key, []).append(float(value))
    return timings


def render_markdown(timings: dict[str, list[float]]) -> str:
    total = sum(sum(values) for values in timings.values()) or 1.0
    lines = ["| stage | avg ms | p50 | p95 | share |", "|---|---:|---:|---:|---:|"]
    for name, values in sorted(timings.items(), key=lambda item: sum(item[1]), reverse=True):
        values_sorted = sorted(values)
        p95 = values_sorted[min(len(values_sorted) - 1, int(len(values_sorted) * 0.95))]
        lines.append(f"| {name} | {mean(values):.2f} | {median(values):.2f} | {p95:.2f} | {sum(values) / total:.1%} |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()

