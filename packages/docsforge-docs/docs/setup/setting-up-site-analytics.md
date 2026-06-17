# Setting up site analytics

Add analytics to understand how readers use your documentation.

## Google Analytics 4 (built-in)

DocsForge ships with a built-in Google Analytics 4 integration.

``` yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX  # Your Measurement ID
```

## Other providers

For Plausible, Fathom, GoatCounter, Umami, or any other provider, add the tracking script via `extra_javascript`:

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

## Tracking events

Track custom events (e.g., button clicks, downloads) by adding JavaScript:

``` js title="docs/assets/javascripts/events.js"
document.addEventListener('click', function(e) {
  if (e.target.matches('a[href*=".zip"]')) {
    // Track download
    gtag('event', 'download', {
      event_category: 'documentation',
      event_label: e.target.href
    });
  }
});
```

## Best practices

- Use privacy-focused analytics when possible
- Only track what's necessary for improving docs
- Document your analytics practices in a privacy policy
- Respect user preferences (Do Not Track, GDPR consent)
- Test analytics in production builds, not development
- Regularly review analytics data to identify popular and underused pages

## Troubleshooting

### Analytics not loading

1. Check that `property` is set correctly
2. Verify you're viewing a production build, not `docsforge serve`
3. Check browser console for JavaScript errors
4. Ensure ad blockers aren't blocking the tracking script

### Data not appearing

1. Analytics dashboards may have a delay (up to 24 hours for some providers)
2. Verify the correct property ID is configured
3. Check that the site is publicly accessible (analytics can't track localhost)
