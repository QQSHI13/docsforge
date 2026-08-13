---
icon: material/source-branch
---

# 添加 Git 仓库

将你的文档与其源代码仓库关联。这会添加一个“编辑此页”按钮，并在页眉中显示仓库名称。

## 基础配置

``` yaml
repo_name: username/repo
repo_url: https://github.com/username/repo
```

## 编辑按钮

启用“编辑此页”按钮：

``` yaml
theme:
  features:
    - content.action.edit
```

这会添加一个铅笔图标，直接链接到 GitHub（或你的提供商）上的源文件。

## 查看源代码按钮

在编辑按钮旁边启用“查看源代码”按钮：

``` yaml
theme:
  features:
    - content.action.edit
    - content.action.view
```

## 自定义提供商

DocsForge 支持任何遵循 GitHub URL 模式的 Git 提供商：

``` yaml
repo_url: https://gitlab.com/username/repo
# or
repo_url: https://bitbucket.org/username/repo
# or
repo_url: https://gitea.example.com/username/repo
```

## 仓库图标

仓库图标显示在页眉中。它会根据 URL 自动确定：

- `github.com` → GitHub icon
- `gitlab.com` → GitLab icon
- `bitbucket.org` → Bitbucket icon

## 自定义编辑路径

如果你的文档位于仓库的某个子目录中：

``` yaml
edit_uri: edit/main/docs/
```

完整的编辑 URL 将变为：`https://github.com/username/repo/edit/main/docs/page.md`

## 完整示例

``` yaml
repo_name: myproject/docs
repo_url: https://github.com/myproject/docs
edit_uri: edit/main/docs/

theme:
  features:
    - content.action.edit
    - content.action.view
```

## 下一步

- [发布你的网站](../publishing-your-site.md)
- [设置概览](index.md)

## 故障排除

### 编辑按钮 404

如果编辑按钮跳转到了 404 页面：

1. 检查 `edit_uri` 是否与你的仓库结构匹配
2. GitHub：`edit_uri: edit/main/docs/`（分支 + docs 文件夹）
3. GitLab：`edit_uri: edit/main/docs/-/blob/`（不同的路径格式）
4. 确保仓库是公开的（或用户有访问权限）

### 显示错误的图标

仓库图标会根据 URL 自动检测。如果显示了错误的图标：

1. 检查 `repo_url` 是否正确
2. 要自定义图标，请在 `docsforge.yml` 中设置 `theme.icon.repo`：
   ```yaml
   theme:
     icon:
       repo: fontawesome/brands/github
   ```

## 私有仓库

对于私有仓库，有访问权限的用户仍然可以使用编辑按钮：

``` yaml
repo_url: https://github.com/mycompany/private-docs
```

没有访问权限的用户点击编辑按钮时会看到 404。可以考虑在你的文档中添加一条相关说明。
