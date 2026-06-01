# Annotations

Annotations add explanations, comments, and callouts directly to code blocks.

## Line numbers

Enable line numbers in code blocks:

```` markdown
``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")  # (1)!
    return True  # (2)!
```

1.  Greet the user with a personalized message
2.  Return success status
````

``` python linenums="1"
def hello(name):
    print(f"Hello, {name}!")  # (1)!
    return True  # (2)!
```

1.  Greet the user with a personalized message
2.  Return success status

## Highlighting lines

Highlight specific lines:

```` markdown
``` python hl_lines="2 4"
def process(data):
    result = []      # Normal
    for item in data:  # Highlighted
        value = item * 2  # Normal
        result.append(value)  # Highlighted
    return result
```
````

``` python hl_lines="2 4"
def process(data):
    result = []      # Normal
    for item in data:  # Highlighted
        value = item * 2  # Normal
        result.append(value)  # Highlighted
    return result
```

## Inline annotations

Add markers in code that reference footnotes:

```` markdown
``` yaml
theme:
  features:
    - navigation.tabs  # (1)!
    - search.highlight  # (2)!
```

1.  Enable tabbed navigation
2.  Highlight search terms in results
````

``` yaml
theme:
  features:
    - navigation.tabs  # (1)!
    - search.highlight  # (2)!
```

1.  Enable tabbed navigation
2.  Highlight search terms in results

## Copy to clipboard

Code blocks get a copy button automatically when `content.code.copy` is enabled:

``` yaml
theme:
  features:
    - content.code.copy
```

## Code block title

Add a title bar to code blocks:

```` markdown
``` yaml title="docsforge.yml"
site_name: My Project
```
````

``` yaml title="docsforge.yml"
site_name: My Project
```

## Next steps

- [Code blocks](code-blocks.md)
- [Content tabs](content-tabs.md)
