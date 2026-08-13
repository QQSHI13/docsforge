---
icon: material/view-list
---

# 设置导航

DocsForge 提供丰富的导航选项。在 `docsforge.yml` 的 `theme.features` 下配置它们。

## 导航结构

默认情况下，DocsForge 会根据 `docs/` 目录结构构建导航：

``` { .sh .no-copy }
docs/
├── index.md
├── getting-started.md
├── setup/
│   ├── index.md
│   ├── colors.md
│   └── fonts.md
└── reference/
    ├── index.md
    └── markdown.md
```

这会生成：
- Home
- Getting started
- Setup（可展开章节）
  - Setup overview（索引页面）
  - Colors
  - Fonts
- Reference（可展开章节）
  - Reference overview（索引页面）
  - Markdown

## 顶层导航标签页

将顶层章节转换为标签页：

``` yaml
theme:
  features:
    - navigation.tabs
```

!!! tip
    与 `navigation.tabs.sticky` 组合使用，滚动时保持标签页可见：
    ``` yaml
    theme:
      features:
        - navigation.tabs
        - navigation.tabs.sticky
    ```

## 章节索引

使章节标题可点击，链接到其 `index.md`：

``` yaml
theme:
  features:
    - navigation.indexes
```

## 默认展开章节

``` yaml
theme:
  features:
    - navigation.expand
```

## 章节分组

将导航项分组为可折叠章节（默认启用）：

``` yaml
theme:
  features:
    - navigation.sections
```

## 返回顶部按钮

向下滚动时显示“返回顶部”按钮：

``` yaml
theme:
  features:
    - navigation.top
```

## 页脚导航

在每页底部添加上一页/下一页链接：

``` yaml
theme:
  features:
    - navigation.footer
```

## 目录

### 跟随活动锚点

滚动时高亮目录中的当前章节：

``` yaml
theme:
  features:
    - toc.follow
```

### 与导航整合

将目录移入侧边导航（用于窄屏布局）：

``` yaml
theme:
  features:
    - toc.integrate
```

## 自定义导航

在 `docsforge.yml` 中显式定义导航：

``` yaml
nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started.md
    - Quick start: quick-start.md
  - Setup:
    - setup/index.md
    - Colors: setup/colors.md
    - Fonts: setup/fonts.md
```

## 导航追踪

高亮导航中的当前页面：

``` yaml
theme:
  features:
    - navigation.tracking
```

默认启用。

## 完整导航示例

``` yaml
theme:
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - navigation.footer
    - navigation.tracking
    - toc.follow
```

## 下一步

- [设置站点搜索](setting-up-site-search.md)
- [设置站点分析](setting-up-site-analytics.md)
