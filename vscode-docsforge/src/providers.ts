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
    const srcUri = document.uri.fsPath.slice(docsDirAbs.length + 1)
      .split(path.sep).join('/');
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

  provideCodeActions(
    document: vscode.TextDocument, _range: vscode.Range,
    context: vscode.CodeActionContext,
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];
    const text = document.getText();
    const lines = text.split('\n');
    const docsDirAbs = path.join(this.root, docsDirFromConfig(this.root));
    for (const diag of context.diagnostics) {
      const line = lines[diag.range.start.line];
      if (!line) {
        continue;
      }
      const linkMatch = line.match(/\[[^\]]*\]\(([^)\s]+)\)/);
      if (!linkMatch) {
        continue;
      }
      const dest = linkMatch[1];
      const { target } = splitAnchor(dest);
      if (!target) {
        continue;
      }
      // Suggest a fix that points to an existing file with the same name.
      const wanted = path.posix.basename(target);
      const candidates: string[] = [];
      const walk = (dir: string, prefix: string) => {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
          const p = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            walk(p, `${prefix}${entry.name}/`);
          } else if (entry.name === wanted) {
            candidates.push(`${prefix}${entry.name}`);
          }
        }
      };
      if (fs.existsSync(docsDirAbs)) {
        walk(docsDirAbs, '');
      }
      if (candidates.length && !candidates.includes(target)) {
        const fix = new vscode.CodeAction(
          `Fix link: use ${candidates[0]}`,
          vscode.CodeActionKind.QuickFix,
        );
        const srcUri = document.uri.fsPath.slice(docsDirAbs.length + 1)
          .split(path.sep).join('/');
        let newTarget = path.posix.relative(path.posix.dirname(srcUri), candidates[0]);
        if (!newTarget.startsWith('.')) {
          newTarget = `./${newTarget}`;
        }
        const at = line.indexOf(dest);
        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.replace(
          document.uri,
          new vscode.Range(diag.range.start.line, at, diag.range.start.line, at + dest.length),
          newTarget,
        );
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

  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(sel, new DocsForgeDocumentSymbolProvider()),
    vscode.languages.registerFoldingRangeProvider(sel, new DocsForgeFoldingProvider()),
    vscode.languages.registerDefinitionProvider(sel, new DocsForgeDefinitionProvider(root)),
    vscode.languages.registerHoverProvider(sel, new DocsForgeHoverProvider(root)),
    vscode.languages.registerReferenceProvider(sel, new DocsForgeReferenceProvider(root)),
    vscode.languages.registerCompletionItemProvider(sel, new DocsForgeCompletionProvider(root), ':'),
    vscode.languages.registerDocumentHighlightProvider(sel, new DocsForgeHighlightProvider()),
    vscode.languages.registerDocumentLinkProvider(sel, new DocsForgeDocumentLinkProvider(root)),
    vscode.languages.registerCodeActionsProvider(sel, new DocsForgeCodeActionProvider(root)),
    vscode.languages.registerDocumentFormattingEditProvider(sel, new DocsForgeFormattingProvider()),
  );
}
