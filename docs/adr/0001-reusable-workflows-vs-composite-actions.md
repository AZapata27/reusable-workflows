# ADR 0001 — Reusable workflows vs composite actions

- Status: Accepted
- Date: 2026-10-13

## Context

Six or more personal repositories (Java/Gradle, Java/Maven, Node/Nx) each carry a hand-written
`ci.yml` that differs only in versions, working directories and commands. Action versions drift
(most still use `actions/checkout@v4` by tag), none set `timeout-minutes` consistently, and
hardening (harden-runner, `persist-credentials: false`, linting of the workflows themselves)
would have to be repeated in every repository.

GitHub offers two reuse mechanisms:

| | Reusable workflow (`on: workflow_call`) | Composite action (`runs: using: composite`) |
| --- | --- | --- |
| Granularity | One or more **jobs** | A sequence of **steps** inside a job |
| Runner choice, `timeout-minutes`, `strategy` | Yes (per job) | No (inherits the caller's job) |
| Job-level `permissions:` | Yes, and the caller can only narrow them | No |
| Secrets | Explicit `secrets:` contract | Only via inputs/env |
| Outputs | Job outputs → workflow outputs | Step outputs |
| Shows in the UI | As separate jobs | Folded into the caller's step |
| Nesting limit | 10 levels, 50 called workflows per run | — |

## Decision

1. **Reusable workflows** for anything that is a whole pipeline or needs its own permissions:
   `java-gradle.yml`, `java-maven.yml`, `node.yml`, `workflow-lint.yml`, `security.yml`,
   `release.yml`. Each defines the job's runner, timeout and minimal `permissions:`.
2. **Composite actions** for step sequences shared *between* those workflows and usable on their
   own in a consumer's custom job: `actions/setup-jvm` (JDK + Gradle/Maven cache) and
   `actions/test-reports` (JUnit summary + artifact).
3. Matrices stay in the **caller** (`strategy.matrix` + `uses:` on the job). A reusable workflow
   receives one cell per call, which keeps inputs scalar and makes each matrix cell a visible job.

### How a reusable workflow loads this repo's composite actions

Inside a called workflow, `uses: ./actions/...` resolves against the *caller's* workspace, so it
cannot point at this repository. Referencing `AZapata27/reusable-workflows/actions/x@<ref>` would
require hard-coding a ref that drifts from the workflow's own version. Instead each workflow:

1. checks out the caller repository (`persist-credentials: false`);
2. checks out `${{ job.workflow_repository }}` at `${{ job.workflow_sha }}` — the exact commit of
   the reusable workflow being executed — into `.reusable-workflows/` (sparse: `actions/` only,
   added to `.git/info/exclude`);
3. uses `./.reusable-workflows/actions/<name>`.

So a consumer pinned to `@<sha>` always runs workflows **and** actions from that same commit.
`node.yml` performs step 2 only *after* the user command, so tools that scan the tree (Nx, ESLint)
never see the extra directory.

`job.workflow_repository` / `job.workflow_sha` are documented in the
[`job` context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#job-context)
(not available on GHES). actionlint v1.7.12 does not know them yet, so they are ignored in
`.github/actionlint.yaml`.

## Alternatives considered

- **Everything as composite actions**: consumers would still copy job boilerplate (runner,
  timeouts, permissions, checkout), which is exactly what drifts today.
- **Everything inline in each reusable workflow** (no composite actions): duplicates the
  JDK/cache and report logic three times and offers nothing to consumers with custom jobs.
- **GitHub's self-repository syntax `uses: $/...`** (changelog 2026-07-30): resolves to "the
  workflow's own repository at the exact commit that is running" without a checkout and counts
  as pinned. It would replace step 2 above, but (a) its resolution inside a reusable workflow
  called from *another* repository is not documented yet and (b) actionlint v1.7.12 rejects it.
  **Revisit** once both are settled; the change is internal and non-breaking for consumers.
  zizmor's `self-repository` finding is accepted until then (`.github/zizmor.yml`).

## Consequences

- Consumers write ~10 lines per job and inherit fixes by bumping one SHA.
- Each reusable workflow job performs one extra sparse checkout (~1 s).
- Inputs are the public API of this repository: see ADR 0002 for the semver contract.
