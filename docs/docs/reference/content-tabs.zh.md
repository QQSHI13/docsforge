# 内容标签页

内容标签页将相关内容分组，让读者可以在不同选项之间切换，而无需滚动页面。

## 语法

使用 `===` 定义标签页：

``` markdown
=== "标签页 1"
    标签页 1 的内容。必须缩进。

=== "标签页 2"
    标签页 2 的内容。必须缩进。
```

## 示例：安装方法

``` markdown
=== "pip"
    ``` bash
    pip install mypackage
    ```

=== "conda"
    ``` bash
    conda install mypackage
    ```

=== "Docker"
    ``` bash
    docker pull mypackage:latest
    ```
```

=== "pip"
    ``` bash
    pip install mypackage
    ```

=== "conda"
    ``` bash
    conda install mypackage
    ```

=== "Docker"
    ``` bash
    docker pull mypackage:latest
    ```

## 示例：操作系统

``` markdown
=== "Linux"
    ``` bash
    docsforge serve
    ```

=== "macOS"
    ``` bash
    docsforge serve
    ```

=== "Windows"
    ``` powershell
    docsforge serve
    ```
```

=== "Linux"
    ``` bash
    docsforge serve
    ```

=== "macOS"
    ``` bash
    docsforge serve
    ```

=== "Windows"
    ``` powershell
    docsforge serve
    ```

## 示例：编程语言

``` markdown
=== "Python"
    ``` python
    def greet(name):
        return f"Hello, {name}!"
    ```

=== "JavaScript"
    ``` javascript
    function greet(name) {
        return `Hello, ${name}!`;
    }
    ```

=== "Rust"
    ``` rust
    fn greet(name: &str) -> String {
        format!("Hello, {}!", name)
    }
    ```
```

=== "Python"
    ``` python
    def greet(name):
        return f"Hello, {name}!"
    ```

=== "JavaScript"
    ``` javascript
    function greet(name) {
        return `Hello, ${name}!`;
    }
    ```

=== "Rust"
    ``` rust
    fn greet(name: &str) -> String {
        format!("Hello, {}!", name)
    }
    ```

## 嵌套标签页

标签页可以包含任何 Markdown 内容，包括其他标签页：

``` markdown
=== "设置"
    === "Linux"
        ``` bash
        sudo apt install python3
        ```
    
    === "Windows"
        ``` powershell
        winget install Python.Python.3.11
        ```

=== "配置"
    编辑 `docsforge.yml` 以自定义你的网站。
```

## 带图标的标签页标签

在标签页标签中使用图标：

``` markdown
=== ":material-linux: Linux"
    Linux 专属内容。

=== ":material-apple: macOS"
    macOS 专属内容。

=== ":material-microsoft-windows: Windows"
    Windows 专属内容。
```

## 配置

内容标签页需要启用 `pymdownx.tabbed` 扩展：

``` yaml
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
```

`alternate_style` 选项提供现代的标签页界面。

## 下一步

- [代码块](code-blocks.md)
- [提示框](admonitions.md)
