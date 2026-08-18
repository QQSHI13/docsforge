# Security Policy

## Introduction

DocsForge takes security seriously. This policy describes which versions
receive security fixes, how to report a vulnerability privately, and what
happens after you report one.

## Supported versions

Only the **latest released version** of DocsForge receives security fixes.
There are no backports: if you hit a security issue, upgrade to the latest
release.

| Version | Supported |
|---------|-----------|
| Latest release | ✅ security fixes |
| Any older release | ❌ not supported |

Releases are frequent, so the upgrade path is short. If you cannot upgrade
immediately, pin your dependency to the latest version and track releases.

## Scope

### In scope

- The `docsforge` Python package (engine, core plugins, theme templates).
- The DocsForge Studio VS Code extension (`studio/`).
- The documentation site and the demo site.

### Out of scope

- Third-party dependencies — please report them to the respective upstream
  project instead.
- Content you author with DocsForge (your documentation is your own
  responsibility).
- Upstream MkDocs / Material for MkDocs code we vendor — report upstream
  issues to their maintainers; we pick up fixes in our vendored copies
  through normal release cadence.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report privately
through one of the channels below:

1. **Preferred:** GitHub private vulnerability reporting — open the repo's
   *Security → Report a vulnerability* page
   (`https://github.com/QQSHI13/docsforge/security/advisories/new`).
2. **Alternative:** email **qingquanshi65@gmail.com** with `[SECURITY]` in
   the subject.

### What to include

The more context you provide, the faster we can triage:

- **Affected component(s)** — engine (`docsforge`), DocsForge Studio (VS
  Code extension), the demo site, or the documentation site.
- **Versions** — DocsForge version (`docsforge --version`) and Python
  version (`python --version`).
- **Operating system** — OS name and version, and how DocsForge was
  installed (`pip`, Docker, from source, ...).
- **A minimal reproduction** — the smallest config, Markdown, or steps that
  trigger the issue.
- **Impact** — what an attacker could do (e.g. XSS, arbitrary code
  execution, SSRF via the privacy plugin, data exposure).
- **Proof of concept** — if you have one, include it. A PoC is helpful but
  not required.

### What not to include

- Do not include credentials, tokens, or other secrets in the report.
- Do not publish the vulnerability or a proof of concept publicly before a
  fix is released (see "Disclosure policy" below).

## Response process

1. **Acknowledgement** — we aim to acknowledge your report within
   **5 business days**, even if only to say we received it.
2. **Triage** — we assess severity and impact, reproduce the issue, and
   determine the fix. We may ask you for additional details.
3. **Fix** — a fix lands in the next release. Because only the latest
   version is supported, the fix ships with the normal release cadence.
4. **Advisory** — after the fix is released, we publish a GitHub security
   advisory describing the issue, impact, and affected versions.
5. **Attribution** — you will be credited in the advisory unless you prefer
   to stay anonymous. Tell us your preference when you report.

## Disclosure policy

- We follow a **coordinated disclosure** model: the vulnerability is kept
  private until a fixed release is available.
- We're happy to coordinate a public disclosure date with you — just ask.
- If a vulnerability is being actively exploited, we may release a fix
  earlier and disclose sooner.

## Security notes for users

- **Keep DocsForge up to date** — security fixes only ship in the latest
  release.
- **Use the privacy plugin** (enabled by default) — external assets are
  fetched at build time and served locally, so readers never contact third
  parties from the published site.
- **Sanitize untrusted Markdown** — DocsForge renders Markdown to HTML
  without sanitization. Do not publish sites that embed untrusted content
  without an HTML sanitizer.
- **Run the Docker image as a non-root user** — the published image already
  does, and your own builds should follow suit.
- **Pin your dependencies** when deploying — combine DocsForge's version
  pinning with your own lockfile practice.

## Contact

- GitHub private vulnerability reporting (preferred)
- Email: qingquanshi65@gmail.com (`[SECURITY]` in the subject)