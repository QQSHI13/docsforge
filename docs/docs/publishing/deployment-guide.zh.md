# 部署指南

DocsForge 生成静态 HTML，可以部署到任何静态托管平台。本指南涵盖最流行的选项。

## 快速对比

| 平台 | 费用 | 自定义域名 | HTTPS | CI/CD | 最适合 |
|----------|------|--------------|-------|-------|----------|
| **GitHub Pages** | 免费 | :material-check-bold: | :material-check-bold: | GitHub Actions | 开源项目 |
| **Netlify** | 免费套餐 | :material-check-bold: | :material-check-bold: | Git push | 原型设计、JAMstack |
| **Vercel** | 免费套餐 | :material-check-bold: | :material-check-bold: | Git push | Next.js、快速部署 |
| **Cloudflare Pages** | 免费 | :material-check-bold: | :material-check-bold: | Git push | 速度、CDN |
| **GitLab Pages** | 免费 | :material-check-bold: | :material-check-bold: | GitLab CI | GitLab 用户 |
| **AWS S3 + CloudFront** | 按量付费 | :material-check-bold: | :material-check-bold: | GitHub Actions | 企业、规模化 |
| **Firebase Hosting** | 免费套餐 | :material-check-bold: | :material-check-bold: | GitHub Actions | Google 生态 |
| **Surge.sh** | 免费 | :material-check-bold: | :material-check-bold: | CLI | 快速部署 |
| **Render** | 免费套餐 | :material-check-bold: | :material-check-bold: | Git push | 静态站点、快速 CDN |
| **DigitalOcean App Platform** | 按量付费 | :material-check-bold: | :material-check-bold: | GitHub Actions | 完全控制、可扩展 |
| **Docker + Nginx** | 服务器费用 | :material-check-bold: | :material-check-bold: | 任意 | 自托管 |
| **Caddy** | 服务器费用 | :material-check-bold: | 自动 | 任意 | 自托管、简单 TLS |

---

## GitHub Pages

开源项目最简单的选择。免费、可靠，与 GitHub 集成。

### GitHub Actions（推荐）

创建 `.github/workflows/docsforge-pages.yml`：

```yaml
name: 部署文档

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
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install docsforge
      - run: docsforge build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

### Alternative: peaceiris/actions-gh-pages

更简单的单任务工作流，推送到 `gh-pages` 分支：

```yaml
name: 部署文档

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install docsforge
      - run: docsforge build
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

### 设置
1. 前往 **Settings → Pages**
2. Source: **GitHub Actions**
3. 推送工作流文件——站点将自动部署

### 自定义域名
1. 将 `CNAME` 文件添加到 `docs/`（或构建后的 `site/`）：
   ```
   docs.example.com
   ```
2. 在仓库设置中：**Pages → Custom domain**
3. 添加 DNS 记录：
   - `docs.example.com` → `CNAME` → `yourusername.github.io`

---

## Netlify

非常适合原型设计和 JAMstack 站点。支持拖拽或基于 Git 的部署。

### 方法 1：基于 Git（推荐）

1. 将你的仓库推送到 GitHub/GitLab/Bitbucket
2. 登录 [Netlify](https://netlify.com)
3. **Add new site → Import from Git**
4. 选择你的仓库
5. 构建设置：
   - Build command: `pip install docsforge && docsforge build`
   - Publish directory: `site`
6. 部署！

### 方法 2：CLI

```bash
# 安装 Netlify CLI
npm install -g netlify-cli

# 构建文档
docsforge build

# 部署
netlify deploy --dir=site --prod
```

### `netlify.toml`
```toml
[build]
  command = "pip install docsforge && docsforge build"
  publish = "site"

[[redirects]]
  from = "/*"
  to = "/404.html"
  status = 404
```

---

## Vercel

部署快速，非常适合前端项目。与 Netlify 类似。

### 基于 Git

1. 推送到 GitHub
2. 登录 [Vercel](https://vercel.com)
3. **Add New Project → Import**
4. Framework preset: **Other**
5. Build command: `pip install docsforge && docsforge build`
6. Output directory: `site`

### `vercel.json`
```json
{
  "builds": [
    {
      "src": "docsforge.yml",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "site"
      }
    }
  ]
}
```

---

## Cloudflare Pages

最快的 CDN，免费额度慷慨。非常适合全球性能。

### 基于 Git

1. 推送到 GitHub/GitLab
2. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
3. **Pages → Create a project**
4. 连接你的 Git 仓库
5. 构建设置：
   - Build command: `pip install docsforge && docsforge build`
   - Build output directory: `site`
6. 部署

### Cloudflare Pages Functions

如需自定义标头或重定向，请将 `_headers` 或 `_redirects` 添加到 `docs/`：
```
# docs/_headers
/*.html
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
```

---

## GitLab Pages

与 GitLab CI 集成。非常适合 GitLab 用户。

### `.gitlab-ci.yml`
```yaml
image: python:3.11

pages:
  script:
    - pip install docsforge
    - docsforge build
  artifacts:
    paths:
      - site
  only:
    - main
```

你的站点将位于 `https://username.gitlab.io/projectname`。

---

## AWS S3 + CloudFront

企业级托管。可扩展到任何流量级别。

### S3 存储桶设置

1. 创建 S3 存储桶（例如 `docs.example.com`）
2. 启用 **Static website hosting**
3. 上传你的 `site/` 目录：
   ```bash
   aws s3 sync site/ s3://docs.example.com --delete
   ```
4. 设置存储桶策略以允许公开读取：
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::docs.example.com/*"
       }
     ]
   }
   ```

### CloudFront CDN

1. 创建 CloudFront 分发
2. Origin: 你的 S3 存储桶
3. Viewer protocol policy: **Redirect HTTP to HTTPS**
4. 在 **Alternate domain names** 中添加自定义域名
5. 使用 AWS Certificate Manager 获取 SSL

### GitHub Actions + S3

```yaml
- name: Deploy to S3
  run: aws s3 sync site/ s3://docs.example.com --delete
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Firebase Hosting

Google Firebase 的一部分。如果你已经在 Google 生态中，这是个不错的选择。

### 设置

```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 登录
firebase login

# 初始化项目
firebase init hosting
# 选择 "Configure as a single-page app?" → No
# 设置 public directory → site

# 构建并部署
docsforge build
firebase deploy
```

### `firebase.json`
```json
{
  "hosting": {
    "public": "site",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/404.html"
      }
    ]
  }
}
```

---

## Surge.sh

最简单的部署方式。非常适合快速预览。

```bash
# 安装 Surge
npm install -g surge

# 构建并部署
docsforge build
surge site/ docs-example.surge.sh

# 自定义域名
surge site/ docs.example.com
```

---

## Render

[Render](https://render.com) 为静态站点提供慷慨的免费套餐，包含全球 CDN、自动 HTTPS 和基于 Git 的部署。

### 基于 Git（推荐）

1. 将你的仓库推送到 GitHub/GitLab
2. 登录 [Render Dashboard](https://dashboard.render.com)
3. **New + → Static Site**
4. 连接你的仓库
5. 构建设置：
   - Build command: `pip install docsforge && docsforge build`
   - Publish directory: `site`
6. **Create Static Site**

Render 会在每次推送到连接的分支时自动部署。

### 自定义域名

1. 前往静态站点的 **Settings → Custom Domain**
2. 添加你的域名
3. 更新 DNS（Render 会提供目标 CNAME）

---

## DigitalOcean App Platform

[DigitalOcean App Platform](https://www.digitalocean.com/products/app-platform) 提供托管静态托管服务，包含自动 HTTPS、CDN 和基于 Git 的部署。

### 基于 Git（推荐）

1. 将你的仓库推送到 GitHub
2. 登录 [DigitalOcean](https://cloud.digitalocean.com)
3. **Apps → Create App**
4. 连接你的仓库
5. 选择分支（`main`）
6. 编辑套餐（Static Site 起价为 $0——有免费套餐可用）
7. 构建设置：
   - Build command: `pip install docsforge && docsforge build`
   - Output directory: `site`
8. **Review and Create**

### GitHub Actions + DigitalOcean

如需更多控制，可以在本地构建并通过 DigitalOcean CLI 部署：

```yaml
- name: Deploy to DigitalOcean App Platform
  uses: digitalocean/app_action@v1
  with:
    app_name: my-docs
    token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
```

---

## Docker + Nginx

自托管方案。完全控制服务器。

### `Dockerfile`
```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY . /app
RUN pip install docsforge && docsforge build

FROM nginx:alpine
COPY --from=builder /app/site /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### `nginx.conf`
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    error_page 404 /404.html;
}
```

### 构建并运行
```bash
docker build -t my-docs .
docker run -p 8080:80 my-docs
```

---

## Caddy

现代、易于配置的 Web 服务器，支持自动 HTTPS。

### `Caddyfile`
```
docs.example.com {
    root * /var/www/docs
    file_server
    try_files {path} {path}/ /404.html
}
```

### 部署
```bash
# 构建文档
docsforge build

# 复制到服务器
rsync -avz site/ user@server:/var/www/docs/

# 启动 Caddy
caddy run --config Caddyfile
```

Caddy 会自动申请 Let's Encrypt 证书。无需手动设置 SSL。

---

## 平台专属技巧

### GitHub Pages
- 在配置中使用 `site_url: https://username.github.io/repo-name`
- 对于用户/组织站点（`username.github.io`），相应地设置 `site_url`
- 在仓库设置中启用 "Enforce HTTPS"

### Netlify
- 添加 `_redirects` 文件用于 SPA 路由：
  ```
  /* /404.html 404
  ```
- 使用分支部署来预览 PR

### Vercel
- 将 `site_url` 设置为你的 Vercel 域名
- 使用 `vercel --prod` 进行生产部署

### Cloudflare Pages
- 启用 "Always Use HTTPS"
- 对静态资源使用 Cloudflare 缓存

### AWS S3
- 如需回滚能力，请启用版本控制
- 使用 `aws s3 sync --delete` 删除旧文件
- 面向全球受众时，考虑使用 S3 Transfer Acceleration

### Render
- 将 `site_url` 设置为你的 Render 域名（例如 `https://my-docs.onrender.com`）
- 每次推送到连接的分支时自动部署
- 免费套餐包含每月 100 GB 带宽

### DigitalOcean
- Static Sites 免费起步，包含 1 GB 存储
- 将 `site_url` 设置为你的 App Platform 域名
- 在 GitHub Actions 中使用 DigitalOcean API token 实现自动部署

---


## 持续部署

### 每次推送时触发部署

所有平台都支持在推送到 Git 时自动部署。通用模式如下：

1. **构建**：安装 DocsForge，构建站点
2. **部署**：将 `site/` 上传到你的主机
3. **刷新**：清除 CDN 缓存（如果使用 CDN）

### 示例：GitHub Actions + 任意平台
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install docsforge
      - run: docsforge build
      # 在此处添加你的部署步骤
```

---

## 故障排除

| 问题 | 平台 | 解决方案 |
|-------|----------|----------|
| 刷新时 404 | SPA 主机 | 配置回退到 `index.html` |
| CSS 无法加载 | 全部 | 检查 `site_url` 是否与实际域名匹配 |
| 搜索无法使用 | 全部 | 确保 `search` 插件已启用 |
| 构建失败 | CI/CD | 固定 Python 版本，使用 `pip install docsforge` |
| 部署缓慢 | 全部 | 使用 `.gitignore` 排除大文件 |
| 缓存问题 | CDN | 添加缓存破坏查询字符串或清除 CDN |

---

## 下一步

- [使用指南](usage.md) — DocsForge 日常使用
- [迁移指南](migration.md) — 从 MkDocs/Material 迁移
- [更新日志](../changelog/index.md) — 新增内容
