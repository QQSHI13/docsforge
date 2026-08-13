---
icon: material/format-font
---

# 更改字体

DocsForge 开箱即用地支持 Google Fonts。在 `docsforge.yml` 中的 `theme.font` 键下配置字体。

## 配置

### Google Fonts

``` yaml
theme:
  font:
    text: Roboto
    code: Roboto Mono
```

### 支持的字体字重

DocsForge 会自动加载 regular（400）和 bold（700）字重。对于需要不同字重名称的字体族：

``` yaml
theme:
  font:
    text: "Open Sans"  # 多词名称需要引号
    code: "Fira Code"
```

### 禁用字体加载

如果你想使用系统字体或自行加载字体：

``` yaml
theme:
  font: false
```

## 推荐字体搭配

<div class="grid cards" markdown>

-   **Roboto + Roboto Mono**

    ---

    默认搭配。简洁、现代，非常适合技术文档。

-   **Inter + JetBrains Mono**

    ---

    Inter 针对屏幕可读性进行了优化。JetBrains Mono 具有连字，并能清晰区分相似字符。

-   **Open Sans + Source Code Pro**

    ---

    友好且亲切。非常适合面向社区的项目。

-   **Lato + Fira Code**

    ---

    温暖而专业。Fira Code 增加了编程连字。

</div>

## 自定义字体

要使用 Google Fonts 上没有的字体，请通过自定义 CSS 加载：

``` yaml
extra_css:
  - assets/stylesheets/custom.css
```

``` css title="docs/assets/stylesheets/custom.css"
@font-face {
  font-family: "My Font";
  src: url("../fonts/my-font.woff2") format("woff2");
  font-weight: 400;
}

:root {
  --md-text-font: "My Font";
}
```

将你的字体文件放在 `docs/assets/fonts/` 目录中。

## 下一步

- [Changing the colors](changing-the-colors.md)
- [Changing the language](changing-the-language.md)
