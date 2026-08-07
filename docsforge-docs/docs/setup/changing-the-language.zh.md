# 更改语言

在 `docsforge.yml` 中设置站点语言。这会影响搜索词干提取、排版（例如中文对齐）和 RTL 布局。

## 配置

``` yaml
extra:
  alternate:
    - name: English
      link: /
      lang: en
    - name: 中文
      link: /zh/
      lang: zh
```

对于单语言站点，语言主要通过主题进行配置：

``` yaml
theme:
  language: en
```

## 支持的语言

DocsForge（通过 Material 主题）支持 60 多种语言：

- `en` — 英语
- `zh` — 中文（简体）
- `zh-Hant` — 中文（繁体）
- `ja` — 日语
- `ko` — 韩语
- `de` — 德语
- `fr` — 法语
- `es` — 西班牙语
- `pt` — 葡萄牙语
- `pt-BR` — 葡萄牙语（巴西）
- `it` — 意大利语
- `ru` — 俄语
- `ar` — 阿拉伯语
- `hi` — 印地语
- 以及 50 多种其他语言

## 搜索语言

搜索词干提取是区分语言的。搜索插件会自动使用配置的语言：

``` yaml
plugins:
  - search:
      lang:
        - en
        - de
```

可以为多语言搜索指定多种语言。

## 从右到左（RTL）支持

对于阿拉伯语、希伯来语和其他 RTL 语言，DocsForge 会在设置语言时自动调整布局方向：

``` yaml
theme:
  language: ar
```

## 自定义翻译

你可以通过主题的本地化文件覆盖单个翻译字符串，或者在 `docs/locales/xx/LC_MESSAGES/messages.po` 中创建自定义翻译文件，并在你的覆盖文件中引用它。

## 下一步

- [设置导航](setting-up-navigation.md)
- [设置站点搜索](setting-up-site-search.md)
