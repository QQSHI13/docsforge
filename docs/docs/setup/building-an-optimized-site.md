---
icon: material/gauge
---

# Building an optimized site

DocsForge includes the `minify` plugin by default. It compresses HTML, CSS, and JavaScript at build time.

## What's optimized automatically

The `minify` plugin strips:
- Whitespace and newlines from HTML
- HTML comments
- Optional attribute quotes
- CSS and JavaScript whitespace

This runs on every build with no configuration needed.

## Image optimization

For best results, optimize images before adding them to your docs:

``` bash
# Using pngquant for PNGs
pngquant --quality=70-90 docs/assets/images/*.png

# Using cwebp for WebP conversion
cwebp -q 80 image.png -o image.webp
```

### Recommended formats

| Format | Best for | Size |
|--------|----------|------|
| SVG | Logos, icons, diagrams | Smallest |
| WebP | Photos, screenshots | ~25% smaller than PNG |
| PNG | Screenshots with transparency | Lossless |
| JPEG | Photos without transparency | Good compression |

### Image sizing guidelines

- Keep images under 200KB when possible
- Use `width` attribute to constrain large images: `![Alt](img.png){ width="400" }`
- Lazy loading is enabled by default — no configuration needed

## Privacy plugin (external assets)

The `privacy` plugin downloads and caches external assets (like Google Fonts) during the build. This means:
- No CDN calls at runtime
- Faster page loads
- Works offline
- Better privacy for your users

Runs automatically on every build.

## Offline mode

By default DocsForge registers a service worker that precaches every built page
and asset, so the whole site works offline and loads instantly on repeat
visits. If you would rather serve the site purely from the network with no
service worker, cache manifest, or PWA manifest, set `offline.mode` to `none`:

``` yaml
offline:
  mode: none
```

When `none`, DocsForge generates no `sw.js`, no `cache-manifest.json`, and no
`manifest.json`, and pages carry no service worker registration or manifest
link. This is useful for documentation that changes frequently, sits behind an
authenticated proxy, or must never be cached by the client. The default mode
is `cache-first`.

## Build output

``` bash
docsforge build
```

The `site/` directory contains the optimized static site, ready for deployment.

## Performance checklist

- [ ] Images optimized (WebP preferred, SVG for icons)
- [ ] No external assets (privacy plugin handles this)
- [ ] Minification enabled (default)
- [ ] Cache-busting hashes in filenames (default)
- [ ] Service worker for offline use (default)
- [ ] Lazy loading for images (default)

## Measuring performance

Use these tools to check your site's performance:

- [Google PageSpeed Insights](https://pagespeed.web.dev/)
- [Lighthouse](https://developer.chrome.com/docs/lighthouse) (built into Chrome DevTools)
- [WebPageTest](https://www.webpagetest.org/)

A well-optimized DocsForge site typically scores 90+ on all Lighthouse metrics.