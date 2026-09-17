/**
 * Single source of truth for "which project does this action apply to?"
 * (multi-root): the active editor's folder first, else the first configured
 * root, else the first folder. ServerManager and the update check share it
 * so serve and Check for Updates never target different interpreters.
 */
import * as vscode from 'vscode';
import { hasConfig } from './pure';

export function currentProjectRoot(): string | undefined {
  const active = vscode.window.activeTextEditor?.document.uri.fsPath;
  if (active) {
    const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(active));
    if (folder) {
      return folder.uri.fsPath;
    }
  }
  const folders = vscode.workspace.workspaceFolders ?? [];
  return (folders.find((f) => hasConfig(f.uri.fsPath)) ?? folders[0])?.uri.fsPath;
}
