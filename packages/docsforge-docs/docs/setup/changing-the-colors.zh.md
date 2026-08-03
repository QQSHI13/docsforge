# 更改颜色

DocsForge 使用 Material 主题的颜色系统。在 `docsforge.yml` 的 `theme.palette` 键下自定义颜色。

## 调色板

调色板定义了整个站点使用的颜色。你可以定义多个调色板，并让用户在它们之间切换（例如，浅色和深色模式）。

### 最小配置

``` yaml
theme:
  palette:
    primary: teal
    accent: teal
```

### 主色

主色用于页头、导航、链接和交互元素。

| 颜色名称 | 色值 |
|-----------|-------|
| `red` | `#F44336` |
| `pink` | `#E91E63` |
| `purple` | `#9C27B0` |
| `deep purple` | `#673AB7` |
| `indigo` | `#3F51B5` |
| `blue` | `#2196F3` |
| `light blue` | `#03A9F4` |
| `cyan` | `#00BCD4` |
| `teal` | `#009688` |
| `green` | `#4CAF50` |
| `light green` | `#8BC34A` |
| `lime` | `#CDDC39` |
| `yellow` | `#FFEB3B` |
| `amber` | `#FFC107` |
| `orange` | `#FF9800` |
| `deep orange` | `#FF5722` |
| `brown` | `#795548` |
| `grey` | `#9E9E9E` |
| `blue grey` | `#607D8B` |
| `black` | `#000000` |
| `white` | `#FFFFFF` |

### 强调色

强调色用于悬停状态、激活元素和需要突出的内容。

与主色取值相同，但不可使用 `grey`、`brown`、`blue grey`、`black` 和 `white`。

## 浅色与深色模式

配置多个调色板以支持自动和手动切换：

``` yaml
theme:
  palette:
    # 自动检测系统偏好设置
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: teal
      accent: teal
      toggle:
        icon: material/brightness-7
        name: 切换到深色模式
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: black
      accent: teal
      toggle:
        icon: material/brightness-4
        name: 切换到浅色模式
```

### 配色方案

- `default` — 白色背景的浅色模式
- `slate` — 深灰色背景的深色模式

## 自定义颜色

使用任意十六进制颜色值：

``` yaml
theme:
  palette:
    primary: "#1E90FF"
    accent: "#FF6B6B"
```

## 代码块颜色

代码块主题与调色板方案绑定：

- `default` 方案 → 浅色代码高亮（浅色背景）
- `slate` 方案 → 深色代码高亮（深色背景）

这会自动生效，无需额外配置。

## 下一步

- [更改字体](changing-the-fonts.md)
- [设置导航](setting-up-navigation.md)
