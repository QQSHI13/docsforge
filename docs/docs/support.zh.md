---
icon: material/help-circle
---

# 支持

DocsForge 免费且开源。如果你遇到问题、需要迁移帮助或发现了 bug —— 我们随时提供帮助。

## 若迁移过程中出现任何问题，我们免费修复

从 MkDocs + Material for MkDocs 迁移，不该让你花一周时间去调试。如果站点在
DocsForge 下无法构建，或渲染结果与迁移前不同：

**把细节发给我们，我们会持续修复 DocsForge —— 或你的配置 —— 直到一致，不收取
任何费用。** 此承诺长期有效。

=== "GitHub issue"

    [提交 issue](https://github.com/QQSHI13/docsforge/issues)，附上你的
    `mkdocs.yml` 和仓库链接。开源站点推荐这种方式，讨论结果也能帮到其他人。

=== "邮件"

    发送邮件至 **qingquanshi65@gmail.com**，主题注明 `[MIGRATION]`。
    如果文档涉及隐私、配置敏感，或只是不想公开贴出配置，请走这条路 ——
    两种方式享受同样的承诺。

## 最快路径：一键迁移脚本

从 **MkDocs、ProperDocs 或 Zensical** 迁移？一条命令即可转换现有配置 —— 脚本会把
`mkdocs.yml` / `properdocs.yml` / `zensical.toml` 自动转换为 `docsforge.yml`：

=== "macOS / Linux"

    ``` bash
    curl -fsSL https://qqshi13.github.io/docsforge/migrate.sh | bash
    ```

=== "Windows (PowerShell)"

    ``` powershell
    irm https://qqshi13.github.io/docsforge/migrate.ps1 | iex
    ```

脚本会：

- 转换导航、主题、插件和扩展，
- 对无法迁移的内容（第三方插件、`INHERIT`、钩子）发出警告，
- 并打印一份报告，告诉你需要检查哪些内容。

遇到无法处理的内容？发邮件或开 issue —— 我们会帮你迁移。

## 获取帮助

| 需求 | 途径 |
|------|-------|
| **Bug、功能请求** | [GitHub Issues](https://github.com/QQSHI13/docsforge/issues) |
| **安全漏洞** | [安全策略](https://github.com/QQSHI13/docsforge/blob/main/SECURITY.md)（私密报告） |
| **迁移帮助、私人问题** | **qingquanshi65@gmail.com**（主题注明 `[MIGRATION]`） |
| **在线演示** | [Live demo](https://docsforge-demo.pages.dev) |

## 报告中应包含什么

为获得最快答复，请提供：

1. `docsforge --version`（如相关，也提供 Python 版本）
2. 操作系统
3. 你的 `docsforge.yml`（如需保密可打码）—— 或完整的错误信息
4. 复现步骤

对于迁移脚本无法转换的插件、钩子或功能，请告诉我们：

- 转换失败的配置片段，
- 你希望它实现的功能，
- 我们会帮你移植，或指出内置的等价方案。

## 先看哪里

- [故障排除](troubleshooting.md) —— 常见问题与修复
- [迁移指南](publishing/migration.md) —— 逐键映射详解
- [更新日志](changelog/index.md) —— 每个版本的变化
