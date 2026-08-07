# Tooltips

工具提示在鼠标悬停文本时显示额外信息。

## Abbreviations

定义在悬停时显示完整文本的缩写：

``` markdown
The HTML specification is maintained by the W3C.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium
```

HTML 规范由 W3C 维护。

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium

## Footnotes

添加带引用的脚注：

``` markdown
DocsForge is a self-contained documentation build system.[^1]

[^1]: All dependencies are vendored into the project repository.
```

DocsForge 是一个自包含的文档构建系统。[^1]

[^1]: 所有依赖都已 vendored 到项目仓库中。

## Content tooltips

使用 `content.tooltips` 功能启用：

``` yaml
theme:
  features:
    - content.tooltips
```

这将为整个站点中的缩写和链接添加悬停工具提示。

## Link tooltips

使用 `title` 属性为链接添加工具提示：

``` markdown
[DocsForge](https://github.com/QQSHI13/docsforge "Self-contained documentation builds")
```

## Definition lists as tooltips

定义列表项可用作词汇表条目：

``` markdown
DocsForge
:   A self-contained documentation build system with vendored dependencies.

Material
:   The most popular documentation theme, built into DocsForge.
```

DocsForge
:   一个带有 vendored 依赖项的自包含文档构建系统。

Material
:   最受欢迎的文档主题，内置于 DocsForge。

### Creating a glossary page

将所有定义收集在一个页面上，便于查阅：

``` markdown
# Glossary

## A

**API**
:   Application Programming Interface — a set of protocols for building software.

## B

**Build**
:   The process of converting Markdown files into a static HTML site.

## D

**DocsForge**
:   A self-contained documentation engine with vendored dependencies.
```

## Magic links

针对 GitHub 引用的自动链接转换：

``` markdown
See issue #123 and PR #456 for details.
```

启用方式：

``` yaml
markdown_extensions:
  - pymdownx.magiclink:
      repo_url_shorthand: true
      user: QQSHI13
      repo: docsforge-docs
```

## Link preview tooltips

启用 `content.tooltips` 后，指向外部站点的链接在悬停时会显示预览：

``` yaml
theme:
  features:
    - content.tooltips
```

悬停在 [这个 GitHub 链接](https://github.com/QQSHI13/docsforge) 上查看预览。

## Best practices

- 保持缩写简短且常用
- 用自己的话编写定义，不要照搬词典
- 在定义列表中对相关术语进行分组
- 在移动设备上测试工具提示（它们在触摸设备上的表现有所不同）

## Next steps

- [格式设置](formatting.md)
- [图标与表情](icons-emojis.md)
