"""Seed data for the Mock Gov Service.

ALL SCHEMES ARE FICTIONAL. They exist only to give the agents something
realistic to reason about. Figures are illustrative.
"""

from __future__ import annotations

SCHEMES: dict[str, dict] = {
    "SMG": {
        "id": "SMG",
        "name": "Senior Mobility Grant",
        "summary": "Co-pays mobility aids (wheelchairs, walking frames, home rails) for lower-income seniors.",
        "benefit": "Up to $2,000 per applicant every 5 years",
        "criteria": {
            "min_age": 60,
            "max_age": None,
            "max_per_capita_income": 1500,
            "residency": ["citizen", "pr"],
        },
        "required_documents": ["Proof of household income (last 3 months)", "Quotation for the mobility aid"],
        "needs_appointment": True,
        "appointment_type": "Home mobility assessment",
    },
    "HER": {
        "id": "HER",
        "name": "Household Energy Rebate",
        "summary": "Quarterly utilities credit for lower- and middle-income households.",
        "benefit": "$60 to $150 utilities credit per quarter, based on household income",
        "criteria": {
            "min_age": 21,
            "max_age": None,
            "max_per_capita_income": 2500,
            "residency": ["citizen"],
        },
        "required_documents": ["Latest utilities bill"],
        "needs_appointment": False,
        "appointment_type": None,
    },
    "SUC": {
        "id": "SUC",
        "name": "Skills Upgrade Credit",
        "summary": "Credit for approved training courses to help working-age residents upskill.",
        "benefit": "$1,000 one-off credit, valid for 3 years",
        "criteria": {
            "min_age": 25,
            "max_age": 64,
            "max_per_capita_income": None,
            "residency": ["citizen", "pr"],
        },
        "required_documents": ["Course enrolment confirmation"],
        "needs_appointment": False,
        "appointment_type": None,
    },
    "CSV": {
        "id": "CSV",
        "name": "Community Sports Voucher",
        "summary": "Vouchers for youth to join community sports programmes.",
        "benefit": "$200 in sports vouchers per year",
        "criteria": {
            "min_age": 13,
            "max_age": 25,
            "max_per_capita_income": None,
            "residency": ["citizen", "pr"],
        },
        "required_documents": [],
        "needs_appointment": False,
        "appointment_type": None,
    },
}

SERVICE_CENTRES = ["Central Service Centre", "North Service Centre", "East Service Centre"]
