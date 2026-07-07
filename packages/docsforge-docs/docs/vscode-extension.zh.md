# Visual Studio Code 扩展

DocsForge 提供 VS Code 扩展，让你在编辑器内即可编写、预览和构建文档，无需切换窗口。

## 安装

### 从 GitHub Releases（推荐）

1. 从 [GitHub Releases 页面](https://github.com/QQSHI13/docsforge/releases) 下载最新的 `.vsix` 文件
2. 在 VS Code 中，打开 **Extensions**（`Ctrl+Shift+X`）
3. 点击 **...**（More Actions）菜单 → **Install from VSIX...**
4. 选择下载的 `.vsix` 文件

### 从 VSIX（手动）

```bash
# 通过命令行安装
code --install-extension docsforge-vscode-*.vsix
```

### 前提条件

- **VS Code 1.99+**
- **Python 3.10+** 且已安装 `docsforge`：
  ```bash
  pip install docsforge
  ```

## 快速开始

### 1. 打开 DocsForge 项目

打开包含 `docsforge.yml` 文件的文件夹。扩展会自动激活并提示：

> **"DocsForge project detected. Start dev server?"**

选择 **"Yes"** 立即启动开发服务器，或稍后使用侧边栏。

### 2. 创建新项目

如果你还没有项目：

1. 点击活动栏（左侧边栏）中的 **DocsForge 图标**
2. 点击 **Initialize Project**
3. 按照向导操作：站点名称、描述、主题颜色、语言、隐私模式等
4. 项目会在工作区根目录创建

## 功能

### 侧边栏操作

DocsForge 侧边栏会出现在活动栏中，并显示上下文操作：

| 操作 | 时机 | 作用 |
|--------|------|-------------|
| **Start Server** | 服务器已停止 | 在工作区启动 `docsforge serve --no-open` |
| **Stop Server** | 服务器运行中 | 停止正在运行的开发服务器 |
| **Build** | 始终 | 运行 `docsforge build` 并在通道中显示输出 |
| **Open Preview** | 服务器运行中 | 在 VS Code 内置浏览器中打开站点 |
| **Initialize Project** | 始终 | 以交互方式创建新的 DocsForge 项目 |

### 状态栏

状态栏显示当前服务器状态：

- **`▶ DocsForge: stopped`** —— 点击启动服务器
- **`▶ DocsForge: starting...`** —— 服务器正在启动
- **`▶ DocsForge: http://localhost:8000`** —— 服务器正在运行。点击打开预览

### 开发服务器

扩展在后台运行 `docsforge serve --no-open`：

- 输出流向 **DocsForge** 输出通道（`Ctrl+Shift+U` → 选择 "DocsForge"）
- 进度通知会显示 "Starting DocsForge server..."，直到检测到 URL
- 服务器就绪后，URL 会显示在状态栏中
- VS Code 的内置浏览器处理导航和热重载

### 预览

点击 **Open Preview** 在 VS Code 的 Simple Browser 中查看站点。这是 VS Code 基于 Electron 的浏览器——支持所有功能导航、搜索和页面切换。

### 构建

点击 **Build** 运行 `docsforge build`。输出流向 DocsForge 通道。通知会显示结果。

## 配置

### 设置

| 设置 | 默认值 | 描述 |
|---------|---------|-------------|
| `docsforge.pythonPath` | `"python"` | Python 解释器路径。在 `python` 不是 Python 3 的系统上使用 `"python3"` |
| `docsforge.lan` | `false` | 在所有接口（`0.0.0.0`）上服务，而非仅 localhost |
| `docsforge.openBrowser` | `true` | 服务器启动时在 VS Code 的 Simple Browser 中打开站点 |

### 示例：配置 Python 路径

如果你使用虚拟环境或非默认 Python：

```json
{
  "docsforge.pythonPath": "/home/user/.venv/bin/python"
}
```

或在你的项目中通过 `.vscode/settings.json`：

```json
{
  "docsforge.pythonPath": ".venv/bin/python"
}
```

## 工作流

### 编辑 → 预览循环

1. 从侧边栏 **Start Server**
2. 就绪后点击 **Open Preview**
3. 编辑 Markdown 文件
4. 保存时预览自动重载
5. 完成后 **Stop Server**

### 构建 → 部署

1. 从侧边栏 **Build**
2. 检查输出是否有错误
3. 构建好的站点位于 `site/` —— 可部署到任何地方

### 初始化 → 开发 → 部署

1. **Initialize Project** —— 创建项目结构
2. **Start Server** —— 预览和迭代
3. **Build** —— 生产构建
4. 将 `site/` 部署到你的托管平台

## 故障排除

| 问题 | 解决方法 |
|-------|-----|
| **"Failed to run python"** | 将 `docsforge.pythonPath` 设置为正确的 Python 可执行文件 |
| **"No docsforge.yml found"** | 先运行 **Initialize Project**，或手动创建 `docsforge.yml` |
| **Preview shows blank page** | 检查 VS Code 中的 DevTools 控制台（`Help → Toggle Developer Tools`） |
| **Server won't start** | 打开 DocsForge 输出通道（`Ctrl+Shift+U`）查看错误详情 |
| **"python: command not found"** | 从 [python.org](https://python.org) 安装 Python 3.10+ |

## 命令

所有可用命令（通过 `Ctrl+Shift+P` 访问）：

| 命令 | 描述 |
|---------|-------------|
| `DocsForge: Initialize Project` | 创建新的 docsforge 项目 |
| `DocsForge: Start Dev Server` | 启动开发服务器 |
| `DocsForge: Stop Dev Server` | 停止开发服务器 |
| `DocsForge: Build` | 构建文档 |
| `DocsForge: Open in VS Code Browser` | 打开预览 |
| `DocsForge: Refresh` | 刷新侧边栏 |

### 快速安装

**macOS / Linux：**
```bash
curl -fsSL https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/install.sh | bash
```

**Windows (PowerShell)：**
```powershell
irm https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/install.ps1 | iex
```

### 从 GitHub Releases

从 [GitHub Releases 页面](https://github.com/QQSHI13/docsforge/releases) 下载最新的 `.vsix`，然后：

```
Extensions → … → Install from VSIX… → select the file
```

### 前提条件

查看 [GitHub Releases](https://github.com/QQSHI13/docsforge/releases) 获取新版本。发布包含 Python 包和 `.vsix` 文件。扩展版本与主包版本一致。

## 下一步

- [使用指南](publishing/usage.md) —— 日常使用 DocsForge
- [部署指南](publishing/deployment-guide.md) —— 构建后部署站点
- [功能特性](features.md) —— 所有核心功能
