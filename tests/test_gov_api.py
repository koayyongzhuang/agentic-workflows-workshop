from fastapi.testclient import TestClient

from workshop.gov_api.app import app

client = TestClient(app)


def elig(**kw):
    body = {"scheme": "SMG", "age": 67, "monthly_household_income": 2400, "household_size": 2, "residency": "citizen", **kw}
    return client.post("/eligibility", json=body).json()


def test_eligible_senior():
    r = elig()
    assert r["eligible"] and r["per_capita_income"] == 1200


def test_income_too_high():
    r = elig(monthly_household_income=4000)
    assert not r["eligible"] and any("exceeds" in x for x in r["reasons"])


def test_scheme_resolved_by_name():
    assert client.get("/schemes/senior mobility grant").json()["id"] == "SMG"


def test_submit_requires_eligibility_flag():
    assert client.post("/applications", json={"scheme": "SUC"}).status_code == 422
    ok = client.post("/applications", json={"scheme": "SUC", "eligibility_checked": True}).json()
    assert ok["status"] == "SUBMITTED"
    assert client.get(f"/applications/{ok['application_id']}").json()["scheme_id"] == "SUC"


def test_booking_takes_slot():
    first = client.post("/appointments", json={"scheme": "SMG"}).json()
    second = client.post("/appointments", json={"scheme": "SMG"}).json()
    assert first["slot"] != second["slot"]
