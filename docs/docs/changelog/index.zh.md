## [未发布]

## [13.0.1] — 2026-09-17

### 新增

- **Studio pip 与安装处理** —— 在 PEP 668
  外部管理解释器（Debian/Ubuntu 系统 Python）上安装与升级自动追加
  `--break-system-packages`，`--user`
  安装保留原标志；多个解释器装有 DocsForge
  时每个流程都会询问使用哪一个（记住的选择预选中）。更新流程每项最多
  确认一次（quick-pick 选择直接执行；发行注记重显同一对话框而非递归）。

### 修复

- **并行构建不再合并导航高亮** —— 并发页面渲染共享同一导航树，模板在
  渲染中途会快照到其它页面的 `active`
  标记：兄弟分节同时点亮（新老页面在侧边栏里混在一起），重复的吸顶分节
  标题互相遮挡（8 worker 构建中 50 页有 46
  页受影响）。渲染期间 `active`
  读取改为按线程精确解析为正在渲染的页面及其祖先与语言对应页——并行度
  保持不变，输出恢复与串行一致。附带屏障强制交叠的回归测试。
- **并行下语言输出保持正确** —— 翻译导航高亮按渲染显式注册；页面模板
  优先读取页面上下文 locale，而非可能串页的共享配置值。
- **Service Worker 不再挤爆首次加载** —— 清单同步池实际上无上限（记账
  bug 移除了刚加入而非已完成的任务），激活时数百个 no-cache
  请求齐发；清单刷新在每次导航都触发而非仅真实重载。两处已修复；访问
  时间写入不再阻塞响应；URL 字符串缓存键的 LRU 跟踪恢复正确。
- **侧边栏高度钳制限定断点** —— 页脚防交叠保护从 60em
  起生效，在平板上裁掉了全高导航抽屉；现仅在 screen+
  约束双栏、在 tablet-landscape 约束 TOC 栏。
- **build_frontend.py 拒绝漂移的依赖** —— 脚本曾用过期 node_modules
  静默构建（旧图标、旧 mermaid/wasm），甚至覆盖更新的内置资源。现版本
  不符直接报错并提示 `pnpm install`；图标刷新改为显式的
  `--refresh-icons`（常规构建绝不碰 `src/`）；输出同步清理删除项；空的
  twemoji 拉取直接中止而非清空资源集。
- **Studio 翻译诊断取代检查命令** —— 缺失语言变体与孤儿翻译直接成为文件
  上的编辑器错误（随诊断刷新，无需运行命令），`DocsForge: Check
  Translation Twins` 已移除。可编辑安装完全不参与更新检查（永远不为其
  提供引擎更新）。`DocsForge: Open Output`
  已移除（Output 视图仍在侧边栏）。用户可见文案统一称翻译，不称 twins。

## [13.0.1b1] — 2026-09-17

### 新增

- **Studio 页面工作流** —— `DocsForge: New Page`
  脚手架创建文档（目录默认取当前文件所在目录，可选语言孪生桩，文本方式
  插入 `nav:` 并可选择分节），`DocsForge: Check Translation Twins`
  列出缺失/孤儿语言变体，一键生成桩文件或删除孤儿文件。
- **Studio 锚点/片段/frontmatter 补全** —— 链接内 `#`
  后补全目标文档标题 slug（mtime 校验的索引位于
  `.docsforge/studio/headings.json`），`--8<-- "…"`
  中补全同目录与文档树文件，frontmatter 提供引擎支持的键及
  `hide:`/`search:` 取值（自定义键合法，绝不误报）。
- **Studio 多项目服务器** —— 每个工作区文件夹拥有独立的
  serve/build 状态与 pidfile 接管；命令作用于当前文件所在项目（含糊时弹
  出选择器），状态栏标出文件夹名，Open Built Page
  使用文档自己的服务器。
- **Studio 离线更新缓存** —— 成功检查的版本持久化保存；离线手动检查复
  用上次版本（标注缓存），静默启动检查只用缓存刷新侧边栏徽标，不弹窗。

### 修复

- **Studio 代码评审修复** —— New Page 不再用桩覆盖已有翻译（跳过的孪
  生会报告）；快速双击 serve/build 不再遗弃服务器进程；构建失败带真实
  错误而非未处理的 rejection；`./` 与 `../` 链接前缀可补全；Rename
  Anchor 改写同页 `[text](#anchor)` 链接；slug 保留中文（`# 你好` →
  `你好`）；Format Document 不动围栏代码块；`docsforge.formatOnSave`
  经 will-save 生效；Rename Document 拒绝逃逸路径；歧义快速修复改为询
  问而非猜测；混合新鲜/缓存的更新按通道标注；带本地元数据的短横预发布
  可解析；跳转与悬停作用于光标处链接；Stop Server 不再劫持为取消构建；
  pidfile PID 必须为数字且诊断路径不出 docs 目录。语言标签大小写不敏感
  （`pt-BR`）。
- **第二轮 Studio 代码评审修复** —— `:icon:` 补全改走工作区解释器对应
  的已安装包（用户项目中不再永远为空），并补上 frontmatter `icon:`
  取值；离线缓存版本只展示、不再提供必然失败的更新按钮；片段补全遍历
  全部缓存文件（不再静默截断）；无文件夹打开时恢复明确报错；更新检查
  与 serve 共用项目定位逻辑；锚点补全大小写不敏感且合并重复标题；
  formatOnSave 读取文档级作用域配置；frontmatter 补全跳过结尾
  `---`，围栏代码块内的片段补全被抑制；脚手架目录校验改为按段检查。

### 修复

- **Studio 对 beta/可编辑安装的引擎更新** —— 扩展曾把 `13.0.0b3`
  截断为 `13.0.0`，导致 beta 检出看起来已是最新、永远只提示扩展更新。
  现在预发布段会保留参与比较，可编辑安装（`pip install -e .`）经
  `direct_url.json` 识别且绝不被 pip 静默替换（提示会给出检出路径并提供
  显式替换），用户目录安装升级时保留 `--user`，失败时会打印手工重试命令。

## [13.0.0] — 2026-09-15

### 要点

DocsForge 13 是正确性与性能的大版本。下面内容已在 13.0.0b1–b3
测试版中陆续发布（完整逐条细节见下方各 beta 条目）；b3
之后仅新增了更新器提示文案修复与 Studio 文档重写。

- **真正并行的增量构建** —— 页面渲染真正用满 `concurrency`，片段包含页不再永远重建，静态拷贝增量进行，manifest
  无变化不写。
- **中文导航正确性** —— 独立 homepage、prev/next 链、`i18n_titles`
  保留，单页 description 不再被覆盖。
- **离线可靠的资源处理** —— Google Fonts 每构建最多拉取一次并带本地回退，原子写入，缺失产物自动恢复，社交卡片不再被当“无用资源”删掉。
- **更安静的 serve 与 CLI** —— 可中断的重建、404 记为 info、更友好的 help/check/setup 输出。
- **可自我更新的 Studio 扩展** —— 从命令面板、侧边栏或静默启动检查更新引擎与 VSIX，支持预发布开关。

### 行为变化

- 非默认语言页面保留自己的 frontmatter/H1 标题与 description；导航标签翻译不再改写它们。
- 开发服务器的 404 请求日志从 error 级别降为 info。
- 未开启 `docsforge.includePrereleases` 时，更新检查跳过预发布版本。

## [13.0.0b3] — 2026-09-15

### 新增

- **边栏可检查更新** —— Actions 视图新增 Check for Updates
  项（标题栏也有按钮），检查到新版本后直接在行内显示可用的版本号。

## [13.0.0b2] — 2026-09-15

### 新增

- **Studio 可自我更新** —— 新增 `DocsForge: Check for Updates`
  命令，对比已安装引擎（PyPI）与扩展（GitHub releases）的最新版本，用 pip
  在原解释器配置中升级引擎，下载新版 VSIX 并安装、提示重载。启动 45
  秒后静默检查一次（仅在有更新时通知，同版本只提醒一次，可用
  `docsforge.autoCheckUpdates` 关闭），`docsforge.includePrereleases`
  可把 beta/alpha 纳入检查。

## [13.0.0b1] — 2026-09-15

### 变更

- **内置 Mermaid 从 11.17 升级到 12.0** —— 上游将 ELK 布局引擎直接内嵌，
  `</br>` 现被识别为换行；DocsForge 固定了 v11 的外观默认值
  （`layout: dagre`、`theme: default`、`look: classic`），确保现有图表
  渲染效果不变；逐图 front matter 覆盖仍然有效。IIFE 产物增大约 600 kB
  压缩体积（含内嵌 ELK；已计入 precache 清单），备用 CDN 路径升级到
  `mermaid@12`。已在 Chromium 中验证全部 9 类核心图（flowchart、sequence、
  class、state、ER、gantt、pie、mindmap、journey）渲染正常，
  `initialize()` 无需改动即可接受 DocsForge 的既有配置。

### 修复

- **缺失的构建产物会被恢复，而不是永远丢失** —— 缓存中有、但站点目录里缺失的社交卡片（被旧版清理逻辑或手动删除）
  会在 `on_post_build` 拷回；以前增量构建中它们永远找不回来，因为未变化的卡片会被跳过、只有重建的页面才会拷贝。
  优化步骤之后新增一道通用检查，对其它所有有源文件的预期静态产物同样恢复；页面（缺失输出会触发重建）与优化器管理的目录（有意的剪枝）则不受影响。
- **社交卡片不再被当作“无用资源”删掉** —— 卡片 PNG
  只通过绝对路径同源 `og:image`/`twitter:image` meta
  标签引用，而引用扫描既不收集 `meta` 标签，又把绝对路径 URL
  当外部链接丢弃，导致清理步骤在同一构建内删掉所有刚生成的卡片。现在收集 meta
  图片/音视频引用，同源绝对路径解析为站内相对路径（外部源仍排除）；引用缓存按
  origin 区分，build/serve 的扫描结果不会互相串用。
- **帮助输出微调** —— 去掉 emoji 与示例区块，命令简介缩短到完整显示，不再中途截断。

- **开发服务器的 404 不再是报错** —— 之前每个缺失文件（写错的链接、favicon
  探测、草稿）都会打一条红色 `ERROR`；现在 404 记为 info 级别（其它 4xx 为
  warning，5xx 仍为 error）。日志前缀也不再把 `-`
  分隔符跟着级别名称一起染红/染黄。
- **更友好的命令行输出** —— `docsforge --help` 展示示例与彩色命令列表，`docsforge check`
  用绿/红/黄状态行并给出提示，setup 向导的横幅、步骤、报错与总结也用上了颜色。

- **构建在缓慢或被阻断的网络下也能完成** —— social
  插件曾对不可达的 Google Fonts 按每页重试（94
  次串行连接超时、每页一个报错、卡死数十秒）。超时保持不变，但每个字体族每构建最多拉取一次：失败时警告一次，卡片改用本地回退字体渲染（优先其它已缓存字体族，再按风格匹配系统字体），下次构建再重试。
  仅当本地没有任何可用字体时，页面才无卡片正常构建。卡片/图层线程池关闭时不再等待卡住的网络
  worker，一次 Ctrl-C 即可停止构建，无需按第二次。

- **并行页面构建真正并行** —— `_build_page`
  曾用一把共享锁包住模板渲染与文件写入，`concurrency`
  形同虚设。现在锁只保护共享状态（`page.active`、`config._current_page`、`get_context`
  的 git-meta 写入与插件钩子），渲染与原子写入在锁外执行。`active`
  清除改为 sibling-aware，`_current_page` 在每个加锁钩子内重新确认，并发构建不再互相闪烁侧栏高亮。
- **片段包含页面在增量构建中收敛** —— 新鲜度检查只用插件依赖，而缓存记录的是片段依赖，导致任何带
  `--8<--` 的页面永远重建；空依赖列表还会被丢弃。现在两处检查都提前计算片段依赖并与
  `update_cache` 共用，后者持久化空列表并清理已移除依赖。
- **增量 I/O 不再空转** —— 静态文件改用 `dirty=True`
  与 size+mtime_ns 比较，theme/extra/manifest 输出改为内容无变化不写，孤儿扫描排除生成物（`assets/`、sitemap、搜索索引、PWA
  文件）并参考已知 `dest_uri` 集合，所有文件/缓存写入均为原子写入（tmp + `os.replace`）。
- **中文导航正确性** —— locale 导航使用自己的 homepage（而非英文对象），拥有独立的 prev/next
  链，翻译页与回退页（含已物化页面）保留 `i18n_titles`，不再覆盖单页 description 或用导航标签改写文档标题，locale
  标题幂等重算，回退条目按 `src_uri` 高亮。
- **Social、搜索、标签与 minify 健壮性** —— 卡片层分发加锁（消除 sentinel
  死锁），字体下载加超时且仅在启用时建池，缺失 `</head>` 不再损坏输出，搜索排除按元素身份跟踪（嵌套同标签
  `div` 保持排除），tag listing ID 正则转义且 fragment 处理正确，`?v=`
  哈希在 serve 重建后存活，meta 文件一次排序并统一 `/` 路径。
- **Serve 重建可中断且无竞态** —— `KeyboardInterrupt` /
  `SystemExit` 重新抛出而非吞掉，重建标志在锁内变更，端口占用重试使用 `errno.EADDRINUSE`，自定义
  `site_dir` 按路径忽略（非硬编码 `site`），通配符主机探测回环地址，privacy
  下载排空至静止并上报错误，超大或不可解码资源安全跳过，配置缓存键为
  `(mtime_ns, size)`，shutdown 等待 observer，`check --fix` 原子写入。

- **配置加载不再因表情索引卡顿约 13 秒** —— twemoji
  索引构建曾对每个内置图标文件重建一次全量名称集合（约 1
  万个 SVG 上的 O(N²)），导致每次全新的 `build`/`serve`/`check`
  调用都无输出地阻塞。现在改为增量记录已占用名称，冷加载降到
  1 秒以内，结果完全一致。

- **参考文档不再把标题和图表吞进代码块** —— diagrams、content-tabs、
  admonitions、lists、creating-your-site、publishing usage 和 troubleshooting
  页面的 `markdown` 示例围栏使用三反引号，但内部又包含三反引号围栏，导致
  外层提前闭合，后续标题、表格和实时图表都被渲染成代码。现在外层统一改
  为四反引号（英文与中文 twin 一并修复）。

- **增量构建时翻译后的标签页图标不再丢失** —— 顶栏图标取自各分节首页
  front-matter 的 `icon`，但模板渲染前只预读了默认语言的源文件，因此重建
  的 setup/reference 之外的中文页面会丢失 setup/reference/首页图标。现在
  locale 导航的源文件同样预读，导航签名也覆盖 locale 标题与图标，纯中文
  改动也能正确触发重建。

- **构建中途 Ctrl-C 中断 `serve` 不再卡死** —— privacy
  下载线程池缺少 shutdown 钩子，中断后网络线程残留，解释器在 join
  它们时一直阻塞到所有下载超时。现在 shutdown 时取消排队中的下载（下次
  `on_config` 回收残留池），HTTP 响应必定关闭，页面构建线程池在中断时取
  消排队任务，缓存失效提示只打印一次，未版本化的残留缓存显示为
  `unversioned` 而非 `v0`。首次长构建还会输出 `Rendering N pages...` /
  `Writing N pages...`，慢与卡死可区分。

## [12.5.7] — 2026-08-22

### 新增

- **CI 与发布流程新增 ruff 检查关卡** —— `ruff check` 现在作为独立任务在 CI
  和发布工作流中运行，并且发布依赖于它通过，因此正确性回归无法进入发布。
  该关卡同时覆盖正确性（pyflakes、bugbear、pylint 错误类）与代码风格
  （pycodestyle、isort、pep8-naming、pyupgrade、flake8-simplify 等）：
  DocsForge 已不再跟随上游 ProperDocs / Material for MkDocs，因此整个代码树
  统一遵循一套自有风格 —— 双引号、120 列宽度上限、导入排序、禁止跨越父包的
  相对导入。每一条被忽略的规则与单文件豁免都在 `pyproject.toml` 的
  `[tool.ruff.lint]` 中给出了理由。新增 `pip install -e '.[dev]'` 附加依赖，
  可安装与 CI 完全一致的固定版本 ruff。

### 修复

- **模板一致性关卡现在能发现新增文件** —— CI 此前使用 `git diff --exit-code`
  将已提交的 `docsforge/templates` 目录与重新运行 `build_frontend.py` 的结果
  比对，而该命令只能报告被修改和被删除的文件，对新增文件视而不见。因此，
  凡是*新增*资源的依赖升级（例如 `lucide-static` 升级带来九个新图标）都会让
  这些文件停留在未跟踪状态却依然通过检查，使已提交的目录树与构建产物悄然
  不一致。现在未跟踪的构建产物会导致 CI 失败，并明确列出需要 `git add`
  的文件。

- **VS Code 类型定义升级不会再破坏发布流程** —— CI 的 `studio` 任务此前只做
  编译、lint 和测试，从不打包，而 `vsce package` 会强制执行编译器不检查的约束
  —— 尤其是 `@types/vscode` 不得高于 `engines.vscode`。由于打包只在发布工作流
  中进行，且发生在打标签与发布到 PyPI *之后*，这类升级会导致已发布的版本没有
  附带 `.vsix`。现在 CI 会执行打包，并且 `@types/vscode` 固定在
  `engines.vscode` 的兼容性下限，不再由 Dependabot 跟踪升级。

- **开发服务器的路径边界现已被测试覆盖** —— 实时重载服务器的目录穿越防护此前
  虽然实现正确，但内联在请求处理逻辑中、缺少说明且完全没有测试：请求路径变成
  `open()` 调用的唯一入口没有任何回归防护网。现已提取为 `_resolve_within_root()`
  这一个有完整文档的方法，当请求会逃出站点根目录时返回 `None` 而不是路径，并
  额外显式拒绝任何在归一化后仍残留的 `..` 作为纵深防御。新增八个单元测试锁定
  该边界，覆盖目录穿越、百分号编码的穿越、与根目录同前缀的兄弟目录
  （`/site` 与 `/sitezz`）、逃出根目录的符号链接，以及本可劫持
  `os.path.join` 的绝对路径。行为未变：此前能解析的路径依然能解析，此前被
  拦截的路径依然被拦截。

- **社交卡片不再在多次构建间泄漏** —— `SocialPlugin.manifest` 此前是类属性，
  却被实例代码修改，因此所有插件实例共享同一个字典，且在同一个
  `docsforge serve` 会话内卡片条目会跨重建不断累积。现已改为每个实例独立。

- **翻译页面保留索引页身份** —— `index.zh.md` 这样的翻译兄弟文件此前被
  当作普通页面而非索引页，导致多语言站点在非默认语言下顶部导航标签页
  丢失图标（图标来自标签页对应的索引页），且开启 `navigation.indexes`
  时翻译的章节索引页不会合并进所属章节。翻译兄弟文件现在共享默认文件
  的文件名主干身份，`index.zh.md` 的行为与 `index.md` 完全一致。
- **`privacy` 插件在无法创建符号链接时不再崩溃** —— 在不支持符号链接的文件
  系统上（尤其是未开启开发者模式的 Windows），直接写入已下载资源的回退路径
  读取了 `res.content`，而由于为了限制下载大小已经以流式方式消费过响应体，
  该读取会抛出 `RuntimeError: The content for this response was already
  consumed`。现在改为写入已经流式读取到的字节。
- **PWA manifest 与 `theme-color` 使用真实颜色值** —— 两者此前都直接输出
  Material 调色板的*名称*（如 `teal`），而该位置要求的是 CSS 颜色值，浏览器
  因此忽略该值，主题色未生效。现在调色板名称会被解析为对应的十六进制颜色，
  而字面量 CSS 颜色则原样透传。
- **可在 Python 3.10 上正常构建** —— 并行页面渲染失败时会抛出 `ExceptionGroup`
  这一 3.11+ 内置异常，因此在 `requires-python` 允许的 3.10 上，错误处理本身
  会抛出 `NameError`，掩盖真正的构建错误。3.11 以下现在使用兼容的回退实现。
- **TikZ 编译不会再挂住构建** —— 每次 LaTeX 与 SVG 转换器调用现在都带有超时
  限制（120 秒，可用 `DOCSFORGE_TIKZ_TIMEOUT` 覆盖）。此前格式错误的图表若让
  TeX 进入交互式提示，会永久阻塞构建，因为编译运行在构建所等待的线程池中。
- **TikZ 编译计数器线程安全** —— 已编译/已跳过计数器与内容哈希映射此前在编译
  线程池中无同步地被修改，导致统计数字可能出错、哈希条目可能丢失，进而使未
  改动的图表在下次构建时被重新编译。
- **缓存格式变更时丢弃过期缓存** —— `CACHE_VERSION` 从未与已存储的版本比较，
  因此旧格式版本写入的缓存会被当作当前格式读取。现在格式变更时会使其失效。
- **`cache.invalidate()` 清理所有缓存文件** —— 列表中遗漏了 `validation.json`，
  导致链接/锚点校验数据在失效操作后仍然存留。所有缓存文件现在来自单一来源。
- **`docsforge fix` 会备份配置文件** —— 自动修复通过 `yaml.dump` 重写
  `docsforge.yml`，会静默丢弃注释、空行和引号风格。现在会先写入 `.bak` 副本
  并明确提示。
- **社交卡片 manifest 读取错误不再吞掉中断信号** —— manifest 读取外层的裸
  `except` 会捕获 `KeyboardInterrupt`，导致该阶段的 Ctrl-C 被忽略。

## [12.5.6] — 2026-08-20

### 新增

- **离线模式开关** —— 新增 `offline.mode` 配置项，可完全关闭 service worker。
  默认的 `cache-first` 模式不变（注册 service worker，预缓存所有页面和资源，
  先读缓存再回源，支持离线使用）。设置为 `offline.mode: none` 时完全跳过
  service worker：不生成 `sw.js`、`cache-manifest.json` 或 `manifest.json`，
  页面中也不含注册代码或 manifest 链接，站点纯粹通过网络提供服务。

### 修复

- **主题签名与安装位置无关** —— 主题模板签名此前使用绝对路径，同一份
  模板安装在路径不同的环境（例如 GitHub Actions 的 Python 工具缓存更新、
  或重装到新环境）会产生不同的签名，导致每次 CI 构建都作废整个构建缓存，
  增量构建形同虚设。签名现在对模板内容计算哈希，路径改为相对各自主题
  目录，因此相同的模板无论安装在哪里都得到相同的签名。

## [12.5.5] — 2026-08-20

### 新增

- **`cache-manifest.json` 附带文件大小** —— manifest 现在带有一个
  `sizes` 映射，记录每个构建文件的精确字节数。Service Worker 用它
  （以及响应的 `Content-Length`，缺失时直接测量响应体）按真实大小进行
  配额逐出，取代旧的"每个条目按 5 MiB 估算"的做法。

### 变更

- **Service Worker 配额逐出精确化** —— 浏览器缓存满时，SW 按
  最近最少使用（LRU）顺序逐出条目，直到实际释放的字节数（真实测量，
  不再估算）覆盖所需空间并留出配额 10% 的成比例余量，然后重试。旧的
  固定 20 MiB 空闲余量已移除。被逐出的条目会从持久化的"上次同步文件
  列表"中删除，被逐出的文件绝不会被错误记录为已缓存 —— 下次同步会
  重新拉取，而不是跳过。
- **manifest 同步带预算控制** —— 后台同步在下载前先查询
  `storage.estimate()` 报告的空闲空间：每个变更文件预占 20 MiB 预算
  （用量估算落后于在途写入），预算耗尽后同步即停止，不再下载那些注定
  会被再次逐出的文件。放不下的文件在真正访问时才按需缓存。单个资源
  大于整个配额时永远不会被缓存。

### 修复

- **Safari（以及任何小额配额的浏览器）不再抖动** —— 此前同步会下载
  整个 manifest，撞上配额上限后把刚缓存的文件逐出，却仍把它们记录为
  已缓存；离线覆盖范围静默退化为 manifest 末尾的少量文件。现在同步会
  提前停止，已跟踪文件列表始终真实可信。
- **TikZ 图表缓存改为基于内容** —— 未变化的图表现在通过计算有效源码
  （tex 加上导言区）的哈希来跳过编译，不再比较文件 mtime。git 检出与
  CI 缓存恢复都会刷新所有文件的 mtime，此前会导致每次构建重新编译
  全部图表；修改 `tikz_preamble` 现在也能正确触发重新编译（mtime
  比较此前根本感知不到导言区变更）。
- **主题签名改为基于内容** —— 全量重建现在由模板内容的真实变化触发，
  不再依赖 stat（mtime/大小）差异。重装 docsforge 包或恢复 CI 缓存会
  给内容相同的主题模板盖上新的 mtime；此前这会令每次 CI 构建都作废
  整个构建缓存，使增量构建形同虚设。

## [12.5.4] — 2026-08-18

### 新增

- **内置 Twemoji SVG 资源** —— 完整的 twemoji 表情集（4,000+ 个表情，
  固定到 `jdecked/twemoji` v17.0.3，即已归档 `twitter/twemoji` 的维护分支）
  随包发布。Unicode 表情（`:smile:`、`:us:`）现在在构建时本地内联，不再
  引用任何 CDN（jsdelivr/maxcdn）—— 仅当表情码点不在内置集合中时才回退
  到 CDN。
- **内置资源附带许可证文件** —— Mermaid（MIT）和 KaTeX（MIT）许可证随
  打包的脚本一起分发，lunr 词干模块附带其 MPL-1.1 许可证（许可证必须在
  所有情况下随代码一起分发）。
- **Docker 镜像以非 root 用户运行** —— 镜像现在创建 `docsforge` 用户
  （uid 1000）并降权运行（`USER docsforge`）。
- **TikZ 默认数学前言** —— 裸图表源文件（没有 `\documentclass`）现在会
  自动包装为 standalone 文档，预载 `amsmath`、`amssymb`、`tikz`、
  `pgfplots`、`tikz-cd` 和 `tkz-euclide`，图表只需写 `tikzpicture` 内容
  即可。新增 `tikz_preamble` 配置项用于注入额外前言行。Docker 镜像新增
  `texlive-fonts-recommended`（amssymb/amsfonts）—— pgfplots、tikz-cd 和
  tkz-euclide 已随 `texlive-pictures` 提供。
- **TikZ SVG 内嵌字体** —— `dvisvgm` 不再使用 `--no-fonts`，图表文字保持
  可选中、可搜索；仅在 TeX 字体不可用时回退为轮廓路径。
- **TikZ 编译不再超时** —— 移除了每步固定 60 秒的限制；大型或慢速图表
  （pgfplots 曲面、大量 `foreach` 循环）可以按需编译任意时长。

### 变更

- **全局 `concurrency` 设置** —— 新增顶层 `concurrency` 配置键（默认值：
  CPU 数 − 1），统一控制所有并行池：Markdown 页面渲染、页面构建、TikZ
  编译、社交卡片生成和隐私下载。`social` 和 `privacy` 插件原有的
  `concurrency` 选项已移除 —— 请改用顶层 `concurrency:`（破坏性变更；
  插件级用法现在只会给出警告）。
- **PDF 导出标签页数按内存封顶** —— 基础标签页数来自 `--jobs`，否则使用
  全局 `concurrency`（默认 CPU 数 − 1），并按剩余内存封顶（每个
  Chromium 标签页约 200 MiB），避免并行渲染导致构建内存不足（OOM）。
- **`scripts/fetch_twemoji.py` 合并进 `build_frontend.py`** —— 通过
  `python build_frontend.py --fetch-twemoji`（固定标签）刷新内置的
  twemoji 集合，然后正常构建即可同步到 `docsforge/templates/`。
- **迁移脚本改为由文档站点提供** —— `migrate.sh`、`migrate.ps1` 和
  `migrate.py` 位于文档内容目录中，构建时复制到站点输出（docsforge
  会复制 `docs_dir` 中的静态文件），一键命令更新为：

  ```bash
  curl -fsSL https://qqshi13.github.io/docsforge/migrate.sh | bash
  ```

  ```powershell
  irm https://qqshi13.github.io/docsforge/migrate.ps1 | iex
  ```

  脚本从同一站点下载 `migrate.py`
  （`https://qqshi13.github.io/docsforge/migrate.py`），不再使用 GitHub
  raw URL；入门迁移指南现在也记录了自动一键迁移（此前写着“暂无自动
  迁移命令”）。

## [12.5.3] — 2026-08-17

### 新增

- **一键迁移脚本**：`curl | bash`（Unix）和 `irm | iex`（PowerShell）可自动把
  现有的 `mkdocs.yml` / `properdocs.yml` / `zensical.toml` 转换为
  `docsforge.yml` —— 导航、主题、插件和扩展。对无法迁移的内容（第三方插件、
  `INHERIT`、钩子）发出警告，并打印包含联系方式（邮箱 + issues）的报告。
- **配置加载支持 `!!python/name:` 标签** —— mkdocs 配置常用
  `slugify: !!python/name:pymdownx.slugs.uslugify`；此类配置（如 OI-wiki 的）
  现在可以干净地解析和往返转换。
- **SECURITY.md** —— 私密漏洞报告（GitHub advisory 或邮箱）、受支持版本策略。
- **支持页面**（中英文）—— 一键迁移、支持渠道和“报告中应包含什么”清单。
- **每个文档页面的侧边栏导航图标**（Material 图标集，中英文）。

### 变更

- **minify 后端改为 Go 压缩器**（`minify-go`，由我们自己的 cron 工作流基于
  `tdewolff/minify` 构建 wheels，含 macOS arm64）：长期维护的分支
  （min-html、min-js、csscompress）合并为单个依赖。HTML 页面现在也会压缩
  内联的 `<style>`/`<script>` 块；SVG 默认值属性（如
  `preserveAspectRatio="xMidYMid meet"`）会被移除，非默认值与大小写敏感
  的属性名（`viewBox`）保持不变。注意：Go 绑定不支持 musllinux/Alpine
  （c-shared `.so` 无法在 musl 上 dlopen）。
- **内置 `paginate`**（`docsforge/paginate.py`）—— 又移除一个停更依赖
  （2017）。
- README：新增一键迁移；修复失效的 `install.sh`/`install.ps1` 引用
  （Studio 扩展以 release 中的 `.vsix` 分发）。

### 修复

- `docsforge check` / CLI / PDF 的配置解析现在统一走 docsforge YAML 加载器，
  `!!python/name:` 标签不再导致配置发现崩溃。
- 迁移脚本：`theme.name: null`（本地主题配置）默认改为 `material`；外部导航
  链接会丢弃并给出提示（docsforge 导航仅支持内部页面）。

## [12.5.2] — 2026-08-12

### 新增

- **博客 RSS/Atom 订阅源**：博客插件现在在每次构建时为站点生成
  `feed_rss_created.xml`、`feed_rss_updated.xml` 和 `feed_atom.xml`（草稿
  除外）—— 不再需要手工维护订阅源文件。可通过
  `plugins: [blog: {feed: false}]` 关闭。
- **文档参考扩展**：补全 9 个此前未记录的配置键（`exclude_docs`、
  `draft_docs`、`not_in_nav`、`extra_templates`、`tikz`、`hooks`、`watch`、
  旧版 `remote_branch`/`remote_name`）、`social` + `i18n` 插件选项表、
  Lucide 图标章节、社交卡片插件文档，以及零配置的
  `extra.i18n_languages` 形式（中英文）。

### 修复

- **博客入口页在增量构建时保持过期**：当入口页自身源文件未变化时，添加、
  编辑或删除文章不会重新渲染博客列表。新增 `on_page_deps` 插件事件与依赖
  集合变化检测，使博客视图保持最新；无变更的构建仍会跳过。
- **内置插件重复加载**：声明内置插件（`plugins: [blog: {...}]`）时会以默认
  配置再加载一个自动加载实例，因为去重检查将未加命名空间的名称与带命名空间
  的实例计数器（`material/blog`）比较。每个声明的核心插件都被静默重复
  —— 现已正确去重。
- **演示内容**：修正过时的“31 个扩展 / 7 个插件”描述；启动文章中的插件
  列表补上 `i18n`。

### 变更

- **依赖下限提升到当前最新版本**：click 8.4.2、Jinja2 3.1.6、Markdown
  3.10.3、PyYAML 6.0.3、watchdog 6.0.0、pymdown-extensions 11.0.1、backrefs
  8.0、Pygments `>=2.20.0`（其 `default` 风格输出与已提交的 `pygments.css`
  一致），以及所有其他运行时依赖；可选依赖包括 playwright 1.62.0、pypdf
  6.15.0、pillow 12.3.0、cairosvg 2.9.0。

## [12.5.1] — 2026-08-12

### 新增

- **增量 PDF 导出缓存**：`docsforge build --pdf` 现在会跳过自上次导出以来
  构建产物未变化的页面（按页内容哈希存储于 `.docsforge/cache/pdf.json`，
  与站点构建使用相同的机制）。单页修改只会重新渲染该页；孤儿 PDF 会被
  清理；仅成功渲染的页面会被记录为已缓存。
- **`on_build_done` 钩子事件**：在成功构建的最末尾运行一次 —— 在页面渲染、
  链接/锚点校验、`on_post_build` 插件、资源优化、PWA 清单与服务工作者
  生成、缓存保存之后 —— 钩子可以检查或后处理最终的构建产物（例如
  `sw.js`、`cache-manifest.json`）。严格模式下构建中止时不运行。

### 变更

- **E2E 测试支持 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`**：浏览器启动点现在使用
  与 `docsforge.pdf` 相同的环境变量，本地无需安装 Playwright 自带的
  Chromium 即可用系统浏览器运行 e2e 测试。未设置时回退到自带浏览器
  （CI），两者都不可用时优雅跳过。

### 修复

- **文档修正**：插件数量（8 个核心自动加载 + social 可选）与 Markdown 扩展
  数量（36 个默认 + 3 个内置）现已与引擎一致；TikZ 描述修正（`.tex` 文件
  在构建时编译，需要 LaTeX 工具链）；迁移指南中移除过时的 "Insiders" 引用
  （mkdocs-material 正在迁移到 Zensical）；补齐 zh 更新日志 12.2.0–12.4.0；
  修复 zh 页面失效的自锚点；修正图标数量（五大图标家族共 16,500+）。
- **示例站点集成测试**指向 12.5.0 之前的 `examples/site` 路径而静默跳过
  —— 现改为运行 `examples/sites/docsforge-demo`。
- **演示站点**：新增三篇博客文章（TikZ 图表、后缀式 i18n、DocsForge Studio
  诊断）；移除一个孤儿页面；`latex-equations.md` 加入导航；TikZ 图现在可
  正确解析。

## [12.5.0] — 2026-08-11

### 新增

- **DocsForge Studio**（VS Code 扩展，`studio/`，由 `vscode-docsforge` 更名）：
  无需语言服务器即可获得完整编辑器能力 — 基于构建产物
  `validation.json` 的诊断（断链/锚点、脚注）、大纲、折叠、定义跳转
  （Ctrl+点击）、悬停断链提示、补全（`:material-`/`:lucide-` 图标与文档
  路径）、查找所有引用，以及“重命名文档”/“重命名锚点”（自动改写所有
  入站链接，感知锚点与翻译变体 — 重命名 `.zh` 文件会同时重命名基础文件
  及其全部语言变体）。资源管理器中的重命名会被自动拦截处理。
  “修复全部断链 (N)”快速修复、打开链接目标、“在内置浏览器打开构建后
  页面”、保存时格式化（可选）、侧边栏输出面板。
- **Python 环境管理**：自动检测解释器（设置 → 记住的 venv → `.venv` →
  PATH），检查 pip 与 docsforge，提供 venv / 用户 / 全局安装选项。
- **Apache-2.0 许可证**：由 LGPL-3.0-or-later 切换；新增 `NOTICE`
  上游署名（ProperDocs/MkDocs BSD-2、Material MIT、各图标库）。
- **KaTeX 与 Mermaid 改为内置**（纳入 package.json 受依赖管理，此前为
  冻结快照 / 硬编码 CDN）：前端构建新增 `copy_katex()` 与 `copy_mermaid()`；
  Mermaid 从本地资源加载，CDN 仅作回退。
- **pygments.css 改为构建时生成**（此前为冻结快照）。
- **CI 覆盖 Studio**：`ci.yml` 新增 `studio` 任务（npm ci + 编译 + lint +
  测试），并合并 `frontend.yml` 为 `frontend` 任务。

### 变更

- **Social 插件改为可选启用**：从默认加载的核心插件中移除（依赖
  pillow + cairosvg）；通过 `plugins: [social]` 启用。文档与示例配置已更新。
- **链接/锚点校验修复**：锚点问题现在会持久化到 `validation.json`
  （此前仅记录日志而未存储 — 导致 Studio 诊断无数据可显示）；
  修复了类级共享的 `link_warnings` 列表导致警告在所有页面重复的问题。
- **目录更名**：`vscode-docsforge/` → `studio/`、`docsforge-docs/` →
  `docs/`、`examples/site/` → `examples/sites/`（移除 gitignore 否定规则，
  由全局 `site/` 规则直接覆盖）。
- **TypeScript 6.0.3**（TS 7 超出 typescript-eslint 的 peer 范围）。
- **演示站部署**：wrangler-action v4（不再固定 wrangler 版本）。

### 修复

- **Social 卡片字体拉取可能卡死构建**：Google Fonts 请求无超时
  （已回退，与上游一致）。默认缓存移至 `.docsforge/cache/social`。
- **演示站流水线**：修复每次运行失败的
  `rm -rf /var/lib/apt/lists/*` 权限问题；`neural-network.tex` 缺少
  `amssymb`；补充缺失的 `shannon-state-machine.tex`。

## [12.4.0] — 2026-08-09

### 新增

- **社交卡片插件**（`social`）：移植自 mkdocs-material 的 social 插件，扁平化为
  `docsforge/core/social.py`（OpenGraph 卡片生成，两阶段并行渲染，缓存 + 清单，
  字体下载）。每个 i18n 语言页面生成独立卡片。需要
  `pip install "docsforge[social]"`（pillow + cairosvg）。
- **Lucide 图标集**：2022 个图标，可通过 `:lucide-name:` 内联使用或用于主题
  图标配置；`.md-icon` 支持描边渲染。
- **每次构建都进行链接/锚点校验**：链接与锚点问题现在每次构建都会报告，
  而不仅仅是首次 —— 校验数据按页面持久化到构建缓存中，对未重新渲染的
  页面也会重新检查。
- **编程式配色 API**：`window.docsforge.setPalette({scheme, primary,
  accent})` 可从内联脚本/嵌入（如主题游乐场）应用并持久化主题，包括
  没有页眉切换的组合。
- 示例：演示站点现在位于仓库内（`examples/site/docsforge-demo`），带有
  `custom_dir` 覆盖、自定义过滤插件示例、hooks 示例和 CI 构建测试；
  演示通过 GitHub Actions 部署到 Cloudflare Pages（带 TeX Live 以支持 TikZ）。

### 变更

- **仓库卫生**：移除所有 vendored mkdocs-material MIT 头部（署名统一到
  许可证页面）；移除 parity 工具；在 CI 和发布时强制执行前端可复现性。
- 服务工作者在每次真实页面加载时重新校验清单（Navigation Timing API）——
  重新部署的站点无需硬刷新即可被感知；移除了 5 分钟更新轮询和硬刷新
  监视器。
- 侧边栏高度改用 `dvh`，使左侧（导航）和右侧（TOC）侧边栏在
  iOS/iPadOS 上滚动一致。

## [12.3.0] — 2026-08-06

### 变更

- **仓库扁平化。** monorepo 的 `packages/` 层级已移除：核心包、
  `pyproject.toml`、`src/`、`tests/` 和前端流水线位于仓库根目录；
  文档站点为 `docsforge-docs/`，VS Code 扩展为 `vscode-docsforge/`。
  所有工作流、Dockerfile、dependabot 配置和文档链接均已更新；
  完整包 README 现在是根 README。
- **svgo 4。** 图标流水线现在使用 svgo 4（配置已迁移；`viewBox` 保留不变）。
  已验证字节级可复现的构建输出。
- **pnpm 11** 用于前端构建（workspace 文件使用 pnpm 10+ 语法，pnpm 9 会
  拒绝），并禁用了 `minimumReleaseAge` 供应链门控，使 dependabot 对刚
  发布版本的升级能通过 CI。
- **前端 CI 重新可复现**：`frontend.yml` 在构建输出与已提交的
  `docsforge/templates/` 不一致时失败，发布工作流在发布 wheel 前会从
  `src/` 重新构建前端。
- 移除了过渡期 parity 测试工具和基线快照（其任务已完成）；
  `build_frontend.py` 移至仓库根目录。
- CI 运行完整测试套件，包括专用的 Playwright e2e 任务。

## [12.2.0] — 2026-08-06

### 新增

- **前端从源码构建。** Material 主题以源码形式 vendored 到 `src/`
  （mkdocs-material v9.7.7），由仓库内流水线（`scripts/build_frontend.py`）
  构建：esbuild 打包、sass + autoprefixer CSS、svgo 图标、压缩模板和
  服务工作者。每个发布的资源都可复现，parity 门控
  （`scripts/check_frontend_parity.py`）在 CI 上按区域验证。
- **DocsForge 前端自定义现在位于源码中**，而不是手工修补压缩 bundle：
  服务工作者（清单驱动增量同步、语言感知页面服务、离线快速 404、
  清单感知候选跳过）、无状态 i18n 语言切换器（IndexedDB 支持）、按语言
  搜索索引、按语言 404 页面，以及保持即时导航在首选语言上的
  `X-DocsForge-Instant-Nav` 头。

### 变更

- 服务工作者以压缩形式发布，带有 `__DOCSFORGE_BASE_URL__` /
  `__DOCSFORGE_BUILD_HASH__` 占位符；`docsforge build` 注入真实基础路径
  和确定性哈希，使 SW 字节在构建之间变化。
- SW 跳过 `cache-manifest.json` 中不存在的页面候选 —— 对（无后缀）
  默认语言的存储偏好不再请求 `index.en.html`（404）。
- 当 meta 插件激活时，没有 `title:` front-matter 键的博客文章不再导致
  构建崩溃。
- `scripts/check_frontend_parity.py` 新增 `--vs-ref`（与 git ref 输出差异，
  无需构建）和哨兵标记检查。

## [12.0.0] — 未发布

### 变更

- **破坏性变更：与语言无关的 i18n 架构。** 翻译页面现在作为兄弟文件输出（同一目录下的 `index.html` 和 `index.<locale>.html`），并共享相同的公开 URL。Service Worker 将用户的偏好语言存储在 IndexedDB 中，并在每次请求时提供对应的兄弟文件。这移除了 `/<locale>/` 子站点、回退页面、按语言复制的资源以及链接/资源重写。
- **i18n 搜索支持按语言切换。** 每种语言都有自己的 `search/search_index.<locale>.json`；前端会加载当前显示语言对应的索引，而不是始终搜索默认语言。
- **i18n 语言切换器重新加载同一 URL。** 选择语言会将偏好写入 IndexedDB 并重新加载当前页面，因此切换器不会产生过时的语言专属 URL。

### 移除

- **i18n `fallback_to_default` 选项。** 由于不再生成回退页面，该选项现已被忽略。

## [11.5.4] — 2026-07-07

### 修复

- **i18n 链接重写现在支持无引号和单引号的 `href` 属性。** HTML 压缩器会输出类似 `href=second/` 的属性，而之前的链接重写器会遗漏这些属性，导致本地化页面链接回默认语言站点。现在它会重写双引号、单引号和无引号的 `href` 值。
- **i18n `nav_translations` 现在应用于页面导航项。** 此前仅翻译了章节标题；现在页面导航项也会使用 `nav_translations`，当未配置显式导航标题或翻译时，将使用 frontmatter 标题作为回退。

## [11.5.3] — 2026-07-07

### 修复

- **i18n 回退页面现在继承标题和导航覆盖设置。** 回退本地化页面（以及在导航运行前创建的已翻译页面）不再将导航项渲染为“None”；它们会使用默认页面标题以及为该条目配置的任何自定义 `nav` 标题。
- **本地化链接现在为所有页面重写，而不仅是导航页面。** 从已翻译页面指向回退/非导航页面的内部链接现在会正确保留在本地化子树中，而不是跳回默认语言 URL。

## [11.5.2] — 2026-07-07

### 新增

- **i18n 资源回退。** 已翻译资源（例如 `assets/diagram.zh.png`）会发布到本地化路径下（`zh/assets/diagram.png`）。如果缺少翻译版本，系统会自动复制默认资源，因此本地化站点不会丢失图片、CSS 或其他文档资源。
- **按本地化区域设置 Material UI 语言。** 已翻译页面现在会加载对应的 Material UI 字符串文件，因此 `<html lang>`、搜索占位符和语言切换器标签会跟随页面本地化区域，而不是停留在默认语言。

### 修复

- **消除翻译页面的导航误报警告。** `docsforge build` 和 `docsforge serve` 不再为 i18n 插件处理的已翻译 `.zh.md` 文件记录“pages exist in the docs directory, but are not included in the nav”警告。
- `docsforge check` 现在将 `material/i18n` 视为内置插件，而非第三方插件。

## [11.5.1] — 2026-07-06

### 修复

- **i18n 语言切换器使用了服务器绝对 URL。** 备用 URL 包含了 `site_url` 子路径，因此当模板 `url` 过滤器将其解析为当前页面的相对路径时，部署在路径下的站点（例如 `https://qqshi13.github.io/docsforge/`）会指向 `docsforge/docsforge/...`。i18n 插件现在输出页面相对 URL（`page.url`），因此切换器和 `<link rel="alternate">` 标签会保留在文档根路径内。

## [11.5.0] — 2026-07-06

### 新增

- **内置 i18n 插件（`material/i18n`）。** 在默认语言文件旁边添加已翻译文件（例如 `index.zh.md` 放在 `index.md` 旁边），DocsForge 会构建一个根目录下的默认站点，以及每个本地化区域对应的子站点（`/<locale>/`）。支持回退页面、按语言配置的导航/标题翻译、页眉语言切换器、`<link rel="alternate" hreflang="...">` 标签、按本地化区域的搜索索引以及按本地化区域的站点地图。
- 新增文档页面：[多语言站点](../setup/i18n.md)。

### 修复

- Material 主题现在提供默认 `palette`，因此省略 `theme.palette` 时构建不再失败。
- 从模板上下文中移除了 `properdocs_version`/`mkdocs_version` 遗留字段。
- VS Code 扩展构建通过将 TypeScript 回滚到 `^5.9.3`、将 `@types/node` 回滚到 `^22.20.0` 并采用 `commonjs`/`node` 模块解析策略后恢复。

## [11.3.12] — 2026-06-27

### 新增

- **浏览器端到端测试（Playwright）。** 一个包含 5 个测试的 Chromium 套件（`tests/e2e/`），覆盖无法通过单元测试验证的 Service Worker 行为：SW 安装并缓存可见页面、离线重载时提供已缓存页面、`search_index.json` 可正常提供，以及悬停预取会缓存目标页面以便离线加载。当没有可用浏览器时，测试会自动跳过（因此默认的 `pytest` 运行不受影响）；在 `ubuntu-latest` 上有一个专门的非阻塞 `e2e` CI 任务会安装 Chromium 并运行 `pytest -m e2e`。

## [11.3.11] — 2026-06-27

### 新增

- **VS Code 扩展测试（10 个）。** 为扩展的纯 helper 函数添加了 mocha + ts-node 测试套件：配置文件发现（`findConfig`/`hasConfig`，优先使用 `.yml` 而非 `.yaml`）以及从 stdout 提取服务器 URL。这些 helper 被提取到不依赖 vscode 的 `src/pure.ts` 中（行为保持不变），以便无需启动 VS Code 即可测试。CI 现在在 `build-vsix` 任务中运行 `npm test`；`test/` 目录不会打包进 VSIX。

## [11.3.10] — 2026-06-27

### 新增

- **Serve / 实时重载单元测试（15 个）。** 覆盖 `_find_available_port`（空闲、占用时递增、全部占用、防火墙丢弃 SYN 及短超时 WSL 修复）、`_serve_url`/`_normalize_mount_path`/`_try_relativize_path`，以及防止无限重载循环的重建队列逻辑（构建期间的事件通过 `_pending_rebuild` 排队，而非立即发出信号）。

### 变更

- 将实时重载的文件监视回调提取为可测试的 `LiveReloadServer._on_file_event` 方法（行为保持不变）。

## [11.3.9] — 2026-06-26

### 新增

- **通过 `SOURCE_DATE_EPOCH` 实现可复现构建。** `get_build_datetime()` 现在遵守标准的 `SOURCE_DATE_EPOCH` 环境变量（reproducible-builds.org）。设置后，构建日期、页面 `update_date`、站点地图 `<lastmod>` 以及 `sitemap.xml.gz` 的修改时间都将从该时间戳派生，而不是使用墙钟时间——因此同一来源的两次构建会产生字节完全相同的输出（已验证：跨干净构建的内容哈希一致）。未设置时默认为当前时间。

### 变更

- **搜索索引条目现在按位置排序** 后再序列化，即使构建循环以非确定性顺序填充条目，也能保证 `search_index.json` 的字节级可复现性。

## [11.3.8] — 2026-06-26

### 修复

- **模板编辑现在会触发完整重建。** 构建缓存只追踪源 `.md` 文件的哈希、配置哈希和包版本——因此编辑 `base.html`、局部模板或 `theme.custom_dir` 模板不会重建未更改的页面（输出过时）。构建现在会记录主题目录中所有 `.html`/`.xml` 模板的 stat-only 签名（排除 14k+ 的 `.icons/`），并在其变化时强制完整重建。编辑 `base.html` 等操作现在会重建每个页面。

## [11.3.7] — 2026-06-26

### 变更

- **并行 Markdown 渲染。** `_populate_page`（读取源文件 + `markdown.convert`，构建中最耗 CPU 的部分）现在通过 `ThreadPoolExecutor` 并行运行（最多 32 个 worker）。每个线程拥有独立的 `Markdown` 实例，使 `render()` 线程安全；只有插件事件调用和 `config._current_page` 通过锁串行化。模板渲染（`_build_page`）保持串行，以避免侧边栏激活状态竞争。文档站点冷构建时间：约 10 秒 → 约 7 秒；跨构建输出字节一致（已验证 5 次运行）。

## [11.3.6] — 2026-06-26

### 修复

- **DocsForge 升级现在会触发完整重建。** 构建缓存只追踪源 `.md` 文件的哈希和 `docsforge.yml` 的哈希，因此升级 DocsForge（新主题模板、Service Worker、构建逻辑）不会重建未更改的页面——新的 SW 和模板只有在源文件被编辑后才会进入构建站点。缓存现在会记录包版本，并在其变化时强制完整重建。
- **配置更改现在会实际重建未更改页面。** `cache.invalidate()` 删除了磁盘文件，但保留了规划器的内存哈希，因此配置/包更改不会在当前构建中重建源文件未更改的页面（差一错误：更改在*下一次*构建才生效）。`planner.invalidate()` 会同时清除内存和磁盘状态。`meta`（修改时间/大小哈希缓存）在版本升级时保留，因此重建时仍会跳过读取未更改的源文件。

## [11.3.5] — 2026-06-26

### 新增

- **悬停/聚焦链接预取。** 内部链接现在会在 `mouseover`/`focusin` 时预取（通过 Service Worker 的 `serveCurrentPage` 即发即弃），因此用户点击时目标页面已经缓存——页面切换变得即时。仅同域，去重，跳过同页/锚点链接。

### 修复

- **SW 更新消息与客户端对齐。** Service Worker 现在发送 `DOCSFORGE_UPDATE_READY`（`base.html` 已在监听的消息名），而不是未使用的 `docsforge-updated`。

## [11.3.4] — 2026-06-26

### 变更

- **构建：文件哈希的 mtime+size 预过滤。** `should_rebuild` 和 `cache-manifest.json` 生成在每次构建时都会重新读取并对每个源 `.md` 进行 SHA-256 计算。它们现在会查询 `{path: {mtime, size, hash}}` 缓存（`meta.json`），当 `stat()` 报告相同的 mtime 和 size 时复用缓存的哈希——用一次 stat 替代完整读取+哈希。在空构建中，这使哈希阶段变为仅 stat（文档站点：0.87 秒 → 0.66 秒；大型站点收益更大）。

## [11.3.3] — 2026-06-26

### 变更

- **构建：站点未变化时跳过资源优化。** `optimize_assets` 在每次构建时都会重新扫描所有 HTML/CSS/JS。现在它只在页面实际重建或源文件集合变化时运行；在空增量构建中完全跳过（文档站点：1.61 秒 → 0.87 秒）。

## [11.3.2] — 2026-06-26

### 变更

- **构建：未删除源文件时跳过孤儿输出扫描。** `find_orphaned_outputs` 在每次构建时都会遍历整个 `site_dir`，但孤儿输出只会在源文件*被删除*时出现。构建现在会记录源 URI 集合（`sources.json`），当该集合与上次构建相比未变化或仅增加时，跳过 `site_dir` 遍历。在缓存命中的典型增量构建中，这会移除一次完整的输出树遍历。

## [11.3.1] — 2026-06-26

### 变更

- **SW：条件性 manifest 获取。** `fetchManifest` 现在使用 `fetch(cache-manifest.json, { cache: 'no-cache' })`，而不是用 `?v=Date.now()` 破坏缓存。静态主机在 manifest 未变化时返回 **304**，因此快速导航不再每次都重新下载完整 manifest——同样新鲜，更少带宽。

## [11.3.0] — 2026-06-26

### 变更

- **Service Worker 围绕“当前页面优先”重新设计。** SW 现在对 `docsforge serve` 和已部署站点一视同仁，并优先处理你实际正在查看的页面：
  - **安装不再阻塞**——仅执行 `skipWaiting()`，不再预缓存所有页面（之前的预缓存会让 SW 在每个页面都获取完成前保持非活动状态）。
  - **`serveCurrentPage(request, manifest)`** 在每次导航/页面切换时运行：获取一次 manifest，如果当前页面哈希是最新的则立即从缓存提供，否则获取并缓存最新页面并显示（离线时回退到过时缓存）。这是与后台同步*独立*的函数。
  - **`syncCacheFromManifest(manifest)`** 在后台运行（节流 ≥10 分钟，去重），使用*同一份*已获取的 manifest，缓存所有缺失或哈希已变更的其他页面。
  - **`activate` 首先预加载可见页面**（用户所在标签页），然后后台同步其余页面——因此“首次安装先缓存当前页面” literally 成立。
  - 也适用于**页面切换**：通过 `Accept: text/html` 检测程序化 HTML 获取（Material 即时导航），并将其路由到 `serveCurrentPage`，而不仅是硬导航。

### 修复

- **Manifest 同步不再对每个缓存的 HTML 正文重新哈希。** `cache-manifest.json` 存储的是源 `.md` 文件的哈希，但 SW 缓存的是构建后的 HTML，因此旧的对正文哈希比较永远不匹配，每次同步都会重新获取每个页面。SW 现在将 manifest 与之前同步的每个文件哈希进行**差异比较，并检查缓存是否存在**——只有在页面缺失或实际发生变化时才重新获取。不再对正文哈希。

## [11.2.1] — 2026-06-26

### 变更

- **Service Worker：高效得多的缓存同步。** 此前 `syncCacheFromManifest` 在*每次*导航时都会运行——每次导航都会发起一次 `cache-manifest.json` 网络请求，并对每个已缓存页面进行完整正文的 SHA-256 重新哈希。现在：
  - **节流**：最多每 10 分钟一次（并去重，使并发导航共享一次同步）。
  - **基于差异**：保存上一份 manifest 的每个文件哈希，因此同步只重新获取哈希实际变化的页面。缓存正文不再在每次同步时重新哈希（仅在首次看到某个 URL 时进行一次哈希检查）。
  - 在文档站点（44 页）上，这消除了每次导航约 44 次 SHA-256 运算 + 一次 manifest 请求，替换为一次节流请求，只触及变化页面。
  - 当内容变化时，SW 现在会向打开的标签页发送 `docsforge-updated` 消息（前向兼容钩子；如果没有客户端监听器则无害）。

## [11.2.0] — 2026-06-26

### 变更

- **`docsforge serve` 现在使用与已部署站点完全相同的 Service Worker 缓存策略——没有 localhost 特殊处理。** 之前的版本对 `localhost`/`127.0.0.1` 做了特殊处理（先是硬性的仅网络绕过，然后是 network-first 变体）以保持实时重载新鲜。这使开发环境与生产环境行为不同，并破坏了离线开发。SW 现在将 localhost 与任何其他主机同等对待：HTML/资源使用 cache-first，其余使用 stale-while-revalidate，并进行后台 manifest 同步。结果：实时重载自动刷新可能会提供缓存内容，直到 SW 后台同步跟上——与已部署站点的新鲜度模型相同。开发现在忠实于生产环境，包括服务器停止后的离线支持。

## [11.1.9] — 2026-06-26

### 新增

- **Docker 镜像现在发布带版本号的标签。** 此前只推送 `latest` 和 `sha-*`（`type=semver` 元数据从未触发，因为构建任务检出的是提交 SHA，而不是标签）。每个版本现在还会发布 `ghcr.io/qqshi13/docsforge:<version>`（例如 `:11.1.9`）和 `:<major>.<minor>`（例如 `:11.1`）用于稳定版本。
- **友好、有帮助的 GitHub release notes。** Release 正文现在从对应的 CHANGELOG 条目生成，包含安装/升级命令、Docker pull/run 示例以及 VS Code 扩展下载提示——而不是仅有“Full Changelog”链接。

### 修复

- **`docsforge serve` 页面在服务器停止后仍可离线工作。** Service Worker 有一个硬性的 localhost 绕过：在 `localhost`/`127.0.0.1` 上它从网络获取，**不缓存也不回退**，因此一旦停止开发服务器（或离线），每个页面都是空白。现在对 localhost 使用 **network-first**——服务器运行时提供最新内容（因此实时重载保持无循环，这是最初绕过的原因）——并缓存成功响应，使访问过的页面在服务器关闭后仍然可用。由于 SW 在重载期间从不提供过时的 HTML，过时的缓存重载循环问题依然得到修复。

## [11.1.8] — 2026-06-25

### 修复

- **配置检查摘要现在出现在 `build`/`serve` 输出的开头，而不是末尾。** `check()` 通过 `print()` 输出到 stdout，而构建通过 `logging` 输出到 stderr（无缓冲）。当两个流合并并被管道传输时——即 CI、`docker run` 或任何 `| grep`/`| tail`——stdout 是块缓冲的，直到进程退出才刷新，因此检查块虽然先运行，却落在了构建日志之后。`check()` 现在在返回前刷新 stdout。（回归防护：`test_regression_config_check_appears_before_build_logs`。）

## [11.1.7] — 2026-06-24

### 新增

- **`docsforge serve --strict`** — 开发服务器现在接受 `--strict`（与 `docsforge build` 一致）。重建时将警告视为错误；服务器保持运行并记录中止信息，以便你无需重启即可修复问题。该标志通过 `DevServer.serve` → `serve_module.serve` → `load_config` 传播 `strict=True`。
- **Docker：可自定义 PDF 浏览器。** 文档说明了如何通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 将 PDF 导出指向不同的 Chromium/Chrome（覆盖路径、回退到 Playwright 捆绑的浏览器，或挂载主机二进制文件）。参见 `docs/advanced/docker.md`。

### 变更

- Docker 指南现在列出所有 `--strict`/PDF 浏览器/`--jobs` 选项，并附带可复制的 `docker run` 示例。

## [11.1.6] — 2026-06-24

### 新增

- **新增 75 个测试**（总计 154 个）：`test_files.py`（File 模型、dest_uri/url 映射、`get_files` 遍历）、`test_config.py`（load_config、默认值、env-tag 替换、验证）、`test_init.py`（项目脚手架）、`test_search.py`（SearchIndex 条目/标签/jieba 门控）、`test_tags.py`（Tag 模型）、`test_privacy.py`（FragmentParser、mime 映射）、`test_minify.py`（JS/CSS/HTML 压缩）、`test_meta.py`（meta 文件合并）。

### 修复

- **`load_config` 在 YAML 无效时因 `NameError` 崩溃。** `except yaml.YAMLError` 处理程序引用了一个未导入的 `yaml`，因此 `docsforge.yml` 中的语法错误会产生原始的 `NameError: name 'yaml' is not defined`，而不是友好的错误。（由 `test_config.py::test_invalid_yaml_raises` 发现。）

## [11.1.5] — 2026-06-24

### 新增

- **测试套件。** DocsForge 现在提供 pytest 测试套件（79 个测试），覆盖增量缓存、配置加载、CLI 前端、工具函数、端到端构建以及一个回归文件，每个历史 bug 都有一个命名防护。此前项目没有任何测试。

### 修复

编写测试套件时发现的问题：

- **增量缓存现在对非根页面生效。** `BuildPlanner.find_orphaned_outputs` 只检查 `docs/<name>/index.md` 是否对应输出 `site/<name>/index.html`，遗漏了常见的 `use_directory_urls=True` 映射 `docs/<name>.md` → `site/<name>/index.html`。因此每个非根页面在每次构建开始时都会被当作“孤儿”删除并从头重建，使它们的增量缓存失效。文档站点的第二次构建时间从约 4.7 秒降至约 0.9 秒。
- **`detect_environment` 始终报告 `docs_dir_exists: False`。** 它引用了 `_open_config_file` 但未导入（导入在另一个函数作用域中）； resulting `NameError` 被裸 `except` 吞掉，因此 `docs_dir_exists`/`has_index` 从未被填充。
- **`_open_config_file` 拒绝 `pathlib.Path` 参数。** 它只处理 `str`/`IO`/`None`；`Path` 会落入文件描述符分支并在 `.seek(0)` 时崩溃。现在接受任何 `os.PathLike`。
- **`BuildPlanner.save` 未更新内存中的 `config_hash`。** 将配置哈希写入磁盘后，同一规划器实例上的后续 `should_full_rebuild` 仍看到陈旧的（None）值并强制完整重建。
- **博客插件 `on_shutdown` 可能导致构建崩溃。** 当临时目录已经消失时（同一进程中重复构建），`rmtree(self.temp_dir)` 会抛出 `FileNotFoundError`；清理现在幂等。

## [11.1.4] — 2026-06-24

### 修复

- **增量缓存依赖追踪现在真正生效。** v11.1.3 的实现存在两个缺陷，使其静默无效：
  - `build.py` 向 `DependencyTracker.get_file_deps` 传递 `page.content`（渲染后的 HTML），但 `pymdownx.snippets` 的 `--8<--` 包含标记在 `md.convert()` 期间已被消耗。现在传递 `page.markdown`（保留标记的原始源文件）。
  - 包含路径此前只相对于源文件目录解析，但 `pymdownx.snippets` 是相对于其配置的 `base_path` 解析（docsforge 未设置，因此默认为当前工作目录/项目根目录）。包含现在相对于 `docs_dir`、源文件目录和当前工作目录解析。
- **失败的构建不再被缓存。** 在 strict 模式下，`_build_page` 会重新抛出异常，但构建循环仍会调用 `planner.update_cache`——将损坏的页面标记为最新，导致下一次运行静默跳过它。缓存现在只针对成功构建的页面更新。

## [11.1.3] — 2026-06-23

### 修复

- **增量缓存现在追踪 snippet 包含文件。** `DependencyTracker.get_file_deps` 此前是返回 `[]` 的存根，因此通过 `pymdownx.snippets`（`--8<-- "path"`）包含的文件被编辑时不会触发重建。包含现在相对于源文件解析并被监控变化。`BuildPlanner.update_cache` 中一个从未存储依赖哈希的潜在 bug（使依赖检查无效）也已修复。
- **移除了 `_OPTIONAL_PLUGINS` 死代码路径** 在 `cli_core._check_optional_deps` 中——清空的 plugin→dependency 映射及其未使用的 `plugin_names` 循环。真正的 `jieba`/`docsforge[chinese]` 检查保留。

### 变更

- **仓库卫生——从 git 中移除未跟踪的构建产物：**
  - 移除了 `docsforge-docs/pdf/` 下 42 个已提交的 PDF 构建输出；该目录现在被 gitignore。
  - `docs/blog/index.md`（由博客插件自动生成）取消跟踪并在包级别正确 gitignore。此前根级别的 `docs/blog/index.md` 模式是斜杠锚定的，从未匹配到 `docsforge-docs/` 下的实际路径。
  - 从磁盘删除了陈旧的 `docsforge-vscode-11.0.0-beta.2.vsix`。

## [11.0.0b1] — 2026-06-19

### 新增

- **VSCode 扩展：打开预览** — 侧边栏按钮通过 `simpleBrowser.api.open` 在 VS Code 的 Simple Browser 中打开开发服务器。
- **VSCode 扩展：打开文档** — 侧边栏按钮打开 DocsForge 文档站点。
- **VSCode 扩展：停止构建** — 侧边栏按钮取消正在运行的构建。
- **VSCode 扩展：托管外部服务器** — 通过 `.docsforge/server.json` pidfile 检测终端中启动的 `docsforge serve`。
- **Pidfile** — `docsforge serve` 将 PID 和 URL 写入 `.docsforge/server.json`，供外部工具使用。
- **基于内容的缓存破坏** — 下载的外部资源文件名中包含内容哈希。
- **Docs badge** — 紧凑和标准版 DocsForge 徽章。

### 变更

- **Service worker：localhost 绕过缓存** — SW 检测 `localhost`/`127.0.0.1` 并从网络获取。防止开发期间过时缓存重载循环。
- **Livereload：`_rebuilding` 标志** — 构建期间的文件更改排队处理，不立即执行。之后触发一次最终重建。
- **Tags 模板布局扁平化** — `fragments/tags/{layout}/tag.html` → `fragments/tags/{layout}-tag.html`，`listing.html` → `{layout}-listing.html`。

### 修复

- **Asset optimizer：无引号 HTML 属性** — 使正则中的引号变为可选，以匹配 Material 的无引号输出。
- **Privacy plugin：`url_relative_to` 参数顺序** — 路径此前是从文件到页面，而不是从页面到文件。
- **Privacy plugin：路径规范化** — 正则 `/.` 会匹配 `.icons` → `_icons`。已修复。
- **Webserver：`.well-known` 路由** — Chrome DevTools 探测返回 404。
- **无限重载循环** — `_rebuilding` 标志 + SW localhost 绕过。

### VSCode 扩展

- 通过 `simpleBrowser.api.open` 打开预览
- 打开文档侧边栏按钮
- 停止时进度通知消失
- 3 秒轮询的 Pidfile 检测
- 停止外部服务器（按 PID 终止）
- 停止构建按钮
- 服务器和构建状态的侧边栏状态同步

## [10.9.9] — 2026-06-18

### 修复

- **Favicon 404** — Asset optimizer 正则使引号可选。
- **Privacy font CSS 路径** — `url_relative_to()` 参数顺序已修复。
- **Privacy 路径规范化** — `/.` 正则过于宽泛。

### 新增

- **Pidfile** — `.docsforge-server.json` 用于外部服务器检测。
- **VSCode 扩展：打开预览、打开文档**。

## [10.9.8] — 2026-06-18

### 新增

- **统一发布工作流** — `release.yml`，包含版本升级、提交、标签、release、PyPI、VSIX。
- **DocsForge 徽章** — 紧凑（110×20）和标准版 SVG 徽章。
- **文档：Render、DigitalOcean 部署指南**。

### 变更

- **Tags 模板布局扁平化** — 子目录 → 前缀命名。

## [10.9.7] — 2026-06-18

### 新增

- **统一发布工作流** — 替代 `publish.yml` + `bundle-extension.yml`。
- **VSCode 扩展：侧边栏改进** — 10+ 个 bug 修复。

## [10.9.6] — 2026-06-18

### 修复

- **Privacy：下载 CSS 中的嵌套 URL**。
- **Google Fonts 的 font-display swap**。

### 新增

- **基于哈希的缓存 manifest** 用于离线同步。
- **`.well-known/` 浏览器探测** — 返回 200 + 空 JSON。

## [10.9.5] — 2026-06-17

### 变更

- **简化构建** — 始终完整输出。

### 修复

- **WSL 端口检测** — Socket 超时。
- **SW 仅在内容变化时重新缓存**。

## [10.9.4] — 2026-06-17

### 修复

- **Python `__version__` 与发布同步。**

## [10.9.3] — 2026-06-17

### 修复

- **热重载重复构建** — 竞态条件。

## [10.9.2] — 2026-06-17

### 修复

- **导出插件目录处理。**

## [10.9.1] — 2026-06-11

### 修复

## [10.9.0] — 2026-06-11

### 新增

- **Git 修订日期** — 每个页面现在自动显示 git 历史中的“最后更新”和“创建”日期。无需配置——适用于任何 git 仓库中的文档站点。日期从 `git log` 读取并格式化为人类可读字符串（例如“Jun 11, 2026”）。现有的 `source-file.html` 模板已支持此功能——现在真正被填充。在 docsforge.yml 中通过 `extra.git_revision_date: false` 禁用。

- **CLI serve 选项** — 为 `docsforge serve` 添加 `--no-open`、`--port` 和 `--host` 标志：
  ```bash
  docsforge serve --no-open          # 不自动打开浏览器
  docsforge serve --port 3000        # 在 3000 端口提供服务
  docsforge serve --host 0.0.0.0     # 在所有接口上提供服务
  ```

### 变更

- **默认启用所有主题功能** — material 主题现在默认启用一组丰富的功能，因此新站点无需在 docsforge.yml 中编写冗长的 `features:` 列表即可获得完整体验。新默认值包括：
  - `content.action.edit`, `content.action.view`
  - `content.code.annotate`, `content.code.copy`
  - `content.tooltips`
  - `navigation.footer`, `navigation.indexes`, `navigation.sections`, `navigation.tabs`, `navigation.top`, `navigation.tracking`, `navigation.instant`, `navigation.instant.progress`
  - `search.highlight`, `search.share`, `search.suggest`
  - `toc.follow`

## [10.8.12] — 2026-06-11

### 优化

- **Markdown 实例复用** — 在 `pages.py` 中添加了每个线程的 `markdown.Markdown` 实例缓存。此前，每个页面都会创建一个新的 Markdown 实例，从头初始化所有扩展（pymdownx、codehilite 等）。对于 36 个页面和 10 多个扩展来说，这是显著的开销。现在：
  - 每个线程获得一个以 `(extensions, configs)` 为键的缓存 Markdown 实例
  - 页面之间通过 `reset()` 重置实例，而不是重新创建
  - **构建时间改进**：约 2.5 秒（此前约 3.4 秒）——**快约 25%**
  - 对拥有大量 Markdown 扩展的大型站点尤其有效

- **精简 build.py** — 多项内部优化：
  - 移除了 `_populate_page` 中冗余的 `if _page_lock: with _page_lock:` 分支（它始终是串行调用，不需要锁）
  - 移除了 `_build_page` 中嵌套的 `_do_build()` 闭包，该闭包为每个页面增加了函数调用开销
  - 缓存了 `files.documentation_pages()` 的结果，而不是每次构建调用 3 次
  - 将 `hashlib` 导入从 `_inject_sw_build_hash` 内联位置移到模块顶部
  - 简化了锁处理：在 `_build_page` 中始终获取锁，移除了 `None` 回退路径

- **从版权头中移除 “Cyrus”** — 发现并修复了 3 个仍在版权字符串中包含 “Cyrus” 的文件：`theme.py`、`preview.py`、`filter_config.py`

## [10.8.11] — 2026-06-08

### 变更

- **延迟后台缓存** — 将 Service Worker 安装期间阻塞的 `cache.addAll()` 替换为非阻塞的增量后台缓存。此前，SW 会在安装时尝试一次性下载所有页面，可能阻塞初始页面加载。现在：
  1. SW 立即安装并激活——当前页面无延迟加载。
  2. 激活后，其他页面通过 `backgroundCachePages()` 逐个在后台缓存。
  3. 当前页面在用户访问时已被 `fetch` 处理程序缓存。
  4. 完成后向所有客户端发送 `DOCSFORGE_CACHE_COMPLETE` 消息，因此 UI 可以显示一个微妙的指示器（例如“所有页面可离线使用”）。

## [10.8.10] — 2026-06-08

### 修复

- **Service Worker 预缓存 URL 解析** — `PRE_CACHE_PAGES` URL 是相对于站点根目录的（例如 `"./"`、`"advanced/customization/"`），但 SW 内部的 `cache.addAll()` 是相对于 **SW 脚本位置**（`/assets/javascripts/sw.js`）解析 URL 的。这导致所有预缓存请求静默失败，使缓存为空并破坏离线支持。所有预缓存 URL 现在加上 `../../` 前缀，以便从 SW 正确解析到站点根目录。
- **子路径部署的离线 404 回退** — `cache.match("/404.html")` 被硬编码到域根目录，这对部署在子路径下的站点（例如 `/docsforge/`）是错误的。SW 现在从自身位置计算 `BASE_URL`，并使用 `BASE_URL + '404.html'` 作为回退。

### 新增

- **PWA 更新通知** — 当部署新的 DocsForge 版本时，Service Worker 激活并向所有打开的标签页发送 `DOCSFORGE_UPDATE_READY` 消息。页面在顶部显示固定横幅：*“此文档有新版本可用。”* 并带有 **刷新** 和 **忽略** 按钮。用户可以点击刷新立即加载新内容，或点击忽略继续阅读当前版本。
- **定期更新检查** — 页面每 5 分钟检查一次 Service Worker 更新（`registration.update()`），因此用户即使在长时间运行的会话中也能收到新内容通知，无需手动重载。

## [10.8.9] — 2026-06-07

### 新增

- **完整 PWA / 离线支持** — DocsForge 现在生成 `manifest.json`，并在 Service Worker 安装阶段预缓存所有 HTML 页面，使首次访问后所有文档页面均可离线浏览。
  - **`manifest.json`** — 自动生成，包含站点名称、描述、主题颜色（从调色板提取）和起始 URL。通过每个页面 `<head>` 中的 `<link rel="manifest">` 链接。
  - **预缓存所有页面** — Service Worker 现在接收一个 `__PRE_CACHE_PAGES__` 占位符，构建时替换为所有构建出的 HTML 页面 URL 的完整列表。在 `install` 期间，SW 缓存每个页面，因此它们可以立即离线工作，无需先访问每个页面。
  - **Cache-first 策略** — Service Worker 现在对 HTML 文档使用 `cacheFirstWithNetworkFallback`（此前是 `staleWhileRevalidate`，导致每次导航都发起网络请求）。这意味着即使在线，页面也会从缓存即时加载，并在后台更新。
  - **离线回退** — 如果页面未缓存且用户离线，SW 提供 404 页面（如果 404 未缓存则提供通用离线消息）。

### 变更

- **Service Worker 策略** — 对 HTML 页面和资源从 `staleWhileRevalidate` 切换到 `cacheFirstWithNetworkFallback`。这优先考虑离线可靠性和即时加载，而非始终最新内容。对于大多数文档站点，这是期望的行为。

### 修复

- **从所有文档中移除 “Cyrus”** — 从文档、站点页脚和版权字符串中消除了所有剩余的 “Cyrus” 引用。`license.md` 和 `docsforge.yml` 的站点作者/版权现在仅使用 “QQ”。

## [10.8.8] — 2026-06-06

### 变更

- **始终增量构建** — 从 `serve()` 中移除 `build_type` 参数以及所有 `dirty=False` 默认值。所有构建现在默认增量。`dirty` 标志是一个遗留概念，会造成混淆——完整重建只在配置文件变化时触发（通过哈希检测），并且只有在配置变化时才跳过 `clean_directory` + `cache.invalidate()`。

## [10.8.7] — 2026-06-06

### 修复

- **`docsforge serve` 缓存失效。** `DevServer.serve()` 没有将 `build_type='dirty'` 传递给 `serve_module.serve()`，导致开发服务器在每次文件变化时都进行完整重建和缓存失效。这使实时重载非常慢。`build` 命令已经默认进行 dirty/增量构建；现在 `serve` 也如此。

## [10.8.6] — 2026-06-06

### 修复

- **子页面资源 404。** `get_relative_url()` 计算的 `base_url` 对子目录页面返回没有尾部斜杠的 `..`。没有尾部斜杠时，`_get_relative_url` 将其视为文件名（将其剥离），导致 CSS/JS/资源路径相对于页面目录解析，而不是站点根目录。在 `get_context()` 和 `_build_template()` 中添加了尾部斜杠规范化。

## [10.8.5] — 2026-06-06

### 修复

- **侧边栏竞态条件。** ThreadPoolExecutor 并行页面构建导致多个页面同时被标记为 `active`。每个 `Page.active` setter 会传播到其父 `Section`，因此并发构建会在页面之间泄漏激活状态。结果是侧边栏显示多个部分同时展开，而只有当前部分应该展开。重构 `_build_page`，在整个模板渲染 + 文件写入阶段持有现有的 `RLock`，确保任何时候只有一个页面处于激活状态。

## [10.8.4] — 2026-06-06

### 修复

- **非根页面搜索索引 404。** `build.py` 中的 `base_url` 计算反了：`get_relative_url('.', page.url)` 返回的是从根*到*页面的路径，而不是从页面*到*根的路径。JS 将其注入页面配置为 `base`，然后相对于它解析 `search/search_index.json`，产生重复路径如 `/docsforge/getting-started/getting-started/search/search_index.json`。已修复为 `get_relative_url(page.url, '.')`。
- **桌面端侧边栏与页脚重叠。** 在 `min-width: 60em` 下为 `.md-sidebar__scrollwrap` 添加 `max-height: calc(100vh - 2.4rem)`，防止侧边栏超出视口并与页脚重叠。

## [10.3.3] — 2026-05-17

### 新增

- **带版本号的 Service Worker** — 每次构建在 SW 中生成唯一哈希，确保浏览器安装新版本并清除旧缓存
- **自动缓存清理** — 新 SW 激活时自动删除旧缓存
- **离线支持** — 所有同源文件被缓存；HTML 使用 network-first，资源使用 cache-first
- **PWA 就绪** — 每个构建页面都注册 Service Worker

### 修复

- Service Worker 作用域设置为 `/`（根目录）而非 `/assets/javascripts/`，以便拦截所有请求

## [10.3.2] — 2026-05-17

### 修复

- Service Worker 作用域固定为 `/`，以便缓存博客文章和文档页面
- 添加 `request.mode === "navigate"` 检查以更好检测 HTML 页面

## [10.3.1] — 2026-05-17

### 修复

- `.icons/` 目录现在包含在 PyPI wheel 构建中
- 在 `pyproject.toml` 中添加 `artifacts` 模式，确保 Material 主题图标被打包

## [10.3.0] — 2026-05-17

### 新增

- **TikZ 图表支持** — 在 Markdown 中编写 TikZ 图表，构建时自动编译为 SVG
- **主题游乐场** — 带实时预览的交互式调色板切换器
- **博客插件** — 内置博客，支持作者、标签、归档、分页和 RSS feed

### 修复

- 修复源仓库空白点（无 stars/forks 时移除固定 234px 宽度）
- 跨页面导航的主题持久化（使用 `__md_scope` 而非每页 URL）
- 调色板切换按钮高亮同步
- 404 页面样式

### 变更

- 清理仓库中无关的开发文件
- 所有仓库使用 `main` 作为默认分支

## [10.2.0] — 2026-05-16

### 新增

- **Vendored mkdocs + Material** — 自包含，无外部依赖
- **GitHub Pages 部署** — 用于自动部署的 GitHub Actions 工作流
- **PyPI 发布** — 通过 GitHub Actions 自动发布

## [10.1.0] — 2026-05-10

### 新增

- **零配置 Markdown** — 默认加载 31 个扩展（所有 pymdownx + python-markdown）。无需 `markdown_extensions:` 配置。
- **KaTeX 数学** — Vendored KaTeX（1.5MB）渲染 `$$...$$` 行内和显示数学。读者无需 CDN 调用，无需配置。
- **Pygments 高亮** — 构建时进行语法着色代码块。无客户端 JS。
- **深色模式切换** — 页眉中的浅色/深色模式切换。自动检测系统偏好。
- **自动加载插件** — search、tags、blog、info、meta、minify、privacy 均无需配置即可工作。
- **自托管字体** — Privacy 插件下载并本地缓存 Google Fonts。

### 变更

- **配置文件** 从 `properdocs.yml` 重命名为 `docsforge.yml`
- **主题命名空间** 从 `mkdocs.themes` 更改为 `docsforge.themes`
- **插件系统** — 移除了 6 个插件，保留 7 个作为默认内置插件

### 移除

- `typeset` — 用户可以直接使用 Unicode
- `optimize` — 需要外部 `pngquant` 二进制文件
- `social` — 需要 Pillow + CairoSVG
- `projects` — 小众的多项目功能
- `offline` — Privacy 插件覆盖大多数用例
- `group` — 插件编排器（小众）

## [0.1.0] — 2025-05-10

### 新增

- 初始版本
