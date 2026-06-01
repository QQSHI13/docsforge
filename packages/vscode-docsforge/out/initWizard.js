"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.InitWizard = void 0;
const vscode = require("vscode");
const child_process_1 = require("child_process");
class InitWizard {
    static async run() {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
        if (!workspaceRoot) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }
        const fs = require('fs');
        const path = require('path');
        if (fs.existsSync(path.join(workspaceRoot, 'docsforge.yml'))) {
            vscode.window.showInformationMessage('docsforge.yml already exists');
            return;
        }
        const siteName = await vscode.window.showInputBox({
            prompt: 'Site name',
            placeHolder: 'My Documentation',
            validateInput: (value) => value ? null : 'Site name is required'
        });
        if (!siteName)
            return;
        const themeColor = await vscode.window.showQuickPick(['teal', 'indigo', 'blue', 'green', 'purple'], { placeHolder: 'Select theme color' });
        const enableSearch = await vscode.window.showQuickPick(['Yes', 'No'], { placeHolder: 'Enable search?' });
        const pythonPath = vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Creating DocsForge project...'
        }, () => {
            return new Promise((resolve) => {
                const proc = (0, child_process_1.spawn)(pythonPath, [
                    '-m', 'docsforge', 'init',
                    '--name', siteName,
                    '--theme-color', themeColor || 'teal',
                    enableSearch === 'Yes' ? '--search' : '--no-search'
                ], {
                    cwd: workspaceRoot
                });
                proc.on('close', () => {
                    vscode.window.showInformationMessage('DocsForge project created!', 'Start Server').then(choice => {
                        if (choice === 'Start Server') {
                            vscode.commands.executeCommand('docsforge.serve');
                        }
                    });
                    resolve();
                });
            });
        });
    }
}
exports.InitWizard = InitWizard;
//# sourceMappingURL=initWizard.js.map