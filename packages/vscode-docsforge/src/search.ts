import * as vscode from 'vscode';
import { ServerManager } from './serverManager';

/** Open a QuickPick search dialog that queries the running server's search index. */
export async function showSearch() {
  const serverUrl = ServerManager.instance?.serverUrl;
  if (!serverUrl) {
    vscode.window.showInformationMessage('DocsForge: start the server first to enable search.');
    return;
  }

  // Fetch the search index from the running server
  let searchIndex: any[] = [];
  try {
    const indexUrl = serverUrl.replace(/\/+$/, '') + '/search/search_index.json';
    const resp = await fetch(indexUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: any = await resp.json();
    searchIndex = data.docs || [];
  } catch {
    vscode.window.showErrorMessage('DocsForge: could not load search index. Is the server running?');
    return;
  }

  const quickPick = vscode.window.createQuickPick();
  quickPick.placeholder = 'Search documentation...';
  quickPick.matchOnDescription = true;
  quickPick.matchOnDetail = true;
  quickPick.items = searchIndex.map((doc: any) => ({
    label: doc.title || '(untitled)',
    description: doc.location || '',
    detail: doc.text?.slice(0, 120) || '',
    // Store the full URL for opening
    url: serverUrl.replace(/\/+$/, '') + '/' + (doc.location || ''),
  }));

  quickPick.onDidAccept(() => {
    const selected = quickPick.selectedItems[0] as any;
    if (selected?.url) {
      vscode.commands.executeCommand('simpleBrowser.api.open', vscode.Uri.parse(selected.url));
    }
    quickPick.hide();
  });

  // Filter as user types — search index is already filtered by the search plugin
  quickPick.onDidChangeValue(() => {
    // The QuickPick's built-in filtering handles substring matching
  });

  quickPick.show();
}
