/**
 * Editor intelligence providers for DocsForge markdown — no LSP, everything
 * computed from the docs tree and the build's validation.json.
 *
 * Registered only for markdown documents inside the workspace docs_dir.
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  extractHeadings,
  extractLinks,
  splitAnchor,
  resolveLinkTarget,
  docsDirFromConfig,
  formatMarkdown,
  slugifyHeading,
  walkDocs,
  srcUriOfPath,
  linkTargetPrefix,
  filterDocsByPrefix,
  snippetPathPrefix,
  anchorPrefix,
  frontmatterRange,
  FRONTMATTER_KEYS,
  HIDE_VALUES,
  SEARCH_CHILD_KEYS,
} from './links';
import { getHeadings } from './studioCache';

/** Re-exported pure helpers (canonical implementations live in links.ts). */
export { linkTargetPrefix, filterDocsByPrefix };

/** Docs-relative URI for a file, or null when outside the docs dir.
 *  Central guard for non-docs .md files (e.g. root README.md) that match the
 *  broad `root/**​/*.md` selector but would otherwise produce garbage via
 *  `fsPath.slice(docsDir.length + 1)`. */
export function srcUriOf(
  root: string, docsDirAbs: string, fsPath: string,
): string | null {
  void root;
  return srcUriOfPath(docsDirAbs, fsPath);
}

/** Cached docs file list per workspace root (avoids readdirSync walks on
 *  hot paths like completion keystrokes and lightbulb requests). */
export class DocsFileCache {
  private files: Array<{ absPath: string; srcUri: string }> | null = null;
  private nameIndex: Map<string, string[]> | null = null;
  private watcher: vscode.FileSystemWatcher | null = null;
  private debounce: NodeJS.Timeout | null = null;

  constructor(
    private root: string,
    private docsDirAbs: string,
  ) {}

  getFiles(): Array<{ absPath: string; srcUri: string }> {
    if (!this.files) {
      try {
        this.files = fs.existsSync(this.docsDirAbs) ? walkDocs(this.docsDirAbs) : [];
      } catch {
        this.files = [];
      }
    }
    return this.files;
  }

  /** Basename → srcUris index (single walk per request, not per link). */
  findByName(wanted: string): string[] {
    if (!this.nameIndex) {
      this.nameIndex = new Map<string, string[]>();
      for (const f of this.getFiles()) {
        const base = f.srcUri.slice(f.srcUri.lastIndexOf('/') + 1);
        const list = this.nameIndex.get(base) ?? [];
        list.push(f.srcUri);
        this.nameIndex.set(base, list);
      }
    }
    return this.nameIndex.get(wanted) ?? [];
  }

  invalidate(): void {
    this.files = null;
    this.nameIndex = null;
  }

  scheduleInvalidate(delayMs = 250): void {
    if (this.debounce) {
      clearTimeout(this.debounce);
    }
    this.debounce = setTimeout(() => {
      this.debounce = null;
      this.invalidate();
    }, delayMs);
  }

  ensureWatcher(context: vscode.ExtensionContext): void {
    if (this.watcher) {
      return;
    }
    try {
      const docsDir = path.relative(this.root, this.docsDirAbs) || 'docs';
      const pattern = new vscode.RelativePattern(this.root, `${docsDir}/**/*.md`);
      this.watcher = vscode.workspace.createFileSystemWatcher(pattern);
      this.watcher.onDidCreate(() => this.scheduleInvalidate(), null, context.subscriptions);
      this.watcher.onDidDelete(() => this.scheduleInvalidate(), null, context.subscriptions);
      context.subscriptions.push(this.watcher);
    } catch {
      this.watcher = null;
    }
  }

  dispose(): void {
    if (this.debounce) {
      clearTimeout(this.debounce);
      this.debounce = null;
    }
    this.watcher?.dispose();
    this.watcher = null;
  }
}

const docsCaches = new Map<string, DocsFileCache>();

/** Shared cache for a workspace root (created lazily, watcher on register). */
export function getDocsCache(root: string): DocsFileCache {
  const existing = docsCaches.get(root);
  if (existing) {
    return existing;
  }
  const docsDirAbs = path.join(root, docsDirFromConfig(root));
  const cache = new DocsFileCache(root, docsDirAbs);
  docsCaches.set(root, cache);
  return cache;
}

/** Dispose all docs caches (tests / deactivate). */
export function disposeDocsCaches(): void {
  for (const cache of docsCaches.values()) {
    cache.dispose();
  }
  docsCaches.clear();
}

/** Whether a document is a markdown doc inside the project's docs dir. */
export function isDocDocument(
  document: vscode.TextDocument, root: string,
): boolean {
  if (document.languageId !== 'markdown') {
    return false;
  }
  const docsDir = path.join(root, docsDirFromConfig(root));
  const fsPath = document.uri.fsPath;
  return fsPath.startsWith(docsDir + path.sep) || fsPath === docsDir;
}

/** Read a doc's text, or null. */
function readDoc(absPath: string): string | null {
  try {
    return fs.readFileSync(absPath, 'utf-8');
  } catch {
    return null;
  }
}

/** Offset → Position using the document's line offsets. */
function offsetToPosition(text: string, offset: number): vscode.Position {
  const before = text.slice(0, offset);
  const line = before.split('\n').length - 1;
  const lastNl = before.lastIndexOf('\n');
  const ch = lastNl === -1 ? offset : offset - lastNl - 1;
  return new vscode.Position(line, ch);
}

/* ------------------------------------------------------------------ */

class DocsForgeDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
  provideDocumentSymbols(document: vscode.TextDocument): vscode.DocumentSymbol[] {
    const text = document.getText();
    const lines = text.split('\n');
    const headings = extractHeadings(text);
    if (!headings.length) {
      return [];
    }
    const symbols: vscode.DocumentSymbol[] = [];
    // Stack of open symbols with their heading level.
    const stack: Array<{ level: number; symbol: vscode.DocumentSymbol }> = [];
    for (const h of headings) {
      const lineLen = lines[h.line]?.length ?? 0;
      const range = new vscode.Range(h.line, 0, h.line, lineLen);
      const sym = new vscode.DocumentSymbol(
        h.title, `H${h.level}`, vscode.SymbolKind.String, range, range,
      );
      // Pop parents that are deeper or equal in level.
      while (stack.length && stack[stack.length - 1].level >= h.level) {
        stack.pop();
      }
      if (stack.length) {
        stack[stack.length - 1].symbol.children.push(sym);
      } else {
        symbols.push(sym);
      }
      stack.push({ level: h.level, symbol: sym });
    }
    return symbols;
  }
}

class DocsForgeFoldingProvider implements vscode.FoldingRangeProvider {
  provideFoldingRanges(document: vscode.TextDocument): vscode.FoldingRange[] {
    const text = document.getText();
    const lines = text.split('\n');
    const ranges: vscode.FoldingRange[] = [];
    const headings: number[] = [];
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(/^(#{1,6})\s/);
      if (m) {
        headings.push(i);
      }
    }
    for (let i = 0; i < headings.length; i++) {
      const end = i + 1 < headings.length ? headings[i + 1] - 1 : lines.length - 1;
      if (end > headings[i]) {
        ranges.push(new vscode.FoldingRange(headings[i], end));
      }
    }
    // Fenced code blocks
    let inFence = false;
    let fenceStart = 0;
    for (let i = 0; i < lines.length; i++) {
      if (/^```/.test(lines[i]) || /^~~~/.test(lines[i])) {
        if (!inFence) {
          inFence = true;
          fenceStart = i;
        } else {
          inFence = false;
          if (i > fenceStart + 1) {
            ranges.push(new vscode.FoldingRange(fenceStart, i));
          }
        }
      }
    }
    return ranges;
  }
}

class DocsForgeDefinitionProvider implements vscode.DefinitionProvider {
  constructor(private root: string) {}

  provideDefinition(document: vscode.TextDocument, position: vscode.Position): vscode.Location | null {
    const text = document.getText();
    const line = text.split('\n')[position.line];
    if (!line) {
      return null;
    }
    const links = extractLinks(line);
    for (const link of links) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
      const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
      if (!srcUri) {
        return null;
      }
      const resolved = resolveLinkTarget(
        path.join(this.root, docsDirFromConfig(this.root)),
        srcUri, target,
      );
      if (!resolved) {
        continue;
      }
      if (!fs.existsSync(resolved.absPath)) {
        continue;
      }
      const targetText = readDoc(resolved.absPath);
      let pos = new vscode.Position(0, 0);
      if (anchor && targetText) {
        const headings = extractHeadings(targetText);
        const found = headings.find(
          (h) => slugifyHeading(h.title) === slugifyHeading(anchor),
        );
        if (found) {
          pos = new vscode.Position(found.line, 0);
        }
      }
      return new vscode.Location(vscode.Uri.file(resolved.absPath), pos);
    }
    return null;
  }
}

class DocsForgeHoverProvider implements vscode.HoverProvider {
  constructor(private root: string) {}

  provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | null {
    const text = document.getText();
    const line = text.split('\n')[position.line];
    if (!line) {
      return null;
    }
    const links = extractLinks(line);
    for (const link of links) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
      const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
      if (!srcUri) {
        return null;
      }
      const resolved = resolveLinkTarget(
        path.join(this.root, docsDirFromConfig(this.root)),
        srcUri, target,
      );
      if (!resolved) {
        return new vscode.Hover('*Broken link:* target escapes the docs directory.');
      }
      if (!fs.existsSync(resolved.absPath)) {
        return new vscode.Hover('*Broken link:* target file not found.');
      }
      const targetText = readDoc(resolved.absPath);
      if (anchor) {
        const headings = extractHeadings(targetText ?? '');
        const found = headings.find(
          (h) => slugifyHeading(h.title) === slugifyHeading(anchor),
        );
        if (!found) {
          return new vscode.Hover(`*Broken link:* no anchor \`#${anchor}\` in target.`);
        }
        return new vscode.Hover(`**${found.title}** — \`${resolved.srcUri}#${anchor}\``);
      }
      const preview = (targetText ?? '').split('\n').slice(0, 5).join('\n').slice(0, 400);
      return new vscode.Hover(preview || `\`${resolved.srcUri}\``);
    }
    return null;
  }
}

class DocsForgeReferenceProvider implements vscode.ReferenceProvider {
  constructor(private root: string) {}

  async provideReferences(
    document: vscode.TextDocument, _position: vscode.Position,
  ): Promise<vscode.Location[]> {
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const targetSrcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
    const locations: vscode.Location[] = [];
    if (!targetSrcUri || !fs.existsSync(docsDirAbs)) {
      return locations;
    }
    // Cached file list (FileSystemWatcher-invalidated) instead of a
    // synchronous full-tree walk on every request.
    const files = getDocsCache(this.root).getFiles();
    for (const f of files) {
      const src = readDoc(f.absPath);
      if (!src) {
        continue;
      }
      for (const link of extractLinks(src)) {
        const { target } = splitAnchor(link.dest);
        if (!target) {
          continue;
        }
        const resolved = resolveLinkTarget(docsDirAbs, f.srcUri, target);
        if (resolved && resolved.srcUri === targetSrcUri) {
          const pos = offsetToPosition(src, link.offset + 1);
          locations.push(new vscode.Location(vscode.Uri.file(f.absPath), pos));
        }
      }
    }
    return locations;
  }
}

class DocsForgeCompletionProvider implements vscode.CompletionItemProvider {
  constructor(private root: string) {}

  async provideCompletionItems(
    document: vscode.TextDocument, position: vscode.Position,
  ): Promise<vscode.CompletionItem[]> {
    const text = document.getText();
    const line = text.split('\n')[position.line] ?? '';
    const before = line.slice(0, position.character);
    // Frontmatter keys/values (manual invoke: no trigger char fires here).
    const fm = frontmatterRange(text);
    if (fm && position.line > fm.startLine && position.line <= fm.endLine) {
      return this.frontmatterCompletions(text, position);
    }
    // Snippet includes: --8<-- "partial (paths resolve against the
    // source file's directory first, then the project root).
    const snip = snippetPathPrefix(before);
    if (snip !== null) {
      return this.snippetCompletions(document, position, snip);
    }
    // Anchors inside a link destination must win over path completion.
    const anch = anchorPrefix(before);
    if (anch !== null) {
      return this.anchorCompletions(document, position, anch);
    }
    const iconMatch = before.match(/:([a-z0-9-]*)$/);
    if (iconMatch) {
      return this.iconCompletions(iconMatch[1]);
    }
    // Link target completion only inside `](…)` of a markdown link — not
    // inside arbitrary parens — so normal typing doesn't pay for a docs walk.
    const partial = linkTargetPrefix(before);
    if (partial === null) {
      return [];
    }
    return this.pathCompletions(partial);
  }

  /** Known frontmatter keys + `hide:` / `search:` values. Key context has
   *  no trigger char, so this mostly serves manual invoke (Ctrl+Space). */
  private frontmatterCompletions(
    text: string, position: vscode.Position,
  ): vscode.CompletionItem[] {
    const lines = text.split('\n');
    const line = lines[position.line] ?? '';
    const before = line.slice(0, position.character);
    if (/^\s{0,3}[A-Za-z_-]*$/.test(before)) {
      return FRONTMATTER_KEYS.map(({ key, detail }) => {
        const item = new vscode.CompletionItem(key, vscode.CompletionItemKind.Property);
        item.insertText = `${key}: `;
        item.filterText = key;
        item.detail = detail;
        return item;
      });
    }
    // Nearest mapping key above the cursor (e.g. `hide:` / `search:`).
    let parent: string | null = null;
    for (let i = position.line - 1; i >= 0; i--) {
      const km = lines[i].match(/^([A-Za-z_-]+):\s*$/);
      if (km) {
        parent = km[1];
        break;
      }
      if (/^\S/.test(lines[i])) {
        break;
      }
    }
    if (/^\s*hide:\s*(\[[\w\s,"]*)?$/.test(before) || (/^\s*-\s*[\w-]*$/.test(before) && parent === 'hide')) {
      return HIDE_VALUES.map((v) => {
        const item = new vscode.CompletionItem(v, vscode.CompletionItemKind.Value);
        item.detail = 'hide: option';
        return item;
      });
    }
    if (/^\s{2,}[A-Za-z_-]*$/.test(before) && parent === 'search') {
      return SEARCH_CHILD_KEYS.map(({ key, detail }) => {
        const item = new vscode.CompletionItem(key, vscode.CompletionItemKind.Property);
        item.insertText = `${key}: `;
        item.filterText = key;
        item.detail = detail;
        return item;
      });
    }
    return [];
  }

  /** Headings of the link target as `#slug` completions. */
  private anchorCompletions(
    document: vscode.TextDocument, position: vscode.Position,
    anch: { target: string; partial: string },
  ): vscode.CompletionItem[] {
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
    let absPath: string | null = null;
    if (!anch.target) {
      absPath = document.uri.fsPath;
    } else if (srcUri) {
      const resolved = resolveLinkTarget(docsDirAbs, srcUri, anch.target);
      if (resolved) {
        absPath = resolved.absPath;
      }
    }
    if (!absPath || !absPath.endsWith('.md') || !fs.existsSync(absPath)) {
      return [];
    }
    const startCh = position.character - anch.partial.length;
    return getHeadings(this.root, absPath)
      .filter((h) => h.slug.startsWith(anch.partial))
      .slice(0, 50)
      .map((h) => {
        const item = new vscode.CompletionItem(`#${h.slug}`, vscode.CompletionItemKind.Value);
        item.insertText = h.slug;
        item.filterText = h.slug;
        item.detail = h.title;
        item.range = new vscode.Range(position.line, startCh, position.line, position.character);
        return item;
      });
  }

  /** Files for a `--8<-- "…"` include: siblings first, then docs-tree
   *  paths relative to the current file. */
  private snippetCompletions(
    document: vscode.TextDocument, position: vscode.Position, partial: string,
  ): vscode.CompletionItem[] {
    const items: vscode.CompletionItem[] = [];
    const seen = new Set<string>();
    const startCh = position.character - partial.length;
    const push = (name: string, detail: string) => {
      if (seen.has(name) || items.length >= 100) {
        return;
      }
      seen.add(name);
      const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.File);
      item.insertText = name;
      item.filterText = name;
      item.detail = detail;
      item.range = new vscode.Range(position.line, startCh, position.line, position.character);
      items.push(item);
    };
    // Siblings in the source file's directory (any extension), honoring
    // a typed `sub/dir/` prefix. Sandboxed to the workspace root.
    const slash = partial.lastIndexOf('/');
    const dirPart = slash === -1 ? '' : partial.slice(0, slash);
    const seg = slash === -1 ? partial : partial.slice(slash + 1);
    const base = path.dirname(document.uri.fsPath);
    const dir = dirPart ? path.normalize(path.join(base, dirPart)) : base;
    const outside = path.relative(this.root, dir).startsWith('..');
    if (!outside) {
      try {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
          if (entry.name.startsWith('.') || !entry.name.startsWith(seg)) {
            continue;
          }
          const name = entry.isDirectory() ? `${entry.name}/` : entry.name;
          push(dirPart ? `${dirPart}/${name}` : name, 'sibling file');
        }
      } catch {
        /* unreadable dir → docs-tree candidates only */
      }
    }
    // Docs-tree .md files, expressed relative to the current file.
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
    if (srcUri && fs.existsSync(docsDirAbs)) {
      for (const name of filterDocsByPrefix(getDocsCache(this.root).getFiles(), '', 200)) {
        let rel = path.posix.relative(path.posix.dirname(srcUri), name);
        if (!rel.startsWith('.')) {
          rel = `./${rel}`;
        }
        if (rel.startsWith(partial)) {
          push(rel, 'docs file');
        }
      }
    }
    return items;
  }

  private iconCompletions(prefix: string): vscode.CompletionItem[] {
    const items: vscode.CompletionItem[] = [];
    const themeIcons = this.findThemeIconsDir();
    if (!themeIcons) {
      return items;
    }
    // Match the family: `:material-…`, `:lucide-…`, etc.
    const familyMatch = prefix.match(/^(material|lucide|fontawesome|octicons)(?:-|$)/);
    const families = familyMatch ? [familyMatch[1]] : ['material', 'lucide', 'fontawesome', 'octicons'];
    const namePrefix = familyMatch ? prefix.slice(familyMatch[1].length + 1) : prefix;
    for (const family of families) {
      const icons = this.iconsFor(family, themeIcons);
      for (const name of icons) {
        if (!name.startsWith(namePrefix)) {
          continue;
        }
        const item = new vscode.CompletionItem(`:${family}-${name}:`, vscode.CompletionItemKind.Color);
        item.insertText = `:${family}-${name}:`;
        item.detail = `${family}/${name}`;
        item.filterText = `${family}-${name}`;
        items.push(item);
        if (items.length >= 100) {
          return items;
        }
      }
    }
    return items;
  }

  private iconCache = new Map<string, string[]>();

  private iconsFor(family: string, themeIcons: string): string[] {
    const cached = this.iconCache.get(family);
    if (cached) {
      return cached;
    }
    const dir = path.join(themeIcons, family);
    let names: string[] = [];
    if (fs.existsSync(dir)) {
      names = fs.readdirSync(dir)
        .filter((f) => f.endsWith('.svg'))
        .map((f) => f.slice(0, -4));
    }
    this.iconCache.set(family, names);
    return names;
  }

  private findThemeIconsDir(): string | null {
    // Theme icons live in the installed docsforge package under templates/.icons.
    const candidate = path.join(this.root, 'docsforge', 'templates', '.icons');
    if (fs.existsSync(path.join(candidate, 'material'))) {
      return candidate;
    }
    return null;
  }

  private pathCompletions(partial: string): vscode.CompletionItem[] {
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    if (!fs.existsSync(docsDirAbs)) {
      return [];
    }
    // Cached file list + prefix pruning (no full readdirSync walk per keystroke).
    const files = getDocsCache(this.root).getFiles();
    const names = filterDocsByPrefix(files, partial, 200);
    return names.map((name) => {
      const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.File);
      item.insertText = name;
      item.detail = name;
      return item;
    });
  }
}

/** Highlight repeated occurrences of the token under the cursor, and all
 *  links sharing the same destination (Zensical-style "spot repeated"). */
class DocsForgeHighlightProvider implements vscode.DocumentHighlightProvider {
  provideDocumentHighlights(
    document: vscode.TextDocument, position: vscode.Position,
  ): vscode.DocumentHighlight[] {
    const text = document.getText();
    const lines = text.split('\n');
    const line = lines[position.line] ?? '';
    const wordRe = /[A-Za-z0-9_\-.:/]+/g;
    let m: RegExpExecArray | null;
    let word: string | null = null;
    while ((m = wordRe.exec(line)) !== null) {
      if (position.character >= m.index && position.character <= m.index + m[0].length) {
        word = m[0];
        break;
      }
    }
    if (!word) {
      return [];
    }
    const highlights: vscode.DocumentHighlight[] = [];
    // Repeated word occurrences.
    const wRe = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    for (let i = 0; i < lines.length; i++) {
      let mm: RegExpExecArray | null;
      wRe.lastIndex = 0;
      while ((mm = wRe.exec(lines[i])) !== null) {
        highlights.push(new vscode.DocumentHighlight(
          new vscode.Range(i, mm.index, i, mm.index + mm[0].length),
        ));
      }
    }
    // Same destination links (e.g. the same anchor linked in many rows).
    if (word.startsWith('#')) {
      for (const link of extractLinks(text)) {
        if (link.dest === word) {
          highlights.push(new vscode.DocumentHighlight(
            new vscode.Range(link.line, link.offset, link.line, link.offset + link.dest.length + 2),
            vscode.DocumentHighlightKind.Text,
          ));
        }
      }
    }
    return highlights;
  }
}

/** Decorate markdown links with their resolved target (documentLink). */
class DocsForgeDocumentLinkProvider implements vscode.DocumentLinkProvider {
  constructor(private root: string) {}

  provideDocumentLinks(document: vscode.TextDocument): vscode.DocumentLink[] {
    const text = document.getText();
    const lines = text.split('\n');
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
    if (!srcUri) {
      return [];
    }
    const links: vscode.DocumentLink[] = [];
    for (const link of extractLinks(text)) {
      const { target, anchor } = splitAnchor(link.dest);
      const resolved = target ? resolveLinkTarget(docsDirAbs, srcUri, target) : null;
      const startChar = lines[link.line].indexOf('(', link.offset) + 1;
      const endChar = startChar + link.dest.length;
      const range = new vscode.Range(link.line, startChar, link.line, endChar);
      const dl = new vscode.DocumentLink(
        range,
        resolved && fs.existsSync(resolved.absPath)
          ? vscode.Uri.file(resolved.absPath)
          : undefined,
      );
      dl.tooltip = resolved
        ? `${resolved.srcUri}${anchor ? `#${anchor}` : ''}${fs.existsSync(resolved.absPath) ? '' : ' (broken)'}`
        : (target ? `target escapes docs dir` : 'anchor link');
      links.push(dl);
    }
    return links;
  }
}

/** Quick fixes for broken links (code actions on diagnostics). */
class DocsForgeCodeActionProvider implements vscode.CodeActionProvider {
  constructor(private root: string) {}

  async provideCodeActions(
    document: vscode.TextDocument, range: vscode.Range,
    context: vscode.CodeActionContext,
  ): Promise<vscode.CodeAction[]> {
    const actions: vscode.CodeAction[] = [];
    const text = document.getText();
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const srcUri = srcUriOf(this.root, docsDirAbs, document.uri.fsPath);
    if (!srcUri) {
      return actions;
    }
    const cache = getDocsCache(this.root);
    // All links in the file (handles images, titled links, and multiple
    // links per line — String.match without /g only saw the first).
    const allLinks = extractLinks(text);
    const byLine = new Map<number, typeof allLinks>();
    for (const link of allLinks) {
      const list = byLine.get(link.line) ?? [];
      list.push(link);
      byLine.set(link.line, list);
    }
    // Track which link destinations we've already offered actions for, so a
    // repeated anchor doesn't produce duplicate actions on the same line.
    const seen = new Set<string>();
    const handleLine = (lineNo: number) => {
      const linksOnLine = byLine.get(lineNo) ?? [];
      for (const link of linksOnLine) {
        const dest = link.dest;
        if (seen.has(dest)) {
          continue;
        }
        seen.add(dest);
        const { target } = splitAnchor(dest);
        if (!target) {
          // Anchor-only links (e.g. [#section]) — nothing to open/fix.
          continue;
        }
        // Suggest a fix that points to an existing file with the same name
        // (single cached index lookup, not a readdirSync walk per lightbulb).
        const wanted = path.posix.basename(target);
        const candidates = cache.findByName(wanted);
        if (candidates.length && !candidates.includes(target)) {
          const fix = new vscode.CodeAction(
            `Fix link: use ${candidates[0]}`,
            vscode.CodeActionKind.QuickFix,
          );
          let newTarget = path.posix.relative(path.posix.dirname(srcUri), candidates[0]);
          if (!newTarget.startsWith('.')) {
            newTarget = `./${newTarget}`;
          }
          const linkPos = offsetToPosition(text, link.offset + 1);
          const endPos = offsetToPosition(text, link.offset + 1 + dest.length);
          fix.edit = new vscode.WorkspaceEdit();
          fix.edit.replace(document.uri, new vscode.Range(linkPos, endPos), newTarget);
          actions.push(fix);
        }
        // Offer to open the target in the editor.
        const open = new vscode.CodeAction('Open link target', vscode.CodeActionKind.QuickFix);
        open.command = {
          command: 'docsforge.openLinkTarget',
          title: 'Open link target',
          arguments: [{ uri: document.uri.toString(), dest }],
        };
        actions.push(open);
      }
    };

    // Diagnostic-driven: every broken link occurrence gets its own actions
    // (repeated anchors emit a diagnostic per line, so all lightbulbs show).
    for (const diag of context.diagnostics) {
      handleLine(diag.range.start.line);
    }
    // Also handle the line under the cursor even without a diagnostic, so the
    // lightbulb appears on any link (e.g. before the first build writes
    // validation.json, or for a link not covered by validation).
    handleLine(range.start.line);
    // Feature #3: "Fix all broken links in file" — one action that applies
    // every auto-fixable link correction across the document (one entry per
    // occurrence, not per distinct dest, so repeats are all fixed).
    const fixes: Array<{ uri: vscode.Uri; range: vscode.Range; newText: string }> = [];
    for (const link of allLinks) {
      const dest = link.dest;
      const { target } = splitAnchor(dest);
      if (!target) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, srcUri, target);
      if (resolved && fs.existsSync(resolved.absPath)) {
        continue; // not broken
      }
      const wanted = path.posix.basename(target);
      const candidates = cache.findByName(wanted);
      if (!candidates.length || candidates.includes(target)) {
        continue;
      }
      let newTarget = path.posix.relative(path.posix.dirname(srcUri), candidates[0]);
      if (!newTarget.startsWith('.')) {
        newTarget = `./${newTarget}`;
      }
      const linkPos = offsetToPosition(text, link.offset + 1);
      const endPos = offsetToPosition(text, link.offset + 1 + dest.length);
      fixes.push({
        uri: document.uri,
        range: new vscode.Range(linkPos, endPos),
        newText: newTarget,
      });
    }
    if (fixes.length > 1) {
      const fixAll = new vscode.CodeAction(
        `Fix all broken links (${fixes.length})`,
        vscode.CodeActionKind.QuickFix,
      );
      const edit = new vscode.WorkspaceEdit();
      for (const f of fixes) {
        edit.replace(f.uri, f.range, f.newText);
      }
      fixAll.edit = edit;
      actions.push(fixAll);
    }
    return actions;
  }
}

/** Format markdown: normalize trailing whitespace and blank-line runs. */
class DocsForgeFormattingProvider implements vscode.DocumentFormattingEditProvider {
  provideDocumentFormattingEdits(document: vscode.TextDocument): vscode.TextEdit[] {
    const formatted = formatMarkdown(document.getText());
    if (formatted === document.getText()) {
      return [];
    }
    const full = new vscode.Range(0, 0, document.lineCount, 0);
    return [vscode.TextEdit.replace(full, formatted)];
  }
}

/** Register all providers for a workspace root. */
export function registerProviders(context: vscode.ExtensionContext, root: string): void {
  const sel: vscode.DocumentSelector = {
    scheme: 'file',
    language: 'markdown',
    pattern: `${root}/**/*.md`,
  };

  // Warm the cached docs list and invalidate it on md create/delete (debounced).
  getDocsCache(root).ensureWatcher(context);

  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(sel, new DocsForgeDocumentSymbolProvider()),
    vscode.languages.registerFoldingRangeProvider(sel, new DocsForgeFoldingProvider()),
    vscode.languages.registerDefinitionProvider(sel, new DocsForgeDefinitionProvider(root)),
    vscode.languages.registerHoverProvider(sel, new DocsForgeHoverProvider(root)),
    vscode.languages.registerReferenceProvider(sel, new DocsForgeReferenceProvider(root)),
    vscode.languages.registerCompletionItemProvider(sel, new DocsForgeCompletionProvider(root), ':', '(', '/', '#', '"'),
    vscode.languages.registerDocumentHighlightProvider(sel, new DocsForgeHighlightProvider()),
    vscode.languages.registerDocumentLinkProvider(sel, new DocsForgeDocumentLinkProvider(root)),
    vscode.languages.registerCodeActionsProvider(sel, new DocsForgeCodeActionProvider(root)),
    vscode.languages.registerDocumentFormattingEditProvider(sel, new DocsForgeFormattingProvider()),
  );
}
