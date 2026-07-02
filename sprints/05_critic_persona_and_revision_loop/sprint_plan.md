### FILEPATH: /sprints/05_critic_persona_and_revision_loop/sprint_plan.md

**Sprint Goal:** Implement the Critic persona's review checks and the capped PM-Critic revision loop with an explicit human sign-off gate.

**Dependencies:** Sprint 04

**Security Considerations:** The Critic is the sole enforcement point ensuring no spec reaches human sign-off with an empty or skipped security/regulatory/supply-chain/cost field — a defect here means every downstream spec silently bypasses the tool's core DevSecOps guarantee. Mitigation: the Critic's completeness check must explicitly fail (not warn) when `security_and_risk_considerations`, `regulatory_and_compliance_constraints`, or `supply_chain_security_expectations` is an empty string, with a unit test asserting this failure mode independently of the general completeness check.

**Risks & Blockers:** None identified.

**Tasks:**

- **Task 1: Implement Critic review checks**
  - **Description:** Create `src/pm_agent_loop/personas/critic.py` with `review(spec: ProjectSpec) -> list[CriticFinding]` (define `CriticFinding` as a dataclass with `field: str`, `issue: str`) implementing the five checks listed in `draft_and_review_loop.critic_checks` of `docs/project_spec.json`: internal consistency, checklist completeness, testable acceptance criteria, non-empty security/risk field, and non-empty regulatory/supply-chain/cost fields.
  - **Target Files:** `src/pm_agent_loop/personas/critic.py`
  - **Acceptance Criteria:** A unit test constructs a `ProjectSpec` with `security_and_risk_considerations=""` and asserts `review()` returns a `CriticFinding` referencing that field; a second test constructs a fully-populated valid spec and asserts `review()` returns an empty list.

- **Task 2: Implement the PM-Critic revision cycle with a hard cap**
  - **Description:** In a new `src/pm_agent_loop/orchestrator.py`, implement `run_revision_loop(initial_spec: ProjectSpec, pm_followup_fn, max_cycles: int = 4) -> ProjectSpec` that calls `critic.review()`; if findings are non-empty, invokes `pm_followup_fn(findings)` to obtain a revised spec, repeating until `review()` returns no findings or `max_cycles` is reached, at which point it raises a `RevisionCapReached` exception carrying the last spec and remaining findings.
  - **Target Files:** `src/pm_agent_loop/orchestrator.py`
  - **Acceptance Criteria:** A unit test with a `pm_followup_fn` mock that never resolves findings asserts `RevisionCapReached` is raised after exactly 4 calls to `pm_followup_fn`; a second test with a mock resolving findings on the 2nd call asserts the loop returns the resolved spec after 2 calls.

- **Task 3: Implement explicit human sign-off gate**
  - **Description:** In `orchestrator.py`, add `require_signoff(spec: ProjectSpec, prompt_fn) -> bool` that calls `prompt_fn` (a Typer confirmation prompt in production) and returns its boolean result. The caller must not proceed to `spec_io.write_spec` unless this returns `True`.
  - **Target Files:** `src/pm_agent_loop/orchestrator.py`
  - **Acceptance Criteria:** A unit test asserts a spec is never passed to a mocked `write_spec` when `require_signoff`'s `prompt_fn` mock returns `False`.

---
