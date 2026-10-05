"""Serve the Citizen Services Platform over HTTP (the "Deploy to Production" step).

    uvicorn lab_2_multi_agent.citizen_platform.serve:app --port 8080
    # docker compose: `make serve`, then open http://localhost:8080/docs

Endpoints
    POST /chat      {"thread_id": "t1", "message": "..."}         -> answer, or an approval request
    POST /approve   {"thread_id": "t1", "decision": "yes" | "no"} -> resumes the paused run
    GET  /threads/{thread_id}                                     -> saved state (from the checkpointer)
    GET  /metrics                                                 -> success rate, tools used, avg response time

With DATABASE_URL set, paused runs live in Postgres: restart the server between
/chat and /approve and the run still resumes.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from lab_2_multi_agent.citizen_platform.graph import build_platform
from scripts.trace_report import summarise
from workshop.errors import explain
from workshop.memory import get_checkpointer
from workshop.observability import traced

app = FastAPI(title="Citizen Services Platform", version="1.0.0")
graph = build_platform(checkpointer=get_checkpointer())


class ChatIn(BaseModel):
    thread_id: str
    message: str
    user_id: str = "demo-user"


class ApproveIn(BaseModel):
    thread_id: str
    decision: str = "yes"


def _respond(result: dict, thread_id: str) -> dict:
    if result.get("__interrupt__"):
        req = result["__interrupt__"][0].value
        return {"thread_id": thread_id, "status": "awaiting_approval", "approval_request": req}
    return {
        "thread_id": thread_id,
        "status": "blocked" if result.get("blocked") else "done",
        "answer": result["messages"][-1].content,
        "agents": result.get("turn_steps", []),
        "guardrail_events": result.get("guardrail_events", []),
    }


def _error(exc: Exception) -> HTTPException:
    e = explain(exc)
    return HTTPException(e.http_status, {"error": e.kind, "message": e.headline, "advice": e.advice,
                                         "retryable": e.retryable, "detail": e.detail})


@app.post("/chat")
def chat(body: ChatIn) -> dict:
    """Send a message. If the previous turn on this thread failed, send {"message": ""} to retry it."""
    config_base = {"configurable": {"thread_id": body.thread_id, "user_id": body.user_id}}
    retrying = not body.message.strip() and bool(graph.get_state(config_base).next)
    try:
        with traced("api:citizen_platform", body.message, verbose=False) as (config, tracer):
            config.update(config_base)
            result = graph.invoke(None if retrying else {"messages": [HumanMessage(body.message)]}, config)
            tracer.outcome = str(result["messages"][-1].content)
    except Exception as exc:  # noqa: BLE001
        raise _error(exc) from exc
    return _respond(result, body.thread_id)


@app.post("/approve")
def approve(body: ApproveIn) -> dict:
    config = {"configurable": {"thread_id": body.thread_id}}
    if not graph.get_state(config).next:
        raise HTTPException(409, "Nothing is waiting for approval on this thread.")
    try:
        with traced("api:approval", body.decision, verbose=False) as (cfg, tracer):
            cfg.update(config)
            result = graph.invoke(Command(resume=body.decision), cfg)
            tracer.outcome = str(result["messages"][-1].content)
    except Exception as exc:  # noqa: BLE001
        raise _error(exc) from exc
    return _respond(result, body.thread_id)


@app.get("/threads/{thread_id}")
def thread_state(thread_id: str) -> dict:
    snap = graph.get_state({"configurable": {"thread_id": thread_id}})
    if not snap.values:
        raise HTTPException(404, "Unknown thread")
    v = snap.values
    return {
        "waiting_on": list(snap.next),
        "validated_schemes": v.get("validated_schemes", []),
        "completed_actions": v.get("completed_actions", []),
        "messages": [{"role": m.type, "name": getattr(m, "name", None), "content": m.content} for m in v.get("messages", [])],
    }


@app.get("/metrics")
def metrics() -> dict:
    return summarise()
