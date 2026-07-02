import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pm_agent_loop.schema.project_spec import ProjectSpec
from pm_agent_loop.spec_io import read_spec, write_spec

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "example_project_spec.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _spec(spec_version: int) -> ProjectSpec:
    data = _load_fixture()
    data["spec_version"] = spec_version
    return ProjectSpec.model_validate(data)


def test_write_spec_then_overwrite_preserves_prior_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "project_spec.json"

    write_spec(_spec(1), target)
    v1_content = target.read_text(encoding="utf-8")

    write_spec(_spec(2), target)

    backup = tmp_path / "project_spec.v1.json"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == v1_content
    assert read_spec(target).spec_version == 2


def test_write_spec_creates_missing_parent_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "docs" / "project_spec.json"

    write_spec(_spec(1), target)

    assert target.exists()
    assert read_spec(target).spec_version == 1


def test_read_spec_invalid_json_raises_validation_error(tmp_path):
    invalid_path = tmp_path / "invalid_spec.json"
    data = _load_fixture()
    del data["security_and_risk_considerations"]
    invalid_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValidationError):
        read_spec(invalid_path)


def test_write_spec_rejects_path_traversal_outside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    escaping_path = tmp_path / ".." / ".." / "escape" / "project_spec.json"

    with pytest.raises(ValueError, match="Refusing to write outside"):
        write_spec(_spec(1), escaping_path)
