/**
 * New-page scaffolding: create a doc (+ optional locale twin), append a
 * `nav:` entry, open the file. Textual config edit — no YAML dependency.
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  docsDirFromConfig,
  walkDocs,
  detectLocales,
  sanitizePageName,
  humanizePageName,
  parseNavParents,
  appendNavEntry,
  srcUriOfPath,
} from './links';
import { findConfig } from './pure';
import { getDocsCache } from './providers';

function twinStub(title: string, locale: string): string {
  return `# ${title}\n\n> TODO: translate this page into ${locale}.\n`;
}

/** Run the New Page wizard for a workspace root. */
export async function runNewPage(workspaceRoot: string): Promise<void> {
  const configName = findConfig(workspaceRoot);
  if (!configName) {
    vscode.window.showErrorMessage(
      'DocsForge: no docsforge.yml found. Run "Initialize Project" first.',
    );
    return;
  }
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));

  // Default folder: the active doc's directory, else the docs root.
  let defaultDir = '';
  const active = vscode.window.activeTextEditor?.document.uri.fsPath;
  if (active) {
    const src = srcUriOfPath(docsDirAbs, active);
    if (src && src.includes('/')) {
      defaultDir = src.slice(0, src.lastIndexOf('/'));
    }
  }
  const dir = (await vscode.window.showInputBox({
    prompt: 'Folder inside the docs directory (empty for the docs root)',
    value: defaultDir,
    validateInput: (v) => {
      const t = v.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
      return t === '' || !/[<>:\"|?*\0]|\.\./.test(t) ? null : 'Invalid folder path';
    },
  }))?.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  if (dir === undefined) {
    return;
  }

  const nameRaw = await vscode.window.showInputBox({
    prompt: 'Page file name (e.g. my-page or guide/my-page)',
    validateInput: (v) => (sanitizePageName(v) ? null : 'Invalid page name'),
  });
  if (!nameRaw) {
    return;
  }
  const leaf = sanitizePageName(nameRaw)!;
  const srcUri = dir ? `${dir}/${leaf}` : leaf;
  const absPath = path.join(docsDirAbs, ...srcUri.split('/'));
  if (fs.existsSync(absPath)) {
    vscode.window.showErrorMessage(`DocsForge: ${srcUri} already exists.`);
    return;
  }

  const title = (await vscode.window.showInputBox({
    prompt: 'Page title (first H1)',
    value: humanizePageName(srcUri),
    validateInput: (v) => (v.trim() ? null : 'Title is required'),
  }))?.trim();
  if (!title) {
    return;
  }

  // Locale twins: offer one stub per locale observed in the tree.
  const locales = detectLocales(walkDocs(docsDirAbs));
  let twinLocales: string[] = [];
  if (locales.length) {
    const picks = await vscode.window.showQuickPick(
      [{ label: 'Base file only', value: '' },
        ...locales.map((l) => ({ label: `Also create .${l} twin stub`, value: l }))],
      { placeHolder: 'Create a translation stub?', canPickMany: true },
    );
    if (!picks) {
      return;
    }
    twinLocales = picks.map((p) => p.value).filter(Boolean);
  }

  fs.mkdirSync(path.dirname(absPath), { recursive: true });
  fs.writeFileSync(absPath, `# ${title}\n`);
  const skipped: string[] = [];
  for (const locale of twinLocales) {
    const twinSrc = srcUri.replace(/\.md$/, `.${locale}.md`);
    const twinAbs = path.join(docsDirAbs, ...twinSrc.split('/'));
    // Never clobber an existing translation with a stub.
    if (fs.existsSync(twinAbs)) {
      skipped.push(twinSrc);
      continue;
    }
    fs.writeFileSync(twinAbs, twinStub(title, locale));
  }
  getDocsCache(workspaceRoot).invalidate();

  // Nav entry (best-effort: textual append, manual fallback).
  const configPath = path.join(workspaceRoot, configName);
  let configText: string;
  try {
    configText = fs.readFileSync(configPath, 'utf-8');
  } catch {
    configText = '';
  }
  const parents = parseNavParents(configText);
  const where = await vscode.window.showQuickPick(
    [{ label: 'Top level', value: '' },
      ...parents.map((p) => ({ label: `Under "${p}"`, value: p })),
      { label: 'Skip nav entry', value: '__skip' }],
    { placeHolder: `Add "${title}" to nav?` },
  );
  if (!where) {
    // Cancelled: file is created, nav untouched.
  } else if (where.value !== '__skip' && configText) {
    const next = appendNavEntry(configText, title, srcUri, where.value || null);
    if (next && next !== configText) {
      fs.writeFileSync(configPath, next);
    } else {
      vscode.window.showWarningMessage(
        'DocsForge: could not insert the nav entry automatically — add it to nav: by hand.',
      );
    }
  }

  await vscode.window.showTextDocument(vscode.Uri.file(absPath));
  if (skipped.length) {
    vscode.window.showWarningMessage(
      `DocsForge: kept existing translation(s), stub not written: ${skipped.join(', ')}`,
    );
  }
}
