# Setting up site analytics

Add analytics to understand how readers use your documentation.

## Plausible Analytics

[Plausible](https://plausible.io) is privacy-friendly, lightweight, and open source.

``` yaml
extra:
  analytics:
    provider: plausible
    property: docs.example.com
```

## Google Analytics

``` yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX  # Your Measurement ID
```

## Custom analytics

For other analytics providers, add the tracking script via extra JavaScript:

``` yaml
extra_javascript:
  - assets/javascripts/analytics.js
```

``` js title="docs/assets/javascripts/analytics.js"
// Your custom analytics initialization
```

## Privacy considerations

DocsForge is designed with privacy in mind:

- Search is client-side (no search data leaves the browser)
- No external fonts are loaded by default (all vendored)
- No external JavaScript except what you explicitly add
- Works fully offline with no network requests

If you add analytics, consider:
- Using privacy-focused providers (Plausible, Fathom, GoatCounter)
- Adding a privacy policy if required by your jurisdiction
- Respecting Do Not Track signals

## Disabling analytics in development

The DocsForge development server (`docsforge serve`) does not include analytics scripts. They are only added during production builds.

## Next steps

- [Setting up social cards](setting-up-social-cards.md)
- [Building an optimized site](building-an-optimized-site.md)
