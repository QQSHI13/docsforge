---
title: 博客
---

# 博客

DocsForge 包含内置的博客插件。用 Markdown 编写文章，即可获得一个支持作者、标签、归档、分页和 RSS 订阅源的美观博客。

## 设置

在 `docs/` 文件夹内添加一个 `blog/` 目录：

``` { .sh .no-copy }
docs/
├── blog/
│   ├── .authors.yml          # 作者资料
│   ├── index.md              # 博客 landing 页
│   └── posts/
│       └── 2026/
│           └── 01/
│               └── 01/
│                   └── hello-world/
│                       └── index.md
```

## 作者资料

创建 `docs/blog/.authors.yml`：

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

## 编写文章

创建 `docs/blog/posts/YYYY/MM/DD/post-slug/index.md`：

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

前置元数据：

| 属性 | 必填 | 描述 |
|----------|----------|-------------|
| `date` | :material-check-bold: | 文章日期（`YYYY-MM-DD`） |
| `authors` | :material-check-bold: | 来自 `.authors.yml` 的作者键列表 |
| `tags` | ❌ | 标签列表 |
| `categories` | ❌ | 分类列表 |
| `draft` | ❌ | 设为 `true` 可隐藏于列表 |

## 博客索引页

创建 `docs/blog/index.md` 作为博客 landing 页：

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

## 配置

博客插件提供合理的默认值。如需自定义：

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

| 选项 | 默认值 | 描述 |
|--------|---------|-------------|
| `blog_dir` | `blog` | `docs/` 下的目录 |
| `post_date_format` | `long` | 文章日期格式 |
| `archive_date_format` | `YYYY` | 归档日期格式 |
| `categories_allowed` | all | 限制允许的分类 |
| `pagination_per_page` | 10 | 每页文章数 |

## RSS 订阅源

博客插件在每次构建时自动生成订阅源（草稿除外）：

- `feed_rss_created.xml` —— RSS 2.0，所有文章，最新的在前
- `feed_rss_updated.xml` —— RSS 2.0，按更新时间排序
- `feed_atom.xml` —— Atom 订阅源

通过 `/{blog_dir}/feed_rss_created.xml` 访问。可通过
`plugins: [blog: {feed: false}]` 关闭。

## 归档

文章会自动按年份和月份分组：

- `/blog/archive/2026/` —— 2026 年的所有文章
- `/blog/archive/2026/01/` —— 2026 年 1 月的文章

## 标签

标签列在博客索引上，每个标签都有自己的页面：

- `/blog/tag/tutorial/` —— 所有标记为 "tutorial" 的文章

## 阅读时间

每篇文章会根据字数显示预估阅读时间。
