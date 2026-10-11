"""Every scheme lives in two places: its rules (Mock Gov API) and its scheme text (knowledge base).

Lab 1, Exercise D adds a scheme. This test fails if only one half was added.
"""

from workshop.config import get_settings
from workshop.gov_api.data import SCHEMES
from workshop.rag.ingest import load_documents, parse


def _scheme_ids_in_knowledge_base() -> set[str]:
    ids = set()
    for _name, raw in load_documents(get_settings().knowledge_base_dir):
        meta, _body = parse(raw)
        if meta.get("scheme_id"):
            ids.add(meta["scheme_id"])
    return ids


def test_every_scheme_has_rules_and_policy_text():
    in_api, in_kb = set(SCHEMES), _scheme_ids_in_knowledge_base()
    assert in_api - in_kb == set(), f"rules but no scheme file in data/knowledge_base/: {in_api - in_kb}"
    assert in_kb - in_api == set(), f"scheme file but no rules in workshop/gov_api/data.py: {in_kb - in_api}"
