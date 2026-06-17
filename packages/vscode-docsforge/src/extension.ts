import * as vscode from 'vscode';
import { ServerManager } from './serverManager';
import { PreviewPanel } from './previewPanel';
import { InitWizard } from './initWizard';
import { DocsForgeSidebarProvider } from './sidebarProvider';

let serverManager: ServerManager;
let sidebarProvider: DocsForgeSidebarProvider;

export function activate(context: vscode.ExtensionContext) {
  console.log('DocsForge extension activated');

  // Initialize server state context so conditional sidebar items render correctly
  vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);

  serverManager = new ServerManager();
  sidebarProvider = new DocsForgeSidebarProvider();

  // Register sidebar tree view
  const treeView = vscode.window.createTreeView('docsforge.sidebar', {
    treeDataProvider: sidebarProvider,
  });
  context.subscriptions.push(treeView);

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.init', () => {
      if (!vscode.workspace.workspaceFolders?.length) {
        vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
        return;
      }
      InitWizard.run();
    }),

    vscode.commands.registerCommand('docsforge.serve', () => {
      serverManager.start();
    }),

    vscode.commands.registerCommand('docsforge.stop', () => {
      serverManager.stop();
    }),

    vscode.commands.registerCommand('docsforge.openServer', () => {
      serverManager.openBrowser();
    }),

    vscode.commands.registerCommand('docsforge.preview', () => {
      PreviewPanel.createOrShow(context.extensionUri);
    }),

    vscode.commands.registerCommand('docsforge.build', () => {
      serverManager.build();
    }),

    vscode.commands.registerCommand('docsforge.refreshSidebar', () => {
      sidebarProvider.refresh();
    })
  );

  // Refresh sidebar when server state changes
  ServerManager.onStateChange(() => {
    sidebarProvider.serverRunning = serverManager.isRunning();
    sidebarProvider.refresh();
  });

  // Auto-start server if docsforge.yml exists
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (workspaceRoot) {
    const fs = require('fs');
    const path = require('path');
    const configs = ['docsforge.yml', 'docsforge.yaml', 'mkdocs.yml', 'mkdocs.yaml'];
    const hasConfig = configs.some(c => fs.existsSync(path.join(workspaceRoot, c)));

    if (hasConfig) {
      vscode.window.showInformationMessage(
        'DocsForge project detected. Start dev server?',
        'Yes', 'Later'
      ).then(choice => {
        if (choice === 'Yes') {
          serverManager.start();
        }
      });
    }
  }
}

export function deactivate() {
  serverManager?.dispose();
}
