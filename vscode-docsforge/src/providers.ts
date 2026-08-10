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
} from './links';

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
      const srcUri = document.uri.fsPath.slice(
        path.join(this.root, docsDirFromConfig(this.root)).length + 1,
      ).split(path.sep).join('/');
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
        const slug = anchor.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        const found = headings.find(
          (h) => h.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') === slug,
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
      const srcUri = document.uri.fsPath.slice(
        path.join(this.root, docsDirFromConfig(this.root)).length + 1,
      ).split(path.sep).join('/');
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
        const slug = anchor.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        const found = headings.find(
          (h) => h.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') === slug,
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

  provideReferences(
    document: vscode.TextDocument, _position: vscode.Position,
  ): vscode.Location[] {
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    const targetSrcUri = document.uri.fsPath.slice(docsDirAbs.length + 1)
      .split(path.sep).join('/');
    const locations: vscode.Location[] = [];
    if (!fs.existsSync(docsDirAbs)) {
      return locations;
    }
    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(p);
        } else if (entry.name.endsWith('.md')) {
          const src = readDoc(p);
          if (!src) {
            continue;
          }
          const srcUri = p.slice(docsDirAbs.length + 1).split(path.sep).join('/');
          for (const link of extractLinks(src)) {
            const { target } = splitAnchor(link.dest);
            if (!target) {
              continue;
            }
            const resolved = resolveLinkTarget(docsDirAbs, srcUri, target);
            if (resolved && resolved.srcUri === targetSrcUri) {
              const pos = offsetToPosition(src, link.offset + 1);
              locations.push(new vscode.Location(vscode.Uri.file(p), pos));
            }
          }
        }
      }
    };
    walk(docsDirAbs);
    return locations;
  }
}

class DocsForgeCompletionProvider implements vscode.CompletionItemProvider {
  constructor(private root: string) {}

  provideCompletionItems(
    document: vscode.TextDocument, position: vscode.Position,
  ): vscode.CompletionItem[] {
    const text = document.getText();
    const line = text.split('\n')[position.line];
    const before = line.slice(0, position.character);
    const iconMatch = before.match(/:([a-z0-9-]*)$/);
    if (iconMatch) {
      return this.iconCompletions(iconMatch[1]);
    }
    // Link target completion: inside (…) of a markdown link
    const parenMatch = before.match(/\(([^)]*)$/);
    if (parenMatch) {
      return this.pathCompletions(document, parenMatch[1]);
    }
    return [];
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

  private pathCompletions(
    document: vscode.TextDocument, partial: string,
  ): vscode.CompletionItem[] {
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    if (!fs.existsSync(docsDirAbs)) {
      return [];
    }
    const items: vscode.CompletionItem[] = [];
    const walk = (dir: string, prefix: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(p, `${prefix}${entry.name}/`);
        } else if (entry.name.endsWith('.md')) {
          const name = `${prefix}${entry.name}`;
          if (!name.startsWith(partial)) {
            continue;
          }
          const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.File);
          item.insertText = name;
          item.detail = name;
          items.push(item);
        }
      }
    };
    void document;
    walk(docsDirAbs, '');
    return items.slice(0, 200);
  }
}

/** Register all providers for a workspace root. */
export function registerProviders(context: vscode.ExtensionContext, root: string): void {
  const sel: vscode.DocumentSelector = {
    scheme: 'file',
    language: 'markdown',
    pattern: `${root}/**/*.md`,
  };

  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(sel, new DocsForgeDocumentSymbolProvider()),
    vscode.languages.registerFoldingRangeProvider(sel, new DocsForgeFoldingProvider()),
    vscode.languages.registerDefinitionProvider(sel, new DocsForgeDefinitionProvider(root)),
    vscode.languages.registerHoverProvider(sel, new DocsForgeHoverProvider(root)),
    vscode.languages.registerReferenceProvider(sel, new DocsForgeReferenceProvider(root)),
    vscode.languages.registerCompletionItemProvider(sel, new DocsForgeCompletionProvider(root), ':'),
  );
}
