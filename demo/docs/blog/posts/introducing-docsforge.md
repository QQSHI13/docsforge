---
title: Introducing DocsForge
description: A self-contained documentation engine
date: 2026-05-09
authors:
  - qqshi13
categories:
  - Announcement
---

# Introducing DocsForge

Today we're releasing **DocsForge**, a self-contained fork of MkDocs + Material with all dependencies vendored into a single package.

## Why?

Installing MkDocs + Material requires resolving 10+ dependencies, managing lockfiles, and hoping versions don't conflict. DocsForge eliminates all of that.

## What's Included

- MkDocs 1.6 engine
- Material 9.7 theme
- All Material plugins (blog, tags, search, privacy, social, optimize, minify)
- Full markdown extension support

## Get Started

```bash
pip install docsforge
docsforge new my-docs
cd my-docs && docsforge serve
```

Read the [docs](../../features/index.md) to learn more!
