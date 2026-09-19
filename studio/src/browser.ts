/**
 * Open a URL in VS Code's Simple Browser, falling back to an external
 * browser when it is unavailable (some VS Code forks lack it). Never
 * throws: every caller is a fire-and-forget UI action.
 */
import * as vscode from 'vscode';

export async function openInBrowser(url: string | vscode.Uri): Promise<void> {
  const target = typeof url === 'string' ? vscode.Uri.parse(url) : url;
  try {
    await vscode.commands.executeCommand('simpleBrowser.api.open', target);
  } catch {
    try {
      await vscode.commands.executeCommand('vscode.open', target);
    } catch {
      /* no browser available at all */
    }
  }
}
