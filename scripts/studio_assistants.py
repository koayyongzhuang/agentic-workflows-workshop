"""Create the LangGraph Studio assistants the Lab 1 guide uses.

`make studio` runs this in the background as Studio starts. Participants then pick an
assistant in Studio instead of creating one by hand:

    Default Configuration                     created by Studio itself: role helpdesk
    Lab 1 · A · prompt: strict_officer        Exercise A: same tools, different prompt
    Lab 1 · A · prompt: concise               Exercise A
    Lab 1 · C · role: eligibility_checker     Exercise C: different tools (and prompt)
    Lab 1 · C · role: appointment_scheduler   Exercise C
    Lab 1 · C · role: <any role you add>      Exercise C, a few seconds after you save it
                                              in prompts.py (--watch re-syncs on every save)

Safe to run again: it creates what's missing, updates settings that changed, and
removes assistants it created earlier that the guide no longer uses.

    python -m scripts.studio_assistants          # Studio already running
    python -m scripts.studio_assistants --wait   # wait for Studio to start first
    python -m scripts.studio_assistants --wait --watch   # what `make studio` runs
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
from uuid import NAMESPACE_URL, uuid5

import httpx

GRAPH_ID = "lab_1_single_agent"
CREATED_BY = "make studio"

# Exercise A compares these prompts with the default (helpdesk) prompt; the tools stay the same.
EXERCISE_A_PROMPTS = ["strict_officer", "concise"]
# Exercise C compares these built-in roles. Any role a participant adds is included too.
EXERCISE_C_ROLES = ["eligibility_checker", "appointment_scheduler"]
# Roles that ship with the repo. Anything else in ROLES was added by the participant.
BUILT_IN_ROLES = {"helpdesk", "policy_researcher", "eligibility_checker", "appointment_scheduler"}


PROMPTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "lab_1_single_agent", "prompts.py")


def wanted_assistants() -> list[tuple[str, dict]]:
    """(name, settings) for each assistant the guide uses, read fresh from prompts.py."""
    import lab_1_single_agent.prompts as prompts

    ROLES = importlib.reload(prompts).ROLES

    out = [(f"Lab 1 · A · prompt: {p}", {"role": "helpdesk", "prompt": p}) for p in EXERCISE_A_PROMPTS]
    added = [r for r in ROLES if r not in BUILT_IN_ROLES]
    for r in EXERCISE_C_ROLES + added:
        # Show the prompt the role really uses, so Studio's Prompt field isn't blank.
        out.append((f"Lab 1 · C · role: {r}", {"role": r, "prompt": ROLES[r]["prompt"]}))
    return out


def wait_for(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/ok", timeout=2).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1)
    return False


def assistant_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"stack-workshop/{GRAPH_ID}/{name}"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.getenv("STUDIO_URL", "http://127.0.0.1:2024"))
    ap.add_argument("--wait", action="store_true", help="wait up to 3 minutes for Studio to start")
    ap.add_argument("--watch", action="store_true", help="keep running and re-sync whenever prompts.py is saved")
    args = ap.parse_args()

    if not wait_for(args.url, 180 if args.wait else 3):
        print(f"[studio assistants] Studio isn't answering at {args.url}; skipped. "
              "Create assistants in Studio's Assistants panel instead.", file=sys.stderr)
        sys.exit(1)

    sync(args.url)
    if not args.watch:
        return
    # `make studio` starts us next to the server (our parent). Stop when it stops (Ctrl-C).
    parent = os.getppid()
    last = os.path.getmtime(PROMPTS_FILE)
    while os.getppid() == parent:
        time.sleep(2)
        try:
            mtime = os.path.getmtime(PROMPTS_FILE)
        except OSError:
            continue
        if mtime == last:
            continue
        last = mtime
        time.sleep(3)  # Studio reloads on the same save; let it go down before waiting for it
        if not wait_for(args.url, 60):
            continue
        try:
            sync(args.url)
        except Exception as exc:  # e.g. a half-typed prompts.py; the next save tries again
            print(f"[studio assistants] couldn't read prompts.py: {exc}", file=sys.stderr)


def sync(url: str) -> None:
    wanted = wanted_assistants()
    wanted_ids = {assistant_id(n) for n, _ in wanted}
    created, updated, removed = [], [], []
    with httpx.Client(base_url=url, timeout=30) as client:
        for name, context in wanted:
            aid = assistant_id(name)
            try:
                existing = client.get(f"/assistants/{aid}")
                if existing.status_code == 200:
                    if existing.json().get("context") != context:
                        client.patch(f"/assistants/{aid}", json={"context": context}).raise_for_status()
                        updated.append(name)
                    continue
                client.post("/assistants", json={
                    "assistant_id": aid, "graph_id": GRAPH_ID, "name": name, "context": context,
                    "metadata": {"created_by": CREATED_BY}, "if_exists": "do_nothing",
                }).raise_for_status()
                created.append(name)
            except httpx.HTTPError as exc:
                print(f"[studio assistants] couldn't set up '{name}': {exc}", file=sys.stderr)

        # Tidy up assistants this script made before that the guide no longer uses.
        try:
            ours = client.post("/assistants/search", json={
                "graph_id": GRAPH_ID, "metadata": {"created_by": CREATED_BY}, "limit": 100}).json()
            for a in ours:
                if a["assistant_id"] not in wanted_ids:
                    client.delete(f"/assistants/{a['assistant_id']}").raise_for_status()
                    removed.append(a["name"])
        except httpx.HTTPError as exc:
            print(f"[studio assistants] couldn't tidy old assistants: {exc}", file=sys.stderr)

    summary = f"[studio assistants] {len(wanted)} Lab 1 assistants ready: " + ", ".join(n.split("Lab 1 · ", 1)[1] for n, _ in wanted)
    extras = [f"{len(created)} new"] * bool(created) + [f"{len(updated)} updated"] * bool(updated) + [f"{len(removed)} old removed"] * bool(removed)
    print(summary + (f" ({', '.join(extras)})" if extras else ""))


if __name__ == "__main__":
    main()
