---
icon: material/help-circle
---

# Support

DocsForge is free and open source. If you get stuck, need help migrating, or
found a bug — we're here to help.

## If migration breaks anything, we fix it for free

Migrating from MkDocs + Material for MkDocs should not cost you a week of
debugging. If your site doesn't build under DocsForge, or renders differently
than it did before:

**Send us the details and we will fix DocsForge — or your config — until it
does, at no cost.** This offer does not expire.

=== "GitHub issue"

    [Open an issue](https://github.com/QQSHI13/docsforge/issues) with your
    `mkdocs.yml` and the repo link. Best for open-source sites, since the
    discussion helps others hitting the same thing.

=== "Email"

    Write to **qingquanshi65@gmail.com** with `[MIGRATION]` in the subject.
    Use this if your docs are private, your config is sensitive, or you'd
    simply rather not post it publicly — both routes get the same offer.

## Fastest path: the migration one-liner

Coming from **MkDocs, ProperDocs, or Zensical**? Migrate your existing config
in one command — it converts `mkdocs.yml` / `properdocs.yml` / `zensical.toml`
to `docsforge.yml` automatically:

=== "macOS / Linux"

    ``` bash
    curl -fsSL https://qqshi13.github.io/docsforge/migrate.sh | bash
    ```

=== "Windows (PowerShell)"

    ``` powershell
    irm https://qqshi13.github.io/docsforge/migrate.ps1 | iex
    ```

The script:

- converts navigation, theme, plugins, and extensions,
- warns about anything it can't migrate (third-party plugins, `INHERIT`, hooks),
- and prints a report telling you exactly what to check.

Anything it couldn't handle? Email us or open an issue — we'll help you port it.

## Getting help

| Need | Where |
|------|-------|
| **Bugs, feature requests** | [GitHub Issues](https://github.com/QQSHI13/docsforge/issues) |
| **Security vulnerabilities** | [Security policy](https://github.com/QQSHI13/docsforge/blob/main/SECURITY.md) (private reporting) |
| **Migration help, private questions** | **qingquanshi65@gmail.com** |
| **See it in action** | [Live demo](https://docsforge-demo.pages.dev) |

## What to include in a report

To get the fastest answer, include:

1. `docsforge --version` (and Python version, if relevant)
2. Your operating system
3. Your `docsforge.yml` (redacted if private) — or the error message in full
4. Steps to reproduce

For a plugin, hook, or feature the migration script couldn't convert, tell us:

- the config snippet that failed,
- what you want it to do,
- and we'll port it or point you to a built-in equivalent.

## Where to look first

- [Troubleshooting](troubleshooting.md) — common problems and fixes
- [Migration guide](publishing/migration.md) — detailed key-by-key mapping
- [Changelog](changelog/index.md) — what changed in each release
