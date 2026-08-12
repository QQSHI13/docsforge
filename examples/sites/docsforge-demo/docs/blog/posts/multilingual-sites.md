---
date: 2026-08-12
authors:
  - nova
tags:
  - i18n
  - features
---

# Multi-Language Docs with Suffix-Mode i18n

DocsForge's i18n uses **sibling files** instead of per-locale directory
trees. A translated page is just the same file with a locale suffix:

```
docs/
├── index.md       # English (default)
├── index.zh.md    # 中文
└── getting-started.md
└── getting-started.zh.md
```

## Why suffix mode?

- **No URL forks** — every locale shares one canonical URL; the language
  switcher stores your preference and the service worker serves the right
  sibling.
- **No duplication** — assets live once at the root; untranslated pages
  simply have no sibling.
- **Simple nav** — per-locale titles are declared inline:

```yaml
nav:
  - title: Getting started
    path: getting-started.md
    i18n:
      zh: 入门
```

## Search follows the locale

Each locale gets its own search index (`search_index.zh.json`), so search
on the Chinese site searches Chinese pages. The preference persists across
visits via IndexedDB — and it works on 404 pages too.

This very site is a live example: switch to 中文 in the header and the whole
documentation — this post included — flips languages.
