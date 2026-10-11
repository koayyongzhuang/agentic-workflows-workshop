"""Start `langgraph dev` for `make studio`, watching only the lab code for changes.

`langgraph dev` reloads when a file under the current folder changes. In the container the
watcher has to poll for changes (see WATCHFILES_FORCE_POLLING in docker-compose.yml), and
from /app it would also see the .langgraph_api/*.pckl files the dev server keeps rewriting,
filling the log with "3 changes detected". `langgraph dev` has no option to choose the
folders it watches, so this passes uvicorn the code folders directly.

    python -m scripts.studio_dev --host 0.0.0.0 --port 2024 --no-browser
"""

from __future__ import annotations

import functools
import sys

import uvicorn
from langgraph_cli.cli import cli

WATCH = ["lab_1_single_agent", "lab_2_multi_agent", "lab_3_deep_agent", "workshop"]

_run = uvicorn.run


@functools.wraps(_run)
def _run_watching_code(*args, **kwargs):
    if kwargs.get("reload"):
        kwargs["reload_dirs"] = WATCH
    return _run(*args, **kwargs)


uvicorn.run = _run_watching_code

if __name__ == "__main__":
    cli(["dev", *sys.argv[1:]], prog_name="langgraph")
