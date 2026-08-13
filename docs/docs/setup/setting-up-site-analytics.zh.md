---
icon: material/chart-line
---

# 设置站点分析

添加分析功能以了解读者如何使用你的文档。

## Google Analytics 4（内置）

DocsForge 内置了 Google Analytics 4 集成。

``` yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX  # 你的衡量 ID
```

## 其他提供商

对于 Plausible、Fathom、GoatCounter、Umami 或任何其他提供商，请通过 `extra_javascript` 添加跟踪脚本：

``` yaml
extra_javascript:
  - assets/javascripts/analytics.js
```

``` js title="docs/assets/javascripts/analytics.js"
// 你的自定义分析初始化
```

## 隐私注意事项

DocsForge 在设计时充分考虑了隐私：

- 搜索在客户端进行（没有搜索数据离开浏览器）
- 默认不加载外部字体（全部本地化提供）
- 除了你明确添加的内容外，没有外部 JavaScript
- 完全离线工作，无需网络请求

如果你添加了分析功能，请考虑：
- 使用注重隐私的提供商（Plausible、Fathom、GoatCounter）
- 如果你的司法管辖区要求，请添加隐私政策
- 尊重“请勿跟踪”信号

## 在开发中禁用分析

DocsForge 开发服务器（`docsforge serve`）不包含分析脚本。它们只在生产构建期间添加。

## 后续步骤

- [设置社交卡片](setting-up-social-cards.md)
- [构建优化站点](building-an-optimized-site.md)

## 跟踪事件

通过添加 JavaScript 来跟踪自定义事件（例如按钮点击、下载）：

``` js title="docs/assets/javascripts/events.js"
document.addEventListener('click', function(e) {
  if (e.target.matches('a[href*=".zip"]')) {
    // 跟踪下载
    gtag('event', 'download', {
      event_category: 'documentation',
      event_label: e.target.href
    });
  }
});
```

## 最佳实践

- 尽可能使用注重隐私的分析工具
- 只跟踪改进文档所必需的内容
- 在隐私政策中记录你的分析实践
- 尊重用户偏好（请勿跟踪、GDPR 同意）
- 在生产构建中测试分析，而不是在开发环境中
- 定期审查分析数据，以识别热门和未充分利用的页面

## 故障排除

### 分析未加载

1. 检查 `property` 是否设置正确
2. 确认你查看的是生产构建，而不是 `docsforge serve`
3. 检查浏览器控制台中的 JavaScript 错误
4. 确保广告拦截器没有阻止跟踪脚本

### 数据未显示

1. 分析仪表板可能会有延迟（某些提供商最长可达 24 小时）
2. 确认配置了正确的属性 ID
3. 检查站点是否可公开访问（分析无法跟踪 localhost）
