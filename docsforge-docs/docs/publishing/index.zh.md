# 发布您的站点

DocsForge 会构建静态 HTML，可部署到任何 Web 服务器或静态托管平台。本章节涵盖将您的文档上线所需的全部内容。

## 快速部署

最快的部署方式：

| 平台 | 方式 | 时间 |
|----------|--------|------|
| **GitHub Pages** | GitHub Actions | 5 分钟 |
| **Netlify** | 拖拽 `site/` 文件夹 | 1 分钟 |
| **Render** | Git 推送 | 2 分钟 |
| **Surge.sh** | `surge site/` | 30 秒 |

## 本章节内容

- [**使用指南**](usage.md) —— 日常 DocsForge 命令、配置和内容功能
- [**迁移指南**](migration.md) —— 从 MkDocs/Material 迁移到 DocsForge、功能对比、分步迁移
- [**部署指南**](deployment-guide.md) —— 覆盖 12 个以上平台的详细说明：GitHub Pages、Netlify、Vercel、Cloudflare、Render、DigitalOcean、AWS、Firebase、Docker 等

## 构建输出

DocsForge 会输出一个 `site/` 目录，其中包含：

```
site/
├── index.html          # 首页
├── 404.html            # 错误页面
├── sitemap.xml         # SEO 站点地图
├── sitemap.xml.gz      # 压缩后的站点地图
├── manifest.json       # PWA 清单
├── assets/             # CSS、JS、字体、图片
│   ├── javascripts/
│   ├── stylesheets/
│   └── ...
└── [your pages]/       # 每个 Markdown 页面对应一个 HTML 文件
```

这是一个静态站点 —— 可以部署到任何提供 HTML 文件服务的地方。

## 单命令部署示例

### GitHub Pages（使用 Actions）
完整的 GitHub Actions 工作流请参见 [部署指南 → GitHub Pages](deployment-guide.md#github-pages)。

### Netlify（拖拽上传）
1. 运行 `docsforge build`
2. 访问 [netlify.com](https://netlify.com)
3. 将 `site/` 文件夹拖到页面上

### Surge.sh
```bash
npm install -g surge
docsforge build
surge site/ my-docs.surge.sh
```

### Docker
```bash
docsforge build
docker run -v $(pwd)/site:/usr/share/nginx/html:ro -p 8080:80 nginx:alpine
```

## 部署前检查

### 检查清单
- [ ] `docsforge.yml` 中的 `site_url` 与实际域名一致
- [ ] 已设置 `repo_url`（用于“编辑此页”链接）
- [ ] 已配置 `copyright`
- [ ] 构建成功：`docsforge build`
- [ ] 站点显示正常：`docsforge serve`

### SEO 要点
DocsForge 会自动处理以下内容：
- :material-check-bold: 站点地图（`sitemap.xml.gz`）
- :material-check-bold: PWA 清单（`manifest.json`）
- :material-check-bold: OpenGraph 标签（自动生成）
- :material-check-bold: 语义化 HTML
- :material-check-bold: 快速加载（资源已优化）

## 需要帮助？

- **平台相关问题**：参见 [部署指南](deployment-guide.md)
- **迁移问题**：参见 [迁移指南](migration.md)
- **使用问题**：参见 [使用指南](usage.md)
- **一般帮助**：[GitHub Discussions](https://github.com/QQSHI13/docsforge/discussions)
