"""Turn traces/traces.jsonl into the key metrics from the observability slide.

    python -m scripts.trace_report            # all runs
    python -m scripts.trace_report --label part2
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from statistics import mean

from workshop.config import get_settings


def load(label: str | None = None) -> list[dict]:
    path = get_settings().trace_dir / "traces.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if not label or label in r.get("label", "")]


def summarise(label: str | None = None) -> dict:
    rows = load(label)
    if not rows:
        return {"runs": 0}
    tool_counter = Counter(t["tool"] for r in rows for t in r.get("tools", []))
    tool_errors = sum(1 for r in rows for t in r.get("tools", []) if not t.get("ok", True))
    return {
        "runs": len(rows),
        "success_rate": round(sum(r["success"] for r in rows) / len(rows), 3),
        "avg_response_time_s": round(mean(r["response_time_s"] for r in rows), 3),
        "avg_llm_calls": round(mean(r["llm_calls"] for r in rows), 2),
        "avg_tools_per_run": round(mean(len(r.get("tools", [])) for r in rows), 2),
        "distinct_tools_used": len(tool_counter),
        "tool_error_rate": round(tool_errors / max(1, sum(tool_counter.values())), 3),
        "top_tools": tool_counter.most_common(8),
        "total_tokens": sum(r.get("tokens", 0) for r in rows),
    }


def main() -> None:
    from rich.console import Console
    from rich.table import Table

    ap = argparse.ArgumentParser()
    ap.add_argument("--label", help="filter by label substring, e.g. part1 or part2")
    args = ap.parse_args()
    stats = summarise(args.label)
    table = Table(title="Agent metrics (from traces/traces.jsonl)")
    table.add_column("metric")
    table.add_column("value", justify="right")
    for k, v in stats.items():
        table.add_row(k, ", ".join(f"{n}×{c}" for n, c in v) if k == "top_tools" else str(v))
    Console().print(table)


if __name__ == "__main__":
    main()
