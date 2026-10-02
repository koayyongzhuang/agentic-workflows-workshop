"""Memory for agents.

Short-term memory = the conversation (messages + state) of one thread.
LangGraph saves it after every step with a *checkpointer*, keyed by thread_id:
  * DATABASE_URL set  -> PostgresSaver (survives restarts, shareable across workers)
  * otherwise         -> InMemorySaver (lost when the process exits)

Long-term memory = facts that outlive a thread. Here they are stored as
vectors in the "memories" collection (see `remember_fact` / `recall_facts`
in workshop/tools.py), so agents can search them semantically.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from workshop.config import get_settings


@lru_cache(maxsize=2)
def _checkpointer(database_url: str | None) -> BaseCheckpointSaver:
    if not database_url:
        return InMemorySaver()
    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row

    conn = psycopg.connect(database_url, autocommit=True, prepare_threshold=0, row_factory=dict_row)
    saver = PostgresSaver(conn)
    saver.setup()  # creates checkpoint tables on first run
    return saver


def get_checkpointer() -> BaseCheckpointSaver:
    return _checkpointer(get_settings().database_url)
