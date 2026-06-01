# Formatting

DocsForge extends standard Markdown with additional inline formatting options.

## Highlight

Mark text with `==highlighted==`:

``` markdown
This is ==highlighted text== for emphasis.
```

This is ==highlighted text== for emphasis.

## Subscript

Use `~subscript~`:

``` markdown
H~2~O is the chemical formula for water.
```

H~2~O is the chemical formula for water.

## Superscript

Use `^superscript^`:

``` markdown
The area of a circle is πr^2^.
```

The area of a circle is πr^2^.

## Inserted and deleted text

Use `++inserted++` and `~~deleted~~`:

``` markdown
This is ++new++ and this is ~~old~~.
```

This is ++new++ and this is ~~old~~.

## Keyboard keys

Use `++key++` syntax:

``` markdown
Press ++ctrl+alt+delete++ to restart.

Press ++cmd+shift+3++ to take a screenshot.
```

Press ++ctrl+alt+delete++ to restart.

Press ++cmd+shift+3++ to take a screenshot.

## Mark

Use `==marked==` text (alias for highlight):

``` markdown
==Important==: Read this section carefully.
```

==Important==: Read this section carefully.

## Critic markup

Track changes in drafts:

``` markdown
This is {--deleted--} and this is {++inserted++}.
```

## Smart symbols

Type common symbols easily:

| Input | Output |
|-------|--------|
| `(c)` | © |
| `(tm)` | ™ |
| `(r)` | ® |
| `1/2` | ½ |
| `1/4` | ¼ |
| `+-` | ± |
| `-->` | → |
| `<--` | ← |
| `==>` | ⇒ |
| `<==` | ⇐ |
| `...` | … |

## HTML entities

Use any HTML entity directly:

``` markdown
&copy; &trade; &reg; &mdash; &ndash; &hellip;
```

&copy; &trade; &reg; &mdash; &ndash; &hellip;

## Custom CSS classes

Apply CSS classes to inline elements:

``` markdown
[Text with class]{: .custom-class }
```

Or use `attr_list` extension for more control.

## Next steps

- [Icons & Emojis](icons-emojis.md)
- [Tooltips](tooltips.md)
