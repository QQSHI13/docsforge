---
icon: material/magnify
---

# Setting up site search

DocsForge includes a powerful client-side search engine, powered by [Marz](https://github.com/QQSHI13/marz). It's enabled by default via the `search` plugin. The backend emits a compact prebuilt index (`.marz`) alongside `search_index.json`, so the browser never builds the index itself — results are instant even for large sites, and Chinese/Japanese/Korean text is matched natively without a segmentation dictionary.

## Configuration

### Basic setup

Search is enabled by default:

``` yaml
plugins:
  - search
```

### Search separator

Control how matched terms are highlighted in results:

``` yaml
plugins:
  - search:
      separator: '[\s\u200b\-_,:!=\[\]()"`\/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
```

The separator only affects match highlighting in the UI. Indexing is done by Marz with per-language tokenization, so this never needs tuning for stemming or CJK text.

The default separator splits on:
- Whitespace and zero-width spaces
- Hyphens, underscores, commas, colons
- CamelCase boundaries (e.g., `MyClass` → `My` + `Class`)

### Language

Configure search stemming for your language:

``` yaml
plugins:
  - search:
      lang: en
```

Multiple languages can be combined (`lang: [en, ja]`). Supported codes include `ar`, `cs`, `da`, `de`, `el`, `en`, `es`, `et`, `fi`, `fr`, `hi`, `hu`, `id`, `it`, `ja`, `ko`, `nl`, `no`, `pl`, `pt`, `ro`, `ru`, `sv`, `ta`, `th`, `tr` and `zh` — call `marz.languages()` for the full list. CJK text needs no extra setup: no jieba, no segmentation dictionaries.

## Search features

Enable in `theme.features`:

### Highlighting

Highlight matching terms in search results:

``` yaml
theme:
  features:
    - search.highlight
```

### Suggestions

Show autocomplete suggestions as you type:

``` yaml
theme:
  features:
    - search.suggest
```

### Share search

Allow users to share direct links to search results:

``` yaml
theme:
  features:
    - search.share
```

## Complete search configuration

``` yaml
theme:
  features:
    - search.highlight
    - search.suggest
    - search.share

plugins:
  - search:
      separator: '[\s\u200b\-_,:!=\[\]()"`\/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
      lang: en
```

## Search behavior

- **Instant**: Results appear as you type, with no server round-trip
- **Fuzzy matching**: Minor typos are tolerated
- **Stemming**: Searching for "run" finds "running", "runs", etc.
- **Ranking**: Results ordered by relevance (title matches rank higher)
- **Excerpts**: Each result shows a snippet with context

## Excluding content from search

Add `search.exclude` front matter to hide a page:

``` yaml
---
search:
  exclude: true
---
```

Or exclude specific sections with HTML comments:

``` html
<!--search exclude-->
This content will not be indexed.
<!--end search exclude-->
```

## Next steps

- [Setting up site analytics](setting-up-site-analytics.md)
- [Setting up social cards](setting-up-social-cards.md)
