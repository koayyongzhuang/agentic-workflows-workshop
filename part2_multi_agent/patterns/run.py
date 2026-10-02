"""Run one pattern demo, or all of them.

    python -m part2_multi_agent.patterns.run sequential
    python -m part2_multi_agent.patterns.run all
"""

from __future__ import annotations

import importlib
import sys

PATTERNS = ["sequential", "coordinator", "parallel", "hierarchical", "generator_critic", "supervisor_travel"]


def main() -> None:
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = PATTERNS if choice == "all" else [choice]
    for name in names:
        if name not in PATTERNS:
            raise SystemExit(f"Unknown pattern '{name}'. Choose from: {', '.join(PATTERNS)} or all")
        sys.argv = [sys.argv[0]]
        importlib.import_module(f"part2_multi_agent.patterns.{name}").main()


if __name__ == "__main__":
    main()
