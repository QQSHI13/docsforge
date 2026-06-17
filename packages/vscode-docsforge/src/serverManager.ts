import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';

export class ServerManager {
  private process: ChildProcess | null = null;
  private outputChannel: vscode.OutputChannel;
  private statusBarItem: vscode.StatusBarItem;
  private serverUrl: string | null = null;
  private static stateChangeEmitter = new vscode.EventEmitter<void>();

  static onStateChange(listener: () => void): vscode.Disposable {
    return ServerManager.stateChangeEmitter.event(listener);
  }

  private static emitStateChange() {
    ServerManager.stateChangeEmitter.fire();
  }

  constructor() {
    this.outputChannel = vscode.window.createOutputChannel('DocsForge');
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.statusBarItem.command = 'docsforge.openServer';
    this.updateStatusBar();
    this.statusBarItem.show();
  }

  private get pythonPath(): string {
    return vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');
  }

  private get workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  private showError(message: string) {
    vscode.window.showErrorMessage(message, 'Show Output').then((choice) => {
      if (choice === 'Show Output') {
        this.outputChannel.show();
      }
    });
  }

  private updateStatusBar() {
    if (this.process && this.serverUrl) {
      this.statusBarItem.text = `$(play) DocsForge: ${this.serverUrl}`;
      this.statusBarItem.tooltip = 'DocsForge server is running. Click to open.';
      this.statusBarItem.show();
    } else if (this.process) {
      this.statusBarItem.text = `$(play) DocsForge: starting...`;
      this.statusBarItem.tooltip = 'DocsForge server is starting...';
      this.statusBarItem.show();
    } else {
      this.statusBarItem.text = `$(debug-disconnect) DocsForge: stopped`;
      this.statusBarItem.tooltip = 'Click to start DocsForge server';
      this.statusBarItem.show();
    }
  }

  start() {
    if (this.process) {
      vscode.window.showWarningMessage('DocsForge server is already running');
      if (this.serverUrl) {
        this.openBrowser();
      }
      return;
    }

    const workspaceRoot = this.workspaceRoot;
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    const lan = vscode.workspace.getConfiguration('docsforge').get('lan', false);
    const openBrowser = vscode.workspace.getConfiguration('docsforge').get('openBrowser', true);
    const args = ['-m', 'docsforge', 'serve', '--no-open'];
    if (lan) {
      args.push('--lan');
    }

    this.outputChannel.show();
    this.outputChannel.appendLine('Starting DocsForge server...');
    this.serverUrl = null;
    this.updateStatusBar();

    this.process = spawn(this.pythonPath, args, {
      cwd: workspaceRoot,
      env: { ...process.env, FORCE_COLOR: '1' }
    });

    this.process.stdout?.on('data', (data) => {
      const text = data.toString();
      this.outputChannel.append(text);
      this.detectServerUrl(text);
    });

    this.process.stderr?.on('data', (data) => {
      const text = data.toString();
      this.outputChannel.append(text);
      this.detectServerUrl(text);
    });

    this.process.on('error', (err) => {
      this.process = null;
      this.serverUrl = null;
      vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
      ServerManager.emitStateChange();
      this.updateStatusBar();
      this.showError(`Failed to start DocsForge server: ${err.message}`);
    });

    this.process.on('close', (code) => {
      this.process = null;
      this.serverUrl = null;
      vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
      ServerManager.emitStateChange();
      this.updateStatusBar();
      if (code !== 0 && code !== null) {
        this.outputChannel.appendLine(`Server exited with code ${code}`);
        this.showError(`DocsForge server exited with code ${code}`);
      }
    });

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
    ServerManager.emitStateChange();

    if (openBrowser) {
      // Wait briefly for the server to print its URL, then open browser.
      const disposable = ServerManager.onStateChange(() => {
        if (this.serverUrl) {
          this.openBrowser();
          disposable.dispose();
        }
      });
      // Fallback: if no URL after 10s, stop listening.
      setTimeout(() => disposable.dispose(), 10000);
    }
  }

  private detectServerUrl(text: string) {
    const match = text.match(/Serving on (https?:\/\/[^\s]+)/);
    if (match && !this.serverUrl) {
      this.serverUrl = match[1];
      this.updateStatusBar();
      ServerManager.emitStateChange();
    }
  }

  openBrowser() {
    if (this.serverUrl) {
      vscode.commands.executeCommand('simpleBrowser.show', this.serverUrl);
    } else {
      vscode.window.showWarningMessage('DocsForge server URL is not known yet.');
    }
  }

  stop() {
    if (!this.process) {
      vscode.window.showWarningMessage('DocsForge server is not running');
      return;
    }

    this.process.kill();
    this.process = null;
    this.serverUrl = null;
    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
    ServerManager.emitStateChange();
    this.updateStatusBar();
    vscode.window.showInformationMessage('DocsForge server stopped');
  }

  isRunning(): boolean {
    return this.process !== null;
  }

  build() {
    const workspaceRoot = this.workspaceRoot;
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    vscode.window.withProgress({
      location: vscode.ProgressLocation.Notification,
      title: 'Building DocsForge documentation',
      cancellable: false
    }, async () => {
      return new Promise<void>((resolve, reject) => {
        const proc = spawn(this.pythonPath, ['-m', 'docsforge', 'build'], {
          cwd: workspaceRoot,
          env: { ...process.env, FORCE_COLOR: '1' }
        });

        proc.stdout?.on('data', (data) => {
          this.outputChannel.append(data.toString());
        });
        proc.stderr?.on('data', (data) => {
          this.outputChannel.append(data.toString());
        });

        proc.on('error', (err) => {
          this.showError(`Build failed to start: ${err.message}`);
          reject();
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

  dispose() {
    this.stop();
    this.statusBarItem.dispose();
  }
}
