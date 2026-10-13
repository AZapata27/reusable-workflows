# Usage

Copy-paste examples for calling the reusable workflows. Replace `<sha>` with the full commit
SHA of a release tag and keep the `# vX.Y.Z` comment; Dependabot keeps both up to date.

```bash
# Resolve the SHA of a release tag
gh api repos/AZapata27/reusable-workflows/commits/v1.0.0 -q .sha
```

General rules for callers:

- Declare a `permissions:` block on **every calling job** (the reusable workflow can only narrow
  it). Keep `permissions: {}` at the top of your workflow.
- Pass secrets explicitly (`secrets: { name: ${{ secrets.X }} }`). Never use `secrets: inherit`.
- Do not pass event data (PR titles, branch names, comments) into command-like inputs
  (`gradle-args`, `maven-args`, `pre-build-command`, `install-command`, `run-command`).
- Matrices go on the calling job; each cell becomes one call.

---

## Java — Gradle (`java-gradle.yml`)

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:

permissions: {}

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    uses: AZapata27/reusable-workflows/.github/workflows/java-gradle.yml@<sha> # v1.0.0
    permissions:
      contents: read
    # with:                      # all optional; defaults shown
    #   java-version: '21'
    #   java-distribution: temurin
    #   working-directory: .
    #   gradle-args: build
    #   timeout-minutes: 20
    #   upload-test-reports: true
```

Testcontainers works out of the box: the default `runs-on: ubuntu-latest` has Docker.

### Matrix over Gradle subprojects (independent builds per directory)

```yaml
jobs:
  build:
    name: ${{ matrix.project }} (JVM)
    strategy:
      fail-fast: false
      matrix:
        project: [quarkus-native, quarkus-reactive-native, spring-native, spring-webflux-native]
    uses: AZapata27/reusable-workflows/.github/workflows/java-gradle.yml@<sha> # v1.0.0
    permissions:
      contents: read
    with:
      working-directory: ${{ matrix.project }}
      gradle-args: build --no-daemon
      timeout-minutes: 30
```

Artifact names derive from `working-directory` (`test-reports-<dir>`), so they are unique per
cell. For a JDK matrix on the same directory, set `report-name: test-reports-jdk${{ matrix.java }}`.

## Java — Maven (`java-maven.yml`)

```yaml
jobs:
  backend:
    uses: AZapata27/reusable-workflows/.github/workflows/java-maven.yml@<sha> # v1.0.0
    permissions:
      contents: read
    # with:
    #   maven-args: -B verify      # default; ./mvnw is used when present, otherwise mvn
```

### Multi-module repository with a shared module installed first

`pre-build-command` runs from the **repository root**, after the JDK is ready and before the
main build in `working-directory`. Combine it with a matrix:

```yaml
jobs:
  build:
    name: ${{ matrix.module }}
    strategy:
      fail-fast: false
      matrix:
        module:
          - server-grpc-spring-boot
          - client-grpc-spring-boot
          - server-client-grpc-quarkus
          - cloud-eureka-server
    uses: AZapata27/reusable-workflows/.github/workflows/java-maven.yml@<sha> # v1.0.0
    permissions:
      contents: read
    with:
      working-directory: ${{ matrix.module }}
      pre-build-command: mvn -B -f grpc-interfaces/pom.xml install -DskipTests
```

(`--no-transfer-progress` is always added through `MAVEN_ARGS`.) If the shared module has its
own tests you want to run once, add a separate job calling the workflow with
`working-directory: grpc-interfaces` and `maven-args: -B install`.

## Node / Nx (`node.yml`)

```yaml
jobs:
  frontend:
    uses: AZapata27/reusable-workflows/.github/workflows/node.yml@<sha> # v1.0.0
    permissions:
      contents: read
    with:
      working-directory: frontend
      node-version: '22'          # no .nvmrc in that directory
      run-command: npm run build
```

The package manager is detected from the lockfile (`package-lock.json` → `npm ci`,
`pnpm-lock.yaml` → `pnpm install --frozen-lockfile`, `yarn.lock` → `yarn install
--immutable`/`--frozen-lockfile`); override with `install-command`.

### Nx monorepo

```yaml
jobs:
  ci:
    uses: AZapata27/reusable-workflows/.github/workflows/node.yml@<sha> # v1.0.0
    permissions:
      contents: read
    with:
      fetch-depth: 0              # Nx needs history for affected/base comparisons
      run-command: npx nx run-many -t lint typecheck test build
      # nx-no-cloud: true         # default: NX_NO_CLOUD=true, no Nx Cloud token needed
      timeout-minutes: 20
```

### Test summary for Node

Produce JUnit XML and point `junit-files` at it, e.g. with the Node.js test runner:

```yaml
    with:
      run-command: >-
        node --test --test-reporter=spec --test-reporter-destination=stdout
        --test-reporter=junit --test-reporter-destination=reports/junit.xml
      junit-files: reports/junit.xml
```

## Workflow lint (`workflow-lint.yml`)

```yaml
jobs:
  workflow-lint:
    uses: AZapata27/reusable-workflows/.github/workflows/workflow-lint.yml@<sha> # v1.0.0
    permissions:
      contents: read
    # with:
    #   zizmor-min-severity: low   # informational | low | medium | high
    #   zizmor-config: .github/zizmor.yml
```

actionlint reads `.github/actionlint.yaml` and zizmor reads `.github/zizmor.yml` from your
repository when present.

## Security (`security.yml`)

```yaml
on:
  pull_request:
  push:
    branches: [master]
  schedule:
    - cron: '23 4 * * 1'          # weekly CodeQL run

jobs:
  security:
    uses: AZapata27/reusable-workflows/.github/workflows/security.yml@<sha> # v1.0.0
    permissions:
      contents: read
      actions: read               # CodeQL (required even if CodeQL is disabled; see ADR 0003)
      security-events: write      # CodeQL SARIF upload
    with:
      codeql-languages: '["java-kotlin", "actions"]'
      # codeql-build-mode: none   # default; Java/Kotlin analysed without building
      # fail-on-severity: moderate
```

dependency-review only runs on `pull_request` events. Code scanning must be available for the
repository (public repositories, or GitHub Code Security on private ones).

## Release (`release.yml`)

```yaml
on:
  push:
    branches: [master]

permissions: {}

jobs:
  build:
    uses: AZapata27/reusable-workflows/.github/workflows/java-gradle.yml@<sha> # v1.0.0
    permissions:
      contents: read
    with:
      gradle-args: build
  # A job in the same run that uploads the artifact to release, e.g.
  package:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<sha> # vX.Y.Z
        with:
          persist-credentials: false
      # ... build the jar ...
      - uses: actions/upload-artifact@<sha> # vX.Y.Z
        with:
          name: dist
          path: build/libs/*.jar

  release:
    needs: package
    uses: AZapata27/reusable-workflows/.github/workflows/release.yml@<sha> # v1.0.0
    permissions:
      contents: write             # tags, releases, release assets
      issues: write               # release-please labels
      pull-requests: write        # release PR
      id-token: write             # provenance signing (Sigstore OIDC)
      attestations: write         # store the attestation
    with:
      release-type: simple        # or: config-file/manifest-file for manifest mode
      artifact-name: dist         # optional: attest + attach to the release
    # secrets:
    #   release-token: ${{ secrets.RELEASE_PLEASE_TOKEN }}   # so the release PR triggers CI
```

Outputs: `release_created`, `tag_name`, `version`. Verify an attached file with
`gh attestation verify <file> --repo <owner>/<repo>`.

Keep `id-token` and `attestations` in the block even when you do not pass `artifact-name`:
GitHub checks the permission ceiling of every job in the called workflow when the run starts,
including the provenance job that will be skipped (ADR 0003).

## Composite actions in your own jobs

```yaml
    steps:
      - uses: actions/checkout@<sha> # vX.Y.Z
        with:
          persist-credentials: false
      - uses: AZapata27/reusable-workflows/actions/setup-jvm@<sha> # v1.0.0
        with:
          java-version: '21'
          build-tool: gradle
      - run: ./gradlew check
      - if: ${{ !cancelled() }}
        uses: AZapata27/reusable-workflows/actions/test-reports@<sha> # v1.0.0
        with:
          name: test-reports-check
```

## Dependabot for consumers

Add (or extend) `.github/dependabot.yml` so the SHA + comment of these workflows are bumped on
each release, together with any other action you use:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
    groups:
      github-actions:
        patterns: ["*"]
```
