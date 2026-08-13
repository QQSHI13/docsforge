---
icon: material/lightbulb-on-outline
---

# 设计理念

DocsForge 的诞生源于我们相信文档应该**尽可能简单**。

## 问题所在

现代文档工具需要太多配置。本应是“编写 Markdown，获得网站”的事情，往往变成了：

- 配置 10 多个 Markdown 扩展
- 单独安装主题
- 逐个添加插件
- 为数学公式设置 CDN 脚本
- 为语法高亮配置客户端 JS
- 排查更新后某处出错的原因

## 我们的原则

### 1. 核心功能零配置

**你需要的所有功能都无需配置即可工作。**

编写 `$$...$$` → 渲染数学公式。编写 `!!! note` → 显示提示框。编写 ` ```python ` → 代码高亮。所有 36 个 Markdown 扩展和 8 个核心插件都会默认加载。

你只需配置想要自定义的部分，而不是为了让某些功能存在。

### 2. 自包含

**执行 `pip install docsforge` 后，你就拥有了所有内容。**

主题、所有插件、所有扩展、KaTeX、字体和 Pygments 都打包在包内。外部资源在构建时获取；读者端不会调用 CDN。支持离线使用。

### 3. 稳定

**十年后，你的文档构建方式仍然相同。**

因为所有内容都已打包在包中，固定包版本就固定了整个工具链。没有传递依赖带来的意外。

### 4. Material 品质

**DocsForge 是更简单的 Material for MkDocs。**

我们没有重新发明主题。我们采用了世界上最流行的文档主题，并让它无需配置即可工作。你获得相同的专业外观、相同的响应式布局、相同的深色模式——只是省去了配置步骤。

## 我们移除了什么

| 功能 | 移除原因 |
|---------|-------------|
| `typeset` | 用户可以直接使用 Unicode |
| `optimize` | 需要外部 `pngquant` 二进制文件 |
| `social` | 需要 Pillow + CairoSVG —— 现已作为可选插件回归（`plugins: [social]`） |
| `projects` | 小众的多项目功能 |
| `offline` | privacy 插件已覆盖大部分使用场景 |
| `group` | 插件编排器（小众） |

## 我们改变了什么

| 之前（Material/MkDocs） | 之后（DocsForge） |
|---------------------------|-------------------|
| 配置文件 `mkdocs.yml` | `docsforge.yml` |
| 通过 `mkdocs.themes` 设置主题 | `docsforge.themes` |
| 手动列出所有扩展 | 默认加载 36 个 |
| 手动列出所有插件 | 默认加载 8 个 |
| 用 `extra_javascript` 引入 KaTeX | KaTeX 已内置，零配置 |
| 客户端 JS 高亮 | 构建时使用 Pygments |

## 我们的目标

> `pip install docsforge`，编写 Markdown，完成。
