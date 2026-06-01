import * as vscode from 'vscode';
import { ServerManager } from './serverManager';
import { PreviewPanel } from './previewPanel';
import { InitWizard } from './initWizard';

let serverManager: ServerManager;

export function activate(context: vscode.ExtensionContext) {
  console.log('DocsForge extension activated');
  
  serverManager = new ServerManager();

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.init', () => {
      InitWizard.run();
    }),
    
    vscode.commands.registerCommand('docsforge.serve', () => {
      serverManager.start();
    }),
    
    vscode.commands.registerCommand('docsforge.stop', () => {
      serverManager.stop();
    }),
    
    vscode.commands.registerCommand('docsforge.preview', () => {
      PreviewPanel.createOrShow(context.extensionUri);
    }),
    
    vscode.commands.registerCommand('docsforge.build', () => {
      serverManager.build();
    }),
    
    vscode.commands.registerCommand('docsforge.deploy', () => {
      serverManager.deploy();
    })
  );

  // Auto-start server if docsforge.yml exists
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
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
  serverManager?.stop();
}
