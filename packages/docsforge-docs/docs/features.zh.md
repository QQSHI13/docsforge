# 功能特性

DocsForge 包含编写和发布文档所需的一切。无需额外安装，无需额外配置。

## 核心功能

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } &nbsp; **零依赖**

    ---

    `pip install docsforge` 即可获得文档引擎、Material 主题、全部插件、全部 Markdown 扩展、KaTeX 数学公式、Pygments 高亮、字体、图标和服务工作者。无需安装其他任何东西。

-   :material-rocket-launch:{ .lg .middle } &nbsp; **零配置**

    ---

    几秒钟内即可拥有一个可运行的站点。7 个插件和 31 个 Markdown 扩展会自动加载。仅自定义你需要的部分。

-   :material-theme-light-dark:{ .lg .middle } &nbsp; **浅色与深色模式**

    ---

    自动检测系统偏好，同时支持手动切换。两种模式都可以使用你的品牌颜色完全自定义。

-   :material-magnify:{ .lg .middle } &nbsp; **全文搜索**

    ---

    由 Lunr.js 驱动的客户端搜索。无需外部服务，无需后端。支持离线使用。

-   :material-function-variant:{ .lg .middle } &nbsp; **数学公式渲染**

    ---

    编写 `$$...$$` 即可用 KaTeX 渲染。读者端无需调用 CDN，无需 `extra_javascript`，无需配置。

-   :material-code-tags:{ .lg .middle } &nbsp; **语法高亮**

    ---

    代码块在构建时使用 Pygments 颜色渲染。支持所有主流语言。

-   :material-chart-bar:{ .lg .middle } &nbsp; **TikZ 图表**

    ---

    直接在 Markdown 中编写 TikZ 图表。构建时自动编译为 SVG。无需安装 LaTeX。

-   :material-rss-box:{ .lg .middle } &nbsp; **博客**

    ---

    内置博客插件，支持作者、分类、标签、归档、分页和 RSS 订阅源。

-   :material-wifi-off:{ .lg .middle } &nbsp; **离线支持**

    ---

    服务工作者缓存所有资源。无需互联网连接即可访问文档。

</div>

## Markdown 扩展

全部默认启用。无需配置。

| 分类 | 扩展 |
|----------|-----------|
| **结构** | `toc`、`tables`、`fenced_code`、`def_list`、`footnotes`、`md_in_html`、`meta` |
| **文本** | `admonition`、`abbr`、`attr_list`、`nl2br`、`sane_lists`、`wikilinks` |
| **pymdownx** | `arithmatex`、`betterem`、`caret`、`critic`、`details`、`emoji`、`escapeall`、`extra`、`fancylists`、`highlight`、`inlinehilite`、`keys`、`magiclink`、`mark`、`pathconverter`、`progressbar`、`quotes`、`saneheaders`、`smartsymbols`、`snippets`、`striphtml`、`superfences`、`tabbed`、`tasklist`、`tilde` |

## 插件

全部默认启用。无需 `plugins:` 配置。

| 插件 | 作用 |
|--------|-----------|
| `blog` | 博客，支持作者、分类、归档、分页、RSS |
| `info` | 提示框标注（note、tip、warning、danger） |
| `meta` | OpenGraph 元数据 |
| `minify` | 压缩 HTML/CSS/JS 输出 |
| `privacy` | 自托管外部资源（Google Fonts、CDN 脚本） |
| `search` | 基于 Lunr.js 的全文搜索 |
| `tags` | 标签系统及标签页面 |

## PWA / 离线

每个构建的站点都包含一个服务工作者，它会：

- **缓存 HTML 页面** —— 网络优先，后台更新缓存
- **缓存资源** —— CSS、JS、字体、图片从缓存提供，加快速度
- **版本化更新** —— 每次构建生成唯一的服务工作者哈希，强制浏览器刷新
- **自动清理** —— 新版本激活时清除旧缓存

## 发布

DocsForge 生成静态 HTML。将 `site/` 部署到任意位置：

- **GitHub Pages** —— [即用型工作流](publishing-your-site.md)
- **Netlify、Vercel** —— 直接拖拽
- **自己的服务器** —— `rsync site/ server:/var/www/docs`
