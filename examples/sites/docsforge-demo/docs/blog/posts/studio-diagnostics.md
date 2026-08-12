---
date: 2026-08-12
authors:
  - qq
tags:
  - studio
  - vscode
  - tooling
---

# DocsForge Studio: Link Diagnostics Without a Language Server

Most documentation tooling ships a language server to power editor features.
DocsForge takes a different route: the **build itself validates your docs**,
and the VS Code extension reads the results.

## Every build checks your links

During `docsforge build` (and every `serve` rebuild), DocsForge:

- resolves every relative link and image against the docs tree,
- cross-checks `page.md#anchor` links against the target page's headings,
- checks footnotes and nav entries,
- and persists everything to `.docsforge/cache/validation.json`.

A broken cross-link surfaces even when only the *target* page changed —
validation is re-emitted for every page on every build.

## The extension reads that file

[DocsForge Studio](../../features.md) turns the validation data into:

- **squiggles** on every occurrence of a broken link or anchor,
- **Fix link** / **Fix all broken links** code actions,
- **Rename Document** and **Rename Anchor** refactors that rewrite every
  inbound link — translation-aware, so renaming a `.zh` file renames its
  base and all locale variants.

No language server, no background indexer, no paid tier — just the build
output you already have. Run `docsforge serve` and watch the squiggles
appear (and disappear) as you edit.
