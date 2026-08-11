/**
 * Rename commands:
 *  - "DocsForge: Rename Document" — renames a markdown doc and rewrites every
 *    link that points to it (and to its anchors) across the docs tree.
 *  - "DocsForge: Rename Anchor" — renames a heading and rewrites every link
 *    that points to its anchor slug.
 * The pure edit computation lives in links.ts (vscode-free, unit-tested).
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  extractHeadings,
  docsDirFromConfig,
  slugifyHeading,
  computeDocumentRename,
  computeFolderRename,
  computeAnchorRenameEdits,
} from './links';

/** Register the rename commands. */
export function registerRenameCommands(
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
      // If we're editing a translation (foo.zh.md), offer the base name so the
      // whole document (all locale variants) is renamed together.
      const oldBase = oldSrcUri.replace(/(\.[a-z]{2}(?:-[a-z]{2})?)?\.md$/, '');
      const newName = await vscode.window.showInputBox({
        prompt: 'New document name (relative to docs/, without locale suffix)',
        value: oldBase,
        validateInput: (v) => (v?.trim() ? null : 'Name is required'),
      });
      if (!newName?.trim() || newName.trim() === oldBase) {
        return;
      }
      const newBase = newName.trim().replace(/\.md$/, '');
      const { files, edits } = computeDocumentRename(workspaceRoot, oldSrcUri, newBase);
      if (!files.size) {
        vscode.window.showWarningMessage('DocsForge: no files matched the rename.');
        return;
      }
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
      // Rename every variant file (base + translations).
      const renamedFiles: string[] = [];
      for (const [oldAbs, newAbs] of files) {
        if (fs.existsSync(newAbs)) {
          vscode.window.showErrorMessage(
            `DocsForge: target file already exists: ${path.relative(docsDirAbs, newAbs)}`,
          );
          return;
        }
        fs.mkdirSync(path.dirname(newAbs), { recursive: true });
        fs.renameSync(oldAbs, newAbs);
        renamedFiles.push(path.relative(docsDirAbs, newAbs));
      }
      await vscode.workspace.applyEdit(edit);
      const opened = renamedFiles.find((f) => f.endsWith('.md'));
      if (opened) {
        await vscode.window.showTextDocument(vscode.Uri.file(path.join(docsDirAbs, opened)));
      }
      vscode.window.showInformationMessage(
        `Renamed ${oldBase} → ${newBase}: ${renamedFiles.length} file(s), ` +
          `${edits.size} link edit(s) in ${edits.size} file(s).`,
      );
    }),

    vscode.commands.registerCommand('docsforge.renameAnchor', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage('DocsForge: open a document to rename an anchor.');
        return;
      }
      const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
      const rel = path.relative(docsDirAbs, editor.document.uri.fsPath);
      if (rel.startsWith('..') || path.isAbsolute(rel) || !rel.endsWith('.md')) {
        vscode.window.showWarningMessage('DocsForge: the document is not inside the docs directory.');
        return;
      }
      const docSrcUri = rel.split(path.sep).join('/');
      const headings = extractHeadings(editor.document.getText());
      if (!headings.length) {
        vscode.window.showWarningMessage('DocsForge: no headings found in this document.');
        return;
      }
      const cursorLine = editor.selection.active.line;
      const cursorHeading = headings.find((h) => h.line === cursorLine);
      const items = headings.map((h, i) => ({
        label: `${'#'.repeat(h.level)} ${h.title}`,
        description: `→ #${slugifyHeading(h.title)}`,
        value: i,
        picked: cursorHeading !== undefined && headings[i].line === cursorHeading.line,
      }));
      const pick = await vscode.window.showQuickPick(items, {
        placeHolder: 'Choose a heading to rename its anchor',
      });
      if (pick === undefined) {
        return;
      }
      const heading = headings[pick.value];
      const oldSlug = slugifyHeading(heading.title);
      const newTitle = await vscode.window.showInputBox({
        prompt: 'New heading text',
        value: heading.title,
      });
      if (!newTitle?.trim() || newTitle === heading.title) {
        return;
      }
      const newSlug = slugifyHeading(newTitle.trim());
      const edits = computeAnchorRenameEdits(workspaceRoot, docSrcUri, oldSlug, newSlug);
      const edit = new vscode.WorkspaceEdit();
      // Update the heading line itself.
      const line = editor.document.lineAt(heading.line);
      const escaped = heading.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const newLineText = line.text.replace(
        new RegExp(`^(#{1,6})\\s+${escaped}\\s*#*\\s*$`),
        `$1 ${newTitle.trim()}`,
      );
      let headingEdited = false;
      if (newLineText !== line.text) {
        edit.replace(editor.document.uri, line.range, newLineText);
        headingEdited = true;
      }
      for (const [absPath, fileEdits] of edits) {
        const uri = vscode.Uri.file(absPath);
        const doc = await vscode.workspace.openTextDocument(uri);
        for (const e of fileEdits) {
          edit.replace(uri, new vscode.Range(doc.positionAt(e.start), doc.positionAt(e.end)), e.text);
        }
      }
      await vscode.workspace.applyEdit(edit);
      const affected = edits.size + (headingEdited ? 1 : 0);
      vscode.window.showInformationMessage(
        `Renamed anchor #${oldSlug} → #${newSlug} in ${docSrcUri} (${affected} edit${affected === 1 ? '' : 's'}).`,
      );
    }),
  );
}

/** Register automatic link/translation updates when the user renames a doc
 *  or folder in the Explorer (Zensical-style: no separate command). */
export function registerAutoRename(
  context: vscode.ExtensionContext, workspaceRoot: string,
): void {
  context.subscriptions.push(
    vscode.workspace.onDidRenameFiles(async (event) => {
      const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
      const edit = new vscode.WorkspaceEdit();
      const messages: string[] = [];
      for (const f of event.files) {
        const oldRel = path.relative(docsDirAbs, f.oldUri.fsPath);
        const newRel = path.relative(docsDirAbs, f.newUri.fsPath);
        const oldIsDoc = !oldRel.startsWith('..') && !path.isAbsolute(oldRel);
        const newIsDoc = !newRel.startsWith('..') && !path.isAbsolute(newRel);
        if (!oldIsDoc || !newIsDoc) {
          continue;
        }
        const oldSrc = oldRel.split(path.sep).join('/');
        const newSrc = newRel.split(path.sep).join('/');
        // Folder rename: everything under it moves.
        const isFolder = fs.existsSync(f.oldUri.fsPath) && fs.statSync(f.oldUri.fsPath).isDirectory();
        const result = isFolder
          ? computeFolderRename(workspaceRoot, oldSrc, newSrc)
          : computeDocumentRename(workspaceRoot, oldSrc, newSrc.replace(/\.md$/, ''));
        for (const [absPath, fileEdits] of result.edits) {
          const uri = vscode.Uri.file(absPath);
          const doc = await vscode.workspace.openTextDocument(uri);
          for (const e of fileEdits) {
            edit.replace(uri, new vscode.Range(doc.positionAt(e.start), doc.positionAt(e.end)), e.text);
          }
        }
        if (result.edits.size) {
          messages.push(`${oldSrc} → ${newSrc}: ${result.edits.size} file(s) updated`);
        }
      }
      if (messages.length) {
        await vscode.workspace.applyEdit(edit);
        vscode.window.showInformationMessage(`DocsForge: ${messages.join('; ')}`);
      }
    }),
  );
}
