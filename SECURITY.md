# Security policy

This repository ships CI/CD building blocks that run with access to the source code and,
for releases, write tokens of the repositories that call them. Vulnerabilities here are
supply-chain vulnerabilities for every consumer, so they are treated with priority.

## Supported versions

| Version | Supported |
| --- | --- |
| Latest `v1.x.y` release | ✅ |
| Older releases | ❌ — upgrade by bumping the pinned SHA (Dependabot does this for you) |

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private vulnerability reporting:
**Security → Report a vulnerability** on this repository
(<https://github.com/AZapata27/reusable-workflows/security/advisories/new>).

Include the affected workflow/action, the version or commit SHA, and a proof of concept
if possible. You can expect an acknowledgement within 7 days. Fixes are released as a
patch version and announced in a GitHub Security Advisory.

## Scope

In scope:

- Script/template injection through workflow inputs or event data.
- Permission escalation (a job obtaining more than its documented `permissions:`).
- Credential leakage (tokens persisted on disk, printed in logs, uploaded as artifacts).
- Pinned third-party actions resolving to unexpected code.

Out of scope: vulnerabilities in the consumer repositories' own build scripts, and
findings in the test fixtures under `tests/fixtures/` that do not affect the workflows.

## Hardening summary

See [docs/adr/0003-least-privilege-and-hardening.md](docs/adr/0003-least-privilege-and-hardening.md).
