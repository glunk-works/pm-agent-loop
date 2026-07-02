import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pm_agent_loop.llm.client import LLMResponse
from pm_agent_loop.orchestrator import (
    RevisionCapReached,
    TokenTracker,
    require_signoff,
    run_revision_loop,
)
from pm_agent_loop.schema.project_spec import ProjectSpec

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "example_project_spec.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _spec_with_blank_security() -> ProjectSpec:
    data = _load_fixture()
    data["security_and_risk_considerations"] = ""
    return ProjectSpec.model_validate(data)


def _valid_spec() -> ProjectSpec:
    return ProjectSpec.model_validate(_load_fixture())


def test_run_revision_loop_raises_after_max_cycles_when_never_resolved():
    broken_spec = _spec_with_blank_security()
    pm_followup_fn = MagicMock(return_value=broken_spec)

    with pytest.raises(RevisionCapReached) as exc_info:
        run_revision_loop(broken_spec, pm_followup_fn, max_cycles=4)

    assert pm_followup_fn.call_count == 4
    assert exc_info.value.last_spec is broken_spec
    assert exc_info.value.remaining_findings


def test_run_revision_loop_returns_resolved_spec_after_two_calls():
    broken_spec = _spec_with_blank_security()
    resolved_spec = _valid_spec()
    pm_followup_fn = MagicMock(side_effect=[broken_spec, resolved_spec])

    result = run_revision_loop(broken_spec, pm_followup_fn, max_cycles=4)

    assert result is resolved_spec
    assert pm_followup_fn.call_count == 2


def test_run_revision_loop_accumulates_token_usage_via_tracker():
    broken_spec = _spec_with_blank_security()
    resolved_spec = _valid_spec()
    llm_client = MagicMock()
    llm_client.complete.side_effect = [
        LLMResponse(text="a", input_tokens=10, output_tokens=20),
        LLMResponse(text="b", input_tokens=15, output_tokens=25),
        LLMResponse(text="c", input_tokens=5, output_tokens=5),
    ]
    tracker = TokenTracker()
    specs = iter([broken_spec, broken_spec, resolved_spec])

    def pm_followup_fn(findings):
        del findings
        response = llm_client.complete(
            system_prompt="revise", messages=[], model="claude-haiku-4-5"
        )
        tracker.add(response.input_tokens, response.output_tokens)
        return next(specs)

    result = run_revision_loop(broken_spec, pm_followup_fn, max_cycles=4)

    assert result is resolved_spec
    assert tracker.total_input_tokens == 10 + 15 + 5
    assert tracker.total_output_tokens == 20 + 25 + 5


def test_write_spec_skipped_when_signoff_declined():
    prompt_fn = MagicMock(return_value=False)
    write_spec_mock = MagicMock()
    spec = _valid_spec()

    if require_signoff(spec, prompt_fn):
        write_spec_mock(spec, Path("project_spec.json"))

    write_spec_mock.assert_not_called()
