---
title: Blogging
---

# Blogging

DocsForge includes a built-in blog plugin. Write posts in Markdown, get a beautiful blog with authors, tags, archives, pagination, and RSS feeds.

## Setup

Add a `blog/` directory inside your `docs/` folder:

``` { .sh .no-copy }
docs/
├── blog/
│   ├── .authors.yml          # Author profiles
│   ├── index.md              # Blog landing page
│   └── posts/
│       └── 2026/
│           └── 01/
│               └── 01/
│                   └── hello-world/
│                       └── index.md
```

## Author profiles

Create `docs/blog/.authors.yml`:

```yaml
authors:
  qq:
    name: QQ
    description: 12-year-old developer
    avatar: https://github.com/QQSHI13.png
  nova:
    name: Nova
    description: AI Assistant
    avatar: https://github.com/QQSHI13.png
```

## Writing a post

Create `docs/blog/posts/YYYY/MM/DD/post-slug/index.md`:

```yaml
---
date: 2026-01-01
authors:
  - qq
tags:
  - tutorial
  - docsforge
---

# Hello World

Your post content here...

<!-- more -->

This is the excerpt break. Content before `<!-- more -->` appears in post listings.
```

Front matter:

| Property | Required | Description |
|----------|----------|-------------|
| `date` | ✅ | Post date (`YYYY-MM-DD`) |
| `authors` | ✅ | List of author keys from `.authors.yml` |
| `tags` | ❌ | List of tags |
| `categories` | ❌ | List of categories |
| `draft` | ❌ | Set `true` to hide from listings |

## Blog index page

Create `docs/blog/index.md` for your blog landing page:

```markdown
---
title: Blog
hide:
  - navigation
  - toc
---

# Blog

Welcome to my blog!

[:octicons-rss-24: RSS Feed](../feed_rss_created.xml)
```

## Configuration

The blog plugin works with sensible defaults. To customize:

```yaml
plugins:
  - blog:
      blog_dir: blog
      post_date_format: long        # "January 1, 2026"
      archive_date_format: MMMM YYYY  # "January 2026"
      categories_allowed:
        - tutorial
        - news
        - release
      pagination_per_page: 10
```

| Option | Default | Description |
|--------|---------|-------------|
| `blog_dir` | `blog` | Directory under `docs/` |
| `post_date_format` | `long` | Date format for posts |
| `archive_date_format` | `YYYY` | Date format for archive |
| `categories_allowed` | all | Restrict allowed categories |
| `pagination_per_page` | 10 | Posts per page |

## RSS feeds

The blog plugin automatically generates RSS feeds:

- `feed_rss_created.xml` — All posts, newest first
- `feed_rss_updated.xml` — Recently updated posts

Access them at `/{blog_dir}/feed_rss_created.xml`.

## Archive

Posts are automatically grouped by year and month:

- `/blog/archive/2026/` — All 2026 posts
- `/blog/archive/2026/01/` — January 2026 posts

## Tags

Tags are listed on the blog index and each tag gets its own page:

- `/blog/tag/tutorial/` — All posts tagged "tutorial"

## Reading time

Each post displays an estimated reading time based on word count.
