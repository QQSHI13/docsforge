import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import lunr from 'lunr';

/** Open a QuickPick to search documentation pages using Lunr.js full-text search. */
export async function showSearch() {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) {
    vscode.window.showInformationMessage('DocsForge: open a workspace folder first.');
    return;
  }

  // Find docs directory
  const configPath = path.join(root, 'docsforge.yml');
  let docsDir = path.join(root, 'docs');
  try {
    if (fs.existsSync(configPath)) {
      const content = fs.readFileSync(configPath, 'utf-8');
      const m = content.match(/^\s*docs_dir\s*:\s*(.+)$/m);
      if (m) docsDir = path.resolve(root, m[1].trim());
    }
  } catch {}

  if (!fs.existsSync(docsDir)) {
    vscode.window.showInformationMessage('DocsForge: no docs/ directory found.');
    return;
  }

  interface Page { title: string; path: string; body: string; }

  // Read all .md files
  const pages: Page[] = [];
  try {
    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory() && !entry.name.startsWith('.')) walk(full);
        else if (entry.isFile() && entry.name.endsWith('.md')) {
          try {
            const content = fs.readFileSync(full, 'utf-8');
            const body = content.replace(/---[\s\S]*?---/, '').trim();
            const title = (content.match(/^\s*title\s*:\s*(.+)$/m)?.[1] || content.match(/^#\s+(.+)$/m)?.[1] || path.basename(full, '.md')).trim().replace(/["']/g, '');
            const rel = path.relative(docsDir, full).replace(/\\/g, '/');
            pages.push({ title, path: rel, body });
          } catch {}
        }
      }
    };
    walk(docsDir);
  } catch {}

  if (pages.length === 0) {
    vscode.window.showInformationMessage('DocsForge: no documentation pages found.');
    return;
  }

  // Build Lunr index (runs synchronously, fast for <1000 pages)
  const idx = lunr(function() {
    this.ref('path');
    this.field('title', { boost: 3 });
    this.field('body');

    for (const page of pages) {
      this.add(page);
    }
  });

  // QuickPick
  const qp = vscode.window.createQuickPick();
  qp.placeholder = `Search ${pages.length} pages (Lunr full-text)...`;
  qp.matchOnDescription = false;
  qp.matchOnDetail = false;

  qp.onDidChangeValue(value => {
    if (!value.trim()) {
      qp.items = [];
      return;
    }
    const results = idx.search(value);
    qp.items = results.slice(0, 30).map(r => {
      const p = pages.find(x => x.path === r.ref)!;
      // Build snippet showing match context
      const snippet = p.body.slice(0, 150).replace(/\n/g, ' ');
      return {
        label: p.title,
        description: p.path,
        detail: snippet,
        // Store path for opening
        _path: path.join(docsDir, p.path),
      };
    });
  });

  qp.onDidAccept(() => {
    const sel = qp.selectedItems[0] as any;
    if (sel?._path && fs.existsSync(sel._path)) {
      vscode.workspace.openTextDocument(sel._path).then(doc => vscode.window.showTextDocument(doc));
    }
    qp.hide();
  });

  qp.show();
}
