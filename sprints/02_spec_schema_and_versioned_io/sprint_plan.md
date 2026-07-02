### FILEPATH: /sprints/02_spec_schema_and_versioned_io/sprint_plan.md

**Sprint Goal:** Define the `ProjectSpec` Pydantic schema mirroring the full `required_spec_fields_checklist` and implement versioned, validated read/write of `project_spec.json`.

**Dependencies:** Sprint 01

**Security Considerations:** This sprint defines the on-disk artifact the whole tool revolves around. Threat surface: malformed or maliciously-crafted spec files being read back in (the existing-artifact input case), and a schema that silently accepts an empty or missing `security_and_risk_considerations` field, which the Critic depends on later to gate. Mitigations: Pydantic models must mark `security_and_risk_considerations`, `regulatory_and_compliance_constraints`, and `supply_chain_security_expectations` as required (non-optional) fields rather than allowing silent omission; validate on both read and write per the architecture document; guard all file path handling in `spec_io.py` against path traversal when resolving write targets.

**Risks & Blockers:** None identified.

**Tasks:**

- **Task 1: Define ProjectSpec and nested Pydantic models**
  - **Description:** Create `src/pm_agent_loop/schema/project_spec.py` defining Pydantic models mirroring every field in `required_spec_fields_checklist` from `docs/project_spec.json` (`problem_statement`, `purpose_and_goals`, `target_users`, `in_scope`, `out_of_scope`, `functional_requirements`, `integration_context`, `acceptance_criteria`, `priority_ranking`, `timeline_and_cost_estimates`, `risks_and_assumptions`, `security_and_risk_considerations`, `regulatory_and_compliance_constraints`, `supply_chain_security_expectations`, `cost_sensitivity`, `open_questions_for_architect`, `revision_history`), plus a `RevisionHistoryEntry` model (`version`, `trigger`, `change`, `resolved_by`). All checklist fields are required (no default of `None`); the checklist's "explicit N/A" allowance is represented as the literal string `"N/A"`, not a missing field.
  - **Target Files:** `src/pm_agent_loop/schema/__init__.py`, `src/pm_agent_loop/schema/project_spec.py`
  - **Acceptance Criteria:** `ProjectSpec.model_validate()` against the existing `docs/project_spec.json` (loaded as a dict) succeeds without error; a unit test asserts omitting `security_and_risk_considerations` raises `pydantic.ValidationError`.

- **Task 2: Implement versioned spec read/write in spec_io.py**
  - **Description:** Create `src/pm_agent_loop/spec_io.py` with `write_spec(spec: ProjectSpec, path: Path) -> None` and `read_spec(path: Path) -> ProjectSpec`. `write_spec` validates the spec against the Pydantic model before writing; if `path` already exists, it copies the existing file's contents to a sibling `project_spec.v{N}.json` (`N` = the `spec_version` read from the file being replaced) before overwriting `path` with the new spec. `read_spec` validates the loaded JSON against `ProjectSpec` and raises rather than returning a partially-populated object.
  - **Target Files:** `src/pm_agent_loop/spec_io.py`
  - **Acceptance Criteria:** A unit test writes spec v1, then writes spec v2 to the same path, and asserts `project_spec.v1.json` now exists with the original v1 content while `project_spec.json` contains v2; `read_spec` on a hand-crafted invalid JSON file raises `pydantic.ValidationError`.

- **Task 3: Guard spec_io file path handling against path traversal**
  - **Description:** In `spec_io.py`, resolve all input paths via `Path.resolve()` and raise `ValueError` for any write target whose resolved path falls outside the invoking process's current working directory tree, preventing a maliciously-crafted output path argument from writing outside the intended project directory.
  - **Target Files:** `src/pm_agent_loop/spec_io.py`
  - **Acceptance Criteria:** A unit test asserts `write_spec` raises `ValueError` when given a path containing `../../` that resolves outside the test's temp working directory; `hatch run ruff check src/pm_agent_loop/spec_io.py` reports no new `S`-ruleset findings.

---
