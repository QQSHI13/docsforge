# 图标与表情

DocsForge 开箱即用，内置 **8,000 多个 Material Design 图标** 和 **3,000 多个 Twemoji 表情**。无需外部下载。

---

## 图标

### 语法

在 Markdown 的任何位置使用 `:material-icon-name:` 语法：

``` markdown
:material-heart: I love DocsForge!
```

:material-heart: I love DocsForge!

---

### 查找图标

浏览完整的 [Material Design Icons](https://materialdesignicons.com/) 库。常见分类：

| 分类 | 示例 |
|----------|----------|
| 导航 | :material-home: `:material-home:` :material-arrow-right: `:material-arrow-right:` :material-menu: `:material-menu:` |
| 操作 | :material-download: `:material-download:` :material-upload: `:material-upload:` :material-refresh: `:material-refresh:` |
| 内容 | :material-file-document: `:material-file-document:` :material-image: `:material-image:` :material-code-braces: `:material-code-braces:` |
| 状态 | :material-check-circle: `:material-check-circle:` :material-alert-circle: `:material-alert-circle:` :material-information: `:material-information:` |
| 硬件 | :material-memory: `:material-memory:` :material-harddisk: `:material-harddisk:` :material-server: `:material-server:` |
| 社交 | :material-github: `:material-github:` :material-twitter: `:material-twitter:` :material-web: `:material-web:` |

!!! tip "图标搜索"
    使用 [Material Icons 搜索](https://materialdesignicons.com/) 查找精确名称。将空格替换为连字符：`arrow-right` → `:material-arrow-right:`

---

### 使用图标

#### 在文本中

``` markdown
Click the :material-cog: settings icon to configure.
```

Click the :material-cog: settings icon to configure.

#### 在按钮和链接中

``` markdown
[Get started :material-arrow-right:](getting-started.md)

[Download :material-download:](https://example.com)
```

[Get started :material-arrow-right:](../getting-started.md)

[Download :material-download:](https://example.com)

#### 在提示框中

图标会根据提示框类型自动显示在标题中：

``` markdown
!!! tip "带图标的提示"
    此提示框会自动显示图标。
```

!!! tip "带图标的提示"
    此提示框会自动显示图标。

#### 在标题中

``` markdown
## :material-rocket: 入门指南
```

## :material-rocket: 入门指南

#### 在表格中

``` markdown
| Feature | Status |
|---------|--------|
| :material-check: Working | :material-check-circle: Complete |
| :material-wrench: In progress | :material-alert: Attention needed |
```

| Feature | Status |
|---------|--------|
| :material-check: Working | :material-check-circle: Complete |
| :material-wrench: In progress | :material-alert: Attention needed |

---

### 图标尺寸

应用 CSS 类来调整尺寸（需要自定义 CSS）：

``` markdown
:material-heart:{ .twemoji .lg } Large heart
:material-heart:{ .twemoji .2x } Double size
:material-heart:{ .twemoji .3x } Triple size
```

### 自定义图标颜色

``` markdown
:material-heart:{ .red } Red heart
:material-heart:{ .blue } Blue heart
```

（需要定义 `.red` 和 `.blue` CSS 类。）

---

## 表情

### 标准短代码

使用标准表情短代码：

``` markdown
:smile: :thumbsup: :rocket: :fire: :star: :warning: :heart: :tada:
```

:smile: :thumbsup: :rocket: :fire: :star: :warning: :heart: :tada:

### 文档中常用的表情

| 表情 | 短代码 | 使用场景 |
|-------|-----------|----------|
| :rocket: | `:rocket:` | 新功能、发布 |
| :warning: | `:warning:` | 警告、注意 |
| :star: | `:star:` | 收藏、推荐 |
| :fire: | `:fire:` | 热门话题、趋势 |
| :bulb: | `:bulb:` | 想法、提示 |
| :bug: | `:bug:` | 缺陷、问题 |
| :white_check_mark: | `:white_check_mark:` | 已完成 |
| :x: | `:x:` | 失败、移除 |
| :memo: | `:memo:` | 文档 |
| :gear: | `:gear:` | 配置 |

---

## Font Awesome 图标

Font Awesome 品牌图标同样可用：

``` markdown
:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker
:fontawesome-brands-linux: Linux
:fontawesome-brands-windows: Windows
:fontawesome-brands-apple: Apple
:fontawesome-brands-js: JavaScript
:fontawesome-brands-react: React
:fontawesome-brands-vuejs: Vue
:fontawesome-brands-html5: HTML5
:fontawesome-brands-css3: CSS3
```

:fontawesome-brands-github: GitHub
:fontawesome-brands-python: Python
:fontawesome-brands-docker: Docker
:fontawesome-brands-linux: Linux
:fontawesome-brands-windows: Windows
:fontawesome-brands-apple: Apple
:fontawesome-brands-js: JavaScript
:fontawesome-brands-react: React
:fontawesome-brands-vuejs: Vue
:fontawesome-brands-html5: HTML5
:fontawesome-brands-css3: CSS3

!!! note "Font Awesome regular 与 solid"
    品牌图标（`fontawesome-brands-*`）始终可用。Regular 和 solid 变体可能需要额外配置。

---

## 自定义图标

### 添加自定义图标

将 SVG 图标放入 `docs/assets/icons/` 并引用：

``` yaml
theme:
  icon:
    logo: assets/icons/my-logo.svg
    repo: assets/icons/custom-repo.svg
```

### 在 Markdown 中使用自定义图标

``` markdown
:custom-icon-name:
```

需要在 `docsforge.yml` 中注册该图标：

``` yaml
theme:
  icon:
    admonition:
      note: custom-icon-name
```

---

## 配置

图标支持默认启用。配置如下：

``` yaml
markdown_extensions:
  - pymdownx.emoji:
      emoji_generator: !!python/name:docsforge.emoji.to_svg
      emoji_index: !!python/name:docsforge.emoji.twemoji
```

!!! warning "请勿更改"
    DocsForge 自行打包所有表情和图标资源。更改生成器或索引可能会破坏离线支持。

---

## 最佳实践

- 谨慎使用图标——过多会让文本难以阅读
- 专业文档优先使用 Material 图标，而非表情
- 表情适合非正式内容、发布说明或社交卡片
- 为了可访问性，始终为图标附带文本标签
- 测试图标在浅色和深色主题下的渲染效果
- 避免在表格标题中使用图标——请使用文本

---

## 下一步

- [图片](images.zh.md)
- [列表](lists.zh.md)
- [数据表](data-tables.zh.md)
