# Exercise 2: Add more agents (about 15 minutes)

**Goal:** add a fourth specialist to the Citizen Services Platform: a **Notification Agent** that
drafts an SMS/email confirmation after an appointment is booked.

You will touch four places. That list *is* the checklist for adding any agent.

## 1. Give it a tool (`workshop/tools.py`)

```python
@tool
def send_notification(channel: str, message: str) -> str:
    """Send a confirmation to the applicant by 'sms' or 'email'. Message max 300 characters, no personal identifiers."""
    return f"Queued {channel} notification ({len(message)} chars)."
```

Add it to `ALL_TOOLS`.

## 2. Allow the tool (`workshop/guardrails/tool_policy.py`)

```python
TOOL_ALLOWLIST["notification_agent"] = {"send_notification"}
```

Try skipping this step first. What error do you get, and when? (Answer: at start-up, from
`enforce_allowlist`. Misconfigured agents fail fast, not in front of a citizen.)

## 3. Define the specialist (`lab_2_multi_agent/citizen_platform/agents.py`)

```python
NOTIFICATION_AGENT = Specialist(
    name="notification_agent",
    system_prompt="You send a short confirmation after a booking or submission. Include the reference, date, time and place.",
    tools=[T["send_notification"]],
)
AGENTS = {a.name: a for a in (RETRIEVAL_AGENT, VALIDATION_AGENT, ACTION_AGENT, NOTIFICATION_AGENT)}
```

Update `Route.next` to include `"notification_agent"` and describe it in `SUPERVISOR_PROMPT`.

> **Offline mock mode only:** the mock supervisor routes by keywords, so also teach `Route.mock_response`
> about the new agent (for example: route to `notification_agent` when the request contains "text", "sms" or "email").
> A real LLM just reads your updated `SUPERVISOR_PROMPT`.

## 4. Wire it into the graph (`lab_2_multi_agent/citizen_platform/graph.py`)

```python
def notification_agent(state, config):
    result = run_specialist(AGENTS["notification_agent"], _task_messages(state), config, context=state.get("context", ""))
    return _report(state, "notification_agent", result)

g.add_node("notification_agent", notification_agent)
g.add_edge("notification_agent", "supervisor")
# and add "notification_agent" to the supervisor's conditional edge list + route_supervisor's Literal
```

## Test

```bash
python -m lab_2_multi_agent.citizen_platform.run --auto-approve \
  -q "I'm 67, citizen, household income \$2,400 for 2 people. Check SMG eligibility, book an assessment and text me the details."
python -m lab_2_multi_agent.citizen_platform.run --show-graph   # your new node should appear
```

**Stretch:** add a `translation_agent` so answers can come back in another language. Should it run before
or after `output_guard`? Why?
