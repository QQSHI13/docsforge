/**
 * Rename support: "DocsForge: Rename Document" renames a markdown doc and
 * rewrites every link that points to it (and to its anchors) across the docs
 * tree. Uses docsforge's link resolution semantics (relative posix paths),
 * not naive string replace.
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  extractLinks,
  splitAnchor,
  resolveLinkTarget,
  docsDirFromConfig,
} from './links';

/** srcUri → absolute path inside docs_dir. */
function srcUriToAbs(docsDirAbs: string, srcUri: string): string {
  return path.join(docsDirAbs, ...srcUri.split('/'));
}

/** Walk all .md files under docs_dir, yielding {absPath, srcUri}. */
function walkDocs(
  docsDirAbs: string,
): Array<{ absPath: string; srcUri: string }> {
  const out: Array<{ absPath: string; srcUri: string }> = [];
  const walk = (dir: string, prefix: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(p, `${prefix}${entry.name}/`);
      } else if (entry.name.endsWith('.md')) {
        out.push({ absPath: p, srcUri: `${prefix}${entry.name}` });
      }
    }
  };
  walk(docsDirAbs, '');
  return out;
}

/**
 * Compute the edits needed to rename oldSrcUri → newSrcUri: rewrite every
 * link across all docs that resolves to oldSrcUri. Returns a map of
 * absolute file path → (start offset, end offset, new text) edits.
 */
export function computeRenameEdits(
  workspaceRoot: string, oldSrcUri: string, newSrcUri: string,
): Map<string, Array<{ start: number; end: number; text: string }>> {
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  const edits = new Map<string, Array<{ start: number; end: number; text: string }>>();
  if (!fs.existsSync(docsDirAbs)) {
    return edits;
  }
  const newBase = newSrcUri.replace(/\.[^.]+$/, '');
  for (const doc of walkDocs(docsDirAbs)) {
    const source = fs.readFileSync(doc.absPath, 'utf-8');
    const fileEdits: Array<{ start: number; end: number; text: string }> = [];
    for (const link of extractLinks(source)) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, doc.srcUri, target);
      if (!resolved || resolved.srcUri !== oldSrcUri) {
        continue;
      }
      // New relative target from the same source file.
      let newTarget = path.posix.relative(
        path.posix.dirname(doc.srcUri), newSrcUri,
      );
      if (!newTarget.startsWith('.')) {
        newTarget = `./${newTarget}`;
      }
      if (anchor) {
        newTarget += `#${anchor}`;
      }
      fileEdits.push({
        start: link.offset + 1, // skip '('
        end: link.offset + 1 + link.dest.length,
        text: newTarget,
      });
    }
    if (fileEdits.length) {
      edits.set(doc.absPath, fileEdits);
    }
  }
  void newBase;
  return edits;
}

/** Register the "DocsForge: Rename Document" command. */
export function registerRenameCommand(
  context: vscode.ExtensionContext, workspaceRoot: string,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.renameDocument', async (uri?: vscode.Uri) => {
      const target = uri ?? vscode.window.activeTextEditor?.document.uri;
      if (!target) {
        vscode.window.showWarningMessage('DocsForge: open a document to rename.');
        return;
      }
      const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
      const rel = path.relative(docsDirAbs, target.fsPath);
      if (rel.startsWith('..') || path.isAbsolute(rel) || !rel.endsWith('.md')) {
        vscode.window.showWarningMessage('DocsForge: the document is not inside the docs directory.');
        return;
      }
      const oldSrcUri = rel.split(path.sep).join('/');
      const newName = await vscode.window.showInputBox({
        prompt: 'New document name (relative to docs/)',
        value: oldSrcUri,
        validateInput: (v) => (v?.trim() && v.endsWith('.md') ? null : 'Must end with .md'),
      });
      if (!newName?.trim() || newName === oldSrcUri) {
        return;
      }
      const newSrcUri = newName.trim();
      const edits = computeRenameEdits(workspaceRoot, oldSrcUri, newSrcUri);
      const edit = new vscode.WorkspaceEdit();
      for (const [absPath, fileEdits] of edits) {
        const uri = vscode.Uri.file(absPath);
        const doc = await vscode.workspace.openTextDocument(uri);
        for (const e of fileEdits) {
          const start = doc.positionAt(e.start);
          const end = doc.positionAt(e.end);
          edit.replace(uri, new vscode.Range(start, end), e.text);
        }
      }
      // Rename the file itself.
      const newAbs = srcUriToAbs(docsDirAbs, newSrcUri);
      if (fs.existsSync(newAbs)) {
        vscode.window.showErrorMessage('DocsForge: target file already exists.');
        return;
      }
      fs.mkdirSync(path.dirname(newAbs), { recursive: true });
      fs.renameSync(target.fsPath, newAbs);
      await vscode.workspace.applyEdit(edit);
      await vscode.window.showTextDocument(vscode.Uri.file(newAbs));
      vscode.window.showInformationMessage(
        `Renamed ${oldSrcUri} → ${newSrcUri} and updated ${edits.size} file(s).`,
      );
    }),
  );
}
