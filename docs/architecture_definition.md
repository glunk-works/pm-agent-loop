# Architecture Definition Document — pm-agent-loop

Source specification: `docs/project_spec.json` (v6)

## Resolved Architectural Ambiguities

The following ambiguities from `open_questions_for_architect` (and one item raised during this review) were resolved directly with the human before finalizing this document:

| # | Question | Resolution |
|---|----------|------------|
| 1 | Execution/consumption model | Standalone Python CLI/library — no Claude Code harness dependency |
| 2 | LLM provider for running PM/Critic personas | Provider-agnostic/pluggable via an `LLMClient` abstraction |
| 3 | Secrets storage for LLM API key(s) | OS keyring (`keyring` package) — Infisical Cloud + OIDC was proposed, then rejected because it conflicts with the spec's own v1 sizing constraint ("no external services required," `docs/project_spec.json:97`) |
| 4 | Schema/validation mechanism for `project_spec.json` | Pydantic models |
| 5 | How the Critic role is implemented relative to the PM | Separate system prompt/role, invoked as a distinct sequential LLM call through the same `LLMClient` — not self-review |
| 6 | Versioning/file-naming for preserved prior spec versions | `project_spec.v{N}.json` sibling files; unsuffixed `project_spec.json` always holds the latest version |
| 7 | CI security tooling beyond existing ruff bandit (`S`) + Dependabot | Add secret scanning (gitleaks) and SBOM generation |

---

## 1. System Context & Data Flow

`pm-agent-loop` is a locally-executed CLI tool with no server component and no persistent runtime. A single invocation:

1. Reads input: either a raw one-line idea (stdin/arg) or an existing artifact file path (issue, doc, partial spec).
2. The **PM persona** (one system prompt, invoked via `LLMClient`) detects which input case applies and drives a one-question-at-a-time interview with the human over the terminal, filling the required checklist fields from `docs/project_spec.json`.
3. The PM drafts a candidate spec, validated against the Pydantic `ProjectSpec` schema.
4. The **Critic persona** (a distinct system prompt, invoked as a separate sequential `LLMClient` call — not the same call/context as the PM) reviews the draft against its checklist (consistency, completeness, testable acceptance criteria, security/regulatory/supply-chain/cost fields addressed).
5. Critic findings are returned to the PM persona (in-process), which asks the human targeted follow-up questions and re-drafts. This PM↔Critic cycle is capped at 4 rounds; hitting the cap escalates directly to the human.
6. Once the Critic is satisfied, the human gives explicit sign-off.
7. The CLI writes the final spec to the path provided by the invoker, preserving prior versions as `project_spec.v{N}.json` siblings.

Data egress is limited to outbound HTTPS calls to whichever LLM provider is configured. There is no inbound network exposure, no database, and no state retained between invocations (resumability is out of scope for v1 per the spec).

## 2. Technology Stack

- **Language/runtime:** Python 3.x, packaged with the existing `hatch`-based `pyproject.toml` already scaffolded in this repo.
- **CLI framework:** Typer (type-hint driven, integrates cleanly with the Pydantic schema layer).
- **Core package (`pm_agent_loop`):**
  - `personas/pm.py`, `personas/critic.py` — distinct system prompts and turn-handling logic per role.
  - `llm/client.py` — `LLMClient` abstract interface; `llm/adapters/` — one concrete adapter per provider (Anthropic adapter required for v1; OpenAI/others addable without touching persona logic).
  - `schema/project_spec.py` — Pydantic models (`ProjectSpec`, `RevisionHistoryEntry`, etc.) mirroring `required_spec_fields_checklist`.
  - `spec_io.py` — versioned read/write (`project_spec.json` + `project_spec.v{N}.json`).
- **Storage:** local filesystem only. No database, no object storage, no cloud compute for v1.

## 3. IAM & Workload Identity (Strict Least Privilege)

No cloud infrastructure exists for this tool in v1, so there are no cloud IAM roles, policies, or federation strategies to define. The only identity boundary is local:

- The tool runs with the invoking OS user's local privileges — no elevation, no service accounts.
- LLM provider access is authenticated via an API key retrieved from the OS keyring at call time, passed directly into the active `LLMClient` adapter, and never persisted to disk, logged, or written into `project_spec.json`.
- OIDC/federated auth (Infisical or otherwise) was explicitly considered and rejected for v1 as disproportionate to a single-user local tool; revisit only if this becomes a multi-user or CI-invoked service.

## 4. Security & Network Posture

- **Secrets management:** LLM API key(s) stored in the OS-native credential store via the `keyring` package. Never logged, printed, or committed — enforced by code review and the gitleaks CI gate (Section 5).
- **Encryption in transit:** all LLM API calls occur over HTTPS/TLS via the provider SDKs.
- **Encryption at rest:** not required for v1 — `project_spec.json` content is authored by the human for their own local use; no additional at-rest encryption is imposed beyond standard filesystem permissions.
- **Network isolation:** outbound-only. No listening ports, no inbound network surface.
- **Input handling:** interview input comes from local stdin or a local file path supplied by the human — no untrusted network input surface exists.

## 5. Supply Chain Security

- Retain existing ruff + bandit (`S` ruleset) and Dependabot configuration as-is; extend, do not replace.
- Add **gitleaks** as both a pre-commit hook and a CI job — fails the build on detected secret patterns.
- Add **SBOM generation** (CycloneDX, e.g. via `cyclonedx-bom`) as a CI job, producing an SBOM artifact per build/release.
- Artifact signing is out of scope for v1 (the package is not yet published/distributed beyond source); revisit if published to PyPI.

## 6. Regulatory & Compliance Impacts

`pm-agent-loop` itself collects no PII and handles no regulated data — it only processes whatever project-requirements content the human chooses to type or reference locally. All data stays on the local machine except the LLM API calls required to run the personas. No data residency or compliance regime applies to the tool's own operation at v1. (Note: this is distinct from the `regulatory_and_compliance_constraints` field the PM persona gathers *about downstream projects* it interviews on — that's output content, not a constraint on pm-agent-loop itself.)

## 7. FinOps / Cost Considerations

- The only cost driver is LLM token usage during interview, drafting, and Critic review.
- The 4-cycle PM↔Critic revision cap (per spec) bounds worst-case token spend per spec-generation session.
- The provider-agnostic `LLMClient` design allows per-role model overrides in config (e.g. a smaller/cheaper model for the Critic pass, a larger one for PM drafting) — expose as configuration, not a hardcoded model choice.
- No hosted compute cost exists since there is no server component; cost is fully visible to the human as direct, per-invocation API usage rather than a hidden recurring charge.

## 8. IaC Handoff Directives

- Do **not** provision any cloud infrastructure for this project in v1 — none is required.
- Package as a standard Python package using the existing `hatch` configuration in `pyproject.toml`.
- Implement `LLMClient` as an abstract interface with at least one concrete adapter (Anthropic) for v1; design so additional provider adapters can be added without modifying PM/Critic persona logic.
- Implement secrets access via the `keyring` package. The API key must never be logged, printed to stdout/stderr, or written into `project_spec.json` or any versioned sibling file.
- Define `ProjectSpec` and all nested types as Pydantic models in a dedicated schema module; validate on both write and read.
- Implement spec versioning as `project_spec.v{N}.json` sibling files; the unsuffixed `project_spec.json` always reflects the latest version.
- Implement PM and Critic as separate system prompt modules, invoked as sequential, distinct `LLMClient` calls — never a single self-review call.
- Add gitleaks as both a pre-commit hook and a CI job.
- Add CycloneDX SBOM generation as a CI job.
- Do not remove or replace the existing ruff bandit (`S`) configuration or Dependabot config — extend only.
