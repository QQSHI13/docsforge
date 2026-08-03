# 代码块

DocsForge 支持丰富的代码块，包括语法高亮、标题、行号等功能。

## 基础代码块

使用带有语言标识符的三个反引号：

```` markdown
``` python
def hello(name):
    print(f"Hello, {name}!")
```
````

``` python
def hello(name):
    print(f"Hello, {name}!")
```

## 支持的语言

DocsForge 通过 Pygments 支持 300 多种语言，包括：

- `python`, `py`
- `javascript`, `js`
- `typescript`, `ts`
- `bash`, `sh`, `shell`
- `yaml`, `yml`
- `json`
- `html`
- `css`
- `markdown`, `md`
- `dockerfile`
- `sql`
- `rust`
- `go`
- `java`
- `c`, `cpp`
- `csharp`, `cs`
- `ruby`, `rb`
- `php`
- `lua`
- `r`
- `julia`
- `kotlin`
- `swift`
- `dart`

## 带标题的代码块

```` markdown
``` python title="hello.py"
def hello(name):
    print(f"Hello, {name}!")
```
````

``` python title="hello.py"
def hello(name):
    print(f"Hello, {name}!")
```

## 行号

```` markdown
``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")
    return True
```
````

``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")
    return True
```

## 高亮行

```` markdown
``` python hl_lines="2 3"
def hello(name):
    message = f"Hello, {name}!"
    print(message)
    return message
```
````

``` python hl_lines="2 3"
def hello(name):
    message = f"Hello, {name}!"
    print(message)
    return message
```

## Diff 代码块

显示新增和删除：

```` markdown
``` diff
  def hello(name):
-     print("Hello!")
+     print(f"Hello, {name}!")
      return True
```
````

``` diff
  def hello(name):
-     print("Hello!")
+     print(f"Hello, {name}!")
      return True
```

## 控制台代码块

显示命令输出：

```` markdown
``` console
$ docsforge build
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: site
INFO    -  Documentation built in 2.34 seconds
```
````

``` console
$ docsforge build
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: site
INFO    -  Documentation built in 2.34 seconds
```

## 无复制按钮

禁用特定代码块的复制按钮：

```` markdown
``` python
--8<-- "hello.py"
```
````

或在配置中全局禁用：

``` yaml
theme:
  features:
    # 不要包含 - content.code.copy
```

## 下一步

- [Annotations](annotations.md)
- [Content tabs](content-tabs.md)
