---
tags:
  - latex
  - math
  - reference
---

# LaTeX Equations in Markdown

This page demonstrates every supported way to write and embed LaTeX math in Markdown, and explicitly shows situations where Markdown rendering or LaTeX rendering should be disabled.

---

## 1. Inline Math

Inline math is wrapped in single dollar signs `$...$` and rendered on the same line as the surrounding text.

| Syntax | Example |
|--------|---------|
| `$E = mc^2$` | $E = mc^2$ |
| `$a^2 + b^2 = c^2$` | $a^2 + b^2 = c^2$ |
| `$\frac{1}{2}$` | $\frac{1}{2}$ |
| `$\sum_{i=1}^{n} x_i$` | $\sum_{i=1}^{n} x_i$ |
| `$\alpha \beta \gamma$` | $\alpha \beta \gamma$ |

Einstein showed that $E = mc^2$, while the Pythagorean theorem states $a^2 + b^2 = c^2$.

---

## 2. Display Math

Display math is wrapped in double dollar signs `$$...$$` and rendered as a centered block.

```markdown
$$
E = mc^2
$$
```

$$
E = mc^2
$$

```markdown
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$
```

$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

---

## 3. Math with Delimiters

Some renderers also support these delimiters:

| Delimiter | Type | Example |
|-----------|------|---------|
| `\(...\)` | Inline | \( \sin^2\theta + \cos^2\theta = 1 \) |
| `\[...\]` | Display | \[ \nabla \cdot \mathbf{E} = \frac{\rho}{\varepsilon_0} \] |
| `` `...` `` with `$` | Code-style inline | `$E=mc^2$` |

\[ \nabla \cdot \mathbf{E} = \frac{\rho}{\varepsilon_0} \]

`$E=mc^2$`

---

## 4. Common LaTeX Constructs

### Fractions

$$
\frac{a}{b}, \quad \frac{x^2 + 1}{x - 1}, \quad \frac{\partial f}{\partial x}
$$

### Subscripts and Superscripts

$$
x_i, \quad x^2, \quad x_i^j, \quad a_{n+1}
$$

### Roots

$$
\sqrt{2}, \quad \sqrt[n]{x}, \quad \sqrt{x^2 + y^2}
$$

### Greek Letters

$$
\alpha, \beta, \gamma, \Gamma, \delta, \Delta, \epsilon, \varepsilon, \pi, \Pi, \sigma, \Sigma, \phi, \varphi, \Phi
$$

### Sums, Products, and Limits

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$

$$
\prod_{i=1}^{n} i = n!
$$

$$
\lim_{x \to 0} \frac{\sin x}{x} = 1
$$

### Integrals

$$
\int_a^b f(x)\,dx
$$

$$
\oint_C \mathbf{F} \cdot d\mathbf{r}
$$

### Matrices

$$
\begin{bmatrix}
1 & 2 & 3 \\
4 & 5 & 6 \\
7 & 8 & 9
\end{bmatrix}
$$

$$
\begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
$$

### Multiline Alignment

$$
\begin{aligned}
\nabla \cdot \mathbf{E} &= \frac{\rho}{\varepsilon_0} \\
\nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t}
\end{aligned}
$$

### Cases

$$
f(x) =
\begin{cases}
x^2 & \text{if } x \ge 0 \\
-x^2 & \text{if } x < 0
\end{cases}
$$

### Operators

$$
\sin x, \cos x, \tan x, \log x, \ln x, \exp x, \det A, \ker f, \dim V
$$

### Accents and Decorations

$$
\hat{x}, \bar{x}, \tilde{x}, \vec{x}, \dot{x}, \ddot{x}, \overline{AB}
$$

---

## 5. Math Inside Markdown Containers

### In Admonitions

!!! note "Math in a note"
    The quadratic formula is:
    $$
    x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
    $$

### In Lists

1. Inline math in a list: $a + b = c$
2. Display math in a list:
   $$
   \sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
   $$
3. Final item with $\LaTeX$ inline.

### In Blockquotes

> The Euler-Lagrange equation is
> $$
> \frac{d}{dt}\frac{\partial L}{\partial \dot{q}} - \frac{\partial L}{\partial q} = 0
> $$

### In Tables

| Operation | LaTeX | Result |
|-----------|-------|--------|
| Addition | `$a + b$` | $a + b$ |
| Multiplication | `$a \cdot b$` | $a \cdot b$ |
| Division | `$\frac{a}{b}$` | $\frac{a}{b}$ |
| Exponent | `$a^b$` | $a^b$ |

---

## 6. Escaping Dollar Signs

To show a literal dollar sign without triggering math mode, escape it with a backslash: `\$50` renders as \$50.

A price like \$10 + \$20 = \$30 should not become math.

---

## 7. Where Markdown Should NOT Be Rendered

In the following places Markdown formatting must be treated as plain text.

### Inside Inline Code

Backticks suppress Markdown formatting: `**bold**`, `[link](url)`, `$not math$`.

### Inside Fenced Code Blocks

```markdown
# This is not a heading
**This is not bold**
[This is not a link](https://example.com)
> This is not a blockquote
```

### Inside Code Blocks with Other Languages

```python
# Python comment, not a Markdown heading
def hello():
    print("**not bold**")
```

```html
<!-- HTML comment -->
<p>**not bold**</p>
```

### Inside Inline HTML

<span>**this is not bold**</span>

<div>
# This is not a heading inside raw HTML
</div>

### Inside URLs and Email Addresses

`https://example.com/path_with_underscores` should keep its underscores.

An email like `user_name@example.com` should not italicize `_name`.

---

## 8. Where LaTeX Should NOT Be Rendered

In the following places dollar signs and backslash commands must remain literal text.

### Inside Inline Code

`$E = mc^2$` should not render as math.

`\frac{a}{b}` should remain a literal backslash command.

### Inside Fenced Code Blocks

```markdown
$$
E = mc^2
$$
```

```latex
\documentclass{article}
\begin{document}
$E = mc^2$
\end{document}
```

```python
# A variable named $total is just a string
price = "$10"
```

### In Plain Text About Currency

The total cost is $50, not $E = mc^2$.

Prices like $1.99, $20.00, and $100 should remain currency.

### Inside HTML Attributes

```html
<img alt="$price" src="image.png">
```

### In URLs

`https://example.com/$var/path` should keep `$var` as a URL segment.

### In File Paths and Shell Commands

```bash
cd $HOME
ls -la /usr/local/bin
echo "Price: $5.00"
```

### In YAML Front Matter

```yaml
---
title: "$E = mc^2$ should be literal"
price: "$10"
---
```

### In Inline HTML Tags

<span>$x^2$</span> should not be processed as math.

---

## 9. Mixed Edge Cases

### Math Next to Punctuation

The equation $E = mc^2$, derived by Einstein, changed physics.

### Multiple Inline Expressions

For $x \in \mathbb{R}$ and $\varepsilon > 0$, there exists $\delta > 0$ such that $|x - a| < \delta$ implies $|f(x) - f(a)| < \varepsilon$.

### Multi-line Display Without Alignment

$$
f(x) = x^2 + 2x + 1
$$

$$
g(x) = \sin(x) + \cos(x)
$$

---

## 10. Reference Table

| Syntax | Render Math? | Render Markdown? | Use Case |
|--------|--------------|------------------|----------|
| `$...$` | Yes | No inside | Inline math |
| `$$...$$` | Yes | No inside | Display math |
| `\(...\)` | Yes (if supported) | No inside | Inline math alternative |
| `\[...\]` | Yes (if supported) | No inside | Display math alternative |
| `` `...` `` | No | No | Code / literal text |
| ```` ``` ```` | No | No | Code blocks |
| Raw HTML | No | No | HTML passthrough |
| YAML front matter | No | No | Metadata |
