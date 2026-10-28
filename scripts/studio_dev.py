"""Start `langgraph dev` for `make studio`, watching only the lab code for changes.

In the container the watcher has to poll for changes (see WATCHFILES_FORCE_POLLING in docker-compose.yml), and
from /app it would also see the .langgraph_api/*.pckl files the dev server keeps rewriting,
filling the log with "3 changes detected". `langgraph dev` has no option to choose the
folders it watches, so this passes uvicorn the code folders directly.

We bind to 0.0.0.0 so Docker/Podman's port mapping can reach the process, but `langgraph dev`
prints that same host in its "Studio" URL banner (via the `langgraph_api.cli` logger, which
writes to stderr), and a browser can't open 0.0.0.0 — it needs 127.0.0.1. So stdout and stderr
are both wrapped to rewrite the printed banner (the actual bind address is untouched).

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


class _BrowsableHostStream:
    """Rewrite 0.0.0.0 to 127.0.0.1 in printed output so the Studio URL is clickable."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        return self._stream.write(text.replace("0.0.0.0", "127.0.0.1"))

    def __getattr__(self, name):
        return getattr(self._stream, name)


sys.stdout = _BrowsableHostStream(sys.stdout)
sys.stderr = _BrowsableHostStream(sys.stderr)

if __name__ == "__main__":
    cli(["dev", *sys.argv[1:]], prog_name="langgraph")
