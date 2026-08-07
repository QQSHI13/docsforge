# 自定义指南

DocsForge 提供了超越基础配置的强大自定义选项。本指南涵盖了用于定制网站外观、行为和功能的高级技术。

---

## 自定义 CSS

通过 `docsforge.yml` 中的 `extra_css` 设置添加自定义样式表：

```yaml
extra_css:
  - stylesheets/extra.css
```

创建 `docs/stylesheets/extra.css`：

```css
/* 自定义品牌色 */
:root {
  --md-primary-fg-color: #4051b5;
  --md-primary-fg-color--light: #5d6cc0;
  --md-primary-fg-color--dark: #2e3b8e;
}

/* 自定义标题字体 */
.md-typeset h1,
.md-typeset h2 {
  font-family: 'Georgia', serif;
  font-weight: 700;
}

/* 更宽的内容区域 */
@media screen and (min-width: 76.25em) {
  .md-content {
    max-width: 900px;
  }
}
```

### 覆盖主题变量

DocsForge 使用 CSS 自定义属性进行主题设置。在你的自定义 CSS 中覆盖它们：

| 变量 | 说明 |
|----------|-------------|
| `--md-primary-fg-color` | 主色 |
| `--md-primary-fg-color--light` | 浅色变体 |
| `--md-primary-fg-color--dark` | 深色变体 |
| `--md-accent-fg-color` | 强调色 |
| `--md-typeset-color` | 正文文本颜色 |
| `--md-typeset-a-color` | 链接颜色 |
| `--md-code-fg-color` | 代码文本颜色 |
| `--md-code-bg-color` | 代码背景 |
| `--md-default-fg-color` | 默认前景色 |
| `--md-default-bg-color` | 默认背景色 |

---

## 自定义 JavaScript

通过 `extra_javascript` 添加自定义脚本：

```yaml
extra_javascript:
  - javascripts/extra.js
```

创建 `docs/javascripts/extra.js`：

```javascript
// 页面加载时的自定义行为
document.addEventListener('DOMContentLoaded', function() {
  // 为所有表格添加复制按钮
  const tables = document.querySelectorAll('.md-typeset table');
  tables.forEach(table => {
    const button = document.createElement('button');
    button.className = 'md-clipboard';
    button.innerHTML = 'Copy';
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(table.innerText);
    });
    table.parentElement.insertBefore(button, table);
  });
});
```

### 接入 DocsForge 事件

```javascript
// 监听搜索事件
window.addEventListener('docsforge-search', function(e) {
  console.log('Search query:', e.detail.query);
});

// 监听主题切换
window.addEventListener('docsforge-theme', function(e) {
  console.log('Theme changed to:', e.detail.scheme);
});
```

---

## 自定义模板

通过创建 `overrides` 目录并在 `docsforge.yml` 中引用它来覆盖内置模板：

```yaml
theme:
  custom_dir: overrides
```

### 覆盖局部模板

创建 `docs/overrides/partials/copyright.html`：

```html
<!-- 自定义版权声明 -->
<div class="md-copyright">
  <strong>My Company</strong> — 
  <a href="{{ config.repo_url }}" target="_blank" rel="noopener">
    {{ config.repo_name }}
  </a>
</div>
```

### 覆盖基础模板

创建 `docs/overrides/main.html` 以扩展基础模板：

```html
{% extends "base.html" %}

{% block extrahead %}
  {{ super() }}
  <meta property="og:image" content="{{ config.site_url }}assets/social-card.png">
{% endblock %}

{% block announce %}
  <div class="announcement">
    :material-party-popper: New version released! <a href="/changelog">See what's new</a>
  </div>
{% endblock %}
```

### 可用的块

| 块 | 说明 |
|-------|-------------|
| `extrahead` | 在 `<head>` 标签内 |
| `announce` | 公告横幅 |
| `header` | 网站页眉 |
| `tabs` | 导航标签 |
| `content` | 主内容区域 |
| `footer` | 页面页脚 |
| `outdated` | 过时版本提示 |

---

## 自定义提示框

使用 CSS 定义自定义提示框类型：

```css
/* 品牌色的自定义 "tip" 提示框 */
.md-typeset .admonition.tip {
  border-color: #4051b5;
}

.md-typeset .admonition.tip > .admonition-title {
  background-color: rgba(64, 81, 181, 0.1);
  color: #4051b5;
}

.md-typeset .admonition.tip > .admonition-title::before {
  background-color: #4051b5;
  -webkit-mask-image: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>');
  mask-image: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>');
}
```

在 Markdown 中使用：

```markdown
!!! tip "自定义提示"
    This uses your brand color!
```

---

## 自定义图标和 Logo

### SVG Logo

使用 SVG 以获得任意尺寸下的清晰渲染：

```yaml
theme:
  logo: assets/logo.svg
```

SVG 应经过优化，并包含 `viewBox` 以实现正确缩放。

### 自定义图标定义

在 `extra.css` 中定义自定义图标：

```css
.md-icon--custom::after {
  content: "";
  display: inline-block;
  width: 1em;
  height: 1em;
  background-image: url("assets/custom-icon.svg");
  background-size: contain;
  vertical-align: middle;
}
```

---

## 自定义字体

### 自托管字体

将字体文件放在 `docs/assets/fonts/` 中，并在 CSS 中定义：

```css
@font-face {
  font-family: 'CustomFont';
  src: url('../assets/fonts/CustomFont.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

:root {
  --md-text-font: 'CustomFont', 'Roboto', sans-serif;
}
```

---

## 自定义 404 页面

创建 `docs/overrides/404.html`：

```html
{% extends "base.html" %}

{% block content %}
  <div class="md-content__inner">
    <h1>404 — Page Not Found</h1>
    <p>The page you requested doesn't exist.</p>
    <a href="{{ nav.homepage.url | url }}" class="md-button md-button--primary">
      Go Home
    </a>
  </div>
{% endblock %}
```

---

## 性能调优

### 图片懒加载

图片默认启用懒加载。对于首屏图片，请使用 `loading="eager"`：

```markdown
![Hero image](hero.png){ loading=eager }
```

### 图片优化

在将图片添加到 `docs/` 之前对其进行优化：

```bash
# 转换为 WebP 以减小体积
ffmpeg -i image.png image.webp

# 或者使用 ImageMagick
convert image.png -quality 85 image.webp
```

### 预加载关键资源

```html
{% block extrahead %}
  {{ super() }}
  <link rel="preload" href="{{ 'assets/fonts/CustomFont.woff2' | url }}" as="font" type="font/woff2" crossorigin>
{% endblock %}
```

---

## 无障碍访问

### 颜色对比度

确保你的自定义颜色符合 WCAG AA 标准（普通文本 4.5:1，大文本 3:1）。使用对比度检查器进行测试。

### 键盘导航

DocsForge 开箱即用地支持键盘导航。自定义交互元素应处理 `Tab`、`Enter` 和 `Escape` 键。

### ARIA 标签

```html
<button class="md-button" aria-label="Close announcement">
  <span class="md-icon">close</span>
</button>
```

---

## 多语言网站

DocsForge 包含通过 `material/i18n` 内置的国际化插件。详情请参见 [国际化设置](../setup/i18n.md)。

如果内置插件不符合你的工作流程，你也可以使用以下替代方案之一：

### 选项 1：为每种语言构建单独的网站

为每种语言维护一个 `docsforge.yml` 并独立构建：

```
docs/
├── en/
│   └── index.md
├── de/
│   └── index.md
└── fr/
    └── index.md
```

使用一个小型构建脚本将每种语言输出到单独的子目录。

### 选项 2：使用第三方 i18n 插件

安装与 MkDocs 兼容的 i18n 插件，并在 `plugins:` 下声明：

```yaml
plugins:
  - i18n:
      languages:
        - locale: en
          name: English
          default: true
        - locale: de
          name: Deutsch
        - locale: fr
          name: Français
```

!!! warning "兼容性"
    第三方 MkDocs 插件可能需要针对 DocsForge 进行调整。在将其用于生产环境之前，请进行彻底测试。

---

## 分析集成

### Google Analytics 4

```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

### Plausible

```yaml
extra:
  analytics:
    provider: plausible
    property: docs.example.com
```

### 自定义分析

```html
{% block extrahead %}
  {{ super() }}
  <script async src="https://analytics.example.com/script.js" data-site="YOUR_SITE_ID"></script>
{% endblock %}
```

---

## 社交卡片

DocsForge 不会自动生成社交卡片图片，但它会设置基本的 OpenGraph 标签。如需自定义卡片图片，请在模板覆盖中手动添加：

```html
{% block extrahead %}
  {{ super() }}
  <meta property="og:title" content="{{ page.title | default(config.site_name) }}">
  <meta property="og:description" content="{{ page.meta.description | default(config.site_description) }}">
  <meta property="og:image" content="{{ config.site_url }}assets/social-card.png">
  <meta name="twitter:card" content="summary_large_image">
{% endblock %}
```

---

## 构建钩子

`hooks` 是类似迷你插件的 Python 模块。列在 `hooks:` 下的每个文件都会被导入，并可以实现 `on_pre_build` 和/或 `on_post_build` 事件。

```yaml
hooks:
  - scripts/hooks.py
```

创建 `docs/scripts/hooks.py`：

```python
import os


def on_pre_build(*, config):
    """在 DocsForge 开始构建页面之前运行。"""
    print("Pre-build hook running...")


def on_post_build(*, config):
    """在 DocsForge 写入站点目录之后运行。"""
    print(f"Site built at: {config.site_dir}")
```

!!! note "Shell 脚本"
    如果你需要运行 shell 命令，请从 Python 钩子中使用 `subprocess.run(["..."])` 调用。

## 自定义插件

对于需要跨多个事件或需要自身配置的功能，请编写一个完整的插件，通过继承 `docsforge.core.plugin_base.BasePlugin` 实现。

```python
from docsforge.config_base import Config
from docsforge.config_options import Type
from docsforge.core.plugin_base import BasePlugin


class MyPluginConfig(Config):
    enabled = Type(bool, default=True)


class MyPlugin(BasePlugin[MyPluginConfig]):
    def on_page_markdown(self, markdown, *, page, config, files):
        if not self.config.enabled:
            return markdown
        return markdown.replace("{{year}}", "2026")
```

在 `docsforge.yml` 中注册插件：

```yaml
plugins:
  - my_plugin:
      enabled: true
```

DocsForge 使用与 MkDocs 相同的事件名称（`on_page_markdown`、`on_page_content`、`on_post_build` 等）。如果你要迁移 MkDocs 插件，请将导入从 `mkdocs.plugins` 改为 `docsforge.core.plugin_base`，并使用 DocsForge 的 `Config` 类作为插件选项。
