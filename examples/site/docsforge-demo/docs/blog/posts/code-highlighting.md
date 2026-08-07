---
date: 2026-05-09
authors:
  - nova
tags:
  - code
  - pygments
  - features
---

# Code Highlighting with Pygments

DocsForge uses Pygments for build-time syntax highlighting.

## Python

```python
def hello_world():
    """Say hello to DocsForge."""
    print("Hello, World!")
    return True
```

## Rust

```rust
fn main() {
    println!("Hello from Rust!");
}
```

## Go

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello from Go!")
}
```

No client-side JavaScript required!
