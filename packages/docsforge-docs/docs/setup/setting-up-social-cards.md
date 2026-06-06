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

## Social card image

DocsForge does not automatically generate social card images. To add a custom card image:

``` yaml
extra:
  social:
    cards: true
    cards_image: assets/images/social-card.png
```

Create a 1200×630 PNG image for optimal display across platforms.

## Platform-specific tags

### Twitter/X

Twitter uses its own card system. DocsForge sets these automatically:

- `twitter:card` — `summary` or `summary_large_image`
- `twitter:title` — Page title
- `twitter:description` — Page description
- `twitter:image` — Social card image (if configured)

### LinkedIn

LinkedIn uses standard OpenGraph tags. Ensure your `site_url` is set correctly for LinkedIn to fetch metadata.

### Discord

Discord embeds use OpenGraph tags. The description is truncated to ~300 characters, so keep descriptions concise.

## Verifying your cards

Test with these tools:

- [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [Discord Embed Debugger](https://discord.com/developers/embeds)

## Troubleshooting

### Cards not appearing

1. Ensure `site_url` is set correctly in `docsforge.yml`
2. Your site must be publicly accessible (validators can't reach localhost)
3. Platforms cache metadata — use the debugger tools to force a refresh
4. Check that your image URL is absolute (not relative)

### Wrong image or description

1. Check page front matter for `description` overrides
2. Ensure `site_description` is set in `docsforge.yml`
3. First paragraph of each page is used as fallback description
4. Image dimensions should be 1200×630 for optimal display

### Image not loading

1. Use absolute URLs: `https://docs.example.com/assets/images/card.png`
2. Ensure the image is accessible without authentication
3. Check the image is under 5MB (platform limits vary)
4. Use PNG or JPEG format (avoid WebP for social cards)

## Best practices

- Keep descriptions under 160 characters
- Use consistent branding across all pages
- Test cards on multiple platforms before sharing
- Update card images when doing major releases
- Include your logo in the card image for brand recognition

## Next steps

- [Setting up site analytics](setting-up-site-analytics.md)
- [Building an optimized site](building-an-optimized-site.md)