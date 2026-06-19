import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

/** Open a QuickPick to search documentation pages (works offline, no server needed). */
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

  // Build index
  interface Entry { title: string; path: string; snippet: string; }
  const entries: Entry[] = [];

  try {
    const mdFiles: string[] = [];
    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory() && !entry.name.startsWith('.')) walk(full);
        else if (entry.isFile() && entry.name.endsWith('.md')) mdFiles.push(full);
      }
    };
    walk(docsDir);

    for (const file of mdFiles) {
      try {
        const content = fs.readFileSync(file, 'utf-8');
        const title = (content.match(/^\s*title\s*:\s*(.+)$/m)?.[1] || content.match(/^#\s+(.+)$/m)?.[1] || path.basename(file, '.md')).trim().replace(/["']/g, '');
        const rel = path.relative(docsDir, file).replace(/\\/g, '/');
        const snippet = content.replace(/---[\s\S]*?---/, '').replace(/^#+\s*.*$/m, '').replace(/[#*`\[\]()>|\\]/g, '').trim().slice(0, 120);
        entries.push({ title, path: rel, snippet });
      } catch {}
    }
  } catch {}

  if (entries.length === 0) {
    vscode.window.showInformationMessage('DocsForge: no documentation pages found.');
    return;
  }

  const qp = vscode.window.createQuickPick();
  qp.placeholder = `Search ${entries.length} documentation pages...`;
  qp.matchOnDescription = true;
  qp.items = entries.map(e => ({ label: e.title, description: e.path, detail: e.snippet }));

  qp.onDidAccept(() => {
    const sel = qp.selectedItems[0];
    if (sel) {
      const fullPath = path.join(docsDir, sel.description || '');
      if (fs.existsSync(fullPath)) {
        vscode.workspace.openTextDocument(fullPath).then(doc => vscode.window.showTextDocument(doc));
      }
    }
    qp.hide();
  });

  qp.show();
}
