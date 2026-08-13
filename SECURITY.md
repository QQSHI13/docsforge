# Security Policy

## Supported versions

Only the **latest released version** of DocsForge is supported with security
fixes. Security fixes are backported on request for the two most recent
releases when the fix applies cleanly.

| Version | Supported |
|---------|-----------|
| Latest release (12.5.x) | ✅ |
| Previous two releases | ⚠️ backported on request |
| Older | ❌ |

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report privately:

1. **Preferred:** GitHub private vulnerability reporting — open the repo's
   *Security → Report a vulnerability* page
   (`https://github.com/QQSHI13/docsforge/security/advisories/new`).
2. **Alternative:** email **qingquanshi65@gmail.com** with `[SECURITY]` in
   the subject.

### What to include

- Affected component(s): engine (`docsforge`), DocsForge Studio (VS Code
  extension), or the demo/docs site
- DocsForge version (`docsforge --version`) and Python version
- A minimal reproduction (config, markdown, or steps)
- Impact: what an attacker can do, and any proof of concept

## What happens next

- We aim to acknowledge your report within **3 business days**.
- You'll get updates on the investigation and the fix timeline.
- After a fix is released, we'll publish a security advisory with
  attribution (unless you prefer to stay anonymous).
- We're happy to coordinate a public disclosure date with you.

## Scope

In scope: the `docsforge` Python package, the DocsForge Studio extension, the
documentation site, and the demo site.

Out of scope: third-party dependencies (report them upstream), and content
you author with DocsForge.
