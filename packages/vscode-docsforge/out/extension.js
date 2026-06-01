"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const serverManager_1 = require("./serverManager");
const previewPanel_1 = require("./previewPanel");
const initWizard_1 = require("./initWizard");
let serverManager;
function activate(context) {
    console.log('DocsForge extension activated');
    serverManager = new serverManager_1.ServerManager();
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('docsforge.init', () => {
        initWizard_1.InitWizard.run();
    }), vscode.commands.registerCommand('docsforge.serve', () => {
        serverManager.start();
    }), vscode.commands.registerCommand('docsforge.stop', () => {
        serverManager.stop();
    }), vscode.commands.registerCommand('docsforge.preview', () => {
        previewPanel_1.PreviewPanel.createOrShow(context.extensionUri);
    }), vscode.commands.registerCommand('docsforge.build', () => {
        serverManager.build();
    }), vscode.commands.registerCommand('docsforge.deploy', () => {
        serverManager.deploy();
    }));
    // Auto-start server if docsforge.yml exists
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
    if (workspaceRoot) {
        const fs = require('fs');
        const path = require('path');
        const configs = ['docsforge.yml', 'docsforge.yaml', 'mkdocs.yml', 'mkdocs.yaml'];
        const hasConfig = configs.some(c => fs.existsSync(path.join(workspaceRoot, c)));
        if (hasConfig) {
            vscode.window.showInformationMessage('DocsForge project detected. Start dev server?', 'Yes', 'Later').then(choice => {
                if (choice === 'Yes') {
                    serverManager.start();
                }
            });
        }
    }
}
function deactivate() {
    serverManager?.stop();
}
//# sourceMappingURL=extension.js.map