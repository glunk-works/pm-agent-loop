import pytest

from pm_agent_loop.personas.pm import (
    CHECKLIST_FIELDS,
    CLARIFICATION_HINTS,
    TRIVIAL_BATCH_FIELDS,
    ChecklistState,
    FieldStatus,
    build_clarifying_followup,
    detect_input_type,
    needs_clarification,
    next_question,
)


@pytest.mark.parametrize(
    ("raw_input", "artifact_kind", "expected"),
    [
        ("a raw idea", None, "raw_idea"),
        (None, "existing_file", "existing_artifact"),
        (None, "missing_file", "raw_idea"),
    ],
)
def test_detect_input_type(tmp_path, raw_input, artifact_kind, expected):
    path = None
    if artifact_kind == "existing_file":
        path = tmp_path / "artifact.md"
        path.write_text("some content", encoding="utf-8")
    elif artifact_kind == "missing_file":
        path = tmp_path / "does_not_exist.md"

    assert detect_input_type(raw_input, path) == expected


def test_is_ready_to_draft_false_until_last_field_resolved():
    state = ChecklistState()
    for field in CHECKLIST_FIELDS:
        state.set_status(field, FieldStatus.ANSWERED)
    state.set_status("security_and_risk_considerations", FieldStatus.UNANSWERED)

    assert state.is_ready_to_draft() is False

    state.set_status("security_and_risk_considerations", FieldStatus.ANSWERED)
    assert state.is_ready_to_draft() is True

    state.set_status("security_and_risk_considerations", FieldStatus.MARKED_NA)
    assert state.is_ready_to_draft() is True


@pytest.mark.parametrize(
    "security_field",
    [
        "security_and_risk_considerations",
        "regulatory_and_compliance_constraints",
        "supply_chain_security_expectations",
    ],
)
def test_security_relevant_fields_cannot_be_silently_skipped(security_field):
    state = ChecklistState()
    for field in CHECKLIST_FIELDS:
        state.set_status(field, FieldStatus.ANSWERED)
    state.set_status(security_field, FieldStatus.UNANSWERED)

    assert state.is_ready_to_draft() is False

    state.set_status(security_field, FieldStatus.MARKED_NA)
    assert state.is_ready_to_draft() is True


def test_next_question_single_field_when_not_trivial_batch():
    state = ChecklistState()
    assert state.unanswered_fields()[0] == "problem_statement"

    questions = next_question(state)

    assert questions == ["What is the problem statement for this project?"]


def test_next_question_batches_only_contiguous_trivial_fields():
    state = ChecklistState()
    for field in CHECKLIST_FIELDS:
        if field not in TRIVIAL_BATCH_FIELDS:
            state.set_status(field, FieldStatus.ANSWERED)

    questions = next_question(state)

    assert len(questions) == len(TRIVIAL_BATCH_FIELDS)
    assert len(questions) in (2, 3)


def test_needs_clarification_detects_uncertain_answers():
    assert needs_clarification("I don't know") is True
    assert needs_clarification("We store PII and must comply with GDPR") is False


@pytest.mark.parametrize("field_name", list(CLARIFICATION_HINTS))
def test_build_clarifying_followup_is_field_specific(field_name):
    followup = build_clarifying_followup(field_name, "maybe")

    assert followup
    assert field_name in followup
