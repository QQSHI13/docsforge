---
icon: material/gauge
---

# 构建优化站点

DocsForge 默认包含 `minify` 插件。它会在构建时压缩 HTML、CSS 和 JavaScript。

## 自动优化的内容

`minify` 插件会移除：
- HTML 中的空白字符和换行符
- HTML 注释
- 可选的属性引号
- CSS 和 JavaScript 中的空白字符

每次构建时都会自动运行，无需任何配置。

## 图片优化

为获得最佳效果，请在将图片添加到文档之前对其进行优化：

``` bash
# 使用 pngquant 处理 PNG
pngquant --quality=70-90 docs/assets/images/*.png

# 使用 cwebp 转换为 WebP
cwebp -q 80 image.png -o image.webp
```

### 推荐格式

| 格式 | 适用场景 | 大小 |
|------|----------|------|
| SVG | 徽标、图标、示意图 | 最小 |
| WebP | 照片、截图 | 比 PNG 小约 25% |
| PNG | 带透明的截图 | 无损 |
| JPEG | 不带透明的照片 | 压缩率高 |

### 图片尺寸指南

- 尽可能将图片控制在 200KB 以内
- 使用 `width` 属性限制大图片：`![Alt](img.png){ width="400" }`
- 默认启用懒加载，无需配置

## 隐私插件（外部资源）

`privacy` 插件会在构建期间下载并缓存外部资源（如 Google Fonts）。这意味着：
- 运行时不会请求 CDN
- 页面加载更快
- 可离线使用
- 用户隐私保护更好

每次构建时自动运行。

## 构建输出

``` bash
docsforge build
```

`site/` 目录包含优化后的静态站点，可直接部署。

## 性能检查清单

- [ ] 图片已优化（优先使用 WebP，图标使用 SVG）
- [ ] 无外部资源（由 privacy 插件处理）
- [ ] 已启用压缩（默认）
- [ ] 文件名中包含缓存清除哈希（默认）
- [ ] 用于离线的 Service worker（默认）
- [ ] 图片懒加载（默认）

## 性能测量

使用以下工具检查站点性能：

- [Google PageSpeed Insights](https://pagespeed.web.dev/)
- [Lighthouse](https://developer.chrome.com/docs/lighthouse)（内置于 Chrome 开发者工具）
- [WebPageTest](https://www.webpagetest.org/)

优化良好的 DocsForge 站点通常在所有 Lighthouse 指标上都能获得 90 分以上。
