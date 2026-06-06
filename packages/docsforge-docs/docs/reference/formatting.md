# Formatting

DocsForge extends standard Markdown with additional inline formatting options for emphasis, technical notation, and special characters.

---

## Highlight

Mark text with `==highlighted==` for emphasis:

``` markdown
This is ==highlighted text== for emphasis.
```

This is ==highlighted text== for emphasis.

Use highlights to draw attention to key terms, warnings, or important notes within a paragraph.

---

## Subscript

Use `~subscript~` for chemical formulas and mathematical notation:

``` markdown
H~2~O is the chemical formula for water.

CO~2~ emissions are a major concern.

E = mc~2~ is Einstein's famous equation.
```

H~2~O is the chemical formula for water.

CO~2~ emissions are a major concern.

E = mc~2~ is Einstein's famous equation.

---

## Superscript

Use `^superscript^` for exponents and ordinal numbers:

``` markdown
The area of a circle is πr^2^.

x^2^ + y^2^ = z^2^

1^st^, 2^nd^, 3^rd^
```

The area of a circle is πr^2^.

x^2^ + y^2^ = z^2^

1^st^, 2^nd^, 3^rd^

---

## Inserted and deleted text

Use `++inserted++` and `~~deleted~~` for tracking changes:

``` markdown
This is ++new++ and this is ~~old~~.

The price is ~~$50~~ ++$45++.
```

This is ++new++ and this is ~~old~~.

The price is ~~$50~~ ++$45++.

!!! tip "Diff-like syntax"
    This is useful for showing changes in documentation, changelogs, or migration guides.

---

## Keyboard keys

Use `++key++` syntax for keyboard shortcuts:

``` markdown
Press ++ctrl+alt+delete++ to restart.

Press ++cmd+shift+3++ to take a screenshot.

Press ++ctrl+s++ to save.

Press ++enter++ to confirm.
```

Press ++ctrl+alt+delete++ to restart.

Press ++cmd+shift+3++ to take a screenshot.

Press ++ctrl+s++ to save.

Press ++enter++ to confirm.

### Key combinations

| Syntax | Renders as |
|--------|------------|
| `++ctrl+c++` | ++ctrl+c++ |
| `++ctrl+v++` | ++ctrl+v++ |
| `++ctrl+z++` | ++ctrl+z++ |
| `++cmd+tab++` | ++cmd+tab++ |
| `++alt+f4++` | ++alt+f4++ |
| `++shift+delete++` | ++shift+delete++ |
| `++enter++` | ++enter++ |
| `++escape++` | ++escape++ |
| `++space++` | ++space++ |

---

## Mark (alias for highlight)

Use `==marked==` text (same as highlight):

``` markdown
==Important==: Read this section carefully.
```

==Important==: Read this section carefully.

---

## Critic markup

Track changes in drafts with critic markup:

``` markdown
This is {--deleted--} and this is {++inserted++}.

This is {~~changed~>to this~~}.
```

This is {--deleted--} and this is {++inserted++}.

This is {~~changed~>to this~~}.

!!! note "Critic markup extension"
    Requires `pymdownx.critic` extension to be enabled. It is enabled by default in DocsForge.

---

## Smart symbols

Type common symbols easily:

| Input | Output | Input | Output |
|-------|--------|-------|--------|
| `(c)` | © | `(tm)` | ™ |
| `(r)` | ® | `1/2` | ½ |
| `1/4` | ¼ | `3/4` | ¾ |
| `+-` | ± | `-->` | → |
| `<--` | ← | `<->` | ↔ |
| `==>` | ⇒ | `<==` | ⇐ |
| `<=>` | ⇔ | `...` | … |
| `--` | – | `---` | — |

``` markdown
(c) (tm) (r) 1/2 1/4 +- --> <-- ==> <== ...
```

(c) (tm) (r) 1/2 1/4 +- --> <-- ==> <== ...

---

## HTML entities

Use any HTML entity directly in Markdown:

``` markdown
&copy; &trade; &reg; &mdash; &ndash; &hellip; &larr; &rarr; &uarr; &darr;
```

&copy; &trade; &reg; &mdash; &ndash; &hellip; &larr; &rarr; &uarr; &darr;

---

## Custom CSS classes

Apply CSS classes to inline elements:

``` markdown
[Text with class]{: .custom-class }

[Red text]{: .red }

[Large text]{: .lg }
```

Requires defining the CSS classes in your custom stylesheet.

---

## Combining formatting

Mix multiple formatting styles:

``` markdown
**Bold and ==highlighted== text**

*Italic and ~subscript~ text*

`Code with ^superscript^`

[Link with **bold** text](https://example.com)
```

**Bold and ==highlighted== text**

*Italic and ~subscript~ text*

`Code with ^superscript^`

[Link with **bold** text](https://example.com)

---

## Mathematical notation

For complex math, use the built-in KaTeX support:

``` markdown
$$
E = mc^2
$$

$$
\sum_{i=1}^{n} x_i = x_1 + x_2 + \cdots + x_n
$$
```

$$
E = mc^2
$$

$$
\sum_{i=1}^{n} x_i = x_1 + x_2 + \cdots + x_n
$$

See [Code blocks](code-blocks.md) for more on math blocks.

---

## Best practices

- Use **highlighting** sparingly — overuse makes it meaningless
- Prefer `==highlight==` over raw `<mark>` tags for portability
- Use subscript/superscript for actual mathematical/chemical notation, not styling
- Keyboard keys are great for tutorials, quick starts, and user guides
- Critic markup is useful for collaborative editing and changelogs
- Don't nest too many formatting styles — it becomes hard to read
- Test how special characters render in search results

---

## Next steps

- [Icons & Emojis](icons-emojis.md)
- [Tooltips](tooltips.md)
- [Annotations](annotations.md)
