import json
from unittest.mock import MagicMock

from typer.testing import CliRunner

import pm_agent_loop.cli as cli_module
from pm_agent_loop.llm.client import LLMResponse
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
    mock_llm_client.complete.return_value = LLMResponse(
        text=revised_text, input_tokens=42, output_tokens=17
    )
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


def test_run_artifact_path_prefills_answers_with_human_confirmation(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    artifact_path = tmp_path / "requirements.md"
    artifact_path.write_text("# Habit tracker notes\n...", encoding="utf-8")

    extraction_json = json.dumps(
        {
            "problem_statement": _CLEAN_ANSWERS[0],
            "purpose_and_goals": "a rough first draft of the goal",
        }
    )
    mock_llm_client = MagicMock()
    mock_llm_client.complete.return_value = LLMResponse(
        text=extraction_json, input_tokens=10, output_tokens=5
    )
    monkeypatch.setattr(
        cli_module, "AnthropicLLMClient", MagicMock(return_value=mock_llm_client)
    )

    stdin_lines = [
        "",  # accept the extracted problem_statement as-is
        _CLEAN_ANSWERS[1],  # correct the extracted purpose_and_goals
        *_CLEAN_ANSWERS[2:],
        "y",
    ]
    stdin = "\n".join(stdin_lines) + "\n"

    output_path = tmp_path / "project_spec.json"
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--artifact-path", str(artifact_path), "--output", str(output_path)],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["problem_statement"] == _CLEAN_ANSWERS[0]
    assert written["purpose_and_goals"] == _CLEAN_ANSWERS[1]


def test_run_artifact_prefill_correction_reruns_needs_clarification(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    artifact_path = tmp_path / "requirements.md"
    artifact_path.write_text("# Habit tracker notes\n...", encoding="utf-8")

    extraction_json = json.dumps({"problem_statement": "some extracted text"})
    mock_llm_client = MagicMock()
    mock_llm_client.complete.return_value = LLMResponse(
        text=extraction_json, input_tokens=1, output_tokens=1
    )
    monkeypatch.setattr(
        cli_module, "AnthropicLLMClient", MagicMock(return_value=mock_llm_client)
    )

    stdin_lines = [
        "not sure",  # vague correction -> must re-trigger needs_clarification
        _CLEAN_ANSWERS[0],  # clarified answer, accepted this time
        *_CLEAN_ANSWERS[1:],
        "y",
    ]
    stdin = "\n".join(stdin_lines) + "\n"

    output_path = tmp_path / "project_spec.json"
    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--artifact-path", str(artifact_path), "--output", str(output_path)],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["problem_statement"] == _CLEAN_ANSWERS[0]


def test_run_provider_bedrock_uses_bedrock_llm_client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    revised_text = "Marking a habit complete updates its streak count immediately."
    mock_llm_client = MagicMock()
    mock_llm_client.complete.return_value = LLMResponse(
        text=revised_text, input_tokens=42, output_tokens=17
    )
    mock_llm_client_cls = MagicMock(return_value=mock_llm_client)
    monkeypatch.setattr(cli_module, "BedrockLLMClient", mock_llm_client_cls)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", MagicMock())

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
        [
            "run",
            "--idea",
            "test idea",
            "--output",
            str(output_path),
            "--provider",
            "bedrock",
        ],
        input=stdin,
    )

    assert result.exit_code == 0, result.output
    mock_llm_client_cls.assert_called_once()
    mock_llm_client.complete.assert_called_once()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["acceptance_criteria"] == revised_text


def test_run_unknown_provider_rejected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", MagicMock())
    monkeypatch.setattr(cli_module, "BedrockLLMClient", MagicMock())

    output_path = tmp_path / "project_spec.json"

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        [
            "run",
            "--idea",
            "test idea",
            "--output",
            str(output_path),
            "--provider",
            "openai",
        ],
    )

    assert result.exit_code != 0
    assert not output_path.exists()


def test_keyboard_interrupt_mid_interview_leaves_prior_file_unchanged(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_module, "AnthropicLLMClient", MagicMock())

    output_path = tmp_path / "project_spec.json"
    pre_existing_content = '{"marker": "pre-existing"}'
    output_path.write_text(pre_existing_content, encoding="utf-8")

    call_count = {"n": 0}

    def fake_prompt(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise KeyboardInterrupt
        return "some answer"

    monkeypatch.setattr(cli_module.typer, "prompt", fake_prompt)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["run", "--idea", "test idea", "--output", str(output_path)],
    )

    assert result.exit_code != 0
    assert output_path.read_text(encoding="utf-8") == pre_existing_content


def test_unexpected_llm_exception_leaves_no_spec_written(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    mock_llm_client = MagicMock()
    mock_llm_client.complete.side_effect = RuntimeError("network is down")
    monkeypatch.setattr(
        cli_module, "AnthropicLLMClient", MagicMock(return_value=mock_llm_client)
    )

    answers_with_weak_acceptance_criteria = list(_CLEAN_ANSWERS)
    answers_with_weak_acceptance_criteria[7] = "Works."
    output_path = tmp_path / "project_spec.json"
    stdin = (
        "\n".join(
            [
                *answers_with_weak_acceptance_criteria,
                "a clearer description of what verifying it means",
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

    assert result.exit_code != 0
    assert not output_path.exists()
