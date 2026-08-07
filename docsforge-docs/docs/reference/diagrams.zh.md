# 图表

DocsForge 集成 [Mermaid.js](https://mermaid.js.org)，支持使用文本创建图表。无需外部工具或图像编辑器——只需在代码块中编写图表代码即可。

---

## 配置

默认已启用 Mermaid 支持：

``` yaml
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
```

!!! note "内置"
    Mermaid 已随 DocsForge 一起打包。读者不会发起 CDN 请求；如需外部资源，将在构建时获取。

---

## 流程图

展示流程、决策和工作流：

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

### 流程图方向

| 方向 | 语法 | 说明 |
|-----------|--------|-------------|
| 从左到右 | `graph LR` | 水平流程 |
| 从上到下 | `graph TD` | 垂直流程 |
| 从右到左 | `graph RL` | 反向水平 |
| 从下到上 | `graph BT` | 反向垂直 |

### 节点形状

```mermaid
graph TD
    A[Rectangle] --> B(Rounded)
    B --> C{Decision}
    C --> D[[Subroutine]]
    D --> E[(Database)]
    E --> F((Circle))
```

| 语法 | 形状 |
|--------|-------|
| `A[text]` | 矩形 |
| `A(text)` | 圆角 |
| `A{text}` | 菱形/决策 |
| `A[[text]]` | 子程序 |
| `A[(text)]` | 数据库 |
| `A((text))` | 圆形 |
| `A>text]` | 不对称 |
| `A{text}` | 菱形 |

---

## 序列图

展示实体之间随时间变化的交互：

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

### 箭头类型

| 语法 | 含义 |
|--------|---------|
| `->` | 实线 |
| `-->` | 虚线 |
| `->>` | 实心箭头 |
| `-->>` | 虚线箭头 |
| `-x` | 实心叉 |
| `--x` | 虚线叉 |

---

## 类图

展示面向对象结构：

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

### 关系类型

| 语法 | 含义 |
|--------|---------|
| `-->` | 关联 |
| `*--` | 组合 |
| `o--` | 聚合 |
| `--|>` | 继承 |
| `..>` | 依赖 |
| `--` | 链接 |

---

## 状态图

展示状态机及其转换：

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

## 甘特图

展示项目时间线：

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

### 状态指示器

| 状态 | 语法 | 颜色 |
|--------|--------|-------|
| 已完成 | `:done,` | 绿色 |
| 进行中 | `:active,` | 蓝色 |
| 关键 | `:crit,` | 红色 |
| 默认 | `:,` | 灰色 |

---

## 饼图

展示比例数据：

```mermaid
pie title Distribution
    "Documentation" : 40
    "Code" : 35
    "Tests" : 20
    "Config" : 5
```

---

## Git 图

展示 Git 分支历史：

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

## 思维导图

展示层级概念：

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

## 实体关系图

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

## 用户旅程

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

## C4 图（架构）

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

## 最佳实践

- 保持图表简洁——为保证可读性，节点数量最多 5-10 个
- 同一页面内使用一致的方向（全部 LR 或全部 TD）
- 为箭头添加标签（`-->|label|`）
- 谨慎使用颜色
- 在浅色和深色主题下测试图表
- 避免图表宽度超过内容区域
- 在复杂图表下方添加文字说明，以提升可访问性

---

## 故障排除

### 图表无法渲染

1. 检查 Mermaid 语法是否有效（可使用 [Mermaid Live Editor](https://mermaid.live)）
2. 确保使用 `` ```mermaid `` 围栏（而非 `` ``` ``）
3. 复杂图表可能需要显式启用 `mermaid` 扩展

### 文字过小

将大型图表拆分为较小的子图。可考虑使用 `subgraph`：

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

## 下一步

- [数据表格](data-tables.md)
- [格式化](formatting.md)
- [代码块](code-blocks.md)
