# reusable-workflows

[![CI](https://github.com/AZapata27/reusable-workflows/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AZapata27/reusable-workflows/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/AZapata27/reusable-workflows/badge)](https://scorecard.dev/viewer/?uri=github.com/AZapata27/reusable-workflows)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Centralised CI/CD for my personal repositories: **reusable workflows** and **composite actions**
for Java (Gradle / Maven), Node.js / Nx, workflow linting, security scanning and releases.
Every third-party action is pinned by commit SHA, every job runs with least privilege and a
timeout, and the workflows are themselves linted (actionlint + zizmor) and tested against
fixture projects on every change.

## Catalog

### Reusable workflows (`.github/workflows/`)

| Workflow | Purpose | Key inputs (default) | Outputs | Caller permissions |
| --- | --- | --- | --- | --- |
| [`java-gradle.yml`](.github/workflows/java-gradle.yml) | Build + test with `./gradlew`, JUnit summary, test-report artifact | `java-version` (`21`), `java-distribution` (`temurin`), `working-directory` (`.`), `gradle-args` (`build`), `timeout-minutes` (`20`), `upload-test-reports` (`true`), `gradle-cache-provider` (`basic`), `report-name`, `runs-on`, `fetch-depth` | `tests-failed` | `contents: read` |
| [`java-maven.yml`](.github/workflows/java-maven.yml) | Build + test with `./mvnw` (or `mvn`), optional pre-build step | `java-version` (`21`), `java-distribution`, `working-directory`, `maven-args` (`-B verify`), `pre-build-command`, `timeout-minutes` (`20`), `upload-test-reports` (`true`), `report-name`, `runs-on`, `fetch-depth` | `tests-failed` | `contents: read` |
| [`node.yml`](.github/workflows/node.yml) | Install (npm/pnpm/yarn auto-detected) + run a command; Nx-friendly | `node-version-file` (`.nvmrc`), `node-version`, `working-directory`, `install-command` (auto), `run-command` (`<pm> test`), `nx-no-cloud` (`true`), `fetch-depth` (`1`), `junit-files`, `timeout-minutes` (`20`) | — | `contents: read` |
| [`workflow-lint.yml`](.github/workflows/workflow-lint.yml) | actionlint + zizmor over the caller's `.github/` | `zizmor-min-severity` (`low`), `zizmor-persona` (`regular`), `zizmor-config`, `zizmor-version` | — | `contents: read` |
| [`security.yml`](.github/workflows/security.yml) | dependency-review on PRs; optional CodeQL | `fail-on-severity` (`moderate`), `allow-licenses`, `deny-licenses`, `codeql-languages` (off), `codeql-build-mode` (`none`), `codeql-queries` (`security-extended`) | — | `contents: read`, `actions: read`, `security-events: write` |
| [`release.yml`](.github/workflows/release.yml) | release-please (tag, GitHub Release, CHANGELOG); optional build-provenance attestation + release assets | `release-type` (`simple`), `config-file`, `manifest-file`, `artifact-name`, `artifact-subject-path`; secret `release-token` (optional) | `release_created`, `tag_name`, `version` | `contents`, `issues`, `pull-requests`, `id-token`, `attestations`: `write` |

### Composite actions (`actions/`)

| Action | Purpose | Inputs (default) | Outputs |
| --- | --- | --- | --- |
| [`setup-jvm`](actions/setup-jvm/action.yml) | `actions/setup-java` (+ Maven cache) and, for Gradle, `gradle/actions/setup-gradle` (wrapper validation + cache) | `java-version` (`21`), `distribution` (`temurin`), `build-tool` (`none`/`gradle`/`maven`), `working-directory`, `gradle-cache-provider` (`basic`) | `java-version`, `java-home`, `gradle-version` |
| [`test-reports`](actions/test-reports/action.yml) | JUnit XML → pass/fail/skip table (+ failing tests) in the job summary; uploads reports as an artifact. Standard-library Python, no extra action | `name` (required), `working-directory`, `junit-files`, `path`, `upload` (`true`), `retention-days` (`7`), `title` | `total`, `passed`, `failed`, `skipped`, `artifact-url` |

Why two mechanisms: [ADR 0001](docs/adr/0001-reusable-workflows-vs-composite-actions.md).

## Quickstart

```yaml
# .github/workflows/ci.yml in a consumer repository
name: CI

on:
  push:
    branches: [master]
  pull_request:

permissions: {}

jobs:
  build:
    uses: AZapata27/reusable-workflows/.github/workflows/java-gradle.yml@<sha> # v1.0.0
    permissions:
      contents: read

  workflow-lint:
    uses: AZapata27/reusable-workflows/.github/workflows/workflow-lint.yml@<sha> # v1.0.0
    permissions:
      contents: read
```

More examples — matrix over subprojects, Maven multi-module with `pre-build-command`, Nx
monorepo, security (weekly CodeQL), OpenSSF Scorecard, releases with provenance, Dependabot for consumers — in
**[docs/usage.md](docs/usage.md)**.

## Security model

- **SHA pinning** of every third-party action (`# vX.Y.Z` comment), bumped by Dependabot weekly.
- **Least privilege**: `permissions: {}` at the top of every workflow; each job asks only for
  what it uses. No `secrets: inherit`, no `pull_request_target`.
- **No credential persistence**: `actions/checkout` with `persist-credentials: false`.
- **No template injection**: inputs and context values reach scripts only through `env:`.
- **Runner hardening**: `step-security/harden-runner` (`egress-policy: audit`) first in every
  job, `timeout-minutes` everywhere.
- **Self-verification**: this repository lints its own workflows with actionlint and zizmor
  (zero medium/high findings) and runs CodeQL for the `actions` language.

Details and accepted findings: [ADR 0003](docs/adr/0003-least-privilege-and-hardening.md).
Report vulnerabilities privately: [SECURITY.md](SECURITY.md).

## Versioning

Releases are cut by release-please from [Conventional Commits](https://www.conventionalcommits.org/):
tags `vX.Y.Z`, GitHub Releases and [CHANGELOG.md](CHANGELOG.md). Renaming or removing an input,
output, secret, workflow or action is a **major** release. Consumers pin the release's commit SHA
and let Dependabot bump it. See [ADR 0002](docs/adr/0002-sha-pinning-and-versioning.md).

## Repository layout

```
.github/workflows/   reusable workflows + this repo's ci.yml, release-please.yml and scorecard.yml
actions/             composite actions
tests/fixtures/      minimal Gradle, Maven and Node projects exercised by ci.yml
docs/                usage guide and ADRs
```

## License

[Apache-2.0](LICENSE)
