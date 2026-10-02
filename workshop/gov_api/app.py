"""Mock Gov Service: a small FastAPI app the agents call like a real backend.

Run standalone:  uvicorn workshop.gov_api.app:app --port 8000
Interactive docs: http://localhost:8000/docs

State is in memory and resets on restart. Everything here is fictional.
"""

from __future__ import annotations

import itertools
import re
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from workshop.gov_api.data import SCHEMES, SERVICE_CENTRES

app = FastAPI(
    title="Mock Gov Service",
    description="Fictional citizen-services backend for the agentic workflows workshop.",
    version="1.0.0",
)

_app_seq = itertools.count(1001)
_appt_seq = itertools.count(501)
APPLICATIONS: dict[str, dict] = {}
APPOINTMENTS: dict[str, dict] = {}
BOOKED_SLOTS: set[str] = set()


def resolve_scheme(ref: str) -> dict:
    """Accept an ID ("SMG") or a (partial) name ("senior mobility grant")."""
    ref_clean = ref.strip()
    if ref_clean.upper() in SCHEMES:
        return SCHEMES[ref_clean.upper()]
    low = ref_clean.lower()
    for scheme in SCHEMES.values():
        if scheme["name"].lower() in low or low in scheme["name"].lower():
            return scheme
    for scheme in SCHEMES.values():  # ID mentioned inside a longer string
        if re.search(rf"\b{scheme['id']}\b", ref_clean):
            return scheme
    raise HTTPException(status_code=404, detail=f"Unknown scheme '{ref}'. Known: {', '.join(SCHEMES)}")


# ----------------------------------------------------------------------------- models
class EligibilityRequest(BaseModel):
    scheme: str = Field(description="Scheme ID or name")
    age: int = Field(ge=0, le=120)
    monthly_household_income: float = Field(ge=0)
    household_size: int = Field(default=1, ge=1, le=20)
    residency: Literal["citizen", "pr", "foreigner"] = "citizen"


class EligibilityResult(BaseModel):
    scheme_id: str
    scheme_name: str
    eligible: bool
    per_capita_income: float
    reasons: list[str]
    next_steps: list[str]


class AppointmentRequest(BaseModel):
    scheme: str
    slot: str | None = Field(default=None, description="Slot ID from /appointments/slots. Omit for earliest.")
    applicant_ref: str = Field(default="ANON-0001", description="Pseudonymous applicant reference (never an ID number)")


class ApplicationRequest(BaseModel):
    scheme: str
    applicant_ref: str = "ANON-0001"
    eligibility_checked: bool = False
    notes: str = ""


# ----------------------------------------------------------------------------- routes
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now().isoformat(timespec="seconds")}


@app.get("/schemes")
def list_schemes() -> list[dict]:
    return [{k: s[k] for k in ("id", "name", "summary", "benefit")} for s in SCHEMES.values()]


@app.get("/schemes/{scheme}")
def get_scheme(scheme: str) -> dict:
    return resolve_scheme(scheme)


@app.post("/eligibility", response_model=EligibilityResult)
def check_eligibility(req: EligibilityRequest) -> EligibilityResult:
    s = resolve_scheme(req.scheme)
    c = s["criteria"]
    per_capita = round(req.monthly_household_income / req.household_size, 2)
    reasons: list[str] = []
    ok = True
    if c["min_age"] is not None and req.age < c["min_age"]:
        ok = False
        reasons.append(f"Minimum age is {c['min_age']} (applicant is {req.age}).")
    if c["max_age"] is not None and req.age > c["max_age"]:
        ok = False
        reasons.append(f"Maximum age is {c['max_age']} (applicant is {req.age}).")
    if c["max_per_capita_income"] is not None and per_capita > c["max_per_capita_income"]:
        ok = False
        reasons.append(f"Per-capita household income ${per_capita:,.0f} exceeds the ${c['max_per_capita_income']:,} limit.")
    if req.residency not in c["residency"]:
        ok = False
        reasons.append(f"Residency '{req.residency}' not covered (allowed: {', '.join(c['residency'])}).")
    if ok:
        reasons.append("Meets all published criteria.")
    next_steps = (
        (["Book a " + s["appointment_type"].lower()] if s["needs_appointment"] else [])
        + [f"Prepare: {d}" for d in s["required_documents"]]
        + ["Submit application"]
        if ok
        else ["Consider other schemes via /schemes"]
    )
    return EligibilityResult(
        scheme_id=s["id"], scheme_name=s["name"], eligible=ok,
        per_capita_income=per_capita, reasons=reasons, next_steps=next_steps,
    )


def _slots_for(scheme_id: str, days: int = 5) -> list[dict]:
    slots, d = [], date.today()
    while len(slots) < days * 2:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue
        for hour, centre in ((10, SERVICE_CENTRES[len(slots) % 3]), (15, SERVICE_CENTRES[(len(slots) + 1) % 3])):
            slot_id = f"{scheme_id}-{d:%Y%m%d}-{hour}"
            if slot_id not in BOOKED_SLOTS:
                slots.append({"slot": slot_id, "date": d.isoformat(), "time": f"{hour:02d}:00", "location": centre})
    return slots


@app.get("/appointments/slots")
def appointment_slots(scheme: str) -> list[dict]:
    s = resolve_scheme(scheme)
    if not s["needs_appointment"]:
        return []
    return _slots_for(s["id"])


@app.post("/appointments")
def book_appointment(req: AppointmentRequest) -> dict:
    s = resolve_scheme(req.scheme)
    if not s["needs_appointment"]:
        raise HTTPException(400, f"{s['name']} does not need an appointment; apply directly.")
    available = _slots_for(s["id"])
    chosen = next((x for x in available if x["slot"] == req.slot), None) if req.slot else available[0]
    if chosen is None:
        raise HTTPException(409, f"Slot '{req.slot}' is unavailable. Try one of: {[x['slot'] for x in available[:3]]}")
    BOOKED_SLOTS.add(chosen["slot"])
    ref = f"APT-{next(_appt_seq)}"
    APPOINTMENTS[ref] = {"reference": ref, "scheme_id": s["id"], "type": s["appointment_type"], "applicant_ref": req.applicant_ref, **chosen}
    return APPOINTMENTS[ref]


@app.post("/applications")
def submit_application(req: ApplicationRequest) -> dict:
    s = resolve_scheme(req.scheme)
    if not req.eligibility_checked:
        raise HTTPException(422, "Eligibility must be checked before an application is submitted.")
    app_id = f"APP-{next(_app_seq)}"
    APPLICATIONS[app_id] = {
        "application_id": app_id, "scheme_id": s["id"], "scheme_name": s["name"],
        "applicant_ref": req.applicant_ref, "status": "SUBMITTED",
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "expected_outcome_by": (date.today() + timedelta(days=14)).isoformat(),
    }
    return APPLICATIONS[app_id]


@app.get("/applications/{application_id}")
def application_status(application_id: str) -> dict:
    if application_id not in APPLICATIONS:
        raise HTTPException(404, f"No application {application_id}")
    return APPLICATIONS[application_id]
