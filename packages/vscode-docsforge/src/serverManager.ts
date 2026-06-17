import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';

export class ServerManager {
  private process: ChildProcess | null = null;
  private outputChannel: vscode.OutputChannel;
  private static stateChangeEmitter = new vscode.EventEmitter<void>();

  static onStateChange(listener: () => void): vscode.Disposable {
    return ServerManager.stateChangeEmitter.event(listener);
  }

  private static emitStateChange() {
    ServerManager.stateChangeEmitter.fire();
  }

  constructor() {
    this.outputChannel = vscode.window.createOutputChannel('DocsForge');
  }

  private get pythonPath(): string {
    return vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
  }

  start() {
    if (this.process) {
      vscode.window.showWarningMessage('DocsForge server is already running');
      return;
    }

    const lan = vscode.workspace.getConfiguration('docsforge').get('lan', false);
    const args = ['-m', 'docsforge', 'serve', '--no-open'];
    if (lan) {
      args.push('--lan');
    }

    this.outputChannel.show();
    this.outputChannel.appendLine('Starting DocsForge server...');

    this.process = spawn(this.pythonPath, args, {
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
      ServerManager.emitStateChange();
      if (code !== 0) {
        this.outputChannel.appendLine(`Server exited with code ${code}`);
      }
    });

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
    ServerManager.emitStateChange();
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
    ServerManager.emitStateChange();
    vscode.window.showInformationMessage('DocsForge server stopped');
  }

  isRunning(): boolean {
    return this.process !== null;
  }

  build() {
    vscode.window.withProgress({
      location: vscode.ProgressLocation.Notification,
      title: 'Building DocsForge documentation',
      cancellable: false
    }, async () => {
      return new Promise<void>((resolve, reject) => {
        const proc = spawn(this.pythonPath, ['-m', 'docsforge', 'build'], {
          cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath,
          env: { ...process.env, FORCE_COLOR: '1' }
        });

        proc.stdout?.on('data', (data) => {
          this.outputChannel.append(data.toString());
        });
        proc.stderr?.on('data', (data) => {
          this.outputChannel.append(data.toString());
        });

        proc.on('close', (code) => {
          if (code === 0) {
            vscode.window.showInformationMessage('DocsForge build successful');
            resolve();
          } else {
            vscode.window.showErrorMessage('DocsForge build failed', 'Show Output')
              .then(() => this.outputChannel.show());
            reject();
          }
        });
      });
    });
  }
}
