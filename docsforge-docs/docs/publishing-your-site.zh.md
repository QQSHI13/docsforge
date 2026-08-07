# 发布站点

DocsForge 构建完全静态的站点——没有数据库，没有服务端处理，没有运行时依赖。这意味着你可以在任何能提供静态文件托管的地方部署它。

## GitHub Pages（推荐）

这是将文档上线最快的方式。DocsForge 包含一个即用型的 GitHub Actions 工作流。

### 1. 推送到 GitHub

创建仓库并推送你的文档项目：

``` bash
git init
git add .
git commit -m "Initial documentation"
git branch -M main
git remote add origin https://github.com/username/my-docs.git
git push -u origin main
```

### 2. 启用 GitHub Pages

1. 在 GitHub 上打开你的仓库
2. 点击 **Settings** → **Pages**
3. 在 **Build and deployment** 下，选择 **Source: GitHub Actions**

### 3. 工作流已包含

你的 DocsForge 入门项目已包含 `.github/workflows/pages.yml`。它会在每次推送到 `main` 时自动运行：

``` yaml title=".github/workflows/pages.yml"
name: Deploy Docs to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Build site
        run: docsforge build

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

就这些。你的站点将在一分钟内上线于 `https://username.github.io/my-docs/`。

### 自定义域名

在 `docs/` 目录中添加 `CNAME` 文件：

``` { .sh .no-copy title="docs/CNAME" }
docs.example.com
```

然后在你的 DNS 提供商处配置 CNAME 记录，指向 `username.github.io`。

## Netlify

### 拖拽部署

1. 运行 `docsforge build`
2. 将 `site/` 文件夹拖到 [Netlify Drop](https://app.netlify.com/drop)

### Git 集成

1. 将你的仓库推送到 GitHub
2. 在 Netlify 中，点击 **Add new site** → **Import an existing project**
3. 选择你的 GitHub 仓库
4. 设置构建命令：`docsforge build`
5. 设置发布目录：`site/`

## Vercel

1. 将你的仓库推送到 GitHub
2. 在 Vercel 中，点击 **Add New...** → **Project**
3. 导入你的仓库
4. 覆盖构建设置：
   - **Build Command**: `docsforge build`
   - **Output Directory**: `site/`

## Cloudflare Pages

1. 将你的仓库推送到 GitHub
2. 在 Cloudflare Pages 中，点击 **Create a project**
3. 连接你的 GitHub 账号并选择仓库
4. 设置构建命令：`docsforge build`
5. 设置构建输出目录：`site/`

## Render

1. 将你的仓库推送到 GitHub
2. 登录 [Render Dashboard](https://dashboard.render.com)
3. 点击 **New + → Static Site**
4. 连接你的仓库
5. 设置构建命令：`pip install docsforge && docsforge build`
6. 设置发布目录：`site/`

## DigitalOcean App Platform

1. 将你的仓库推送到 GitHub
2. 登录 [DigitalOcean](https://cloud.digitalocean.com)
3. 点击 **Apps → Create App**
4. 连接你的仓库
5. 选择 **Static Site** 方案
6. 设置构建命令：`pip install docsforge && docsforge build`
7. 设置输出目录：`site/`

## Amazon S3 + CloudFront

企业级部署：

``` bash title="构建并同步到 S3"
docsforge build
aws s3 sync site/ s3://my-docs-bucket --delete
aws cloudfront create-invalidation --distribution-id ABCD --paths "/*"
```

## Docker

如果你更喜欢容器化构建：

``` dockerfile title="Dockerfile"
FROM python:3.11-slim
WORKDIR /docs
COPY . .
RUN docsforge build
FROM nginx:alpine
COPY --from=0 /docs/site /usr/share/nginx/html
```

## 离线分发

由于 DocsForge 站点完全是静态的，你也可以将它们作为 ZIP 文件分发：

``` bash
docsforge build
zip -r my-docs.zip site/
```

接收者可以直接在浏览器中打开 `site/index.html`——无需服务器。

## 针对不同主机的构建设置

某些主机需要特定设置。请相应调整 `docsforge.yml`：

### GitHub Pages（项目站点）

``` yaml
site_url: https://username.github.io/repository-name/
```

### GitHub Pages（用户/组织站点）

``` yaml
site_url: https://username.github.io/
```

### 子目录部署

``` yaml
site_url: https://example.com/docs/
```

`site_url` 的重要性体现在：
- 生成正确的绝对 URL
- 为插件启用 `site_url` 元数据
- 确保搜索和导航正常工作

## 下一步

- [设置指南](setup/index.md) —— 发布前自定义你的站点
- [构建优化站点](setup/building-an-optimized-site.md) —— 启用压缩和压缩
