### FILEPATH: /sprints/03_llm_client_and_secrets/sprint_plan.md

**Sprint Goal:** Implement the provider-agnostic `LLMClient` abstraction with a concrete Anthropic adapter, authenticated exclusively through OS-keyring-backed secret retrieval.

**Dependencies:** Sprint 02

**Security Considerations:** This sprint introduces the tool's only outbound network surface and its only handling of a credential (the LLM provider API key). Threat surface: the API key leaking via logs, stdout/stderr, or exception messages, or being written into `project_spec.json`. Mitigations: retrieve the key exclusively through the `keyring` package at call time; never assign it to a variable that is logged or embedded in an exception message; scrub the adapter's exception paths so no raised error can contain the key value; add a unit test asserting no captured log/stdout output ever contains the raw key.

**Risks & Blockers:** `keyring` backend availability varies by OS (e.g., headless Linux CI runners lack a default backend) — tests exercising keyring calls must mock the backend rather than depend on a system credential store being present in CI.

**Tasks:**

- **Task 1: Define the LLMClient abstract interface**
  - **Description:** Create `src/pm_agent_loop/llm/client.py` defining an abstract base class `LLMClient` (via `abc.ABC`) with an abstract method `complete(self, system_prompt: str, messages: list[dict], model: str) -> str`. Define an `LLMConfig` Pydantic model holding `provider: str`, `pm_model: str`, `critic_model: str` for per-role model overrides.
  - **Target Files:** `src/pm_agent_loop/llm/__init__.py`, `src/pm_agent_loop/llm/client.py`
  - **Acceptance Criteria:** Instantiating `LLMClient` directly raises `TypeError`; a unit test confirms `LLMConfig` accepts distinct `pm_model` and `critic_model` values.

- **Task 2: Implement the Anthropic adapter with keyring-backed secrets**
  - **Description:** Create `src/pm_agent_loop/llm/adapters/anthropic.py` implementing `AnthropicLLMClient(LLMClient)`. Its constructor retrieves the API key via `keyring.get_password("pm-agent-loop", "anthropic-api-key")`, raising `RuntimeError` (with no key value embedded in the message) if not found, and passes the key directly into the `anthropic` SDK client constructor. The key is never assigned to a logged variable or included in any raised exception text.
  - **Target Files:** `src/pm_agent_loop/llm/adapters/__init__.py`, `src/pm_agent_loop/llm/adapters/anthropic.py`, `pyproject.toml` (add `anthropic` and `keyring` to `dependencies`)
  - **Acceptance Criteria:** A unit test mocks `keyring.get_password` to return a dummy key, calls `complete()` against a mocked Anthropic SDK response, and asserts the returned text matches the mock; a second test asserts `RuntimeError` is raised when `keyring.get_password` returns `None`, and captured stdout/stderr/log output from that test contains no dummy-key substring.

- **Task 3: Add a CLI-invoked keyring setup helper**
  - **Description:** Add a `configure-key` Typer command (stubbed in `src/pm_agent_loop/cli.py`, pending full CLI wiring in Sprint 06) that prompts for the Anthropic API key via `typer.prompt(..., hide_input=True)` and stores it with `keyring.set_password("pm-agent-loop", "anthropic-api-key", value)`, printing only a success confirmation (never the key itself).
  - **Target Files:** `src/pm_agent_loop/cli.py`
  - **Acceptance Criteria:** Running the command with a mocked `typer.prompt` return value results in `keyring.get_password("pm-agent-loop", "anthropic-api-key")` returning the same value; the command's captured stdout contains no substring of the entered key.

---
