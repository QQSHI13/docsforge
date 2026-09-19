/**
 * Single source of truth for "which project does this action apply to?"
 * (multi-root): the active editor's project when it holds a config, else
 * the first configured root, else the first folder. ServerManager and the
 * update check share it so serve and Check for Updates never target
 * different interpreters — and an unrelated open folder can never shadow
 * the one configured project.
 */
import * as vscode from 'vscode';
import { hasConfig } from './pure';

export function currentProjectRoot(): string | undefined {
  const folders = vscode.workspace.workspaceFolders ?? [];
  const active = vscode.window.activeTextEditor?.document.uri.fsPath;
  const activeFolder = active
    ? vscode.workspace.getWorkspaceFolder(vscode.Uri.file(active))
    : undefined;
  // The active folder wins only when it holds a config: an unrelated open
  // folder must never shadow the configured project(s).
  if (activeFolder && hasConfig(activeFolder.uri.fsPath)) {
    return activeFolder.uri.fsPath;
  }
  const configured = folders.find((f) => hasConfig(f.uri.fsPath));
  if (configured) {
    return configured.uri.fsPath;
  }
  // Nothing configured yet (init/setup run before any config exists):
  // the folder being worked in still wins over folders[0].
  return activeFolder?.uri.fsPath ?? folders[0]?.uri.fsPath;
}
