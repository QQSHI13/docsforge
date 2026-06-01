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

## Privacy plugin (external assets)

The `privacy` plugin downloads and caches external assets (like Google Fonts) during the build. This means:
- No CDN calls at runtime
- Faster page loads
- Works offline
- Better privacy for your users

Runs automatically on every build.

## Build output

``` bash
docsforge build
```

The `site/` directory contains the optimized static site, ready for deployment.
