# Content tabs

Content tabs group related content, letting readers switch between alternatives without scrolling.

## Syntax

Use `===` to define tabs:

``` markdown
=== "Tab 1"
    Content for tab 1. Must be indented.

=== "Tab 2"
    Content for tab 2. Must be indented.
```

## Example: Installation methods

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

## Example: Operating systems

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

## Example: Programming languages

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

## Nested tabs

Tabs can contain any Markdown, including other tabs:

``` markdown
=== "Setup"
    === "Linux"
        ``` bash
        sudo apt install python3
        ```
    
    === "Windows"
        ``` powershell
        winget install Python.Python.3.11
        ```

=== "Configuration"
    Edit `docsforge.yml` to customize your site.
```

## Tab labels with icons

Use icons in tab labels:

``` markdown
=== ":material-linux: Linux"
    Linux-specific content.

=== ":material-apple: macOS"
    macOS-specific content.

=== ":material-microsoft-windows: Windows"
    Windows-specific content.
```

## Configuration

Content tabs require the `pymdownx.tabbed` extension:

``` yaml
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
```

The `alternate_style` option provides the modern tabbed interface.

## Next steps

- [Code blocks](code-blocks.md)
- [Admonitions](admonitions.md)
