---
icon: material/file-document-edit
---

# 创建站点

## 项目结构

``` { .sh .no-copy }
my-docs/
├── docsforge.yml      # 站点配置
├── docs/                # 你的文档
│   ├── index.md
│   └── ...
└── site/                # 构建输出（自动生成）
```

### `docs/` 目录

每个 `.md` 文件都会成为一个页面。子目录会成为章节。

``` { .sh .no-copy }
docs/
├── index.md
├── getting-started.md
├── guides/
│   ├── index.md
│   ├── install.md
│   └── configure.md
└── reference/
    ├── index.md
    └── api.md
```

### `docsforge.yml` 文件

最小配置：

```yaml
site_name: My Project
```

包含导航的配置：

```yaml
site_name: My Project

nav:
  - Home: index.md
  - Guides:
    - Installation: guides/install.md
    - Configuration: guides/configure.md
  - Reference: reference/index.md
```

## 编写内容

DocsForge 开箱即用支持**所有** Material 风格 Markdown。无需配置扩展。

### 提示框

```markdown
!!! note "注意"
    这是一个标注框。

??? warning "点击展开"
    这是可折叠内容。
```

### 数学公式

```markdown
行内：$E = mc^2$

块级：
$$\sum_{i=1}^n x_i$$
```

### 代码块

```markdown
```python
def hello():
    print("Hello")
```
```

### 表格、任务列表、脚注、定义列表

全部无需配置即可使用。完整语法请参见[参考](reference/index.md)。

## 构建

```bash
docsforge serve      # 带实时重载的开发服务器
docsforge build      # 构建到 site/ 目录
```

## 发布

DocsForge 生成静态 HTML。将 `site/` 部署到任意位置：

- **GitHub Pages**：参见[发布指南](publishing-your-site.md)
- **Netlify、Vercel**：拖拽 `site/` 文件夹
- **自己的服务器**：`rsync -av site/ server:/var/www/docs`
