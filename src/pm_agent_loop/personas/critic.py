from dataclasses import dataclass

from pm_agent_loop.personas.pm import CHECKLIST_FIELDS
from pm_agent_loop.schema.project_spec import ProjectSpec

_SECURITY_FIELD = "security_and_risk_considerations"
_REGULATORY_SUPPLY_CHAIN_COST_FIELDS = (
    "regulatory_and_compliance_constraints",
    "supply_chain_security_expectations",
    "cost_sensitivity",
)
_MIN_TESTABLE_LENGTH = 10


@dataclass
class CriticFinding:
    field: str
    issue: str


def _is_blank(value: str) -> bool:
    return value.strip() == ""


def check_internal_consistency(spec: ProjectSpec) -> list[CriticFinding]:
    in_scope = spec.in_scope.strip()
    if (
        in_scope
        and in_scope.upper() != "N/A"
        and in_scope.lower() == spec.out_of_scope.strip().lower()
    ):
        return [
            CriticFinding(
                field="in_scope",
                issue="in_scope and out_of_scope are identical, a contradiction.",
            )
        ]
    return []


def check_completeness(spec: ProjectSpec) -> list[CriticFinding]:
    findings = []
    for field_name in CHECKLIST_FIELDS:
        if field_name == "revision_history":
            continue
        value = getattr(spec, field_name)
        if _is_blank(value):
            findings.append(
                CriticFinding(
                    field=field_name,
                    issue="Field is blank; must be answered or explicitly marked N/A.",
                )
            )
    return findings


def check_acceptance_criteria_testable(spec: ProjectSpec) -> list[CriticFinding]:
    value = spec.acceptance_criteria.strip()
    if value and value.upper() != "N/A" and len(value) < _MIN_TESTABLE_LENGTH:
        return [
            CriticFinding(
                field="acceptance_criteria",
                issue="Acceptance criteria are too vague to be testable/verifiable.",
            )
        ]
    return []


def check_security_field_not_blank(spec: ProjectSpec) -> list[CriticFinding]:
    if _is_blank(getattr(spec, _SECURITY_FIELD)):
        return [
            CriticFinding(
                field=_SECURITY_FIELD,
                issue=(
                    "Security and risk considerations must be explicitly "
                    "addressed, not left blank."
                ),
            )
        ]
    return []


def check_regulatory_supply_chain_cost_fields_not_blank(
    spec: ProjectSpec,
) -> list[CriticFinding]:
    findings = []
    for field_name in _REGULATORY_SUPPLY_CHAIN_COST_FIELDS:
        if _is_blank(getattr(spec, field_name)):
            findings.append(
                CriticFinding(
                    field=field_name,
                    issue=(
                        f"{field_name} must be explicitly addressed (answered "
                        "or marked N/A), not silently left blank."
                    ),
                )
            )
    return findings


def review(spec: ProjectSpec) -> list[CriticFinding]:
    findings: list[CriticFinding] = []
    findings.extend(check_internal_consistency(spec))
    findings.extend(check_completeness(spec))
    findings.extend(check_acceptance_criteria_testable(spec))
    findings.extend(check_security_field_not_blank(spec))
    findings.extend(check_regulatory_supply_chain_cost_fields_not_blank(spec))
    return findings
