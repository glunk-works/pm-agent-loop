import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from pm_agent_loop.cli import _validate_and_persist, _validate_artifact_path
from pm_agent_loop.schema.project_spec import ProjectSpec

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "example_project_spec.json"


def _valid_spec() -> ProjectSpec:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return ProjectSpec.model_validate(data)


def test_validate_artifact_path_rejects_symlink(tmp_path, monkeypatch):
    fake_link = tmp_path / "link.txt"
    fake_link.write_text("content", encoding="utf-8")
    monkeypatch.setattr(Path, "is_symlink", lambda self: True)

    with pytest.raises(typer.BadParameter):
        _validate_artifact_path(fake_link)


def test_write_spec_skipped_when_final_validation_raises(tmp_path):
    spec = _valid_spec()

    with (
        patch(
            "pm_agent_loop.cli.ProjectSpec.model_validate",
            side_effect=ValueError("boom"),
        ),
        patch("pm_agent_loop.cli.write_spec") as mock_write_spec,
        pytest.raises(ValueError, match="boom"),
    ):
        _validate_and_persist(spec, tmp_path / "project_spec.json")

    mock_write_spec.assert_not_called()
