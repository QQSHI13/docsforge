---
icon: material/card-account-details-outline
---

# 设置社交卡片

DocsForge 会自动包含基本的 OpenGraph 元数据。每个页面会生成：

- `og:title` — 页面标题
- `og:description` — 页面描述或站点描述
- `og:type` — `website`
- `og:url` — 规范化页面 URL
- `og:site_name` — 站点名称

## 基本配置

在 `docsforge.yml` 中设置站点级默认值：

``` yaml
site_name: My Project Docs
site_description: Complete documentation for My Project
site_url: https://docs.example.com/
```

## 自定义单页

使用 front matter 为单个页面覆盖元数据：

``` yaml
---
description: Custom description for this page
---
```

## 社交卡片图片

默认情况下 DocsForge 不生成卡片图片 —— 只输出 OpenGraph 和 Twitter 元数据。有两种方式获得卡片图片：

### 方案 1：social 插件（推荐）

DocsForge 内置了 mkdocs-material 的**社交卡片**插件：构建时为每个页面渲染 1200×630 PNG，无需任何设计工作。启用它（可选 —— 需要 `pillow` + `cairosvg`）：

``` bash
pip install "docsforge[social]"
```

``` yaml
plugins:
  - social
```

卡片生成到构建产物的 `assets/images/social/`，并缓存在 `.docsforge/cache/social` 下。卡片显示站点名称、描述以及你的 `extra.social` 底部链接。

用 `cards_layout_options` 调整布局（参见[配置 → `extra.social`](../reference/configuration.md)）：

``` yaml
plugins:
  - social:
      cards_layout_options:
        background_color: "#0b57d0"
        color: "#ffffff"
        font_family: "Roboto"
```

### 方案 2：手动图片

添加自定义卡片图片并用绝对 URL 引用：

``` yaml
site_name: My Project Docs
site_description: Complete documentation for My Project
site_url: https://docs.example.com/
extra:
  social_image: https://docs.example.com/assets/images/social-card.png
```

创建一张 1200×630 的 PNG 图片，以便在各平台上获得最佳展示效果。然后，你可以在自定义的 `main.html` 覆盖模板中使用 `extra.social_image` 来填充 `twitter:image` 和 `og:image` 标签。

## 平台特定标签

### Twitter/X

Twitter 使用自己的卡片系统。DocsForge 会自动设置以下内容：

- `twitter:card` — `summary` 或 `summary_large_image`
- `twitter:title` — 页面标题
- `twitter:description` — 页面描述
- `twitter:image` — 社交卡片图片（如果已配置）

### LinkedIn

LinkedIn 使用标准的 OpenGraph 标签。请确保正确设置 `site_url`，以便 LinkedIn 获取元数据。

### Discord

Discord 嵌入使用 OpenGraph 标签。描述会被截断至约 300 个字符，因此请保持描述简洁。

## 验证你的卡片

使用以下工具进行测试：

- [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [Discord Embed Debugger](https://discord.com/developers/embeds)

## 故障排除

### 卡片未显示

1. 确保在 `docsforge.yml` 中正确设置了 `site_url`
2. 你的网站必须可以公开访问（验证工具无法访问 localhost）
3. 平台会缓存元数据 —— 使用调试工具强制刷新
4. 检查图片 URL 是否为绝对地址（而非相对地址）

### 图片或描述错误

1. 检查页面 front matter 中的 `description` 覆盖项
2. 确保在 `docsforge.yml` 中设置了 `site_description`
3. 每页的第一段会作为备用描述
4. 图片尺寸应为 1200×630 以获得最佳展示效果

### 图片无法加载

1. 使用绝对 URL：`https://docs.example.com/assets/images/card.png`
2. 确保图片无需认证即可访问
3. 检查图片是否小于 5MB（各平台限制不同）
4. 使用 PNG 或 JPEG 格式（社交卡片避免使用 WebP）

## 最佳实践

- 描述保持在 160 个字符以内
- 所有页面保持品牌一致性
- 分享前在多个平台上测试卡片
- 进行重要版本发布时更新卡片图片
- 在卡片图片中加入 Logo 以增强品牌识别

## 下一步

- [设置站点分析](setting-up-site-analytics.md)
- [构建优化站点](building-an-optimized-site.md)
