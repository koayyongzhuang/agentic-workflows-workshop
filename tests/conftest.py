import os

import pytest

# Deterministic, offline defaults for every test run (CI-safe).
os.environ["MODEL"] = "mock"
os.environ["EMBEDDING_MODEL"] = "hash"
os.environ["VERBOSE"] = "false"
os.environ.setdefault("HUMAN_APPROVAL", "true")
for key in [k for k in os.environ if k.startswith("MODEL_")]:
    del os.environ[key]


@pytest.fixture(autouse=True)
def _trace_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))


ELIGIBLE_SMG = (
    "I'm 67, citizen, household income $2,400 for 2 people. "
    "Am I eligible for the Senior Mobility Grant? If so, book an assessment appointment."
)
