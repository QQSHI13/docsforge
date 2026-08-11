# 故障排除

遇到问题？本页面涵盖最常见的问题及解决方法。每个部分列出症状、可能原因和分步解决方案。

---

## 构建错误

### 严格模式导致构建失败

**症状：** `docsforge build` 以 `ERROR: Strict mode is enabled` 退出，并指向某个文件。

**原因：** 严格模式将警告视为错误。常见触发因素包括缺失的内部链接、无效的 Markdown，或无法解析的文件。

**解决方法：**

1. 检查错误消息中的具体文件和行号。
2. 修复根本问题，或临时禁用严格模式以查看所有警告：

```yaml
# docsforge.yml
strict: false
```

3. 重新构建，记录所有警告，修复它们，然后重新启用 `strict: true`。

### 缺失文件或包含项

**症状：** 构建过程中出现 `File not found` 或 `Include file not found`。

**原因：** `!include` 或 `markdown_extensions` 中的路径引用了不存在的文件，或路径相对于错误目录。

**解决方法：**

- `docsforge.yml` 中的所有路径都相对于项目根目录（即 `docsforge.yml` 所在位置）。
- 检查文件是否存在于错误中显示的精确路径。
- 对于 `extra_css` 和 `extra_javascript`，路径相对于 `docs/` 目录：

```yaml
# docsforge.yml
extra_css:
  - stylesheets/extra.css   # 解析为 docs/stylesheets/extra.css
```

### 配置验证错误

**症状：** 出现 `Config value: 'foo'. Expected: str, received: int` 或类似的模式错误。

**原因：** `docsforge.yml` 中的某个值类型错误。

**解决方法：**

- 查看[参考](reference/index.md)了解预期类型。
- 常见错误：
  - `site_name` 必须是字符串，不能是列表
  - `nav` 项必须是字符串或嵌套列表，不能是整数
  - 插件选项必须与其文档化的模式匹配

---

## 搜索不工作

### 搜索索引未找到

**症状：** 搜索框对每个查询都显示“No results found”，或控制台显示 `search_index.json` 的 `404`。

**原因：** search 插件被禁用，或索引未在构建时生成。

**解决方法：**

1. 确保 search 插件已启用（默认启用）：

```yaml
plugins:
  - search
```

2. 运行 `docsforge build` —— 索引在构建时生成，不是实时生成。
3. 如果使用自定义 `site_url`，请验证基础路径是否正确，以便浏览器能获取 `search_index.json`。

### 常见词无结果

**症状：** 搜索框可用，但常见词没有返回结果。

**原因：** Lunr.js 排除常见停用词（`the`、`and`、`is`）并要求精确的词干匹配。

**解决方法：**

- 使用更具体的关键词（例如搜索 `strict mode` 而不是 `why is strict mode not working`）。
- 如果需要同义词全文搜索，请考虑第三方搜索集成。

### 搜索页面 404

**症状：** 直接访问 `/search.html` 返回 404。

**原因：** DocsForge 搜索是客户端覆盖层；没有独立的 `/search.html` 页面。

**解决方法：** 使用页眉中的搜索框。它在每个页面都可用。

---

## 导航问题

### 侧边栏不显示

**症状：** 左侧侧边栏为空或完全缺失。

**原因：** `docsforge.yml` 中没有 `nav` 部分，或所有页面都被隐藏。

**解决方法：**

1. 显式定义导航：

```yaml
nav:
  - Home: index.md
  - Guide: guide.md
```

2. 或将 `nav` 留空以依赖自动发现。如果侧边栏仍为空，请检查 `docs/` 目录是否包含 `.md` 文件。

### 章节无法展开

**症状：** 点击章节标题没有显示子项。

**原因：** 缺少章节页面，或章节被配置为链接而非容器。

**解决方法：**

- 确保每个章节都有 `index.md`（或对应文件）作为父页面：

```yaml
nav:
  - User Guide:
    - user-guide/index.md
    - user-guide/installation.md
    - user-guide/configuration.md
```

- 或使用 `navigation.expand` 默认展开所有章节：

```yaml
extra:
  features:
    - navigation.expand
```

### 活动状态错误

**症状：** 侧边栏中高亮了错误的页面，或没有高亮任何页面。

**原因：** `site_url` 或 `base_url` 配置错误，导致路径匹配失败。

**解决方法：**

- 将 `site_url` 设置为站点托管的确切 URL：

```yaml
site_url: https://username.github.io/repository-name/
```

- 对于本地 `docsforge serve`，会自动处理。

---

## 资源 404

### CSS 或 JS 未加载

**症状：** 页面渲染无样式，或交互功能（标签页、搜索、深色模式）不工作。

**原因：** 浏览器控制台显示 `.css` 或 `.js` 文件的 404 错误。

**解决方法：**

1. 打开 DevTools → Network 标签，检查哪些文件返回 404。
2. 如果路径错误，请验证 `site_url` 与部署 URL 匹配。
3. 对于 GitHub Pages 项目站点，请确保 `site_url` 包含仓库路径：

```yaml
site_url: https://username.github.io/repository-name/
```

4. 如果使用 CDN 或反向代理，请检查尾部斜杠和路径重写是否正确。

### 部署后图片损坏

**症状：** 图片在本地正常显示，但在部署的站点上显示为损坏链接。

**原因：** 使用绝对路径（`/images/foo.png`）或相对路径不正确。

**解决方法：**

- 使用相对于 Markdown 文件位置的相对路径：

```markdown
![替代文本](../images/foo.png)
```

- 或使用 `attr_list` 的页面相对语法：

```markdown
![替代文本](images/foo.png){ loading=lazy }
```

---

## 数学公式不渲染

### KaTeX 数学块不显示

**症状：** `$$...$$` 或 `\\(...\\)` 显示为原始文本而非渲染后的数学公式。

**原因：** `pymdownx.arithmatex` 扩展被禁用，或 KaTeX 资源被阻止。

**解决方法：**

1. 确保扩展已启用（新项目中默认启用）：

```yaml
markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
```

2. 使用正确语法：

```markdown
$$E = mc^2$$

行内：\\(E = mc^2\\)
```

3. 如果部署到受 CSP 限制的环境，请允许样式的 `unsafe-inline`，或切换到 MathJax（通过自定义 `extra_javascript` 配置）。

---

## 代码高亮不工作

### 无语法颜色

**症状：** 代码块以纯文本渲染，没有颜色。

**原因：** `pymdownx.highlight` 被禁用，或语言标识符缺失/无效。

**解决方法：**

1. 确保扩展已启用：

```yaml
markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
```

2. 在开头的反引号后指定有效语言：

```markdown
```python
def hello():
    print("hello")
```
```

3. 查看 [Pygments 词法分析器列表](https://pygments.org/docs/lexers/)获取正确的语言名称。

### 缺少语言支持

**症状：** 特定语言未被高亮。

**原因：** Pygments 没有该语言的词法分析器，或语言别名错误。

**解决方法：**

- 尝试替代名称（例如 `js` 与 `javascript`、`bash` 与 `shell`）。
- 对于自定义语言，使用 `text` 作为后备，并提交 issue 请求添加词法分析器。

---

## 深色模式不工作

### 切换按钮缺失或无效

**症状：** 页眉中没有月亮/太阳图标，或点击无效。

**原因：** 缺少 palette 配置，或自定义 CSS 覆盖了切换按钮。

**解决方法：**

1. 确保在 `docsforge.yml` 中配置了 palette：

```yaml
extra:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
```

2. 检查 `extra_css` 中是否有隐藏 `.md-header__button` 或覆盖 palette 颜色的规则。

---

## 博客问题

### 文章不显示

**症状：** 博客索引为空或返回 404。

**原因：** blog 插件被禁用，或文章不在预期目录中。

**解决方法：**

1. 确保 blog 插件已启用：

```yaml
plugins:
  - blog
```

2. 将文章放在 `docs/blog/posts/` 目录下，文件名为 `YYYY-MM-DD-title.md`。

3. 在每篇文章的元数据头中包含 `date`：

```markdown
---
date: 2024-01-15
---

# My Post Title
```

### RSS 未生成

**症状：** 构建输出中没有 `feed_rss_created.xml`。

**原因：** RSS 生成是可选的，需要额外配置。

**解决方法：**

```yaml
plugins:
  - blog:
      blog_dir: blog
      blog_toc: true
      post_date_format: full
      archive_date_format: yyyy
      archive_url_date_format: yyyy/MM
      post_url_date_format: yyyy/MM/dd
      post_url_format: "{date}/{slug}"
      archive_url_format: "{date}/archive.html"
      authors: true
      authors_file: "{blog}/.authors.yml"
      draft: true
      draft_on_serve: true
      draft_if_future_date: true
      pagination: true
      pagination_if_single_page: true
      pagination_keep_content: true
      categories: true
      categories_name: Categories
      categories_toc: true
      categories_url_format: "category/{slug}.html"
      pagination_url_format: "page/{page}.html"
      allowed_authors: all
      sort_by: date
      sort_order: descending
      show_total: true
      show_category: true
```

具体而言，要确保 `blog` 插件已启用并设置了 `post_url_format`。RSS 订阅源会自动在 `blog/` 输出目录中生成。

---

## 性能问题

### 构建缓慢

**症状：** 小型站点上 `docsforge build` 需要数分钟。

**原因：** 未优化的大图片、大量 Mermaid/TikZ 图表，或不必要的文件复制。

**解决方法：**

1. 启用压缩：

```yaml
plugins:
  - minify
```

2. 在加入 `docs/` 之前优化图片（使用 WebP 或压缩后的 PNG）。
3. 对于 TikZ 图表，预先编译并提交 SVG，而不是每次构建都重新生成。
4. 使用 `.gitignore` 模式从 `docs/` 中排除大型二进制文件——即使未使用，它们也会被复制到 `site/`。

### 站点输出过大

**症状：** `site/` 目录有数百兆字节。

**原因：** 未优化的图片、视频文件或大型 PDF 位于 `docs/` 中。

**解决方法：**

- 在 `docsforge.yml` 中使用 `exclude` 防止复制不必要的文件：

```yaml
exclude:
  - "*.mp4"
  - "*.pdf"
  - drafts/
```

- 将大型资源存储在其他地方（CDN、Git LFS）并链接到它们。

---

## 部署问题

### GitHub Pages 每个页面都 404

**症状：** 只有 `index.html` 可用；所有其他页面都返回 404。

**原因：** GitHub Pages 项目站点从子目录（`/repo-name/`）提供服务，但 `site_url` 缺失或错误。

**解决方法：**

```yaml
# docsforge.yml
site_url: https://username.github.io/repository-name/
```

### GitHub Pages 上 CSS/JS 损坏

**症状：** 站点加载但没有样式。

**原因：** 绝对资源路径假设根路径（`/`），但站点位于子目录中。

**解决方法：** 部署到子目录时始终设置 `site_url`。DocsForge 会根据该值重写资源路径。

### CNAME 不工作

**症状：** 自定义域名显示 404 或 GitHub Pages 默认域名。

**原因：** `CNAME` 文件缺失、位置错误，或 DNS 未配置。

**解决方法：**

1. 创建 `docs/CNAME`（无文件扩展名，全部大写）：

```
docs.example.com
```

2. 配置 DNS，添加 CNAME 记录指向 `username.github.io`（项目站点）或 `username.github.io`（用户/组织站点）。
3. 等待 DNS 传播（最长 24 小时）。

---

## Python 和环境问题

### 版本要求

**症状：** `pip install docsforge` 失败并显示依赖错误。

**原因：** Python 版本低于 3.10，或 pip 版本过旧。

**解决方法：**

```bash
# 检查 Python 版本
python --version  # 必须 3.10 或更高

# 升级 pip
pip install --upgrade pip

# 在全新的虚拟环境中安装
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install docsforge
```

### Pip 冲突

**症状：** `docsforge build` 失败并显示 `ImportError` 或 `ModuleNotFoundError`。

**原因：** 全局安装的 `markdown`、`jinja2` 或其他依赖版本冲突。

**解决方法：**

1. 始终使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install --force-reinstall docsforge
```

2. 如果使用 Conda，请在 Conda 环境中通过 pip 安装：

```bash
conda create -n docsforge python=3.11
conda activate docsforge
pip install docsforge
```

---

## 常见问题

??? question "为什么 `docsforge serve` 显示旧内容？"

    开发服务器会监视文件并自动重建，但可能会遗漏快速变更。**解决方法：** 保存文件，等待 1–2 秒，然后刷新。如果仍然陈旧，停止并重新启动 `docsforge serve`。

??? question "DocsForge 可以与 Jupyter notebook 一起使用吗？"

    可以。使用 `mkdocs-jupyter`（第三方插件）或用 `jupyter nbconvert --to markdown` 将 notebook 导出为 Markdown。将 `.md` 文件放入 `docs/` 目录并添加到 `nav`。

??? question "如何添加自定义 404 页面？"

    创建 `docs/404.md`。DocsForge 会自动将其用作回退页面。你可以像任何其他页面一样自定义内容和样式。

??? question "为什么我的 `!!! note` 提示框没有渲染？"

    `admonition` 扩展必须启用（默认启用）。确保使用正确语法，内容缩进四个空格：

    ```markdown
    !!! note
        This is the content.
    ```

    如果内容没有缩进，它会显示在提示框外部。

??? question "如何让页面不参与搜索？"

    在页面元数据中添加 `search: false`：

    ```markdown
    ---
    search: false
    ---

    # Secret Page
    ```

??? question "可以不带 `site_url` 部署到子目录吗？"

    技术上可以，但强烈建议设置 `site_url`。没有它，绝对 URL、RSS 订阅源、搜索和部分插件可能会损坏。部署到子目录时始终设置 `site_url`。

??? question "为什么构建失败并显示 `jinja2.exceptions.TemplateNotFound`？"

    这通常意味着自定义主题目录缺失或配置错误。检查 `docsforge.yml` 中的 `theme.custom_dir`，确保路径指向包含有效 Jinja2 模板的现有目录。

??? question "如何调试插件问题？"

    使用调试日志运行构建：

    ```bash
    docsforge build
    ```

    如果需要更多细节，请在环境中将日志级别设置为 `DEBUG`。如果某个特定插件失败，请尝试临时禁用它以隔离问题。

??? question "DocsForge 支持多语言站点吗？"

    原生多语言支持尚未内置。常见变通方案：

    - 为每种语言维护独立的 `docsforge.yml` 文件并独立构建。
    - 使用 `mkdocs-static-i18n` 等第三方翻译插件。
    - 使用语言子目录组织内容，并通过自定义导航切换。

??? question "如何升级 DocsForge？"

    ```bash
    pip install --upgrade docsforge
    ```

    升级主版本前请查看[更新日志](changelog/index.md)了解破坏性变更。

??? question "在哪里报告 bug 或请求功能？"

    在 [GitHub 仓库](https://github.com/docsforge/docsforge) 上提交 issue。请包含你的 `docsforge.yml`、Python 版本和完整的错误输出。

---

## 仍然卡住？

如果以上方法都不起作用：

1. 运行 `docsforge build` 并捕获完整输出。
2. 对照[参考](reference/index.md)检查你的 `docsforge.yml`。
3. 在现有 [GitHub issues](https://github.com/docsforge/docsforge/issues) 中搜索错误信息。
4. 提交新 issue，并提供：
   - `docsforge.yml`
   - Python 版本（`python --version`）
   - DocsForge 版本（`docsforge --version`）
   - 确切的错误信息
   - 复现步骤
