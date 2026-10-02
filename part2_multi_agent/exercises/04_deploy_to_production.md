# Exercise 4: Deploy to production (about 10 minutes)

**Goal:** run the platform as a service with durable state, metrics and tests.

## 1. Serve it

```bash
make serve          # or: uvicorn part2_multi_agent.citizen_platform.serve:app --port 8080
```

Open http://localhost:8080/docs and try:

1. `POST /chat` with `{"thread_id": "t1", "message": "I'm 67, citizen, household income $2,400 for 2 people. Am I eligible for SMG? If so book an assessment."}`
   The response has `"status": "awaiting_approval"`.
2. **Stop the server** (Ctrl+C) and start it again.
3. `POST /approve` with `{"thread_id": "t1", "decision": "yes"}`. The run resumes and books the slot.

This works because the paused graph state lives in **PostgreSQL** (`PostgresSaver`), not in memory.
Try the same without `DATABASE_URL` and see what breaks.

## 2. Observe it

```bash
curl localhost:8080/metrics            # success rate, tools used, avg response time
python -m scripts.trace_report --label api
```

Optional hosted tracing: set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env` and every run appears
in LangSmith with the full tree of agent and tool calls. Or run `make studio` for LangGraph Studio.

## 3. Test it

```bash
make test           # runs offline with the mock model, safe for CI
```

Add a regression test for the bug you care most about, for example "never books without validation".
See `tests/test_platform.py` for the pattern.

## Production checklist (discuss)
- [ ] Secrets from a vault, not `.env`
- [ ] Per-agent model choice (`MODEL_SUPERVISOR`, `MODEL_VALIDATION`, ...) for cost/latency
- [ ] Timeouts and retries on tools; idempotency keys on bookings/submissions
- [ ] HNSW index on `kb_chunks.embedding` once the knowledge base grows
- [ ] Evaluation set of real questions run on every change (success rate must not drop)
- [ ] Audit log of guardrail events and human approvals
- [ ] Rate limits and abuse monitoring on the public endpoint
