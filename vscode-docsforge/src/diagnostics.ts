/**
 * DocsForge diagnostics — surfaces the build's link/anchor validation
 * (`.docsforge/cache/validation.json`, written by every `docsforge build`
 * and by every `docsforge serve` rebuild) as VS Code diagnostics.
 *
 * The monitor refreshes when:
 *  - the validation.json file changes on disk (serve rebuilds), via fs.watchFile
 *  - a manual build completes (ServerManager calls refresh())
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  loadValidation,
  docAbsPath,
  severityForLevel,
  linkFromWarning,
  lineOfLink,
  docsDirFromConfig,
} from './links';

export class DocsForgeDiagnostics {
  private collection: vscode.DiagnosticCollection;
  private watcher: fs.FSWatcher | null = null;
  private pollTimer: NodeJS.Timeout | null = null;
  private lastMtimeMs = 0;
  private root: string;
  private docsDir: string;
  private validationPath: string;
  private cacheDir: string;

  constructor(root: string) {
    this.root = root;
    this.docsDir = docsDirFromConfig(root);
    this.validationPath = path.join(root, '.docsforge', 'cache', 'validation.json');
    this.cacheDir = path.dirname(this.validationPath);
    this.lastMtimeMs = this.mtimeMs();
    this.collection = vscode.languages.createDiagnosticCollection('docsforge');
    this.watch();
  }

  private mtimeMs(): number {
    try {
      return fs.statSync(this.validationPath).mtimeMs;
    } catch {
      return 0;
    }
  }

  /** Watch for validation.json changes.
   *
   * The build writes atomically (tmp + rename), which replaces the inode, so
   * watching the file path can miss events. We watch the cache directory and
   * also poll mtime as a reliable fallback.
   */
  private watch(): void {
    try {
      if (fs.existsSync(this.cacheDir)) {
        this.watcher = fs.watch(this.cacheDir, (_event, filename) => {
          if (filename === 'validation.json') {
            this.refresh();
          }
        });
      }
    } catch {
      this.watcher = null;
    }
    // Poll mtime every 2s as a fallback (directory watchers are unreliable
    // across platforms for atomic renames).
    this.pollTimer = setInterval(() => {
      const mtime = this.mtimeMs();
      if (mtime !== this.lastMtimeMs) {
        this.lastMtimeMs = mtime;
        this.refresh();
      }
    }, 2000);
  }

  /** Re-read validation.json and publish diagnostics. */
  refresh(): void {
    this.collection.clear();
    const data = loadValidation(this.root);
    const byFile = new Map<string, vscode.Diagnostic[]>();

    for (const [srcUri, entry] of Object.entries(data)) {
      const warnings = entry?.warnings ?? [];
      if (!warnings.length) {
        continue;
      }
      const absPath = docAbsPath(this.root, this.docsDir, srcUri);
      if (!fs.existsSync(absPath)) {
        continue;
      }
      let sourceText: string | null = null;
      const diags: vscode.Diagnostic[] = [];
      for (const [level, message] of warnings) {
        let line = 0;
        const dest = linkFromWarning(String(message));
        if (dest) {
          if (sourceText === null) {
            try {
              sourceText = fs.readFileSync(absPath, 'utf-8');
            } catch {
              sourceText = '';
            }
          }
          line = lineOfLink(sourceText, dest) ?? 0;
        }
        const range = new vscode.Range(line, 0, line, 1000);
        const diag = new vscode.Diagnostic(
          range,
          String(message),
          severityForLevel(Number(level)),
        );
        diag.source = 'docsforge';
        diags.push(diag);
      }
      byFile.set(absPath, diags);
    }

    for (const [absPath, diags] of byFile) {
      this.collection.set(vscode.Uri.file(absPath), diags);
    }
  }

  dispose(): void {
    this.watcher?.close();
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }
    this.collection.dispose();
  }
}
