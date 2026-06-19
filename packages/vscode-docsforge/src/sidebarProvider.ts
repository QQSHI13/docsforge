import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

/** A simple doc page index entry. */
interface DocEntry {
  title: string;
  path: string;
  snippet: string;
}

let _serverRunning = false;
let _buildRunning = false;

export class DocsForgeSidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'docsforge.sidebar';

  private _view?: vscode.WebviewView;
  private _docIndex: DocEntry[] = [];

  constructor(private readonly _extensionUri: vscode.Uri) {}

  get serverRunning(): boolean { return _serverRunning; }
  set serverRunning(v: boolean) { _serverRunning = v; this._postState(); }

  get buildRunning(): boolean { return _buildRunning; }
  set buildRunning(v: boolean) { _buildRunning = v; this._postState(); }

  refresh() {
    this._buildDocIndex();
    this._postState();
  }

  resolveWebviewView(webviewView: vscode.WebviewView) {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true, localResourceRoots: [this._extensionUri] };
    webviewView.webview.html = this._getHtml();

    webviewView.webview.onDidReceiveMessage((msg) => {
      switch (msg.type) {
        case 'ready':
          this._buildDocIndex();
          this._postState();
          break;
        case 'search':
          this._handleSearch(msg.query);
          break;
        case 'openFile':
          this._openFile(msg.path);
          break;
        case 'command':
          vscode.commands.executeCommand(msg.command);
          break;
      }
    });
  }

  private _postState() {
    this._view?.webview.postMessage({
      type: 'state',
      serverRunning: _serverRunning,
      buildRunning: _buildRunning,
    });
  }

  // ── Search ──

  private _buildDocIndex() {
    this._docIndex = [];
    const root = this._workspaceRoot;
    if (!root) return;

    const docsDir = this._getDocsDir(root);
    if (!fs.existsSync(docsDir)) return;

    try {
      const files = this._findMdFiles(docsDir);
      for (const file of files) {
        try {
          const content = fs.readFileSync(file, 'utf-8');
          const title = this._extractTitle(content) || path.basename(file, '.md');
          const rel = path.relative(docsDir, file).replace(/\\/g, '/');
          const snippet = content
            .replace(/---[\s\S]*?---/, '')
            .replace(/^#+\s*.*$/m, '')
            .replace(/[#*`\[\]()>|\\]/g, '')
            .trim()
            .slice(0, 150);
          this._docIndex.push({ title, path: rel, snippet });
        } catch {}
      }
    } catch {}
  }

  private _findMdFiles(dir: string): string[] {
    const results: string[] = [];
    try {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory() && !entry.name.startsWith('.')) {
          results.push(...this._findMdFiles(full));
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
          results.push(full);
        }
      }
    } catch {}
    return results;
  }

  private _extractTitle(content: string): string | null {
    const fmTitle = content.match(/^\s*title\s*:\s*(.+)$/m);
    if (fmTitle) return fmTitle[1].trim().replace(/["']/g, '');
    const h1 = content.match(/^#\s+(.+)$/m);
    if (h1) return h1[1].trim();
    return null;
  }

  private _handleSearch(query: string) {
    if (!query.trim()) {
      this._view?.webview.postMessage({ type: 'searchResults', results: [] });
      return;
    }
    const q = query.toLowerCase();
    const results = this._docIndex
      .filter(d => d.title.toLowerCase().includes(q) || d.snippet.toLowerCase().includes(q))
      .slice(0, 30)
      .map(d => ({ title: d.title, path: d.path, snippet: d.snippet }));
    this._view?.webview.postMessage({ type: 'searchResults', results });
  }

  private async _openFile(relPath: string) {
    const root = this._workspaceRoot;
    if (!root) return;
    const fullPath = path.join(this._getDocsDir(root), relPath);
    if (fs.existsSync(fullPath)) {
      const doc = await vscode.workspace.openTextDocument(fullPath);
      vscode.window.showTextDocument(doc);
    }
  }

  private get _workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  private _getDocsDir(root: string): string {
    const configPath = path.join(root, 'docsforge.yml');
    try {
      if (fs.existsSync(configPath)) {
        const content = fs.readFileSync(configPath, 'utf-8');
        const m = content.match(/^\s*docs_dir\s*:\s*(.+)$/m);
        if (m) return path.resolve(root, m[1].trim());
      }
    } catch {}
    return path.join(root, 'docs');
  }

  private _getHtml(): string {
    const filePath = path.join(this._extensionUri.fsPath, 'src', 'sidebar.html');
    try {
      return fs.readFileSync(filePath, 'utf-8');
    } catch {
      return '<body><p>Failed to load sidebar</p></body>';
    }
  }
}
