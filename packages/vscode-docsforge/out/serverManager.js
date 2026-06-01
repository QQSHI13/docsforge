"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ServerManager = void 0;
const vscode = require("vscode");
const child_process_1 = require("child_process");
class ServerManager {
    process = null;
    outputChannel;
    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('DocsForge');
    }
    start() {
        if (this.process) {
            vscode.window.showWarningMessage('DocsForge server is already running');
            return;
        }
        const pythonPath = vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
        const devAddr = vscode.workspace.getConfiguration('docsforge').get('devAddr', 'localhost:8000');
        this.outputChannel.show();
        this.outputChannel.appendLine(`Starting DocsForge server at ${devAddr}...`);
        this.process = (0, child_process_1.spawn)(pythonPath, [
            '-m', 'docsforge', 'serve',
            '--dev-addr', devAddr,
            '--open'
        ], {
            cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath,
            env: { ...process.env, FORCE_COLOR: '1' }
        });
        this.process.stdout?.on('data', (data) => {
            this.outputChannel.append(data.toString());
        });
        this.process.stderr?.on('data', (data) => {
            this.outputChannel.append(data.toString());
        });
        this.process.on('close', (code) => {
            this.process = null;
            vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
            if (code !== 0) {
                this.outputChannel.appendLine(`Server exited with code ${code}`);
            }
        });
        vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
        vscode.window.showInformationMessage('DocsForge server started', 'Open Preview')
            .then(choice => {
            if (choice === 'Open Preview') {
                vscode.commands.executeCommand('docsforge.preview');
            }
        });
    }
    stop() {
        if (!this.process) {
            vscode.window.showWarningMessage('DocsForge server is not running');
            return;
        }
        this.process.kill();
        this.process = null;
        vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
        vscode.window.showInformationMessage('DocsForge server stopped');
    }
    build() {
        const pythonPath = vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Building DocsForge documentation',
            cancellable: false
        }, async () => {
            return new Promise((resolve, reject) => {
                const proc = (0, child_process_1.spawn)(pythonPath, ['-m', 'docsforge', 'build'], {
                    cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath
                });
                let output = '';
                proc.stdout?.on('data', (data) => { output += data; });
                proc.stderr?.on('data', (data) => { output += data; });
                proc.on('close', (code) => {
                    if (code === 0) {
                        vscode.window.showInformationMessage('Build successful');
                        resolve();
                    }
                    else {
                        vscode.window.showErrorMessage('Build failed', 'Show Output')
                            .then(() => this.outputChannel.show());
                        reject();
                    }
                });
            });
        });
    }
    deploy() {
        const pythonPath = vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
        vscode.window.showInformationMessage('Deploy to GitHub Pages?', 'Deploy', 'Cancel').then(choice => {
            if (choice === 'Deploy') {
                const proc = (0, child_process_1.spawn)(pythonPath, ['-m', 'docsforge', 'gh-deploy'], {
                    cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath
                });
                proc.on('close', (code) => {
                    if (code === 0) {
                        vscode.window.showInformationMessage('Deployed to GitHub Pages!');
                    }
                    else {
                        vscode.window.showErrorMessage('Deployment failed');
                    }
                });
            }
        });
    }
}
exports.ServerManager = ServerManager;
//# sourceMappingURL=serverManager.js.map