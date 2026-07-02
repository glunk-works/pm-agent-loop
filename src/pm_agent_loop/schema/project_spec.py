from pydantic import BaseModel


class RevisionHistoryEntry(BaseModel):
    version: int
    trigger: str
    change: str
    resolved_by: str


class ProjectSpec(BaseModel):
    spec_version: int
    problem_statement: str
    purpose_and_goals: str
    target_users: str
    in_scope: str
    out_of_scope: str
    functional_requirements: str
    integration_context: str
    acceptance_criteria: str
    priority_ranking: str
    timeline_and_cost_estimates: str
    risks_and_assumptions: str
    security_and_risk_considerations: str
    regulatory_and_compliance_constraints: str
    supply_chain_security_expectations: str
    cost_sensitivity: str
    open_questions_for_architect: str
    revision_history: list[RevisionHistoryEntry]
