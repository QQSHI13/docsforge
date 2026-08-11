# Code blocks

DocsForge supports rich code blocks with syntax highlighting, titles, line numbers, and more.

## Basic code blocks

Use triple backticks with a language identifier:

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

## Supported languages

DocsForge supports 300+ languages via Pygments, including:

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

## Code block with title

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

## Line numbers

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

## Highlighting lines

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

## Diff blocks

Show additions and deletions:

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

## Console blocks

Show command output:

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

## No copy button

Disable the copy button for a specific block:

```` markdown
``` python
--8<-- "hello.py"
```
````

Or globally disable in config:

``` yaml
theme:
  features:
    # Don't include - content.code.copy
```

## Next steps

- [Annotations](annotations.md)
- [Content tabs](content-tabs.md)
