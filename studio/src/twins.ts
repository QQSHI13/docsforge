/**
 * Translation-twin check: every base page should have one variant per
 * locale observed in the tree (e.g. `guide/foo.md` ↔ `guide/foo.zh.md`).
 * On-demand over a single docs walk — cheap enough that no persisted state
 * is needed (unlike the heading index in studioCache.ts, which serves
 * per-keystroke completion).
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {
  docsDirFromConfig,
  walkDocs,
  detectLocales,
  findMissingTwins,
  extractHeadings,
} from './links';
import { findConfig } from './pure';

/** Run the twin check for a workspace root. */
export async function runCheckTwins(workspaceRoot: string): Promise<void> {
  if (!findConfig(workspaceRoot)) {
    vscode.window.showErrorMessage(
      'DocsForge: no docsforge.yml found. Run "Initialize Project" first.',
    );
    return;
  }
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  if (!fs.existsSync(docsDirAbs)) {
    vscode.window.showErrorMessage('DocsForge: the docs directory does not exist.');
    return;
  }
  const locales = detectLocales(walkDocs(docsDirAbs));
  if (!locales.length) {
    vscode.window.showInformationMessage(
      'DocsForge: single-language project (no .<locale>.md variants found).',
    );
    return;
  }
  const gaps = findMissingTwins(
    walkDocs(docsDirAbs).map((f) => ({ absPath: f.absPath, srcUri: f.srcUri })),
    locales,
  );
  if (!gaps.length) {
    vscode.window.showInformationMessage(
      `DocsForge: all translation twins are present (${locales.join(', ')}).`,
    );
    return;
  }
  const pick = await vscode.window.showQuickPick(
    gaps.map((g) => ({
      label: g.kind === 'missing'
        ? `Missing ${g.expected}`
        : `Orphan ${g.expected} (no base page)`,
      description: g.kind === 'missing' ? 'Create stub' : 'Delete file',
      gap: g,
    })),
    { placeHolder: `${gaps.length} twin gap(s). Pick one to fix.` },
  );
  if (!pick) {
    return;
  }
  const { gap } = pick;
  if (gap.kind === 'orphan') {
    const del = await vscode.window.showWarningMessage(
      `Delete orphan translation ${gap.expected}?`,
      { modal: true }, 'Delete',
    );
    if (del === 'Delete') {
      fs.rmSync(path.join(docsDirAbs, ...gap.expected.split('/')), { force: true });
    }
    return;
  }
  let h1 = gap.base.split('/').pop()!;
  if (gap.baseAbsPath) {
    try {
      const text = fs.readFileSync(gap.baseAbsPath, 'utf-8');
      h1 = extractHeadings(text)[0]?.title ?? h1;
    } catch {
      /* keep filename fallback */
    }
  }
  const absPath = path.join(docsDirAbs, ...gap.expected.split('/'));
  fs.mkdirSync(path.dirname(absPath), { recursive: true });
  fs.writeFileSync(absPath, `# ${h1}\n\n> TODO: translate this page into ${gap.locale}.\n`);
  await vscode.window.showTextDocument(vscode.Uri.file(absPath));
}
