import json
from unittest.mock import MagicMock

from typer.testing import CliRunner

import pm_agent_loop.cli as cli_module
from pm_agent_loop.personas.pm import ChecklistState
from pm_agent_loop.schema.project_spec import ProjectSpec

_CLEAN_ANSWERS = [
    "Users have no easy way to track daily habits and see streaks over time.",
    "Provide a lightweight daily habit tracker with streak visualization.",
    "Individuals who want to build or maintain daily habits.",
    "Adding habits, marking them done each day, and viewing streak counts.",
    "Social features, reminders, and mobile push notifications.",
    "Users can add a habit, mark it complete for today, and view a streak.",
    "Runs locally as a CLI tool; stores data in a local SQLite file.",
    "Marking a habit complete today increments its streak count by one.",
    "Must-have: add habit, mark complete, view streak. Nice: history charts.",
    "Roughly three days of effort; no ongoing hosting cost.",
    "Assumes single-user local usage; no multi-device sync planned.",
    "No sensitive data beyond habit names; single local user, no roles needed.",
    "N/A",
    "Standard dependency scanning via existing repo tooling is sufficient.",
    "Not a cost concern; fully local with no external services.",
    "N/A",
]


def test_run_completes_full_interview_and_produces_valid_spec(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    captured_state = ChecklistState()
    monkeypatch.setattr(cli_module, "ChecklistState", lambda: captured_state)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", MagicMock())

    output_path = tmp_path / "project_spec.json"
    stdin = "\n".join([*_CLEAN_ANSWERS, "y"]) + "\n"

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--idea", "test idea", "--output", str(output_path)],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    assert captured_state.is_ready_to_draft() is True
    written = json.loads(output_path.read_text(encoding="utf-8"))
    ProjectSpec.model_validate(written)


def test_run_override_phrase_stops_interview_and_flags_open_questions(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", MagicMock())

    output_path = tmp_path / "project_spec.json"
    partial_answers = _CLEAN_ANSWERS[:3]
    stdin = "\n".join([*partial_answers, "that's enough", "y"]) + "\n"

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--idea", "test idea", "--output", str(output_path)],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert "functional_requirements" in written["open_questions_for_architect"]


def test_run_uses_llm_client_for_critic_revision(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    revised_text = "Marking a habit complete updates its streak count immediately."
    mock_llm_client = MagicMock()
    mock_llm_client.complete.return_value = revised_text
    mock_llm_client_cls = MagicMock(return_value=mock_llm_client)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", mock_llm_client_cls)

    answers_with_weak_acceptance_criteria = list(_CLEAN_ANSWERS)
    answers_with_weak_acceptance_criteria[7] = "Works."

    output_path = tmp_path / "project_spec.json"
    stdin = (
        "\n".join(
            [
                *answers_with_weak_acceptance_criteria,
                "a clearer description of what verifying it means",
                "y",
            ]
        )
        + "\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--idea", "test idea", "--output", str(output_path)],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    mock_llm_client.complete.assert_called_once()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["acceptance_criteria"] == revised_text
