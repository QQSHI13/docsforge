# Setting up site search

DocsForge includes a powerful client-side search engine. It's enabled by default via the `search` plugin.

## Configuration

### Basic setup

Search is enabled by default:

``` yaml
plugins:
  - search
```

### Search separator

Control how search terms are split into tokens:

``` yaml
plugins:
  - search:
      separator: '[\s\u200b\-_,:!=\[\]()"`\/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
```

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

Supported languages include: `en`, `de`, `es`, `fr`, `ja`, `pt`, `ru`, `zh`.

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
