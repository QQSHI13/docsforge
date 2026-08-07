# DocsForge Documentation

[![Built with Material for MkDocs](https://img.shields.io/badge/Material_for_MkDocs-526CFE?style=for-the-badge&logo=MaterialForMkDocs&logoColor=white)](https://squidfunk.github.io/mkdocs-material/)

The official documentation site for **DocsForge** — a self-contained documentation build system.

## 🚀 Quick Start

```bash
git clone https://github.com/QQSHI13/docsforge-docs.git
cd docsforge-docs
pip install docsforge
docsforge serve
```

Visit [localhost:8000](http://localhost:8000) to preview.

## 📚 Documentation Structure

| Section | Description |
|---------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [Creating Your Site](docs/creating-your-site.md) | Project structure and configuration |
| [Publishing](docs/publishing-your-site.md) | Deploy to GitHub Pages, Netlify, Vercel |
| [Features](docs/features.md) | Overview of DocsForge capabilities |
| [Blogging](docs/blogging.md) | Set up a blog with authors, tags, RSS |
| [Setup Guides](docs/setup/) | Customize colors, fonts, navigation, search |
| [Reference](docs/reference/) | Complete Markdown syntax guide |
| [Changelog](docs/changelog/) | Version history |

## 🏗️ Building

```bash
docsforge build
```

The static site is generated in the `site/` directory.

## 🌐 Deployment

This site auto-deploys to GitHub Pages via [GitHub Actions](.github/workflows/pages.yml) on every push to `main`.

Live URL: **https://qqshi13.github.io/docsforge-docs/**

## 📄 License

[LGPL v3](docs/license.md)

## 🤝 Contributing

This documentation is open source. Feel free to open issues or pull requests for improvements.

## Star History

[![Star History Chart](https://api.star-history.com/chart?repos=QQSHI13/docsforge-docs&type=date&legend=top-left)](https://www.star-history.com/?repos=QQSHI13%2Fdocsforge-docs&type=date&legend=top-left)
