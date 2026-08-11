# PDF 导出

DocsForge 可以使用 `docsforge build --pdf` 将您的文档导出为 PDF 文件。

## 快速开始

```bash
pip install "docsforge[pdf]"
playwright install chromium
docsforge build --pdf
```

输出保存到 `pdf/` 目录，并保留站点目录结构。

## 依赖要求

| 依赖 | 安装方式 | 用途 |
|-----------|---------|---------|
| **Playwright** | `pip install "docsforge[pdf]"` | 用于将 HTML 渲染为 PDF 的无头浏览器 |
| **Chromium** | `playwright install chromium` | 浏览器引擎。也可以使用系统浏览器。 |

## 用法

```bash
# 构建站点并导出 PDF
docsforge build --pdf

# 使用更多并行标签页以加快渲染速度（默认：4）
docsforge build --pdf --jobs 8

# 单线程（用于调试）
docsforge build --pdf --jobs 1
```

输出写入到 `pdf/` 目录，并保留站点的目录结构：

```
pdf/
├── index.pdf
├── getting-started/
│   └── index.pdf
└── setup/
    └── changing-the-colors/
        └── index.pdf
```

## 系统浏览器

不使用 Playwright 自带的 Chromium，而是使用系统已安装的浏览器：

```bash
export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser
docsforge build --pdf
```

自动检测的浏览器：thorium、chromium、google-chrome、brave-browser。

## Docker

```bash
docker run --rm -v $(pwd):/docs ghcr.io/qqshi13/docsforge:latest build --pdf
```

Docker 镜像包含 Playwright、Chromium 和所有依赖。

## 工作原理

1. **完整 `docsforge build`** — 运行完整的构建流程，包含所有插件（Mermaid、KaTeX、TikZ、privacy、search）
2. **Playwright 渲染** — 在每个无头 Chromium 标签页中使用 `@media print` CSS 打开每个 HTML 页面
3. **打印模式会移除 UI 装饰** — 导航栏、标签页、页脚、搜索框会自动隐藏
4. **Mermaid 渲染** — 图表会在截图前由浏览器渲染完成
5. **工具提示展开** — 悬停提示会在 PDF 中以内联方式展开
6. **输出** — 每个页面生成一个 PDF，保留目录结构

## 性能

- **并行标签页**：默认 4。使用 `--jobs N` 调整
- **网络请求**：外部请求由本地文件系统提供（privacy 插件缓存）
- **工作队列**：每个标签页完成后立即获取下一个页面，无需批量等待

## 故障排除

| 问题 | 解决方法 |
|-------|-----|
| **Mermaid 图表空白** | 安装 Playwright 的 Chromium：`playwright install chromium` |
| **“Executable doesn't exist”** | 将 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 设置为系统浏览器路径 |
| **字体缺失** | 先运行 `docsforge build`，以便 privacy 插件下载字体 |
| **PDF 为空 / 白屏** | 先确保 `docsforge build` 成功，再运行 `--pdf` |
| **渲染缓慢** | 增加并行标签页：`--jobs 8` |
| **读取 file:// 页面时出错** | 确保您的浏览器支持 `--allow-file-access-from-files` |
