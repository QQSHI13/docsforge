# 入门

DocsForge 是一款自包含的文档引擎。`pip install`，编写 Markdown，构建完成。

## 安装

```bash
pip install docsforge
```

需要 **Python 3.10+**。

## 快速开始

```bash
# 交互式创建新项目
docsforge
cd my-docs

# 启动开发服务器
docsforge serve

# 构建生产版本
docsforge build
```

## 项目内容

运行 `docsforge` 创建项目后，目录结构如下：

``` { .sh .no-copy }
my-docs/
├── docsforge.yml    # 站点配置
├── docs/
│   └── index.md     # 首页
└── site/            # 构建输出
```

## 配置

最小的有效 `docsforge.yml`：

```yaml
site_name: My Project
```

就这些。所有插件、扩展和主题设置都使用合理的默认值。仅在需要自定义时添加配置。

## 关键默认项

| 功能 | 默认值 |
|---------|---------|
| 主题 | Material（内置） |
| 插件 | search、tags、blog、info、meta、minify、privacy、i18n |
| Markdown 扩展 | 共 36 个 —— 全部 pymdownx + python-markdown（另有 3 个内置：toc、tables、fenced_code） |
| 数学公式 | KaTeX（已内置，`$$...$$` 可用） |
| 代码高亮 | Pygments（彩色语法） |
| 深色模式 | 页眉中的浅色/深色切换 |
| 字体 | 自托管（privacy 插件下载 Google Fonts） |
| 图表 | TikZ 支持（`.tex` → SVG，构建时编译；需要 LaTeX 工具链） |
| 离线 | 服务工作者缓存所有资源 |

## 内置功能

### :material-file-document-edit: 文档
- 使用 36 个扩展编写 Markdown
- 提示框、标签页、任务列表、脚注
- Mermaid 和 TikZ 图表
- KaTeX 数学渲染
- Pygments 代码高亮

### :material-magnify: 发现
- 全文搜索（Lunr.js）
- 标签和标签页
- 分节和标签页导航
- 目录

### :material-palette: 主题
- 支持浅色/深色模式的 Material 主题
- 可自定义颜色和字体
- 16,500+ 图标（Material、Lucide、FontAwesome、Octicons、Simple Icons）

### :material-file-document-edit: 博客
- 作者资料
- 分类和标签
- 归档页面
- 分页
- RSS 订阅源

### :material-web: 发布
- 静态 HTML 输出
- 可直接部署到 GitHub Pages
- 支持离线使用的 PWA
- 压缩后的 HTML/CSS/JS

## 下一步

- [创建站点](creating-your-site.md)
- [设置博客](blogging.md)
- [参考](reference/index.md)
