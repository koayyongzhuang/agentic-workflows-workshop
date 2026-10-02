import pytest

from workshop.rag.ingest import build_chunks, ingest, retrieve


def test_chunks_are_self_describing():
    chunks = build_chunks()
    assert len(chunks) > 10
    assert all(c.content.strip() for c in chunks)
    smg = [c for c in chunks if c.source == "senior_mobility_grant.md"]
    assert all("Senior Mobility Grant" in c.content for c in smg)


@pytest.mark.parametrize("query,source", [
    ("What documents do I need for the Senior Mobility Grant?", "senior_mobility_grant.md"),
    ("How much is the energy rebate per quarter?", "household_energy_rebate.md"),
    ("sports vouchers for youth", "community_sports_voucher.md"),
    ("can the assistant store my NRIC", "data_privacy_and_ai_use.md"),
])
def test_retrieval_finds_right_document(query, source):
    ingest(verbose=False)
    assert retrieve(query, k=2)[0].source == source
