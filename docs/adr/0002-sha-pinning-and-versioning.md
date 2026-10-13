# ADR 0002 — SHA pinning and versioning

- Status: Accepted
- Date: 2026-10-13

## Context

Git tags are mutable. A compromised or force-moved tag of a third-party action (the
`tj-actions/changed-files` incident of March 2025 being the canonical example) silently changes
the code that runs with a repository's token. The same applies to this repository from the
point of view of its consumers.

## Decision

### Third-party actions used here

- Every `uses:` of a third-party action is pinned to the **full 40-character commit SHA** of a
  tagged release of the official repository, followed by a `# vX.Y.Z` comment.
- SHAs were resolved with `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, dereferencing
  annotated tags through `git/tags/<sha>`, and verified with zizmor's online audits
  (`impostor-commit`, `ref-version-mismatch`, `known-vulnerable-actions`, `stale-action-refs`).
- Dependabot (`.github/dependabot.yml`, ecosystem `github-actions`, weekly, single group,
  7-day cooldown) bumps SHA and comment together, in workflows and in `actions/*`.
- actionlint is not an action: `workflow-lint.yml` downloads its release tarball and verifies a
  **pinned SHA-256** (`ACTIONLINT_VERSION` / `ACTIONLINT_SHA256`). Dependabot cannot bump it; it is
  updated manually (take the hash from the release's `checksums.txt`).
- zizmor runs through `zizmorcore/zizmor-action` (SHA-pinned) with an explicit `version` input
  (container image tag) so a new zizmor release cannot change results unannounced.

### Versioning of this repository

- [release-please](https://github.com/googleapis/release-please) on `main` turns
  [Conventional Commits](https://www.conventionalcommits.org/) into a release PR; merging it
  creates the tag `vX.Y.Z`, the GitHub Release and `CHANGELOG.md`.
- The first release is forced to **1.0.0** with `"release-as": "1.0.0"` in
  `release-please-config.json`. **Remove that line right after v1.0.0 is published**, otherwise
  every following release PR will keep proposing 1.0.0.
- **Semver contract** (the public API is: workflow file paths, action paths, input names, input
  types/defaults semantics, outputs, required secrets, required caller permissions):

  | Change | Bump |
  | --- | --- |
  | Rename/remove a workflow, action, input, output or secret; change an input's type; change a default in a way that alters results; require a new caller permission | **major** (`feat!:` / `BREAKING CHANGE:`) |
  | New optional input/output, new workflow or action, new behaviour behind an opt-in input | minor (`feat:`) |
  | Bug fix, internal refactor, pinned action bump without behaviour change | patch (`fix:` / `ci:` / `build:`) |

  Removals are announced as deprecations (input `deprecationMessage` / release notes) at least
  one minor release before the major.

### How consumers reference this repository

```yaml
uses: AZapata27/reusable-workflows/.github/workflows/java-gradle.yml@<40-char-sha> # v1.2.3
```

- Pin by SHA with the version comment — never `@main`, and prefer the SHA over `@v1.2.3`.
- Let Dependabot (`package-ecosystem: github-actions`) bump it: Dependabot understands
  reusable-workflow `uses:` lines and updates the SHA and the comment from this repo's releases.
- Do not use floating major tags (`@v1`); this repository does not publish them on purpose.

## Future steps (GitHub Actions 2026 security roadmap)

GitHub's [2026 Actions security roadmap](https://github.blog/security/supply-chain-security/whats-coming-to-our-github-actions-2026-security-roadmap/)
announces:

- **Workflow dependency locking** — a lock of the full transitive set of actions and reusable
  workflows a run resolves. When generally available, adopt it here and recommend it to
  consumers; it complements (and may eventually replace) manual SHA pinning of transitive
  references such as the actions used *inside* `zizmor-action`.
- **Scoped secrets and no implicit inheritance** — this repository already avoids
  `secrets: inherit` and declares explicit `secrets:` (`release.yml` → `release-token`), so it is
  ready for that model.
- **Immutable releases** for this repository's tags (repository setting) so a published `vX.Y.Z`
  can never be moved.

## Consequences

- Updates are explicit and reviewable (one grouped Dependabot PR per week).
- A SHA without its comment is unreadable; the `# vX.Y.Z` comment is mandatory in reviews.
- Breaking changes require a major release and consumer action — by design.
