import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pm_agent_loop.schema.project_spec import ProjectSpec

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "example_project_spec.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_valid_fixture_validates():
    ProjectSpec.model_validate(_load_fixture())


def test_missing_security_and_risk_considerations_raises():
    data = _load_fixture()
    del data["security_and_risk_considerations"]
    with pytest.raises(ValidationError):
        ProjectSpec.model_validate(data)
