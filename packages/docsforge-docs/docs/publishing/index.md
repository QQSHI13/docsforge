# Publishing Your Site

DocsForge builds static HTML that can be deployed to any web server or static hosting platform. This section covers everything you need to get your docs online.

## Quick Deploy

The fastest ways to deploy:

| Platform | Method | Time |
|----------|--------|------|
| **GitHub Pages** | GitHub Actions | 5 min |
| **Netlify** | Drag `site/` folder | 1 min |
| **Surge.sh** | `surge site/` | 30 sec |

## What's in This Section

- [**Usage Guide**](usage.md) — Day-to-day DocsForge commands, configuration, and content features
- [**Migration Guide**](migration.md) — Moving from MkDocs/Material to DocsForge, feature parity, step-by-step migration
- [**Deployment Guide**](deployment-guide.md) — Detailed instructions for 10+ platforms: GitHub Pages, Netlify, Vercel, Cloudflare, AWS, Firebase, Docker, and more

## Build Output

DocsForge outputs a `site/` directory containing:

```
site/
├── index.html          # Homepage
├── 404.html            # Error page
├── sitemap.xml         # SEO sitemap
├── sitemap.xml.gz      # Compressed sitemap
├── manifest.json       # PWA manifest
├── assets/             # CSS, JS, fonts, images
│   ├── javascripts/
│   ├── stylesheets/
│   └── ...
└── [your pages]/       # One HTML file per Markdown page
```

This is a static site — deploy it anywhere that serves HTML files.

## One-Command Deploy Examples

### GitHub Pages (with Actions)
See [Deployment Guide → GitHub Pages](deployment-guide.md#github-pages) for the full GitHub Actions workflow.

### Netlify (Drag & Drop)
1. Run `docsforge build`
2. Go to [netlify.com](https://netlify.com)
3. Drag the `site/` folder onto the page

### Surge.sh
```bash
npm install -g surge
docsforge build
surge site/ my-docs.surge.sh
```

### Docker
```bash
docsforge build
docker run -v $(pwd)/site:/usr/share/nginx/html:ro -p 8080:80 nginx:alpine
```

## Before You Deploy

### Checklist
- [ ] `site_url` in `docsforge.yml` matches your actual domain
- [ ] `repo_url` set (for "Edit this page" links)
- [ ] `copyright` configured
- [ ] Build succeeds: `docsforge build`
- [ ] Site looks correct: `docsforge serve`

### SEO Essentials
DocsForge handles these automatically:
- ✅ Sitemap (`sitemap.xml.gz`)
- ✅ PWA manifest (`manifest.json`)
- ✅ OpenGraph tags (automatic)
- ✅ Semantic HTML
- ✅ Fast loading (optimized assets)

## Need Help?

- **Platform-specific issues**: See the [Deployment Guide](deployment-guide.md)
- **Migration questions**: See the [Migration Guide](migration.md)
- **Usage questions**: See the [Usage Guide](usage.md)
- **General help**: [GitHub Discussions](https://github.com/QQSHI13/docsforge/discussions)
