---
icon: material/alert-decagram-outline
---

# 提示框

提示框（也称为 callouts 或侧边栏）通过彩色方框和图标突出显示重要信息。

## 语法

``` markdown
!!! type "可选标题"
    内容写在这里。必须缩进。
```

## 类型

### 注释

``` markdown
!!! note
    这是一个注释提示框。
```

!!! note
    这是一个注释提示框。

### 提示

``` markdown
!!! tip
    这是一个提示提示框。
```

!!! tip
    这是一个提示提示框。

### 警告

``` markdown
!!! warning
    这是一个警告提示框。
```

!!! warning
    这是一个警告提示框。

### 危险

``` markdown
!!! danger
    这是一个危险提示框。
```

!!! danger
    这是一个危险提示框。

### 信息

``` markdown
!!! info
    这是一个信息提示框。
```

!!! info
    这是一个信息提示框。

### 成功

``` markdown
!!! success
    这是一个成功提示框。
```

!!! success
    这是一个成功提示框。

### 摘要

``` markdown
!!! abstract
    这是一个摘要提示框。
```

!!! abstract
    这是一个摘要提示框。

## 可折叠提示框

添加 `?` 使提示框可折叠：

``` markdown
??? note "点击展开"
    默认隐藏此内容。
```

??? note "点击展开"
    默认隐藏此内容。

添加 `+` 使其默认展开：

``` markdown
???+ note "已展开"
    默认显示此内容。
```

???+ note "已展开"
    默认显示此内容。

## 自定义标题

``` markdown
!!! note "自定义标题"
    你可以替换默认的类型标签。
```

!!! note "自定义标题"
    你可以替换默认的类型标签。

## 无图标

``` markdown
!!! note ""
    无图标，仅标题和内容。
```

!!! note ""
    无图标，仅标题和内容。

## 嵌套内容

提示框可以包含任何 Markdown 内容，包括代码块：

``` markdown
!!! example "配置示例"
    ``` yaml
    theme:
      palette:
        primary: teal
    ```
```

!!! example "配置示例"
    ``` yaml
    theme:
      palette:
        primary: teal
    ```

## 所有提示框类型

| 类型 | 颜色 | 图标 | 用于 |
|------|-------|------|---------|
| `note` | 蓝色 | 信息圆圈 | 一般信息 |
| `abstract` | 青色 | 文档 | 摘要、概要 |
| `info` | 蓝色 | 信息 | 详细信息 |
| `tip` | 绿色 | 灯泡 | 有用建议 |
| `success` | 绿色 | 对勾 | 积极结果 |
| `question` | 橙色 | 帮助圆圈 | 问题、FAQ |
| `warning` | 橙色 | 警告三角形 | 需要谨慎 |
| `failure` | 红色 | X 圆圈 | 某事失败 |
| `danger` | 红色 | 闪电 | 关键警告 |
| `bug` | 红色 | Bug | Bug 报告 |
| `example` | 紫色 | 列表 | 示例 |
| `quote` | 灰色 | 引号 | 引用 |

## 下一步

- [代码块](code-blocks.md)
- [内容标签页](content-tabs.md)
