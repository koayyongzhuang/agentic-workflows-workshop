"""Create the LangGraph Studio assistants the Lab 1 guide uses.

`make studio` runs this in the background as Studio starts. Participants then pick an
assistant in Studio instead of creating one by hand:

    Default Configuration                     created by Studio itself: role helpdesk
    Lab 1 · A · prompt: strict_officer        Exercise A: same tools, different prompt
    Lab 1 · A · prompt: concise               Exercise A
    Lab 1 · C · role: eligibility_checker     Exercise C: different tools (and prompt)
    Lab 1 · C · role: appointment_scheduler   Exercise C
    Lab 1 · C · role: <any role you add>      Exercise C, after you add it to prompts.py
                                              and restart `make studio`

Safe to run again: it creates what's missing, updates settings that changed, and
removes assistants it created earlier that the guide no longer uses.

    python -m scripts.studio_assistants          # Studio already running
    python -m scripts.studio_assistants --wait   # wait for Studio to start first
"""

from __future__ import annotations

import argparse
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


def wanted_assistants() -> list[tuple[str, dict]]:
    """(name, settings) for each assistant the guide uses."""
    from lab_1_single_agent.prompts import ROLES

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
    args = ap.parse_args()

    if not wait_for(args.url, 180 if args.wait else 3):
        print(f"[studio assistants] Studio isn't answering at {args.url}; skipped. "
              "Create assistants in Studio's Assistants panel instead.", file=sys.stderr)
        sys.exit(1)

    wanted = wanted_assistants()
    wanted_ids = {assistant_id(n) for n, _ in wanted}
    created, updated, removed = [], [], []
    with httpx.Client(base_url=args.url, timeout=30) as client:
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
