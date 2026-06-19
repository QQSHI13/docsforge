import * as vscode from 'vscode';
import { ServerManager } from './serverManager';
import { InitWizard } from './initWizard';
import { DocsForgeSidebarProvider } from './sidebarProvider';

let serverManager: ServerManager;
let sidebarProvider: DocsForgeSidebarProvider;

export function activate(context: vscode.ExtensionContext) {
  // Initialize server and build state context so conditional sidebar items render correctly
  vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
  vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', false);

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
      InitWizard.run(serverManager).catch((err) => {
        vscode.window.showErrorMessage(`DocsForge init failed: ${err.message}`);
      });
    }),

    vscode.commands.registerCommand('docsforge.serve', () => {
      serverManager.start();
    }),

    vscode.commands.registerCommand('docsforge.stop', () => {
      serverManager.stop();
    }),

    vscode.commands.registerCommand('docsforge.stopBuild', () => {
      serverManager.stopBuild();
    }),

    vscode.commands.registerCommand('docsforge.openServer', () => {
      serverManager.openBrowser();
    }),

    vscode.commands.registerCommand('docsforge.build', () => {
      serverManager.build();
    }),

    vscode.commands.registerCommand('docsforge.refreshSidebar', () => {
      sidebarProvider.refresh();
    }),

    vscode.commands.registerCommand('docsforge.openDocs', () => {
      vscode.commands.executeCommand(
        'simpleBrowser.api.open',
        vscode.Uri.parse('https://qqshi13.github.io/docsforge/')
      );
    })
  );

  // Keep sidebar in sync with server and build state
  ServerManager.onStateChange(() => {
    sidebarProvider.serverRunning = serverManager.isRunning();
    sidebarProvider.buildRunning = serverManager.isBuilding();
    sidebarProvider.refresh();
  });

  // Auto-start prompt if a config is found at startup
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (workspaceRoot && ServerManager.hasConfig(workspaceRoot)) {
    vscode.window
      .showInformationMessage('DocsForge project detected. Start dev server?', 'Yes', 'Later')
      .then((choice) => {
        if (choice === 'Yes') {
          serverManager.start();
        }
      });
  }
}

export function deactivate() {
  serverManager?.dispose();
}
