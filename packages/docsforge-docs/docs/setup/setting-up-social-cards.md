# Setting up social cards

DocsForge includes basic OpenGraph metadata automatically. Every page generates:

- `og:title` — Page title
- `og:description` — Page description or site description
- `og:type` — `website`
- `og:url` — Canonical page URL
- `og:site_name` — Site name

## Basic configuration

Set site-wide defaults in `docsforge.yml`:

``` yaml
site_name: My Project Docs
site_description: Complete documentation for My Project
site_url: https://docs.example.com/
```

## Customizing per page

Override metadata for individual pages using front matter:

``` yaml
---
description: Custom description for this page
---
```

## Verifying your cards

Test with these tools:

- [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)

## Troubleshooting

### Cards not appearing

1. Ensure `site_url` is set correctly in `docsforge.yml`
2. Your site must be publicly accessible (validators can't reach localhost)
3. Platforms cache metadata — use the debugger tools to force a refresh

### Wrong image or description

1. Check page front matter for `description` overrides
2. Ensure `site_description` is set in `docsforge.yml`
3. First paragraph of each page is used as fallback description
