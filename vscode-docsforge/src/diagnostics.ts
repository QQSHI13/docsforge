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
  private root: string;
  private docsDir: string;
  private validationPath: string;

  constructor(root: string) {
    this.root = root;
    this.docsDir = docsDirFromConfig(root);
    this.validationPath = path.join(root, '.docsforge', 'cache', 'validation.json');
    this.collection = vscode.languages.createDiagnosticCollection('docsforge');
    this.watch();
  }

  /** Watch validation.json for changes (serve rebuilds rewrite it). */
  private watch(): void {
    if (!fs.existsSync(this.validationPath)) {
      return;
    }
    this.watcher = fs.watch(this.validationPath, () => {
      this.refresh();
    });
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
    this.collection.dispose();
  }
}
