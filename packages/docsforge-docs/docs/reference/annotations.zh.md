# 注释

注释功能可以直接在代码块中添加说明、备注和标注，帮助读者在不打断阅读节奏的情况下理解复杂代码。

---

## 行号

使用 `linenums` 在代码块中启用行号：

```` markdown
``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")  # (1)!
    return True  # (2)!
```

1.  使用个性化消息问候用户
2.  返回成功状态
````

``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")  # (1)!
    return True  # (2)!
```

1.  使用个性化消息问候用户
2.  返回成功状态

### 从指定行开始

从任意行开始编号：

```` markdown
``` python linenums="42"
def meaning_of_life():
    return 42  # (1)!
```

1.  终极答案
````

``` python linenums="42"
def meaning_of_life():
    return 42  # (1)!
```

1.  终极答案

---

## 高亮行

使用 `hl_lines` 高亮指定行：

```` markdown
``` python hl_lines="2 4"
def process(data):
    result = []      # 普通
    for item in data:  # 高亮
        value = item * 2  # 普通
        result.append(value)  # 高亮
    return result
```
````

``` python hl_lines="2 4"
def process(data):
    result = []      # 普通
    for item in data:  # 高亮
        value = item * 2  # 普通
        result.append(value)  # 高亮
    return result
```

### 高亮范围

高亮某个范围的行：

```` markdown
``` python hl_lines="2-4"
def setup():
    config = load_config()  # 高亮
    validate(config)        # 高亮
    apply_defaults(config)  # 高亮
    return config
```
````

---

## 行内注释

在代码中添加标记，以引用代码块下方的脚注：

```` markdown
``` yaml
theme:
  features:
    - navigation.tabs  # (1)!
    - search.highlight  # (2)!
```

1.  启用标签式导航
2.  高亮搜索结果中的搜索词
````

``` yaml
theme:
  features:
    - navigation.tabs  # (1)!
    - search.highlight  # (2)!
```

1.  启用标签式导航
2.  高亮搜索结果中的搜索词

### 同一行多个注释

同一行可以有多个注释：

```` markdown
``` python
x = calculate()  # (1)! (2)!
```

1.  调用 calculate 函数
2.  结果存入 x
````

---

## 代码块标题

为代码块添加标题栏：

```` markdown
``` yaml title="docsforge.yml"
site_name: My Project
```
````

``` yaml title="docsforge.yml"
site_name: My Project
```

---

## 复制到剪贴板

当在 `docsforge.yml` 中启用 `content.code.copy` 后，代码块会自动获得复制按钮：

``` yaml
theme:
  features:
    - content.code.copy
```

鼠标悬停时，复制按钮会出现在每个代码块的右上角。

---

## Diff 高亮

使用 `diff` 高亮显示代码变更：

```` markdown
``` python
  def old_function():
-     return "old"
+     return "new"
```
````

---

## 组合功能

你可以组合使用多个功能：

```` markdown
``` python title="config.py" linenums="1" hl_lines="3"
def configure():
    settings = {}
    settings['debug'] = True  # (1)!
    return settings
```

1.  为开发启用调试模式
````

``` python title="config.py" linenums="1" hl_lines="3"
def configure():
    settings = {}
    settings['debug'] = True  # (1)!
    return settings
```

1.  为开发启用调试模式

---

## 最佳实践

- 谨慎使用注释——过多脚注会让页面显得杂乱
- 保持注释文本简洁（1-2 句话）
- 使用高亮吸引读者注意变更或重要的行
- 行号有助于在周围文本中引用特定行
- 展示配置文件时始终包含标题

## 下一步

- [代码块](code-blocks.md)
- [内容标签页](content-tabs.md)
- [格式化](formatting.md)
