/**
 * DocsForge diagnostics — surfaces the build's link/anchor validation
 * (`.docsforge/cache/validation.json`, written by every `docsforge build`
 * and by every `docsforge serve` rebuild) as VS Code diagnostics, plus
 * extension-side checks that need no build: footnotes and translation
 * coverage (every base page expected to have one variant per locale found
 * in the tree).
 *
 * The monitor refreshes when:
 *  - the validation.json file changes on disk (serve rebuilds), via fs.watchFile
 *  - a manual build completes (ServerManager calls refresh())
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  docAbsPathSafe,
  severityForLevel,
  linkFromWarning,
  linesOfLink,
  docsDirFromConfig,
  checkFootnotes,
  collectFootnoteWarnings,
  tryLoadValidation,
  walkDocs,
  detectLocales,
  findMissingTwins,
} from './links';

/** Re-exported pure helpers (canonical implementations live in links.ts). */
export { collectFootnoteWarnings, tryLoadValidation };

/** Debounce interval for validation.json change → refresh. */
export const DIAGNOSTICS_DEBOUNCE_MS = 250;

export class DocsForgeDiagnostics {
  private collection: vscode.DiagnosticCollection;
  private watcher: fs.FSWatcher | null = null;
  private pollTimer: NodeJS.Timeout | null = null;
  private refreshTimer: NodeJS.Timeout | null = null;
  private lastMtimeMs = 0;
  private published = new Set<string>();
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
            this.scheduleRefresh();
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
        this.scheduleRefresh();
      }
    }, 2000);
  }

  /** Debounced refresh trigger shared by the directory watcher and poll. */
  private scheduleRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = null;
      this.refresh();
    }, DIAGNOSTICS_DEBOUNCE_MS);
  }

  /** Re-read validation.json and publish diagnostics.
   *
   * Parses first and only mutates the collection on success: a missing file
   * publishes an empty (cleared-diff) state, while a corrupt/mid-write file
   * keeps stale squiggles so the update is retried on the next tick instead
   * of being lost. Footnotes are computed over the whole docs tree,
   * independent of validation.json coverage.
   */
  refresh(): void {
    const parsed = tryLoadValidation(this.root);
    if (!parsed.ok) {
      return;
    }
    this.lastMtimeMs = this.mtimeMs();
    const data = parsed.data;
    const byFile = new Map<string, vscode.Diagnostic[]>();

    for (const [srcUri, entry] of Object.entries(data)) {
      const warnings = entry?.warnings ?? [];
      if (!warnings.length) {
        continue;
      }
      // Contained resolution: a crafted/stale validation.json key must not
      // pull diagnostics (or file reads) outside the docs dir.
      const absPath = docAbsPathSafe(this.root, this.docsDir, srcUri);
      if (!absPath || !fs.existsSync(absPath)) {
        continue;
      }
      let sourceText: string | null = null;
      const diags: vscode.Diagnostic[] = [];
      for (const [level, message] of warnings) {
        const dest = linkFromWarning(String(message));
        if (dest) {
          if (sourceText === null) {
            try {
              sourceText = fs.readFileSync(absPath, 'utf-8');
            } catch {
              sourceText = '';
            }
          }
          // A broken link may appear multiple times (e.g. the same anchor in
          // several rows of a table) — squiggle at every occurrence.
          const lines = linesOfLink(sourceText, dest);
          const targets = lines.length ? lines : [0];
          for (const line of targets) {
            const range = new vscode.Range(line, 0, line, 1000);
            const diag = new vscode.Diagnostic(
              range,
              String(message),
              severityForLevel(Number(level)),
            );
            diag.source = 'docsforge';
            diags.push(diag);
          }
        } else {
          const diag = new vscode.Diagnostic(
            new vscode.Range(0, 0, 0, 1000),
            String(message),
            severityForLevel(Number(level)),
          );
          diag.source = 'docsforge';
          diags.push(diag);
        }
      }
      // Footnote diagnostics (extension-side, no build needed).
      if (sourceText === null) {
        try {
          sourceText = fs.readFileSync(absPath, 'utf-8');
        } catch {
          sourceText = '';
        }
      }
      for (const fn of checkFootnotes(sourceText)) {
        const diag = new vscode.Diagnostic(
          new vscode.Range(fn.line, 0, fn.line, 1000),
          fn.message,
          vscode.DiagnosticSeverity.Warning,
        );
        diag.source = 'docsforge';
        diags.push(diag);
      }
      byFile.set(absPath, diags);
    }

    // Footnotes for files absent from validation.json (never built / clean).
    const docsDirAbs = path.join(this.root, this.docsDir);
    for (const [absPath, warnings] of collectFootnoteWarnings(docsDirAbs)) {
      if (byFile.has(absPath)) {
        continue;
      }
      const diags: vscode.Diagnostic[] = warnings.map((fn) => {
        const diag = new vscode.Diagnostic(
          new vscode.Range(fn.line, 0, fn.line, 1000),
          fn.message,
          vscode.DiagnosticSeverity.Warning,
        );
        diag.source = 'docsforge';
        return diag;
      });
      byFile.set(absPath, diags);
    }

    // Translation coverage (extension-side, no build needed): a base page
    // missing a locale variant, or a translation without a base page, is an
    // error on the file itself — no command to run, it is always checked.
    for (const [absPath, diags] of this.translationDiagnostics(docsDirAbs)) {
      const list = byFile.get(absPath) ?? [];
      list.push(...diags);
      byFile.set(absPath, list);
    }

    // Per-file set/delete diff instead of clear() so a failed parse above
    // never flashes squiggles off (we return early on failure).
    for (const prev of this.published) {
      if (!byFile.has(prev)) {
        this.collection.delete(vscode.Uri.file(prev));
      }
    }
    this.published = new Set(byFile.keys());
    for (const [absPath, diags] of byFile) {
      this.collection.set(vscode.Uri.file(absPath), diags);
    }
  }

  /** Missing locale variants and orphan translations as diagnostics.
   *  Single-language trees (no `.<locale>.md` anywhere) report nothing. */
  private translationDiagnostics(
    docsDirAbs: string,
  ): Map<string, vscode.Diagnostic[]> {
    const out = new Map<string, vscode.Diagnostic[]>();
    let files: Array<{ absPath: string; srcUri: string }>;
    try {
      files = walkDocs(docsDirAbs);
    } catch {
      return out;
    }
    const locales = detectLocales(files);
    if (!locales.length) {
      return out;
    }
    const push = (absPath: string | null, message: string) => {
      if (!absPath || !fs.existsSync(absPath)) {
        return;
      }
      const diag = new vscode.Diagnostic(
        new vscode.Range(0, 0, 0, 1000),
        message,
        vscode.DiagnosticSeverity.Error,
      );
      diag.source = 'docsforge';
      const list = out.get(absPath) ?? [];
      list.push(diag);
      out.set(absPath, list);
    };
    for (const gap of findMissingTwins(files, locales)) {
      if (gap.kind === 'missing' && gap.baseAbsPath) {
        push(
          gap.baseAbsPath,
          `Missing ${gap.locale.toUpperCase()} translation: ${gap.expected}`,
        );
      } else if (gap.kind === 'orphan') {
        push(
          docAbsPathSafe(this.root, this.docsDir, gap.expected),
          `Orphan translation without a base page: ${gap.expected}`,
        );
      }
    }
    return out;
  }

  dispose(): void {
    this.watcher?.close();
    this.watcher = null;
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.collection.dispose();
  }
}
