# ADR 0003 — Least privilege and runner hardening

- Status: Accepted
- Date: 2026-10-13

## Context

Reusable workflows execute with the caller's `GITHUB_TOKEN`. Any excess permission, persisted
credential or injection point is multiplied by the number of consumers.

## Decision

### Permissions

- Every workflow declares `permissions: {}` at the top level; each job widens only what it uses:

  | Workflow / job | Permissions |
  | --- | --- |
  | `java-gradle`, `java-maven`, `node`, `workflow-lint` | `contents: read` |
  | `security` / dependency-review | `contents: read` |
  | `security` / codeql | `contents: read`, `actions: read`, `security-events: write` |
  | `release` / release-please | `contents: write`, `issues: write` (autorelease labels), `pull-requests: write` |
  | `release` / provenance | `contents: write` (release assets), `id-token: write`, `attestations: write` |

- Callers must grant at least these permissions on the calling job. GitHub validates the
  permissions of **every** job in a called workflow against the caller's ceiling when the run
  starts, even jobs that will be skipped by `if:`; that is why callers of `security.yml` and
  `release.yml` grant the CodeQL / provenance permissions even when those jobs are disabled.
- `issues: write` is added to release-please beyond the minimum stated in the original brief
  because release-please manages its `autorelease: pending/tagged` labels through the Issues API
  (as documented in the action's README).

### Credentials

- `actions/checkout` always uses `persist-credentials: false`; no job pushes with git.
  release-please and `gh release upload` use the API with an explicit token.
- No `secrets: inherit` anywhere (including docs). Secrets are declared in `workflow_call.secrets`
  (`release.yml` → optional `release-token`).
- No `pull_request_target`, no `workflow_run` triggers.

### Injection

- No `${{ inputs.* }}` / `${{ github.* }}` inside `run:` scripts: values go through `env:` and are
  quoted. Command-like inputs (`gradle-args`, `maven-args`, `pre-build-command`, `install-command`,
  `run-command`, `codeql-build-command`) are, by design, executed as code; they come from the
  caller's own workflow file, which is trusted at the same level as the caller's build scripts.
  Never feed them from event data (PR titles, branch names, comments).
- Args inputs are word-split with `set -f` (no globbing) instead of `eval`.
- Multiline `$GITHUB_OUTPUT` values use a random delimiter.

### Runner hardening

- `timeout-minutes` on every job (configurable through inputs).
- `step-security/harden-runner` is the first step of every job with `egress-policy: audit`: it
  records outbound connections, file and process events in the StepSecurity insights page
  without blocking anything. Once the endpoint list of a consumer is stable, it can switch to
  `egress-policy: block` with `allowed-endpoints:` (would be a new opt-in input → minor release).
  GitHub's [2026 Actions security roadmap](https://github.blog/security/supply-chain-security/whats-coming-to-our-github-actions-2026-security-roadmap/)
  announces a native egress firewall for hosted runners; when it ships it may replace
  harden-runner (removing it is internal, no consumer change).
- `gradle/actions/setup-gradle` validates the Gradle wrapper JAR checksum (`validate-wrappers`)
  and uses the open-source `basic` cache provider by default (`enhanced` is a commercial component
  whose terms must be accepted; available as opt-in through `gradle-cache-provider`).

### Linting the workflows themselves

`workflow-lint.yml` runs actionlint (with shellcheck, preinstalled on ubuntu runners) and zizmor
(regular persona, `min-severity: low`, online audits) on the caller's `.github/`. This repository
runs it on itself in `ci.yml`.

## Accepted findings

| Tool | Finding | Where | Why accepted |
| --- | --- | --- | --- |
| zizmor | `self-repository` (low) — use `$/...` instead of `./...` | `ci.yml`, `release-please.yml`, `java-gradle.yml`, `java-maven.yml`, `node.yml`, `security.yml` | The `$/` syntax (2026-07) is not supported by actionlint v1.7.12 and its semantics inside a cross-repository reusable workflow are undocumented. `./` here is either a same-commit call of this repo's own workflows, or a checkout pinned to `job.workflow_sha` (ADR 0001). Ignored in `.github/zizmor.yml`; revisit with the next actionlint release. |
| actionlint | `property "workflow_repository"/"workflow_sha" is not defined` | reusable workflows | Documented `job` context properties unknown to actionlint v1.7.12. Ignored in `.github/actionlint.yaml`. |

No medium or high zizmor findings exist (also with `--persona pedantic`).

## Consequences

- Consumers must add a `permissions:` block on every calling job (documented in `docs/usage.md`).
- Some consumers will notice harden-runner telemetry in their run logs; it can be audited at
  app.stepsecurity.io for public repositories.
