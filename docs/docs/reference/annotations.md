---
icon: material/comment-plus-outline
---

# Annotations

Annotations add explanations, comments, and callouts directly to code blocks. They help readers understand complex code without breaking the flow.

---

## Line numbers

Enable line numbers in code blocks with `linenums`:

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

### Start from a specific line

Start numbering from any line:

```` markdown
``` python linenums="42"
def meaning_of_life():
    return 42  # (1)!
```

1.  The ultimate answer
````

``` python linenums="42"
def meaning_of_life():
    return 42  # (1)!
```

1.  The ultimate answer

---

## Highlighting lines

Highlight specific lines with `hl_lines`:

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

### Highlight ranges

Highlight a range of lines:

```` markdown
``` python hl_lines="2-4"
def setup():
    config = load_config()  # Highlighted
    validate(config)        # Highlighted
    apply_defaults(config)  # Highlighted
    return config
```
````

---

## Inline annotations

Add markers in code that reference footnotes below the block:

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

### Multiple annotations per line

You can have multiple annotations on the same line:

```` markdown
``` python
x = calculate()  # (1)! (2)!
```

1.  This calls the calculate function
2.  Result is stored in x
````

---

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

---

## Copy to clipboard

Code blocks get a copy button automatically when `content.code.copy` is enabled in your `docsforge.yml`:

``` yaml
theme:
  features:
    - content.code.copy
```

The copy button appears in the top-right corner of every code block on hover.

---

## Diff highlighting

Show code changes with `diff` highlighting:

```` markdown
``` python
  def old_function():
-     return "old"
+     return "new"
```
````

---

## Combining features

You can combine multiple features:

```` markdown
``` python title="config.py" linenums="1" hl_lines="3"
def configure():
    settings = {}
    settings['debug'] = True  # (1)!
    return settings
```

1.  Enable debug mode for development
````

``` python title="config.py" linenums="1" hl_lines="3"
def configure():
    settings = {}
    settings['debug'] = True  # (1)!
    return settings
```

1.  Enable debug mode for development

---

## Best practices

- Use annotations sparingly — too many footnotes clutter the page
- Keep annotation text concise (1-2 sentences)
- Use highlighting to draw attention to changed or important lines
- Line numbers are helpful for referencing specific lines in surrounding text
- Always include a title when showing configuration files

## Next steps

- [Code blocks](code-blocks.md)
- [Content tabs](content-tabs.md)
- [Formatting](formatting.md)
