"""Run one pattern demo, or all of them.

    python -m lab_2_multi_agent.patterns.run pattern_1_sequential_pipeline
    python -m lab_2_multi_agent.patterns.run all
"""

from __future__ import annotations

import importlib
import sys

PATTERNS = [
    "pattern_1_sequential_pipeline",
    "pattern_2_orchestrator",
    "pattern_3_parallel_fan_out_gather",
    "pattern_4_hierarchical_decomposition",
    "pattern_5_generator_critic",
]


def main() -> None:
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = PATTERNS if choice == "all" else [choice]
    for name in names:
        if name not in PATTERNS:
            raise SystemExit(f"Unknown pattern '{name}'. Choose from: {', '.join(PATTERNS)} or all")
        sys.argv = [sys.argv[0]]
        importlib.import_module(f"lab_2_multi_agent.patterns.{name}").main()


if __name__ == "__main__":
    main()
