### FILEPATH: /sprints/06_cli_orchestration_integration/sprint_plan.md

**Sprint Goal:** Wire the PM persona, Critic persona, orchestrator, and LLMClient into a single Typer CLI entrypoint that runs a full idea-to-signed-off-spec session end to end.

**Dependencies:** Sprint 03, Sprint 04, Sprint 05

**Security Considerations:** This sprint introduces the first end-to-end path that accepts a human-supplied file path (existing-artifact case) and API responses from an external network call — the two points where untrusted input enters the process. Mitigation: the CLI must validate the artifact-path argument is a regular file, not a symlink, before `pm.detect_input_type` reads it (Task 3); all Anthropic API responses must pass through `ProjectSpec` Pydantic validation immediately before ever being written to disk, with no raw LLM output written directly to `project_spec.json` (Task 3).

**Risks & Blockers:** End-to-end behavior depends on all three prior sprints' interfaces remaining stable; any interface drift discovered during integration (in `LLMClient.complete()`, `ChecklistState`, or `run_revision_loop`) must be resolved by updating the earlier sprint's code, not by adding adapter shims in the CLI.

**Tasks:**

- **Task 1: Implement the Typer CLI entrypoint**
  - **Description:** Create `src/pm_agent_loop/cli.py` (extending the `configure-key` command from Sprint 03) with a `run` command accepting `--idea TEXT`, `--artifact-path PATH`, and `--output PATH` (default `./docs/project_spec.json`), wiring `pm.detect_input_type` → interview loop → `orchestrator.run_revision_loop` → `orchestrator.require_signoff` → `spec_io.write_spec` in sequence.
  - **Target Files:** `src/pm_agent_loop/cli.py`, `src/pm_agent_loop/__init__.py` (expose `app` for the console script), `pyproject.toml` (add `[project.scripts]` entry)
  - **Acceptance Criteria:** `hatch run pm-agent-loop run --idea "test idea" --output <tmp>` completes end to end against a mocked `LLMClient` in a CLI integration test and produces a valid `project_spec.json` at the output path.

- **Task 2: Wire the interview loop to prompt via Typer**
  - **Description:** In `cli.py`, implement the interactive loop calling `pm.next_question`, prompting via `typer.prompt` for each returned question, recording answers into `ChecklistState`, calling `pm.needs_clarification` on each answer and re-prompting with `pm.build_clarifying_followup` when it returns `True`, stopping when `ChecklistState.is_ready_to_draft()` is `True` or the human types the documented override phrase ("that's enough" / "generate the spec").
  - **Target Files:** `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** A CLI integration test using `typer.testing.CliRunner` with scripted stdin drives a full interview to completion and asserts the resulting `ChecklistState.is_ready_to_draft()` is `True`; a second test asserts typing the override phrase mid-interview stops the loop and records the remaining unanswered fields in the drafted spec's `open_questions_for_architect`.

- **Task 3: Validate artifact-path input and sanitize LLM output before persistence**
  - **Description:** In `cli.py`, before passing `--artifact-path` to `pm.detect_input_type`, call `path.is_file()` and reject (raise `typer.BadParameter`) any path that is a symlink (`path.is_symlink()`), preventing symlink-following reads outside the intended directory. After the Critic loop completes, pass the resulting spec through `ProjectSpec.model_validate()` one final time immediately before calling `spec_io.write_spec`, so no unvalidated LLM output can reach disk.
  - **Target Files:** `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** A unit test asserts `typer.BadParameter` is raised when `--artifact-path` points to a symlink; a second test asserts `write_spec` is never called if the final `model_validate()` call raises.

---
