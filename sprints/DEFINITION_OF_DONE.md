# GLOBAL DEFINITION OF DONE

Derived from `docs/architecture_definition.md` and `docs/project_spec.json` (v6). Every sprint must satisfy all of the following before it is marked complete, in addition to each sprint's own task-level Acceptance Criteria.

- All automated tests pass via `hatch run test` (or `hatch run pytest`), including any tests added in the sprint, with no skipped tests hiding a failure.
- `hatch run ruff check .` reports zero violations, including the `S` (flake8-bandit) and `B` (flake8-bugbear) rule sets already configured in `pyproject.toml` — no `# noqa` suppression added without a one-line justification comment.
- `hatch run ruff format --check .` reports no formatting diffs.
- `gitleaks` (pre-commit hook and CI job, added in Sprint 01) reports zero findings on the sprint's changes.
- Dependabot has no open, unaddressed vulnerability alert introduced by a dependency the sprint added; any new dependency is pinned to a version with no known critical/high CVE at merge time.
- The CycloneDX SBOM CI job (added in Sprint 01) completes successfully and `sbom.json` reflects any dependency changes made in the sprint.
- No API key, token, or credential value appears in source code, test fixtures, log output, exception messages, or `project_spec.json` / `project_spec.v{N}.json` — verified by both gitleaks and the log-redaction unit tests introduced in Sprint 07.
- The GitHub Actions CI workflow (`.github/workflows/ci.yml`) is green on the sprint's branch/PR before merge.
- Every new or modified Pydantic-validated I/O path (`spec_io.py` read/write, CLI artifact-path input) has at least one unit test proving invalid input is rejected rather than silently accepted.
- Every sprint's mandatory security task (see that sprint's `Security Considerations`) is implemented and covered by its own unit test, not merely described.
