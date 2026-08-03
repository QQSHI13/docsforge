# Docker 镜像

DocsForge 可以在 Docker 容器中运行，以实现隔离且可复现的文档构建。

## 快速开始

```bash
# 拉取最新镜像
docker pull ghcr.io/qqshi13/docsforge:latest

# 构建文档
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build

# 启动开发服务器（访问 http://localhost:8000）
docker run --rm -v $(pwd):/docs -p 8000:8000 ghcr.io/qqshi13/docsforge:latest serve --lan

# 导出 PDF
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build --pdf

# 校验配置
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest check

# 自动修复常见配置问题
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest check --fix
```

## 可用标签

| 标签 | 说明 |
|-----|-------------|
| `latest` | 最新稳定版本 |
| `11.0.4` | 特定版本 |
| `sha-abc123` | 特定提交 SHA |
| `11.0` | 最新 11.0.x 版本 |

每次 GitHub 发布时，镜像都会自动发布到 `ghcr.io/qqshi13/docsforge`。

## 包含内容

Docker 镜像（约 1.5GB）包含：

- **包含全部 extras 的 DocsForge**（`docsforge[all]`）
- **用于 PDF 导出的 Playwright + Chromium**
- **用于 TikZ 图表编译的 TeXLive + dvisvgm**
- **Python 3.12 运行时**

## 本地构建

```dockerfile
FROM python:3.12-slim

RUN pip install docsforge

WORKDIR /docs
EXPOSE 8000

ENTRYPOINT ["docsforge"]
CMD ["--help"]
```

```bash
docker build -t my-docsforge .
docker run --rm -v $(pwd):/docs my-docsforge build
```

## Docker Compose

```yaml
# docker-compose.yml
version: '3'
services:
  docs:
    image: ghcr.io/qqshi13/docsforge:latest
    command: serve --lan
    ports:
      - "8000:8000"
    volumes:
      - .:/docs
```

```bash
docker-compose up
```

## CI/CD 集成

在 CI 流水线中使用 Docker 镜像，实现可复现构建：

```yaml
# .github/workflows/docs.yml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 构建文档
        run: |
          docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build
      - name: Deploy
        run: |
          # 将 site/ 上传到你的托管服务商
```

## 环境变量

| 变量 | 说明 |
|----------|-------------|
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | 用于 PDF 导出的 Chromium/Chrome 可执行文件路径。如果未设置，DocsForge 会探测常见的 Linux 路径（`/usr/bin/chromium`、`/usr/bin/google-chrome`、…），最终回退到 Playwright 自带的浏览器。 |

## 自定义 PDF 浏览器

PDF 导出（`docsforge build --pdf`）通过 Playwright 启动无头 Chromium。
镜像在 `/usr/bin/chromium` 提供了 Chromium，并将 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`
指向它。要使用其他浏览器：

**覆盖路径**（文件必须存在于容器*内部*）：
```bash
docker run --rm -v "$PWD:/docs" \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/google-chrome-stable \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

**使用 Playwright 自带的浏览器**（取消环境变量覆盖，使其
通过默认探测列表回退到 Playwright 管理的下载——已通过 `playwright install chromium` 预装在镜像中）：
```bash
docker run --rm -v "$PWD:/docs" \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE= \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

**以只读方式挂载宿主机浏览器可执行文件**并指向它：
```bash
docker run --rm -v "$PWD:/docs" \
  -v /usr/bin/google-chrome:/usr/bin/host-chrome:ro \
  -e PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/host-chrome \
  ghcr.io/qqshi13/docsforge:latest build --pdf
```

使用 `--jobs` 调整并行度：
```bash
docker run --rm -v "$PWD:/docs" ghcr.io/qqshi13/docsforge:latest build --pdf --jobs 2
```
