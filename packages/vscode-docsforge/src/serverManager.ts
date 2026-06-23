import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

const CONFIG_FILES = ['docsforge.yml', 'docsforge.yaml'];

export class ServerManager {
  private process: ChildProcess | null = null;
  private buildProcess: ChildProcess | null = null;
  private outputChannel: vscode.OutputChannel;
  private statusBarItem: vscode.StatusBarItem;
  private _serverUrl: string | null = null;
  private _startProgressResolve: (() => void) | null = null;
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

    // Check for existing server via pidfile
    this.detectExistingServer();
    // Watch for pidfile creation/deletion after VS Code is already open
    this.watchPidfile();
    // Periodic poll as a reliable backup for file watcher edge cases
    this.startPidfilePoll();
  }

  /** Poll .docsforge/server.json every 3s as a reliable fallback. */
  private startPidfilePoll() {
    const poll = () => {
      const root = this.workspaceRoot;
      if (!root) { return; }

      const pidfile = path.join(root, '.docsforge', 'server.json');
      try {
        const exists = fs.existsSync(pidfile);
        const hasUrl = this._serverUrl !== null;

        if (exists && !hasUrl) {
          // Server appeared — adopt it
          this.detectExistingServer();
        } else if (!exists && hasUrl) {
          // Server disappeared — reset
          if (!this.process) {
            this._serverUrl = null;
            this.updateStatusBar();
            vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
            ServerManager.emitStateChange();
          }
          // If we have an internal process, ignore the missing pidfile
          // (it will be re-created on the next build cycle)
        }
      } catch {
        // Ignore
      }
    };
    poll();
    setInterval(poll, 3000);
  }

  /** Watch .docsforge/server.json for create/delete events. */
  private watchPidfile() {
    const root = this.workspaceRoot;
    if (!root) { return; }

    const pidfile = path.join(root, '.docsforge', 'server.json');
    try {
      fs.watchFile(pidfile, (curr, prev) => {
        if (curr.size > 0 && prev.size === 0) {
          // File was created — server started
          this.detectExistingServer();
        } else if (curr.size === 0 && prev.size > 0) {
          // File was deleted — server stopped
          this._serverUrl = null;
          this.updateStatusBar();
          vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
          ServerManager.emitStateChange();
        }
      });
    } catch {
      // Ignore if watching fails
    }
  }

  /** Check if a docsforge serve process is already running via pidfile.
   *  If found, adopt its URL and show the server as running. */
  private detectExistingServer(retries = 3) {
    const root = this.workspaceRoot;
    if (!root) {
      // Workspace not ready yet — retry after a short delay
      if (retries > 0) {
        setTimeout(() => this.detectExistingServer(retries - 1), 1000);
      }
      return;
    }

    const pidfile = path.join(root, '.docsforge', 'server.json');
    try {
      if (fs.existsSync(pidfile)) {
        const data = JSON.parse(fs.readFileSync(pidfile, 'utf-8'));
        if (data.url) {
          this._serverUrl = data.url;
          this.updateStatusBar();
          vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
          ServerManager.emitStateChange();
        }
      }
    } catch {
      // Ignore malformed pidfile
    }
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

  /** Find the docsforge config file in the workspace root. */
  static findConfig(workspaceRoot: string): string | null {
    for (const name of CONFIG_FILES) {
      if (fs.existsSync(path.join(workspaceRoot, name))) {
        return name;
      }
    }
    return null;
  }

  /** Check whether a config file exists (for activation). */
  static hasConfig(workspaceRoot: string): boolean {
    return ServerManager.findConfig(workspaceRoot) !== null;
  }

  /** Detect docsforge server URLs from output lines.
   *  Matches: "Serving on http://host:port/path" */
  private detectServerUrl(text: string) {
    if (this._serverUrl) { return; }
    const match = text.match(/Serving on\s+(https?:\/\/[^\s]+)/i);
    if (match) {
      this._serverUrl = match[1];
      this.updateStatusBar();
      ServerManager.emitStateChange();
    }
  }

  start() {
    // Prevent double-start: if already running (own process or pidfile), just open browser
    if (this.process || this._serverUrl) {
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

    const configName = ServerManager.findConfig(workspaceRoot);
    if (!configName) {
      vscode.window.showErrorMessage(
        'DocsForge: no docsforge.yml found. Run "Initialize Project" first.'
      );
      return;
    }

    const lan = vscode.workspace.getConfiguration('docsforge').get('lan', false);
    const openBrowser = vscode.workspace.getConfiguration('docsforge').get('openBrowser', true);

    // Build CLI args matching `docsforge serve --no-open [--lan]`
    const args = ['-m', 'docsforge', 'serve', '--no-open'];
    if (lan) {
      args.push('--lan');
    }

    this.outputChannel.show();
    this.outputChannel.appendLine(`$ ${this.pythonPath} ${args.join(' ')}`);
    this.outputChannel.appendLine('');
    this._serverUrl = null;
    this.updateStatusBar();

    this._startProgressResolve = null;
    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Starting DocsForge server...',
        cancellable: false,
      },
      () => new Promise<void>((resolve) => {
        this._startProgressResolve = resolve;
        // Resolve when URL is detected (server is ready)
        const disposable = ServerManager.onStateChange(() => {
          if (this._serverUrl) {
            this._startProgressResolve = null;
            disposable.dispose();
            resolve();
          }
        });
        // Safety timeout: resolve after 30s even if URL not yet detected
        setTimeout(() => {
          if (this._startProgressResolve) {
            this._startProgressResolve = null;
            disposable.dispose();
            resolve();
          }
        }, 30000);
      })
    );

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

    // Register auto-open listener that fires when URL is detected
    if (openBrowser) {
      const disposable = ServerManager.onStateChange(() => {
        if (this._serverUrl) {
          this.openBrowser();
          disposable.dispose();
        }
      });
    }
  }

  openBrowser() {
    if (this._serverUrl) {
      vscode.commands.executeCommand('simpleBrowser.api.open', vscode.Uri.parse(this._serverUrl));
    } else if (this.process) {
      vscode.window.showInformationMessage('DocsForge: waiting for server to output its URL...');
    } else {
      vscode.window.showInformationMessage('DocsForge server is not running.');
    }
  }

  /** Stop the server. If `silent` is true, suppress toast messages
   *  (used during extension deactivation).
   *  Supports stopping internal, external (pidfile), and build processes. */
  stop(silent = false) {
    // Stop a running build if one exists
    if (this.buildProcess) {
      const proc = this.buildProcess;
      this.buildProcess = null;
      proc.kill('SIGTERM');
      setTimeout(() => { if (!proc.killed) proc.kill('SIGKILL'); }, 2000);
      if (!silent) vscode.window.showInformationMessage('DocsForge build cancelled');
      return;
    }

    // Stop managed server process
    if (this.process) {
      const proc = this.process;
      proc.kill('SIGTERM');
      setTimeout(() => {
        if (!proc.killed) proc.kill('SIGKILL');
      }, 2000);
      this.cleanupAfterStop();
      if (!silent) vscode.window.showInformationMessage('DocsForge server stopped');
      return;
    }

    // Stop external server (from pidfile)
    const root = this.workspaceRoot;
    if (root) {
      const pidfile = path.join(root, '.docsforge', 'server.json');
      try {
        if (fs.existsSync(pidfile)) {
          const data = JSON.parse(fs.readFileSync(pidfile, 'utf-8'));
          if (data.pid) {
            try {
              process.kill(data.pid, 'SIGTERM');
              if (!silent) vscode.window.showInformationMessage('DocsForge server stopped');
            } catch {
              if (!silent) vscode.window.showWarningMessage('Could not stop external server (PID may have exited)');
            }
            // Delete stale pidfile since the killed process can't clean up itself
            try { fs.unlinkSync(pidfile); } catch { /* Ignore */ }
            this.cleanupAfterStop();
            return;
          }
        }
      } catch {
        // Ignore pidfile errors
      }
    }

    if (!silent) {
      vscode.window.showWarningMessage('DocsForge server is not running');
    }
  }

  stopBuild() {
    if (this.buildProcess) {
      this.buildProcess.kill('SIGTERM');
      setTimeout(() => {
        if (this.buildProcess && !this.buildProcess.killed) {
          this.buildProcess.kill('SIGKILL');
        }
      }, 2000);
      this.buildProcess = null;
    }
  }

  private cleanupAfterStop() {
    if (this._startProgressResolve) {
      this._startProgressResolve();
      this._startProgressResolve = null;
    }
    this.process = null;
    this._serverUrl = null;

    // Clean up stale pidfile if it exists
    const root = this.workspaceRoot;
    if (root) {
      const pidfile = path.join(root, '.docsforge', 'server.json');
      try { if (fs.existsSync(pidfile)) fs.unlinkSync(pidfile); } catch { /* Ignore */ }
    }

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
    ServerManager.emitStateChange();
    this.updateStatusBar();
  }

  isRunning(): boolean {
    return this.process !== null || this._serverUrl !== null;
  }

  isBuilding(): boolean {
    return this.buildProcess !== null;
  }

  build() {
    const workspaceRoot = this.workspaceRoot;
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    if (!ServerManager.hasConfig(workspaceRoot)) {
      vscode.window.showErrorMessage(
        'DocsForge: no docsforge.yml found. Run "Initialize Project" first.'
      );
      return;
    }

    this.outputChannel.show();
    this.outputChannel.appendLine(`$ ${this.pythonPath} -m docsforge build`);
    this.outputChannel.appendLine('');

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Building DocsForge documentation...',
        cancellable: false,
      },
      async () => {
        return new Promise<void>((resolve, reject) => {
          const proc = spawn(this.pythonPath, ['-m', 'docsforge', 'build'], {
            cwd: workspaceRoot,
            env: { ...process.env, FORCE_COLOR: '1' },
          });

          this.buildProcess = proc;
          vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', true);
          ServerManager.emitStateChange();

          proc.stdout?.on('data', (data: Buffer) => {
            this.outputChannel.append(data.toString());
          });
          proc.stderr?.on('data', (data: Buffer) => {
            this.outputChannel.append(data.toString());
          });

          proc.on('error', (err: Error) => {
            this.buildProcess = null;
            vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', false);
            ServerManager.emitStateChange();
            this.showError(`Build failed to start: ${err.message}`);
            reject();
          });

          proc.on('close', (code: number | null) => {
            this.buildProcess = null;
            vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', false);
            ServerManager.emitStateChange();
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
    this.stop(/* silent */ true);
    this.statusBarItem.dispose();
  }
}
