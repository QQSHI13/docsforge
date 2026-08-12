---
date: 2026-08-12
authors:
  - qq
tags:
  - tikz
  - diagrams
  - features
---

# Publication-Quality Diagrams with TikZ

DocsForge compiles TikZ diagrams to SVG **at build time** — no client-side
JavaScript, no browser plugin, just crisp vector graphics in your docs.

## The workflow

TikZ diagrams live as `.tex` files. Drop them anywhere under your docs
directory and reference them like any image:

```markdown
![Binary Entropy](assets/tikz/binary-entropy.svg)
```

When a LaTeX toolchain is available, DocsForge compiles each diagram with
`latex` + `dvisvgm` (or `pdflatex` + `pdf2svg`) and caches the result — a
change to the `.tex` file triggers a rebuild, everything else is skipped.

## Why TikZ?

| | Mermaid | TikZ |
|---|---------|------|
| Syntax | Text-based, simple | LaTeX-based, powerful |
| Math support | Limited | Full LaTeX math |
| Precision | Layout by algorithm | Pixel-perfect |
| Build | None | Compile to SVG |

See the [diagram demo](../../diagram-demo.md) for five live examples, including
the Shannon communication model and a neural network diagram.

!!! note "Graceful degradation"

    If no LaTeX toolchain is installed, the build warns and skips compilation
    instead of failing. Install `texlive texlive-pictures dvisvgm` to enable it.
