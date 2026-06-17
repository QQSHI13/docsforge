import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

export class ServerManager {
  private process: ChildProcess | null = null;
  private outputChannel: vscode.OutputChannel;
  private statusBarItem: vscode.StatusBarItem;
  private _serverUrl: string | null = null;
  private static stateChangeEmitter = new vscode.EventEmitter<void>();
  static instance: ServerManager | undefined;

  static onStateChange(listener: () => void): vscode.Disposable {
    return ServerManager.stateChangeEmitter.event(listener);
  }

  private static emitStateChange() {
    ServerManager.stateChangeEmitter.fire();
  }

  constructor() {
    ServerManager.instance = this;
    this.outputChannel = vscode.window.createOutputChannel('DocsForge');
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.statusBarItem.command = 'docsforge.openServer';
    this.updateStatusBar();
    this.statusBarItem.show();
  }

  get serverUrl(): string | null {
    return this._serverUrl;
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
    if (this.process && this._serverUrl) {
      this.statusBarItem.text = `$(play) DocsForge: ${this._serverUrl}`;
      this.statusBarItem.tooltip = 'DocsForge server is running. Click to open.';
    } else if (this.process) {
      this.statusBarItem.text = `$(play) DocsForge: starting...`;
      this.statusBarItem.tooltip = 'DocsForge server is starting...';
    } else {
      this.statusBarItem.text = `$(debug-disconnect) DocsForge: stopped`;
      this.statusBarItem.tooltip = 'Click to start DocsForge server';
    }
    this.statusBarItem.show();
  }

  start() {
    if (this.process) {
      vscode.window.showWarningMessage('DocsForge server is already running');
      if (this._serverUrl) {
        this.openBrowser();
      }
      return;
    }

    const workspaceRoot = this.workspaceRoot;
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    const hasConfig = ['docsforge.yml', 'docsforge.yaml', 'mkdocs.yml', 'mkdocs.yaml'].some(
      (c) => fs.existsSync(path.join(workspaceRoot, c))
    );
    if (!hasConfig) {
      vscode.window.showErrorMessage(
        'DocsForge: no docsforge.yml or mkdocs.yml found. Run "Initialize Project" first.'
      );
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
    this._serverUrl = null;
    this.updateStatusBar();

    this.process = spawn(this.pythonPath, args, {
      cwd: workspaceRoot,
      env: { ...process.env, FORCE_COLOR: '1' },
    });

    this.process.stdout?.on('data', (data: Buffer) => {
      const text = data.toString();
      this.outputChannel.append(text);
      this.detectServerUrl(text);
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      const text = data.toString();
      this.outputChannel.append(text);
      this.detectServerUrl(text);
    });

    this.process.on('error', (err: Error) => {
      this.cleanupAfterStop();
      this.showError(`Failed to start DocsForge server: ${err.message}`);
    });

    this.process.on('close', (code: number | null) => {
      this.cleanupAfterStop();
      if (code !== 0 && code !== null) {
        this.outputChannel.appendLine(`Server exited with code ${code}`);
        this.showError(`DocsForge server exited with code ${code}`);
      }
    });

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
    ServerManager.emitStateChange();

    if (openBrowser) {
      const disposable = ServerManager.onStateChange(() => {
        if (this._serverUrl) {
          this.openBrowser();
          disposable.dispose();
        }
      });
      setTimeout(() => disposable.dispose(), 10000);
    }
  }

  private detectServerUrl(text: string) {
    // Match common server messages from DocsForge/MkDocs, including host:port forms.
    const match = text.match(/(?:Serving on|Started server at)\s+(https?:\/\/[^\s]+)/i);
    if (match && !this._serverUrl) {
      this._serverUrl = match[1];
      this.updateStatusBar();
      ServerManager.emitStateChange();
    }
  }

  openBrowser() {
    if (this._serverUrl) {
      vscode.commands.executeCommand('simpleBrowser.show', vscode.Uri.parse(this._serverUrl));
    } else if (this.process) {
      vscode.window.showInformationMessage('DocsForge server URL is not known yet.');
    } else {
      vscode.window.showInformationMessage('DocsForge server is not running.');
    }
  }

  stop() {
    if (!this.process) {
      vscode.window.showWarningMessage('DocsForge server is not running');
      return;
    }

    const proc = this.process;
    this.process = null;
    this._serverUrl = null;

    proc.kill('SIGTERM');
    setTimeout(() => {
      if (!proc.killed) {
        proc.kill('SIGKILL');
      }
    }, 2000);

    this.cleanupAfterStop();
    vscode.window.showInformationMessage('DocsForge server stopped');
  }

  private cleanupAfterStop() {
    this.process = null;
    this._serverUrl = null;
    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
    ServerManager.emitStateChange();
    this.updateStatusBar();
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

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Building DocsForge documentation',
        cancellable: false,
      },
      async () => {
        return new Promise<void>((resolve, reject) => {
          const proc = spawn(this.pythonPath, ['-m', 'docsforge', 'build'], {
            cwd: workspaceRoot,
            env: { ...process.env, FORCE_COLOR: '1' },
          });

          proc.stdout?.on('data', (data: Buffer) => {
            this.outputChannel.append(data.toString());
          });
          proc.stderr?.on('data', (data: Buffer) => {
            this.outputChannel.append(data.toString());
          });

          proc.on('error', (err: Error) => {
            this.showError(`Build failed to start: ${err.message}`);
            reject();
          });

          proc.on('close', (code: number | null) => {
            this.outputChannel.appendLine(`Build finished with code ${code ?? 'unknown'}`);
            if (code === 0) {
              vscode.window.showInformationMessage('DocsForge build successful');
              resolve();
            } else {
              vscode.window
                .showErrorMessage('DocsForge build failed', 'Show Output')
                .then(() => this.outputChannel.show());
              reject();
            }
          });
        });
      }
    );
  }

  dispose() {
    this.stop();
    this.statusBarItem.dispose();
  }
}
