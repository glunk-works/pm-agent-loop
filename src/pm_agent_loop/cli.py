from pathlib import Path
from typing import Callable

import keyring
import typer

from pm_agent_loop.llm.adapters.anthropic import AnthropicLLMClient
from pm_agent_loop.llm.client import LLMClient
from pm_agent_loop.orchestrator import (
    RevisionCapReached,
    require_signoff,
    run_revision_loop,
)
from pm_agent_loop.personas import pm
from pm_agent_loop.personas.critic import CriticFinding
from pm_agent_loop.personas.pm import ChecklistState, FieldStatus
from pm_agent_loop.schema.project_spec import ProjectSpec, RevisionHistoryEntry
from pm_agent_loop.spec_io import write_spec

app = typer.Typer()

_SERVICE_NAME = "pm-agent-loop"
_KEY_USERNAME = "anthropic-api-key"
_OVERRIDE_PHRASES = {"that's enough", "generate the spec"}
_DRAFT_MODEL = "claude-haiku-4-5"


@app.callback()
def main() -> None:
    pass


@app.command()
def configure_key() -> None:
    api_key = typer.prompt("Anthropic API key", hide_input=True)
    keyring.set_password(_SERVICE_NAME, _KEY_USERNAME, api_key)
    typer.echo("Anthropic API key stored successfully.")


def _is_override(text: str) -> bool:
    return text.strip().lower() in _OVERRIDE_PHRASES


def _handle_override(state: ChecklistState) -> None:
    remaining = [
        field
        for field in state.unanswered_fields()
        if field != "open_questions_for_architect"
    ]
    if remaining:
        note = "Interview ended early by human request; not addressed: " + ", ".join(
            remaining
        )
    else:
        note = "Interview ended early by human request; all other fields addressed."

    if state.get_status("open_questions_for_architect") is FieldStatus.UNANSWERED:
        existing = state.get_answer("open_questions_for_architect")
        combined = f"{existing} {note}".strip() if existing else note
        state.record_answer("open_questions_for_architect", combined)

    for field_name in remaining:
        state.record_answer(field_name, "N/A")


def _run_interview(state: ChecklistState) -> None:
    while not state.is_ready_to_draft():
        questions = pm.next_question(state)
        if not questions:
            break
        fields = state.unanswered_fields()[: len(questions)]
        for field_name, question in zip(fields, questions, strict=True):
            answer = typer.prompt(question)
            if _is_override(answer):
                _handle_override(state)
                return
            while pm.needs_clarification(answer):
                followup = pm.build_clarifying_followup(field_name, answer)
                answer = typer.prompt(followup)
                if _is_override(answer):
                    _handle_override(state)
                    return
            state.record_answer(field_name, answer)


def _build_initial_spec(state: ChecklistState, spec_version: int = 1) -> ProjectSpec:
    data: dict = dict(state.answers())
    data["revision_history"] = []
    data["spec_version"] = spec_version
    return ProjectSpec.model_validate(data)


def _make_pm_followup_fn(
    state: ChecklistState, llm_client_factory: Callable[[], LLMClient]
) -> Callable[[list[CriticFinding]], ProjectSpec]:
    history: list[RevisionHistoryEntry] = []
    version = {"n": 1}
    client_holder: dict[str, LLMClient] = {}

    def _pm_followup(findings: list[CriticFinding]) -> ProjectSpec:
        if "client" not in client_holder:
            client_holder["client"] = llm_client_factory()
        llm_client = client_holder["client"]

        for finding in findings:
            typer.echo(f"The critic flagged '{finding.field}': {finding.issue}")
            clarification = typer.prompt(
                pm.build_clarifying_followup(finding.field, "")
            )
            revised_text = llm_client.complete(
                system_prompt=(
                    "You are the PM persona. Rewrite the given project spec "
                    "field so it resolves the critic's finding, using the "
                    "human's clarification. Return only the corrected field "
                    "text, with no additional commentary."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Field: {finding.field}\n"
                            f"Critic finding: {finding.issue}\n"
                            f"Human clarification: {clarification}"
                        ),
                    }
                ],
                model=_DRAFT_MODEL,
            )
            state.record_answer(finding.field, revised_text)

        version["n"] += 1
        history.extend(
            RevisionHistoryEntry(
                version=version["n"],
                trigger=finding.issue,
                change=f"Revised {finding.field} based on human clarification.",
                resolved_by="PM persona re-draft, pending human sign-off",
            )
            for finding in findings
        )

        data: dict = dict(state.answers())
        data["spec_version"] = version["n"]
        data["revision_history"] = list(history)
        return ProjectSpec.model_validate(data)

    return _pm_followup


def _validate_artifact_path(artifact_path: Path | None) -> Path | None:
    if artifact_path is not None and artifact_path.is_symlink():
        raise typer.BadParameter(
            "artifact-path must not be a symlink.", param_hint="--artifact-path"
        )
    return artifact_path


def _validate_and_persist(spec: ProjectSpec, output: Path) -> None:
    validated_spec = ProjectSpec.model_validate(spec.model_dump())
    write_spec(validated_spec, output)


@app.command()
def run(
    idea: str | None = typer.Option(None, "--idea"),
    artifact_path: Path | None = typer.Option(None, "--artifact-path"),
    output: Path = typer.Option(Path("./docs/project_spec.json"), "--output"),
) -> None:
    artifact_path = _validate_artifact_path(artifact_path)
    input_type = pm.detect_input_type(idea, artifact_path)
    typer.echo(f"Detected input type: {input_type}")

    state = ChecklistState()
    _run_interview(state)

    initial_spec = _build_initial_spec(state)
    pm_followup_fn = _make_pm_followup_fn(state, AnthropicLLMClient)

    try:
        final_spec = run_revision_loop(initial_spec, pm_followup_fn)
    except RevisionCapReached as exc:
        typer.echo("Revision cap reached; escalating to you directly.")
        final_spec = exc.last_spec

    if not require_signoff(final_spec, lambda: typer.confirm("Sign off on this spec?")):
        typer.echo("Sign-off declined; spec not written.")
        raise typer.Exit(code=1)

    _validate_and_persist(final_spec, output)
    typer.echo(f"Spec written to {output}")


if __name__ == "__main__":
    app()
