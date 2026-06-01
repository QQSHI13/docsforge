# Changing the language

Set the site language in `docsforge.yml`. This affects search stemming, typography (e.g., Chinese justification), and RTL layout.

## Configuration

``` yaml
extra:
  alternate:
    - name: English
      link: /
      lang: en
    - name: 中文
      link /zh/
      lang: zh
```

Or for a single language site, the language is primarily configured via the theme:

``` yaml
theme:
  language: en
```

## Supported languages

DocsForge (via the Material theme) supports 60+ languages:

- `en` — English
- `zh` — Chinese (Simplified)
- `zh-Hant` — Chinese (Traditional)
- `ja` — Japanese
- `ko` — Korean
- `de` — German
- `fr` — French
- `es` — Spanish
- `pt` — Portuguese
- `pt-BR` — Portuguese (Brazil)
- `it` — Italian
- `ru` — Russian
- `ar` — Arabic
- `hi` — Hindi
- And 50+ more

## Search language

Search stemming is language-aware. The search plugin automatically uses the configured language:

``` yaml
plugins:
  - search:
      lang:
        - en
        - de
```

Multiple languages can be specified for multilingual search.

## Right-to-left (RTL) support

For Arabic, Hebrew, and other RTL languages, DocsForge automatically adjusts layout direction when the language is set:

``` yaml
theme:
  language: ar
```

## Custom translations

You can override individual translation strings:

``` yaml
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/username/repo
```

Or create a custom translation file in `docs/locales/xx/LC_MESSAGES/messages.po`.

## Next steps

- [Setting up navigation](setting-up-navigation.md)
- [Setting up site search](setting-up-site-search.md)
