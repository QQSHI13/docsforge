# Diagrams

DocsForge integrates [Mermaid.js](https://mermaid.js.org) for creating diagrams with text. No external tools or image editors needed — just write the diagram code in a fenced block.

---

## Configuration

Mermaid support is enabled by default:

``` yaml
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
```

!!! note "Vendored"
    Mermaid is bundled with DocsForge. No CDN calls, no external dependencies.

---

## Flowchart

Show processes, decisions, and workflows:

```mermaid
graph LR
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    C --> D[Rethink]
    D --> B
    B ---->|No| E[End]
```

``` markdown
```mermaid
graph LR
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    C --> D[Rethink]
    D --> B
    B ---->|No| E[End]
```
```

### Flowchart direction

| Direction | Syntax | Description |
|-----------|--------|-------------|
| Left-to-right | `graph LR` | Horizontal flow |
| Top-to-bottom | `graph TD` | Vertical flow |
| Right-to-left | `graph RL` | Reverse horizontal |
| Bottom-to-top | `graph BT` | Reverse vertical |

### Node shapes

```mermaid
graph TD
    A[Rectangle] --> B(Rounded)
    B --> C{Decision}
    C --> D[[Subroutine]]
    D --> E[(Database)]
    E --> F((Circle))
```

| Syntax | Shape |
|--------|-------|
| `A[text]` | Rectangle |
| `A(text)` | Rounded |
| `A{text}` | Diamond/Decision |
| `A[[text]]` | Subroutine |
| `A[(text)]` | Database |
| `A((text))` | Circle |
| `A>text]` | Asymmetric |
| `A{text}` | Rhombus |

---

## Sequence diagram

Show interactions between entities over time:

```mermaid
sequenceDiagram
    participant User
    participant DocsForge
    participant GitHub

    User->>DocsForge: Write documentation
    User->>DocsForge: Run build
    DocsForge-->>User: Static site
    User->>GitHub: git push
    GitHub-->>User: Deployed site
```

``` markdown
```mermaid
sequenceDiagram
    participant User
    participant DocsForge
    participant GitHub

    User->>DocsForge: Write documentation
    User->>DocsForge: Run build
    DocsForge-->>User: Static site
    User->>GitHub: git push
    GitHub-->>User: Deployed site
```
```

### Arrow types

| Syntax | Meaning |
|--------|---------|
| `->` | Solid line |
| `-->` | Dotted line |
| `->>` | Solid arrow |
| `-->>` | Dotted arrow |
| `-x` | Solid cross |
| `--x` | Dotted cross |

---

## Class diagram

Show object-oriented structure:

```mermaid
classDiagram
    class Site {
        +String name
        +String url
        +build()
        +serve()
    }
    class Theme {
        +String name
        +configure()
    }
    class Plugin {
        +String name
        +load()
    }
    Site --> Theme : uses
    Site *-- Plugin : contains
```

### Relationship types

| Syntax | Meaning |
|--------|---------|
| `-->` | Association |
| `*--` | Composition |
| `o--` | Aggregation |
| `--|>` | Inheritance |
| `..>` | Dependency |
| `--` | Link |

---

## State diagram

Show state machines and transitions:

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Review: Submit
    Review --> Published: Approve
    Review --> Draft: Reject
    Published --> [*]
```

``` markdown
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Review: Submit
    Review --> Published: Approve
    Review --> Draft: Reject
    Published --> [*]
```
```

---

## Gantt chart

Show project timelines:

```mermaid
gantt
    title DocsForge Roadmap
    dateFormat  YYYY-MM-DD
    section Q1
    Core features    :done, a1, 2025-01-01, 2025-02-28
    Testing          :active, a2, 2025-03-01, 2025-03-31
    section Q2
    Release          :a3, 2025-04-01, 2025-04-30
    Documentation    :a4, 2025-05-01, 2025-06-30
```

``` markdown
```mermaid
gantt
    title DocsForge Roadmap
    dateFormat  YYYY-MM-DD
    section Q1
    Core features    :done, a1, 2025-01-01, 2025-02-28
    Testing          :active, a2, 2025-03-01, 2025-03-31
    section Q2
    Release          :a3, 2025-04-01, 2025-04-30
    Documentation    :a4, 2025-05-01, 2025-06-30
```
```

### Status indicators

| Status | Syntax | Color |
|--------|--------|-------|
| Done | `:done,` | Green |
| Active | `:active,` | Blue |
| Critical | `:crit,` | Red |
| Default | `:,` | Gray |

---

## Pie chart

Show proportional data:

```mermaid
pie title Distribution
    "Documentation" : 40
    "Code" : 35
    "Tests" : 20
    "Config" : 5
```

---

## Git graph

Show Git branch history:

```mermaid
gitGraph
    commit
    branch develop
    checkout develop
    commit
    commit
    checkout main
    merge develop
    commit
```

---

## Mindmap

Show hierarchical concepts:

```mermaid
mindmap
  root((DocsForge))
    Getting Started
      Installation
      Quick Start
    Setup
      Colors
      Fonts
      Navigation
    Reference
      Admonitions
      Code Blocks
      Diagrams
```

---

## Entity relationship diagram

```mermaid
erDiagram
    USER ||--o{ DOCUMENT : creates
    USER {
        string username
        string email
    }
    DOCUMENT {
        string title
        string content
        date created_at
    }
```

---

## User journey

```mermaid
journey
    title User journey for DocsForge
    section Install
      Download: 5: User
      Install: 4: User
    section Setup
      Configure: 3: User, DocsForge
      Build: 5: DocsForge
    section Deploy
      Push: 4: User
      Host: 5: DocsForge
```

---

## C4 diagram (architecture)

```mermaid
C4Context
    title System Context Diagram
    Person(user, "User", "Documentation reader")
    System(docsforge, "DocsForge", "Documentation engine")
    System_Ext(github, "GitHub", "Hosting platform")
    Rel(user, docsforge, "Reads docs")
    Rel(docsforge, github, "Deploys to")
```

---

## Best practices

- Keep diagrams simple — 5-10 nodes maximum for readability
- Use consistent direction within a page (all LR or all TD)
- Add labels to arrows (`-->|label|`)
- Use colors sparingly
- Test diagrams in both light and dark themes
- Avoid diagrams wider than the content area
- Add a text description below complex diagrams for accessibility

---

## Troubleshooting

### Diagram not rendering

1. Check Mermaid syntax is valid (use [Mermaid Live Editor](https://mermaid.live))
2. Ensure ` ```mermaid ` fence is used (not ` ``` `)
3. Complex diagrams may need `mermaid` extension explicitly enabled

### Text too small

Break large diagrams into smaller sub-diagrams. Consider using `subgraph`:

```mermaid
graph TD
    subgraph Authentication
        A[Login] --> B[Verify]
    end
    subgraph Content
        C[Load] --> D[Render]
    end
    B --> C
```

---

## Next steps

- [Data tables](data-tables.md)
- [Formatting](formatting.md)
- [Code blocks](code-blocks.md)
