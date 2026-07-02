import json
from pathlib import Path

from pm_agent_loop.schema.project_spec import ProjectSpec


def _validate_write_target(path: Path) -> Path:
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    if not resolved.is_relative_to(cwd):
        msg = f"Refusing to write outside the current working directory: {resolved}"
        raise ValueError(msg)
    return resolved


def read_spec(path: Path) -> ProjectSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ProjectSpec.model_validate(data)


def write_spec(spec: ProjectSpec, path: Path) -> None:
    resolved = _validate_write_target(Path(path))
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if resolved.exists():
        existing = read_spec(resolved)
        backup_path = resolved.with_name(
            f"{resolved.stem}.v{existing.spec_version}{resolved.suffix}"
        )
        backup_path.write_text(resolved.read_text(encoding="utf-8"), encoding="utf-8")
    resolved.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
