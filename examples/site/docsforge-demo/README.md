# DocsForge Demo — official example site

A complete DocsForge site used as the reference example. It exercises many
features at once:

- **Config**: explicit `title`/`path`/`children` nav schema, palette, icons
- **Overrides**: `overrides/main.html` extends `base.html` via the `announce`
  block (`theme.custom_dir`)
- **Blog** with posts, authors, and archives
- **Tags** page
- **Math** (KaTeX) and **TikZ diagrams**
- **Search** and the offline **service worker**

```bash
# Build (outputs to site/)
docsforge build

# Or preview
docsforge serve
```

Built and verified in CI by
`tests/integration/test_example_site.py` — if this site breaks, the tests
catch it. The published version lives at
[https://docsforge-demo.pages.dev](https://docsforge-demo.pages.dev).
