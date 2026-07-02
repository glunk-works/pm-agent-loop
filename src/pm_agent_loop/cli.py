from pathlib import Path
from typing import Callable

import keyring
import typer

from pm_agent_loop.llm.adapters.anthropic import AnthropicLLMClient
from pm_agent_loop.llm.adapters.bedrock import BedrockLLMClient
from pm_agent_loop.llm.client import LLMClient
from pm_agent_loop.logging_config import configure_logging
from pm_agent_loop.orchestrator import (
    RevisionCapReached,
    TokenTracker,
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

_logger = configure_logging()


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
    state: ChecklistState,
    llm_client_factory: Callable[[], LLMClient],
    token_tracker: TokenTracker,
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
            response = llm_client.complete(
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
            token_tracker.add(response.input_tokens, response.output_tokens)
            state.record_answer(finding.field, response.text)

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


def _prefill_from_artifact(
    state: ChecklistState,
    artifact_path: Path,
    llm_client_factory: Callable[[], LLMClient],
    token_tracker: TokenTracker,
) -> None:
    artifact_content = artifact_path.read_text(encoding="utf-8")
    llm_client = llm_client_factory()
    response = llm_client.complete(
        system_prompt=pm.build_extraction_system_prompt(state.unanswered_fields()),
        messages=[
            {"role": "user", "content": pm.wrap_untrusted_artifact(artifact_content)}
        ],
        model=_DRAFT_MODEL,
    )
    token_tracker.add(response.input_tokens, response.output_tokens)
    candidates = pm.parse_extraction_response(response.text, state.unanswered_fields())

    for field_name, extracted_value in candidates.items():
        typer.echo(f"From your artifact, {field_name.replace('_', ' ')}:")
        typer.echo(f'  "{extracted_value}"')
        correction = typer.prompt(
            "Press Enter to accept, or type a correction",
            default="",
            show_default=False,
        )
        if correction.strip() == "":
            state.record_answer(field_name, extracted_value)
            continue

        answer = correction
        while pm.needs_clarification(answer):
            followup = pm.build_clarifying_followup(field_name, answer)
            answer = typer.prompt(followup)
        state.record_answer(field_name, answer)


def _validate_artifact_path(artifact_path: Path | None) -> Path | None:
    if artifact_path is not None and artifact_path.is_symlink():
        raise typer.BadParameter(
            "artifact-path must not be a symlink.", param_hint="--artifact-path"
        )
    return artifact_path


def _resolve_llm_client_cls(provider: str) -> type[LLMClient]:
    providers: dict[str, type[LLMClient]] = {
        "anthropic": AnthropicLLMClient,
        "bedrock": BedrockLLMClient,
    }
    try:
        return providers[provider]
    except KeyError:
        valid = ", ".join(sorted(providers))
        msg = f"Unknown provider '{provider}'. Valid options: {valid}."
        raise typer.BadParameter(msg, param_hint="--provider") from None


def _validate_and_persist(spec: ProjectSpec, output: Path) -> None:
    validated_spec = ProjectSpec.model_validate(spec.model_dump())
    write_spec(validated_spec, output)


@app.command()
def run(
    idea: str | None = typer.Option(None, "--idea"),
    artifact_path: Path | None = typer.Option(None, "--artifact-path"),
    output: Path = typer.Option(Path("./docs/project_spec.json"), "--output"),
    provider: str = typer.Option(
        "anthropic",
        "--provider",
        help="LLM provider to use: 'anthropic' (direct API, keyring-backed key) "
        "or 'bedrock' (AWS Bedrock, AWS credential chain).",
    ),
) -> None:
    artifact_path = _validate_artifact_path(artifact_path)
    llm_client_cls = _resolve_llm_client_cls(provider)
    input_type = pm.detect_input_type(idea, artifact_path)
    typer.echo(f"Detected input type: {input_type}")

    state = ChecklistState()
    token_tracker = TokenTracker()
    pm_followup_fn = _make_pm_followup_fn(state, llm_client_cls, token_tracker)

    try:
        if input_type == "existing_artifact" and artifact_path is not None:
            _prefill_from_artifact(state, artifact_path, llm_client_cls, token_tracker)
        _run_interview(state)
        initial_spec = _build_initial_spec(state)
        final_spec = run_revision_loop(initial_spec, pm_followup_fn)
    except RevisionCapReached as exc:
        typer.echo("Revision cap reached; escalating to you directly.")
        final_spec = exc.last_spec
    except KeyboardInterrupt:
        typer.echo("\nInterrupted. No spec was written; rerun to start over.")
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(f"Unexpected error during the session: {exc}. No spec was written.")
        raise typer.Exit(code=1) from exc

    if not require_signoff(final_spec, lambda: typer.confirm("Sign off on this spec?")):
        typer.echo("Sign-off declined; spec not written.")
        raise typer.Exit(code=1)

    _validate_and_persist(final_spec, output)
    _logger.info(
        "Session token usage: input=%d output=%d",
        token_tracker.total_input_tokens,
        token_tracker.total_output_tokens,
    )
    typer.echo(f"Spec written to {output}")


if __name__ == "__main__":
    app()
