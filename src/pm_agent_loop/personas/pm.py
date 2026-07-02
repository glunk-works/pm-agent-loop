from enum import Enum
from pathlib import Path
from typing import Literal

from pm_agent_loop.schema.project_spec import ProjectSpec

CHECKLIST_FIELDS: list[str] = [
    name for name in ProjectSpec.model_fields if name != "spec_version"
]

TRIVIAL_BATCH_FIELDS = {
    "regulatory_and_compliance_constraints",
    "supply_chain_security_expectations",
    "cost_sensitivity",
}

_UNCERTAINTY_PHRASES = {
    "not sure",
    "i don't know",
    "i dont know",
    "unsure",
    "no idea",
    "not certain",
    "maybe",
}

CLARIFICATION_HINTS: dict[str, str] = {
    "problem_statement": (
        "Describe what's broken or missing today, and for whom, in a sentence or two."
    ),
    "purpose_and_goals": (
        "What should be true once this ships? Focus on outcomes, not features."
    ),
    "target_users": "Who will actually use this, day to day?",
    "in_scope": "List the concrete capabilities this project will deliver.",
    "out_of_scope": "What might people assume is included, but isn't?",
    "functional_requirements": "What specific actions must the system support?",
    "integration_context": (
        "Where will this run, and what existing systems does it need to talk to?"
    ),
    "acceptance_criteria": "How would someone verify this is working correctly?",
    "priority_ranking": "Which parts are must-have for v1 versus nice-to-have later?",
    "timeline_and_cost_estimates": (
        "Roughly how much time or budget is available or expected?"
    ),
    "risks_and_assumptions": (
        "What are you assuming will hold true, and what could go wrong if it doesn't?"
    ),
    "security_and_risk_considerations": (
        "Does this handle sensitive data, credentials, or need distinct access levels?"
    ),
    "regulatory_and_compliance_constraints": (
        "Are there data residency or compliance regimes (e.g. GDPR, HIPAA) that apply?"
    ),
    "supply_chain_security_expectations": (
        "Is dependency scanning, artifact signing, or vuln management expected?"
    ),
    "cost_sensitivity": "Is compute/token cost a hard constraint here, or a non-issue?",
    "open_questions_for_architect": (
        "Is there anything you want to explicitly leave unresolved for now?"
    ),
    "revision_history": (
        "This tracks critic findings and how they were resolved as the spec evolves."
    ),
}


class FieldStatus(Enum):
    UNANSWERED = "unanswered"
    ANSWERED = "answered"
    MARKED_NA = "marked_na"


def detect_input_type(
    raw_input: str | None, artifact_path: Path | None
) -> Literal["raw_idea", "existing_artifact"]:
    if artifact_path is not None and artifact_path.is_file():
        return "existing_artifact"
    return "raw_idea"


class ChecklistState:
    def __init__(self) -> None:
        self._fields: dict[str, FieldStatus] = dict.fromkeys(
            CHECKLIST_FIELDS, FieldStatus.UNANSWERED
        )
        self._answers: dict[str, str] = dict.fromkeys(CHECKLIST_FIELDS, "")
        # revision_history is populated by the critic revision loop from
        # structured RevisionHistoryEntry data, not asked of the human as a
        # free-text interview question like the other 16 fields.
        self._fields["revision_history"] = FieldStatus.ANSWERED

    def get_status(self, field_name: str) -> FieldStatus:
        return self._fields[field_name]

    def set_status(self, field_name: str, status: FieldStatus) -> None:
        if field_name not in self._fields:
            msg = f"Unknown checklist field: {field_name}"
            raise KeyError(msg)
        self._fields[field_name] = status

    def record_answer(self, field_name: str, value: str) -> None:
        if field_name not in self._fields:
            msg = f"Unknown checklist field: {field_name}"
            raise KeyError(msg)
        self._answers[field_name] = value
        self._fields[field_name] = (
            FieldStatus.MARKED_NA
            if value.strip().upper() == "N/A"
            else FieldStatus.ANSWERED
        )

    def get_answer(self, field_name: str) -> str:
        return self._answers[field_name]

    def answers(self) -> dict[str, str]:
        return dict(self._answers)

    def unanswered_fields(self) -> list[str]:
        return [
            field
            for field in CHECKLIST_FIELDS
            if self._fields[field] is FieldStatus.UNANSWERED
        ]

    def is_ready_to_draft(self) -> bool:
        return all(
            status is not FieldStatus.UNANSWERED for status in self._fields.values()
        )


def _question_for(field_name: str) -> str:
    return f"What is the {field_name.replace('_', ' ')} for this project?"


def next_question(state: ChecklistState) -> list[str]:
    unanswered = state.unanswered_fields()
    if not unanswered:
        return []

    if unanswered[0] not in TRIVIAL_BATCH_FIELDS:
        return [_question_for(unanswered[0])]

    batch: list[str] = []
    for field in unanswered:
        if field not in TRIVIAL_BATCH_FIELDS or len(batch) == 3:
            break
        batch.append(field)
    return [_question_for(field) for field in batch]


def needs_clarification(answer: str) -> bool:
    stripped = answer.strip().lower()
    if not stripped:
        return True
    return any(phrase in stripped for phrase in _UNCERTAINTY_PHRASES)


def build_clarifying_followup(field_name: str, answer: str) -> str:
    hint = CLARIFICATION_HINTS.get(field_name, "")
    return (
        f"Your answer ('{answer}') for {field_name} wasn't specific enough to "
        f"record yet. {hint}"
    )
