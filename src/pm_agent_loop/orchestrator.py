from dataclasses import dataclass
from typing import Callable

from pm_agent_loop.personas.critic import CriticFinding, review
from pm_agent_loop.schema.project_spec import ProjectSpec


@dataclass
class TokenTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens


class RevisionCapReached(Exception):
    def __init__(
        self, last_spec: ProjectSpec, remaining_findings: list[CriticFinding]
    ) -> None:
        super().__init__(
            f"Revision cap reached with {len(remaining_findings)} unresolved "
            "finding(s)."
        )
        self.last_spec = last_spec
        self.remaining_findings = remaining_findings


def run_revision_loop(
    initial_spec: ProjectSpec,
    pm_followup_fn: Callable[[list[CriticFinding]], ProjectSpec],
    max_cycles: int = 4,
) -> ProjectSpec:
    spec = initial_spec
    for _ in range(max_cycles):
        findings = review(spec)
        if not findings:
            return spec
        spec = pm_followup_fn(findings)

    findings = review(spec)
    if findings:
        raise RevisionCapReached(spec, findings)
    return spec


def require_signoff(spec: ProjectSpec, prompt_fn: Callable[[], bool]) -> bool:
    return bool(prompt_fn())
