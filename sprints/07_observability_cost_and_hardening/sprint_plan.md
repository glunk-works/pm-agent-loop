### FILEPATH: /sprints/07_observability_cost_and_hardening/sprint_plan.md

**Sprint Goal:** Add secret-redacting structured logging, per-session token/cost visibility, and interrupted-session failure hardening to the end-to-end CLI path, plus end-user usage documentation.

**Dependencies:** Sprint 06

**Security Considerations:** Structured logging introduced in this sprint is the highest-risk addition for accidental secret disclosure, since it now touches every LLM call and CLI turn. Mitigation: the logging formatter must never log full LLM request/response payloads by default (only token counts and truncated field names), and a unit test must assert that a log call containing a realistic API-key-shaped string is redacted before being emitted.

**Risks & Blockers:** None identified.

**Tasks:**

- **Task 1: Add structured per-turn logging with secret redaction**
  - **Description:** Add `src/pm_agent_loop/logging_config.py` configuring Python's `logging` module with a custom `Formatter` subclass that applies a regex-based redaction pass (matching common API key shapes, e.g. `sk-ant-...`), replacing any match with `[REDACTED]` before the record is emitted; wire this formatter into the CLI entrypoint's logging setup in `cli.py`.
  - **Target Files:** `src/pm_agent_loop/logging_config.py`, `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** A unit test emits a log record containing a synthetic string matching the redaction regex and asserts captured log output contains `[REDACTED]` and not the original substring.

- **Task 2: Add per-call token/cost visibility**
  - **Description:** In `llm/client.py`, extend `LLMClient.complete()`'s return contract to expose the provider's reported input/output token counts (via an `LLMResponse` dataclass wrapping `text`, `input_tokens`, `output_tokens`), and in `orchestrator.py` accumulate a running total across a single `run_revision_loop` invocation, logging a per-session token summary via the Task 1 logger at the end of the CLI `run` command.
  - **Target Files:** `src/pm_agent_loop/llm/client.py`, `src/pm_agent_loop/llm/adapters/anthropic.py`, `src/pm_agent_loop/orchestrator.py`, `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** A unit test drives `run_revision_loop` with a mocked `LLMClient` returning fixed token counts across 3 simulated cycles and asserts the accumulated total equals the sum of the 3 mocked responses.

- **Task 3: Harden interrupted-session failure handling**
  - **Description:** Wrap the CLI `run` command's interview and revision-loop calls in a handler for `KeyboardInterrupt` and unexpected `LLMClient` exceptions that prints a clear message stating no partial spec was written (per `resumability.required_for_v1: false`) and exits with a non-zero status code, rather than leaving a partially-written or corrupt `project_spec.json` on disk.
  - **Target Files:** `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** A unit test simulates a `KeyboardInterrupt` raised mid-interview and asserts the output path has no file written (or, if a file existed prior to the run, its contents are byte-for-byte unchanged) and the process exit code is non-zero.

- **Task 4: Write end-user usage documentation**
  - **Description:** Update `README.md` with installation instructions (`pip install .` / `hatch build`), the `pm-agent-loop configure-key` setup step, and example invocations of `pm-agent-loop run --idea "..."` and `pm-agent-loop run --artifact-path ...`, plus a short section documenting that the API key is never logged or written to the spec output.
  - **Target Files:** `README.md`
  - **Acceptance Criteria:** README contains a runnable command block for both the raw-idea and existing-artifact invocation paths and an explicit statement of the no-secrets-persisted guarantee.

---
