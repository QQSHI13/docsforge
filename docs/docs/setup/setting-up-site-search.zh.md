---
icon: material/magnify
---

# 设置站点搜索

DocsForge 包含一个强大的客户端搜索引擎，由 [Marz](https://github.com/QQSHI13/marz) 驱动。它默认通过 `search` 插件启用。构建时会在 `search_index.json` 旁生成紧凑的预构建索引（`.marz`），浏览器无需现场建索引——即使大型站点也能即时返回结果，中日韩文本无需分词字典即可原生匹配。

## 配置

### 基本设置

搜索默认已启用：

``` yaml
plugins:
  - search
```

### 搜索分隔符

控制结果中匹配词的高亮方式：

``` yaml
plugins:
  - search:
      separator: '[\s\u200b\-_,:!=\[\]()"`\/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
```

分隔符仅影响界面中的匹配高亮。索引由 Marz 按语言原生分词构建，因此词干提取和中日韩文本都不需要调整它。

默认分隔符会在以下位置拆分：
- 空格和零宽空格
- 连字符、下划线、逗号、冒号
- 驼峰命名边界（例如，`MyClass` → `My` + `Class`）

### 语言

为你的语言配置搜索词干提取：

``` yaml
plugins:
  - search:
      lang: en
```

支持的语言包括：`en`、`de`、`es`、`fr`、`ja`、`pt`、`ru`、`zh` 等，可组合多种语言（`lang: [en, ja]`）。完整列表见 `marz.languages()`。中日韩文本无需额外配置：不需要 jieba，也不需要分词字典。

## 搜索功能

在 `theme.features` 中启用：

### 高亮

在搜索结果中高亮显示匹配的词条：

``` yaml
theme:
  features:
    - search.highlight
```

### 建议

在你输入时显示自动完成建议：

``` yaml
theme:
  features:
    - search.suggest
```

### 共享搜索

允许用户分享搜索结果的直接链接：

``` yaml
theme:
  features:
    - search.share
```

## 完整搜索配置

``` yaml
theme:
  features:
    - search.highlight
    - search.suggest
    - search.share

plugins:
  - search:
      separator: '[\s\u200b\-_,:!=\[\]()"`\/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
      lang: en
```

## 搜索行为

- **即时**：结果在你输入时立即显示，无需服务器往返
- **模糊匹配**：容忍轻微的拼写错误
- **词干提取**：搜索 "run" 可以找到 "running"、"runs" 等
- **排序**：结果按相关性排序（标题匹配的排名更高）
- **摘要**：每个结果都显示带上下文的片段

## 从搜索中排除内容

添加 `search.exclude` 前置元数据以隐藏页面：

``` yaml
---
search:
  exclude: true
---
```

或者使用 HTML 注释排除特定部分：

``` html
<!--search exclude-->
此内容不会被索引。
<!--end search exclude-->
```

## 后续步骤

- [设置站点分析](setting-up-site-analytics.md)
- [设置社交卡片](setting-up-social-cards.md)
