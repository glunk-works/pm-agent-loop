### FILEPATH: /sprints/01_ci_cd_security_foundation/sprint_plan.md

**Sprint Goal:** Extend the repository's existing CI/CD pipeline and pre-commit tooling with secret scanning and SBOM generation so every subsequent sprint's code lands under enforced security gates.

**Dependencies:** None

**Security Considerations:** This sprint touches the CI/CD pipeline and pre-commit tooling directly — the primary threat surface is a compromised or misconfigured pipeline that lets secrets leak into commits/logs or unscanned vulnerable dependencies merge to `main`. Mitigations: add gitleaks as a blocking gate at both the pre-commit and CI layers so secret patterns never reach a remote branch; add CycloneDX SBOM generation to make dependency provenance auditable; verify the existing ruff bandit (`S`) ruleset and Dependabot config remain enabled and are not weakened by any new tooling added in this sprint.

**Risks & Blockers:** gitleaks and pre-commit are new dependencies not yet present in this repo. The gitleaks GitHub Action must be confirmed public-repo-compatible (no license requirement) before use.

**Tasks:**

- **Task 1: Add pre-commit framework with gitleaks hook**
  - **Description:** Add a `.pre-commit-config.yaml` at repo root configuring the `pre-commit` framework with the `gitleaks` hook set to scan staged changes on every commit. Add `pre-commit` to the `default` hatch environment's dependencies in `pyproject.toml`.
  - **Target Files:** `.pre-commit-config.yaml`, `pyproject.toml`
  - **Acceptance Criteria:** Running `pre-commit run --all-files` locally executes the gitleaks hook and exits 0 on the current clean repo state; `hatch run pre-commit --version` succeeds.

- **Task 2: Add gitleaks CI job**
  - **Description:** Add a new job `secret-scan` to `.github/workflows/ci.yml` that runs `gitleaks/gitleaks-action@v2` against the full repository history on every `push` and `pull_request` targeting `main`, failing the workflow on any detected finding.
  - **Target Files:** `.github/workflows/ci.yml`
  - **Acceptance Criteria:** The `secret-scan` job appears in the CI workflow and runs on both `push` and `pull_request` triggers; the workflow fails when a test secret pattern is intentionally committed to a scratch branch, and passes when none is present.

- **Task 3: Add CycloneDX SBOM generation CI job**
  - **Description:** Add a new job `sbom` to `.github/workflows/ci.yml` that installs `cyclonedx-bom` inside the hatch default environment and runs it to produce a CycloneDX-format SBOM (`sbom.json`) from the project's resolved dependencies, uploading it as a build artifact via `actions/upload-artifact@v4`.
  - **Target Files:** `.github/workflows/ci.yml`, `pyproject.toml` (add `cyclonedx-bom` to the `default` env's dependencies)
  - **Acceptance Criteria:** The `sbom` job produces and uploads a valid `sbom.json` artifact conforming to the CycloneDX schema on every CI run; the artifact is downloadable from the workflow run summary.

- **Task 4: Add a hatch `test` script alias and align CI**
  - **Description:** Add `test = "pytest {args}"` under `[tool.hatch.envs.default.scripts]` in `pyproject.toml`, and update the existing "Run Test Suite" step in `.github/workflows/ci.yml` to invoke `hatch run test` instead of `hatch run pytest`, matching the existing `lint`/`format` script alias pattern.
  - **Target Files:** `pyproject.toml`, `.github/workflows/ci.yml`
  - **Acceptance Criteria:** `hatch run test` executes the test suite locally with the same result as `hatch run pytest`; CI is green on a no-op PR.

---
