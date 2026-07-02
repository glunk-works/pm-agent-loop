### FILEPATH: /sprints/04_pm_persona_interview_engine/sprint_plan.md

**Sprint Goal:** Implement the PM persona's input-type detection, checklist state tracking, one-at-a-time interview pacing, and vague-answer follow-up handling.

**Dependencies:** Sprint 02, Sprint 03

**Security Considerations:** The PM persona is the component that gathers `security_and_risk_considerations`, `regulatory_and_compliance_constraints`, and `supply_chain_security_expectations` from the human — if its checklist-tracking logic silently skips these fields, every downstream spec inherits the gap. Mitigation: the checklist state machine treats these three fields as always-required-or-explicit-N/A, identical to every other checklist field, with a unit test asserting the interview cannot reach a "ready to draft" state while any of them is unanswered.

**Risks & Blockers:** None identified.

**Tasks:**

- **Task 1: Implement input-type detection**
  - **Description:** Create `src/pm_agent_loop/personas/pm.py` with `detect_input_type(raw_input: str | None, artifact_path: Path | None) -> Literal["raw_idea", "existing_artifact"]`, returning `"existing_artifact"` when a valid, readable `artifact_path` is supplied and `"raw_idea"` otherwise.
  - **Target Files:** `src/pm_agent_loop/personas/__init__.py`, `src/pm_agent_loop/personas/pm.py`
  - **Acceptance Criteria:** A parametrized unit test covers both branches plus a supplied `artifact_path` that does not exist, asserting the function falls back to `"raw_idea"` in that case.

- **Task 2: Implement checklist state tracking**
  - **Description:** In `personas/pm.py`, add a `ChecklistState` class tracking, for each of the 17 fields in `required_spec_fields_checklist` (`docs/project_spec.json`), whether it is `unanswered`, `answered`, or `marked_na`. Add `is_ready_to_draft() -> bool`, returning `True` only when every field is `answered` or `marked_na`.
  - **Target Files:** `src/pm_agent_loop/personas/pm.py`
  - **Acceptance Criteria:** A unit test asserts `is_ready_to_draft()` returns `False` when `security_and_risk_considerations` is the sole remaining `unanswered` field, and `True` once it is set to `answered` or `marked_na`.

- **Task 3: Implement one-at-a-time interview turn logic with trivial batching**
  - **Description:** In `personas/pm.py`, implement `next_question(state: ChecklistState) -> list[str]`, returning exactly one question string in the common case, and 2-3 question strings only when the next unanswered fields are drawn from a hardcoded `TRIVIAL_BATCH_FIELDS` set (simple yes/no fields agreed not to have interdependent answers). Fields outside that set are always returned one at a time.
  - **Target Files:** `src/pm_agent_loop/personas/pm.py`
  - **Acceptance Criteria:** A unit test asserts `next_question` returns a single-element list when the next unanswered field is `problem_statement`; a second test asserts a multi-element list only when all next unanswered fields are members of `TRIVIAL_BATCH_FIELDS`.

- **Task 4: Implement vague-answer follow-up handling**
  - **Description:** In `personas/pm.py`, implement `needs_clarification(answer: str) -> bool` using a heuristic (empty string, or an answer matching a hardcoded set of uncertainty phrases such as "not sure", "I don't know", "maybe") and `build_clarifying_followup(field_name: str, answer: str) -> str`, returning explanatory context/tradeoff text for that field from a hardcoded per-field `CLARIFICATION_HINTS` dict.
  - **Target Files:** `src/pm_agent_loop/personas/pm.py`
  - **Acceptance Criteria:** A unit test asserts `needs_clarification("I don't know")` returns `True` and `needs_clarification("We store PII and must comply with GDPR")` returns `False`; a second test asserts `build_clarifying_followup` returns non-empty, field-specific text for every field in `CLARIFICATION_HINTS`.

---
