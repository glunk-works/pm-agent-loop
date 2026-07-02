import json
from pathlib import Path

from pm_agent_loop.personas.critic import (
    CriticFinding,
    check_internal_consistency,
    check_security_field_not_blank,
    review,
)
from pm_agent_loop.schema.project_spec import ProjectSpec

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "example_project_spec.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _valid_spec() -> ProjectSpec:
    return ProjectSpec.model_validate(_load_fixture())


def test_review_flags_blank_security_field():
    data = _load_fixture()
    data["security_and_risk_considerations"] = ""
    spec = ProjectSpec.model_validate(data)

    findings = review(spec)

    assert any(f.field == "security_and_risk_considerations" for f in findings)


def test_review_returns_no_findings_for_fully_populated_spec():
    assert review(_valid_spec()) == []


def test_check_internal_consistency_allows_both_scope_fields_marked_na():
    data = _load_fixture()
    data["in_scope"] = "N/A"
    data["out_of_scope"] = "N/A"
    spec = ProjectSpec.model_validate(data)

    assert check_internal_consistency(spec) == []


def test_check_internal_consistency_flags_identical_real_content():
    data = _load_fixture()
    data["out_of_scope"] = data["in_scope"]
    spec = ProjectSpec.model_validate(data)

    findings = check_internal_consistency(spec)

    assert any(f.field == "in_scope" for f in findings)


def test_security_field_check_flags_independently_of_completeness_check():
    data = _load_fixture()
    data["security_and_risk_considerations"] = ""
    spec = ProjectSpec.model_validate(data)

    findings = check_security_field_not_blank(spec)

    assert findings == [
        CriticFinding(
            field="security_and_risk_considerations",
            issue=(
                "Security and risk considerations must be explicitly "
                "addressed, not left blank."
            ),
        )
    ]
