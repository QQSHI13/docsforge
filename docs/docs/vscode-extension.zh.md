---
icon: material/microsoft-visual-studio-code
---

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

### Cursor

Cursor 原生运行 VS Code 扩展——同一个 `.vsix`，同样步骤：

```bash
cursor --install-extension docsforge-vscode-*.vsix
```

或在 Cursor 内打开 Extensions → **...** → **Install from VSIX...**。

### 编辑器支持

支持 VS Code 1.85+ 与 Cursor。Zed 与 JetBrains IDE
不受支持：Studio 直接构建于 VS Code 扩展 API
之上且没有语言服务器，因而不存在可移植的兼容层——基于服务器的扩展
（如 Zensical）才能覆盖这些编辑器。

### 前提条件

- **VS Code 1.85+**
- **Python 3.10+** 且已安装 `docsforge`：
  ```bash
  pip install docsforge
  ```

如果缺 `docsforge`，扩展会主动提出装进项目 `.venv`、用户目录或全局——无需手工配置。

## 更新

不用再盯着 releases 页面。扩展在两个通道上自我更新：

### 检查更新

通过命令面板（`Ctrl+Shift+P`）运行 **`DocsForge: Check for Updates`**，也可以点侧边栏 Actions 视图或侧边栏标题栏。一次检查覆盖两边：

- **引擎** —— `docsforge` Python 包，与 PyPI 对比。更新会在项目已用的解释器（venv、用户、全局）里执行 `pip install docsforge==<版本>`，进度和输出都在 DocsForge 通道可见。预发布引擎版本（如 `13.0.0b3`）现在能与稳定版正确比较，beta 检出不会再被误判为最新。可编辑安装（`pip install -e .`）完全不参与更新检查：它跟进源码，用 `git pull` + 重装更新即可。成功检查的结果会被缓存，离线时手动检查复用上次版本（标注为缓存）而非直接失败。在 PEP 668 外部管理解释器（Debian/Ubuntu 系统 Python）上，安装与升级自动追加 `--break-system-packages`（`--user` 安装保留原标志）；当多个解释器都装有 DocsForge 时，每个流程都会询问使用哪一个，不再猜测。
- **扩展** —— VSIX 本体，与 GitHub releases 对比。更新会把 `.vsix` 下载到临时目录并安装，然后提示重载窗口。

### 自动检查

启动约 45 秒后，扩展会在后台静默检查一次，仅在有更新时通知你。同一版本最多提醒一次，彻底关闭用：

```json
{
  "docsforge.autoCheckUpdates": false
}
```

### 预发布版本

Beta/alpha 默认跳过。想跟进 `13.0.0bN` 这类测试版（当前 beta 期间推荐打开）：

```json
{
  "docsforge.includePrereleases": true
}
```

检查到新版本后，侧边栏 Actions 项会直接在行内显示可用版本，例如 `Check for Updates — engine 12.5.7 → 13.0.0b3`。

> **还在用 12.5.7 或更早？** 那些版本没有更新器——按上面的方法手工装一次新版 VSIX，之后每次更新都是一次点击的事。

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
4. 项目会在工作区根目录创建，编辑器功能立即生效，无需重载窗口

## 功能

### 侧边栏操作

DocsForge 侧边栏会出现在活动栏中，并显示上下文操作：

| 操作 | 时机 | 作用 |
|--------|------|-------------|
| **Start Server** | 服务器已停止 | 在工作区启动 `docsforge serve --no-open` |
| **Stop Server** | 服务器运行中 | 停止正在运行的开发服务器 |
| **Build** | 始终 | 运行 `docsforge build` 并在通道中显示输出 |
| **Stop Build** | 构建运行中 | 取消正在运行的构建 |
| **Open Preview** | 服务器运行中 | 在 VS Code 内置浏览器中打开站点 |
| **Open Built Page** | 服务器运行中 | 打开当前文档对应的构建后 HTML |
| **Initialize Project** | 始终 | 以交互方式创建新的 DocsForge 项目 |
| **New Page** | 始终 | 创建文档页，可附带翻译桩与导航条目 |
| **Open Docs** | 始终 | 打开 DocsForge 文档站 |
| **Check Python Environment** | 始终 | 检测 Python，缺失时安装 DocsForge |
| **Rename Document** | 始终 | 重命名文档并更新所有指向它的链接 |
| **Rename Anchor** | 始终 | 重命名标题并更新所有指向该锚点的链接 |
| **Refresh Diagnostics** | 始终 | 重读构建校验缓存并刷新波浪线 |
| **Check for Updates** | 始终 | 检查引擎与扩展更新，发现新版本时行内显示 |

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

### 多项目（multi-root）

每个打开的文件夹拥有独立的服务器、构建与 Python 环境。Serve/Build 作用于当前文件所在项目（多个项目打开且无文件上下文时弹出选择器），多文件夹时状态栏会标出项目名，Open Built Page 使用当前文档所属项目的服务器。

### 预览

点击 **Open Preview** 在 VS Code 的 Simple Browser 中查看站点。这是 VS Code 基于 Electron 的浏览器——支持所有功能导航、搜索和页面切换。

### 构建

点击 **Build** 运行 `docsforge build`。输出流向 DocsForge 通道。通知会显示结果。构建结束后诊断信息自动刷新。

### 编辑器智能功能

无需语言服务器——扩展直接读取你的项目：

- **诊断** —— 坏链、缺失锚点、脚注问题、缺失/孤儿翻译以下划波浪线标出，数据来自构建校验缓存，每次构建后刷新，也可手动 Refresh Diagnostics
- **链接导航** —— 在 Markdown 链接上跳转定义、悬停预览可跳到目标文档与锚点；在 `(...)` 内输入有项目文件路径补全
- **锚点补全** —— 在链接内 `#` 后补全目标文档的标题 slug（`](#…)` 指当前文件），标题索引缓存在 `.docsforge/studio/` 中
- **片段补全** —— 在 `--8<-- "…"` 包含中补全同目录文件与文档树路径（优先相对源文件所在目录解析）
- **Frontmatter 补全** —— 已知键（`title`、`description`、`icon`、`tags`、`hide`、`search`、`template` 等）及 `hide:`/`search:` 取值，Ctrl+Space 触发；自定义键合法，绝不误报
- **重命名** —— Rename Document 移动文件（含翻译）并一次性改写所有相关链接（可撤销）；Rename Anchor 对标题同理，含同页 `[text](#anchor)` 链接。在资源管理器里重命名文件夹也会更新链接
- **快速修复** —— 坏链上的小灯泡提供修复；多个同名文件时由你选择目标，批量修复只覆盖无歧义链接
- **格式化** —— Format Document 整理行尾空格与空行（配合 `editor.formatOnSave` 可保存时自动执行）

## 配置

### 设置

| 设置 | 默认值 | 描述 |
|---------|---------|-------------|
| `docsforge.pythonPath` | `"python"` | Python 解释器路径。在 `python` 不是 Python 3 的系统上使用 `"python3"` |
| `docsforge.lan` | `false` | 在所有接口（`0.0.0.0`）上服务，而非仅 localhost |
| `docsforge.openBrowser` | `true` | 服务器启动时在 VS Code 的 Simple Browser 中打开站点 |
| `docsforge.rememberedPython` | `""` | 扩展解析出的解释器（如项目 `.venv`）。自动维护；用 `pythonPath` 覆盖 |
| `docsforge.formatOnSave` | `false` | 保存时格式化 DocsForge Markdown 文档（无需 `editor.formatOnSave`） |
| `docsforge.autoCheckUpdates` | `true` | 启动后检查引擎与扩展更新，仅在有更新时通知 |
| `docsforge.includePrereleases` | `false` | 检查更新时包含 beta/alpha 预发布版本 |

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

### 保持更新

1. 接受更新通知，或运行 **Check for Updates**
2. 按需更新引擎、扩展或两者
3. 按提示重载 —— 发布流程至此结束

## 故障排除

| 问题 | 解决方法 |
|-------|-----|
| **"Failed to run python"** | 将 `docsforge.pythonPath` 设置为正确的 Python 可执行文件，或运行 **Check Python Environment** |
| **"No docsforge.yml found"** | 先运行 **Initialize Project**，或手动创建 `docsforge.yml` |
| **Preview shows blank page** | 检查 VS Code 中的 DevTools 控制台（`Help → Toggle Developer Tools`） |
| **Server won't start** | 打开 DocsForge 输出通道（`Ctrl+Shift+U`）查看错误详情 |
| **"python: command not found"** | 从 [python.org](https://python.org) 安装 Python 3.10+ |
| **更新检查连不上服务器** | 检查网络/代理；启动时的检查会静默跳过，手动检查才会警告 |
| **在用 beta 却收不到更新** | 打开 `docsforge.includePrereleases` —— 预发布默认排除 |
| **开了两个文件夹却服务了错误的项目** | Serve/Build 跟随当前文件所属项目；状态栏会标出项目名 |
| **可编辑安装收不到引擎更新** | 已修复 —— beta 检出会正确低于稳定版，替换源码检出前会有明确提示 |

## 命令

所有可用命令（通过 `Ctrl+Shift+P` 访问）：

| 命令 | 描述 |
|---------|-------------|
| `DocsForge: Initialize Project` | 创建新的 DocsForge 项目 |
| `DocsForge: New Page` | 创建文档页并附带翻译桩与导航条目 |
| `DocsForge: Start Server` | 启动开发服务器 |
| `DocsForge: Stop Server` | 停止开发服务器 |
| `DocsForge: Build` | 构建文档 |
| `DocsForge: Stop Build` | 取消正在运行的构建 |
| `DocsForge: Open Preview` | 在 VS Code 内置浏览器中打开站点 |
| `DocsForge: Open Built Page` | 打开当前文档对应的构建后 HTML |
| `DocsForge: Refresh` | 刷新侧边栏 |
| `DocsForge: Open Docs` | 打开 DocsForge 文档站 |
| `DocsForge: Check Python Environment` | 检测 Python，缺失时安装 DocsForge |
| `DocsForge: Rename Document` | 重命名文档并更新所有链接 |
| `DocsForge: Rename Anchor` | 重命名标题并更新锚点链接 |
| `DocsForge: Refresh Diagnostics` | 重读校验缓存并刷新波浪线 |
| `DocsForge: Open Link Target` | 跳转到链接目标（供快速修复调用） |
| `DocsForge: Check for Updates` | 检查引擎与扩展更新 |

## 下一步

- [使用指南](publishing/usage.md) —— 日常使用 DocsForge
- [部署指南](publishing/deployment-guide.md) —— 构建后部署站点
- [功能特性](features.md) —— 所有核心功能
