import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import { findConfig as findConfigPure, hasConfig as hasConfigPure, extractServerUrl, shouldEscalateToSigkill } from './pure';
import { DocsForgeLogPanel } from './logPanel';
import { currentProjectRoot } from './roots';
import { detectEnvironment, ensureDocsforge, pickInstall } from './environment';

/** Re-exported for backwards compatibility (pure helper lives in pure.ts). */
export { shouldEscalateToSigkill };

/** Managed serve/build state for one workspace root (multi-root: every
 *  folder gets its own entry, created lazily). */
interface RootState {
  process: ChildProcess | null;
  buildProcess: ChildProcess | null;
  serverUrl: string | null;
  /** Set synchronously before the first await so rapid double-invokes
   *  can't pass the already-running guard twice and orphan a process. */
  starting: boolean;
  building: boolean;
  startResolve: (() => void) | null;
  processCloseHandler: ((code: number | null) => void) | null;
  processErrorHandler: ((err: Error) => void) | null;
  startSafetyTimeout: NodeJS.Timeout | null;
}

function freshRootState(): RootState {
  return {
    process: null,
    buildProcess: null,
    serverUrl: null,
    starting: false,
    building: false,
    startResolve: null,
    processCloseHandler: null,
    processErrorHandler: null,
    startSafetyTimeout: null,
  };
}

export class ServerManager {
  private servers = new Map<string, RootState>();
  private logPanel: DocsForgeLogPanel;
  private statusBarItem: vscode.StatusBarItem;
  private pollTimer: NodeJS.Timeout | null = null;
  private watchedPidfiles = new Set<string>();
  private static stateChangeEmitter = new vscode.EventEmitter<void>();
  private static emitterDisposed = false;
  static instance: ServerManager | undefined;

  private static ensureEmitter(): vscode.EventEmitter<void> {
    if (ServerManager.emitterDisposed || !ServerManager.stateChangeEmitter) {
      ServerManager.stateChangeEmitter = new vscode.EventEmitter<void>();
      ServerManager.emitterDisposed = false;
    }
    return ServerManager.stateChangeEmitter;
  }

  /** Dispose the shared state-change emitter (call on extension deactivate). */
  static disposeStateEmitter(): void {
    if (!ServerManager.emitterDisposed) {
      ServerManager.emitterDisposed = true;
      ServerManager.stateChangeEmitter.dispose();
    }
  }

  static onStateChange(listener: () => void): vscode.Disposable {
    return ServerManager.ensureEmitter().event(listener);
  }

  private static emitStateChange() {
    if (ServerManager.emitterDisposed) {
      return;
    }
    ServerManager.stateChangeEmitter.fire();
  }

  constructor() {
    // Dispose any previous instance's UI resources to avoid output-channel leaks.
    if (ServerManager.instance) {
      ServerManager.instance.dispose();
    }
    ServerManager.instance = this;
    this.logPanel = DocsForgeLogPanel.get();
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.statusBarItem.command = 'docsforge.openServer';
    this.updateStatusBar();
    this.statusBarItem.show();

    // Check for existing servers via pidfiles
    this.detectAllExistingServers();
    // Watch for pidfile creation/deletion after VS Code is already open
    this.watchPidfiles();
    // Periodic poll as a reliable backup for file watcher edge cases
    this.startPidfilePoll();
    // The status bar reflects the current root — refresh on editor switch.
    this.editorWatch = vscode.window.onDidChangeActiveTextEditor(
      () => this.updateStatusBar(),
    );
  }

  private editorWatch: vscode.Disposable | null = null;

  /** State for a root, created lazily (multi-root: one entry per folder). */
  private forRoot(root: string): RootState {
    let st = this.servers.get(root);
    if (!st) {
      st = freshRootState();
      this.servers.set(root, st);
    }
    return st;
  }

  /** All workspace folder paths. */
  private static allRoots(): string[] {
    return vscode.workspace.workspaceFolders?.map((f) => f.uri.fsPath) ?? [];
  }

  /** Poll every .docsforge/server.json as a reliable fallback. */
  private startPidfilePoll() {
    const poll = () => {
      for (const root of ServerManager.allRoots()) {
        const st = this.forRoot(root);
        const pidfile = path.join(root, '.docsforge', 'server.json');
        try {
          const exists = fs.existsSync(pidfile);
          const hasUrl = st.serverUrl !== null;

          if (exists && !hasUrl) {
            // Server appeared — adopt it
            this.detectExistingServerFor(root);
          } else if (!exists && hasUrl) {
            // Server disappeared — reset
            if (!st.process) {
              st.serverUrl = null;
              this.updateStatusBar();
              vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', this.isRunning());
              ServerManager.emitStateChange();
            }
            // If we have an internal process, ignore the missing pidfile
            // (it will be re-created on the next build cycle)
          }
        } catch {
          // Ignore
        }
      }
    };
    poll();
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }
    this.pollTimer = setInterval(poll, 3000);
  }

  /** Watch every .docsforge/server.json for create/delete events. */
  private watchPidfiles() {
    for (const root of ServerManager.allRoots()) {
      const pidfile = path.join(root, '.docsforge', 'server.json');
      try {
        if (this.watchedPidfiles.has(pidfile)) {
          continue;
        }
        this.watchedPidfiles.add(pidfile);
        fs.watchFile(pidfile, (curr, prev) => {
          if (curr.size > 0 && prev.size === 0) {
            // File was created — server started
            this.detectExistingServerFor(root);
          } else if (curr.size === 0 && prev.size > 0) {
            // File was deleted — server stopped
            const st = this.forRoot(root);
            st.serverUrl = null;
            this.updateStatusBar();
            vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', this.isRunning());
            ServerManager.emitStateChange();
          }
        });
      } catch {
        // Ignore if watching fails
      }
    }
  }

  /** Check every root for an already-running serve process via pidfile.
   *  If found, adopt its URL and show the server as running. */
  private detectAllExistingServers(retries = 3) {
    const roots = ServerManager.allRoots();
    if (!roots.length) {
      // Workspace not ready yet — retry after a short delay
      if (retries > 0) {
        setTimeout(() => this.detectAllExistingServers(retries - 1), 1000);
      }
      return;
    }
    for (const root of roots) {
      this.detectExistingServerFor(root);
    }
  }

  private detectExistingServerFor(root: string) {
    const pidfile = path.join(root, '.docsforge', 'server.json');
    try {
      if (fs.existsSync(pidfile)) {
        const data = JSON.parse(fs.readFileSync(pidfile, 'utf-8'));
        if (data.url) {
          this.forRoot(root).serverUrl = data.url;
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
    const root = this.currentRoot();
    return root ? this.forRoot(root).serverUrl : null;
  }

  /** Server URL adopted or started for a specific root. */
  urlForRoot(root: string): string | null {
    return this.forRoot(root).serverUrl;
  }

  private get workspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  }

  /** Root commands act on: the active editor's project, else the first
   *  configured root, else the first folder (multi-root aware). */
  currentRoot(): string | undefined {
    return currentProjectRoot();
  }

  /** Ask which project to act on when the current root is ambiguous
   *  (several configured roots, no active editor). Returns undefined when
   *  the user cancels. */
  async pickRoot(): Promise<string | undefined> {
    const folders = vscode.workspace.workspaceFolders ?? [];
    const configured = folders.filter((f) => ServerManager.hasConfig(f.uri.fsPath));
    const current = this.currentRoot();
    if (configured.length < 2 || (current && ServerManager.hasConfig(current))) {
      return current;
    }
    const pick = await vscode.window.showQuickPick(
      configured.map((f) => ({ label: f.name, description: f.uri.fsPath, root: f.uri.fsPath })),
      { placeHolder: 'Several DocsForge projects are open. Pick one.' },
    );
    return pick?.root;
  }

  /** Suffix identifying the root in messages (empty for single-folder). */
  private rootLabel(root: string): string {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (folders.length < 2) {
      return '';
    }
    const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(root));
    return folder ? ` [${folder.name}]` : '';
  }

  private showError(message: string) {
    vscode.window.showErrorMessage(message, 'Show Output').then((choice) => {
      if (choice === 'Show Output') {
        this.logPanel.show();
      }
    });
  }

  /** Resolve a usable Python interpreter, installing docsforge if needed.
   *  Asks which install to use when several interpreters have docsforge.
   *  Returns null when no interpreter is available or the user cancelled. */
  private async resolveEnvironment(root: string): Promise<string | null> {
    const pick = await pickInstall(root);
    if (pick.kind === 'picked') {
      return pick.state.python;
    }
    if (pick.kind === 'cancelled') {
      return null;
    }
    const state = await detectEnvironment(root);
    if (!pick.python) {
      vscode.window.showErrorMessage('DocsForge: no Python interpreter found. Install Python 3.10+ first.');
      return null;
    }
    return ensureDocsforge(root, { ...state, python: pick.python }, (line) => this.logPanel.append(line));
  }

  private updateStatusBar() {
    const root = this.currentRoot();
    const st = root ? this.forRoot(root) : null;
    const label = root ? this.rootLabel(root) : '';
    if (st?.process && st.serverUrl) {
      this.statusBarItem.text = `$(play) DocsForge${label}: ${st.serverUrl}`;
      this.statusBarItem.tooltip = 'DocsForge server is running. Click to open.';
    } else if (st?.process) {
      this.statusBarItem.text = `$(play) DocsForge${label}: starting...`;
      this.statusBarItem.tooltip = 'DocsForge server is starting...';
    } else if (st?.serverUrl) {
      this.statusBarItem.text = `$(globe) DocsForge${label}: external server`;
      this.statusBarItem.tooltip = 'An external DocsForge server was detected (pidfile). Click to open.';
    } else {
      this.statusBarItem.text = `$(debug-disconnect) DocsForge${label}: stopped`;
      this.statusBarItem.tooltip = 'Click to start DocsForge server';
    }
    this.statusBarItem.show();
  }

  /** Find the docsforge config file in the workspace root. */
  static findConfig(workspaceRoot: string): string | null {
    return findConfigPure(workspaceRoot);
  }

  /** Check whether a config file exists (for activation). */
  static hasConfig(workspaceRoot: string): boolean {
    return hasConfigPure(workspaceRoot);
  }

  /** Detect docsforge server URLs from output lines.
   *  Matches: "Serving on http://host:port/path" */
  private detectServerUrl(st: RootState, text: string) {
    if (st.serverUrl) { return; }
    const url = extractServerUrl(text);
    if (url) {
      st.serverUrl = url;
      this.updateStatusBar();
      ServerManager.emitStateChange();
    }
  }

  async start(root?: string) {
    const workspaceRoot = root ?? await this.pickRoot();
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }
    const st = this.forRoot(workspaceRoot);
    const label = this.rootLabel(workspaceRoot);
    // Prevent double-start: if already running (own process or pidfile), just open browser
    if (st.process || st.serverUrl || st.starting) {
      vscode.window.showWarningMessage(`DocsForge server is already running${label}`);
      if (st.serverUrl) {
        this.openBrowser(workspaceRoot);
      }
      return;
    }

    const configName = ServerManager.findConfig(workspaceRoot);
    if (!configName) {
      vscode.window.showErrorMessage(
        `DocsForge: no docsforge.yml found${label}. Run "Initialize Project" first.`
      );
      return;
    }

    st.starting = true;
    const python = await this.resolveEnvironment(workspaceRoot);
    if (!python) {
      st.starting = false;
      return;
    }

    const lan = vscode.workspace.getConfiguration('docsforge').get('lan', false);
    const openBrowser = vscode.workspace.getConfiguration('docsforge').get('openBrowser', true);

    // Build CLI args matching `docsforge serve --no-open [--lan]`
    const args = ['-m', 'docsforge', 'serve', '--no-open'];
    if (lan) {
      args.push('--lan');
    }

    this.logPanel.show();
    this.logPanel.appendLine(`$ ${python} ${args.join(' ')}`);
    this.logPanel.appendLine('');
    st.serverUrl = null;
    this.updateStatusBar();

    st.startResolve = null;
    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `Starting DocsForge server${label}...`,
        cancellable: false,
      },
      () => new Promise<void>((resolve) => {
        st.startResolve = resolve;
        // Resolve when URL is detected (server is ready)
        const disposable = ServerManager.onStateChange(() => {
          if (st.serverUrl) {
            this.clearStartSafetyTimeout(st);
            st.startResolve = null;
            disposable.dispose();
            resolve();
          }
        });
        // Safety timeout: resolve after 30s even if URL not yet detected
        st.startSafetyTimeout = setTimeout(() => {
          st.startSafetyTimeout = null;
          if (st.startResolve) {
            st.startResolve = null;
            disposable.dispose();
            resolve();
          }
        }, 30000);
      })
    );

    st.process = spawn(python, args, {
      cwd: workspaceRoot,
      env: { ...process.env, FORCE_COLOR: '1' },
    });
    // Spawned: the process guard now holds, release the starting flag.
    st.starting = false;

    st.process.stdout?.on('data', (data: Buffer) => {
      const text = data.toString();
      this.logPanel.append(text);
      this.detectServerUrl(st, text);
    });

    st.process.stderr?.on('data', (data: Buffer) => {
      const text = data.toString();
      this.logPanel.append(text);
      this.detectServerUrl(st, text);
    });

    const onError = (err: Error) => {
      this.cleanupAfterStop(st, workspaceRoot);
      this.showError(`Failed to start DocsForge server: ${err.message}`);
    };
    st.processErrorHandler = onError;
    st.process.on('error', onError);

    const onClose = (code: number | null) => {
      this.cleanupAfterStop(st, workspaceRoot);
      if (code !== 0 && code !== null) {
        this.logPanel.appendLine(`Server exited with code ${code}`);
        this.showError(`DocsForge server exited with code ${code}`);
      }
    };
    st.processCloseHandler = onClose;
    st.process.on('close', onClose);

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', true);
    ServerManager.emitStateChange();

    // Register auto-open listener that fires when URL is detected
    if (openBrowser) {
      const disposable = ServerManager.onStateChange(() => {
        if (st.serverUrl) {
          this.openBrowser(workspaceRoot);
          disposable.dispose();
        }
      });
    }
  }

  openBrowser(root?: string) {
    const workspaceRoot = root ?? this.currentRoot();
    const st = workspaceRoot ? this.forRoot(workspaceRoot) : null;
    if (st?.serverUrl) {
      vscode.commands.executeCommand('simpleBrowser.api.open', vscode.Uri.parse(st.serverUrl));
    } else if (st?.process) {
      vscode.window.showInformationMessage('DocsForge: waiting for server to output its URL...');
    } else {
      vscode.window.showInformationMessage('DocsForge server is not running.');
    }
  }

  /** Stop the server. If `silent` is true, suppress toast messages
   *  (used during extension deactivation).
   *  Supports stopping internal, external (pidfile), and build processes. */
  stop(silent = false, root?: string) {
    const workspaceRoot = root ?? this.currentRoot();
    const st = workspaceRoot ? this.forRoot(workspaceRoot) : null;
    const label = workspaceRoot ? this.rootLabel(workspaceRoot) : '';
    // Stop serves the server: only reroute to a running build when there is
    // no server (own process or adopted pidfile) for this root — Stop Build
    // has its own sidebar item and command.
    if (st?.buildProcess && !st.process && !st.serverUrl) {
      this.stopBuild(workspaceRoot);
      if (!silent) vscode.window.showInformationMessage(`DocsForge build cancelled${label}`);
      return;
    }

    // Stop managed server process
    if (st?.process) {
      const proc = st.process;
      st.process = null;
      if (st.processCloseHandler) { proc.removeListener('close', st.processCloseHandler); }
      if (st.processErrorHandler) { proc.removeListener('error', st.processErrorHandler); }
      let exited = false;
      proc.once('close', () => { exited = true; });
      proc.kill('SIGTERM');
      const sigkillTimer = setTimeout(() => {
        if (!exited && shouldEscalateToSigkill(proc)) {
          try { proc.kill('SIGKILL'); } catch { /* already exited */ }
        }
      }, 2000);
      proc.once('close', () => {
        clearTimeout(sigkillTimer);
        this.cleanupAfterStop(st, workspaceRoot!);
        if (!silent) vscode.window.showInformationMessage(`DocsForge server stopped${label}`);
      });
      return;
    }

    // Stop external server (from pidfile)
    if (workspaceRoot) {
      const pidfile = path.join(workspaceRoot, '.docsforge', 'server.json');
      try {
        if (fs.existsSync(pidfile)) {
          const data = JSON.parse(fs.readFileSync(pidfile, 'utf-8'));
          // Pidfile contents are only trusted when numeric: never hand an
          // attacker-crafted value to process.kill (ESRCH vs signal mixup).
          if (typeof data.pid === 'number' && Number.isInteger(data.pid) && data.pid > 0) {
            try {
              process.kill(data.pid, 'SIGTERM');
              if (!silent) vscode.window.showInformationMessage(`DocsForge server stopped${label}`);
            } catch {
              if (!silent) vscode.window.showWarningMessage('Could not stop external server (PID may have exited)');
            }
            // Delete stale pidfile since the killed process can't clean up itself
            try { fs.unlinkSync(pidfile); } catch { /* Ignore */ }
            this.cleanupAfterStop(st!, workspaceRoot);
            return;
          }
        }
      } catch {
        // Ignore pidfile errors
      }
    }

    if (!silent) {
      vscode.window.showWarningMessage(`DocsForge server is not running${label}`);
    }
  }

  stopBuild(root?: string) {
    const workspaceRoot = root ?? this.currentRoot();
    const st = workspaceRoot ? this.forRoot(workspaceRoot) : null;
    if (!st?.buildProcess) { return; }
    const proc = st.buildProcess;
    st.buildProcess = null;
    st.building = false;
    vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', this.isBuilding());
    ServerManager.emitStateChange();
    let exited = false;
    proc.once('close', () => { exited = true; });
    proc.kill('SIGTERM');
    setTimeout(() => {
      if (!exited && shouldEscalateToSigkill(proc)) {
        try { proc.kill('SIGKILL'); } catch { /* already exited */ }
      }
    }, 2000);
  }

  private cleanupAfterStop(st: RootState, root: string) {
    if (st.startResolve) {
      st.startResolve();
      st.startResolve = null;
    }
    st.process = null;
    st.serverUrl = null;
    st.starting = false;

    // Clean up stale pidfile if it exists
    const pidfile = path.join(root, '.docsforge', 'server.json');
    try { if (fs.existsSync(pidfile)) fs.unlinkSync(pidfile); } catch { /* Ignore */ }

    vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', this.isRunning());
    ServerManager.emitStateChange();
    this.updateStatusBar();
  }

  /** Whether any root has a running (managed or adopted) server. */
  isRunning(): boolean {
    for (const st of this.servers.values()) {
      if (st.process !== null || st.serverUrl !== null) {
        return true;
      }
    }
    return false;
  }

  /** Whether any root has a running build. */
  isBuilding(): boolean {
    for (const st of this.servers.values()) {
      if (st.buildProcess !== null) {
        return true;
      }
    }
    return false;
  }

  async build(root?: string) {
    const workspaceRoot = root ?? await this.pickRoot();
    if (!workspaceRoot) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }
    const st = this.forRoot(workspaceRoot);
    const label = this.rootLabel(workspaceRoot);

    if (!ServerManager.hasConfig(workspaceRoot)) {
      vscode.window.showErrorMessage(
        `DocsForge: no docsforge.yml found${label}. Run "Initialize Project" first.`
      );
      return;
    }

    if (st.buildProcess || st.building) {
      vscode.window.showInformationMessage(`DocsForge build is already running${label}`);
      return;
    }

    st.building = true;
    const python = await this.resolveEnvironment(workspaceRoot);
    if (!python) {
      st.building = false;
      return;
    }

    this.logPanel.show();
    this.logPanel.appendLine(`$ ${python} -m docsforge build`);
    this.logPanel.appendLine('');

    // Awaited (not fire-and-forget): failures are caught below after the
    // user-facing messages, so nothing becomes an unhandled rejection.
    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: `Building DocsForge documentation${label}...`,
          cancellable: false,
        },
        async () => {
          await new Promise<void>((resolve, reject) => {
            let proc: ChildProcess;
            try {
              proc = spawn(python, ['-m', 'docsforge', 'build'], {
                cwd: workspaceRoot,
                env: { ...process.env, FORCE_COLOR: '1' },
              });
            } catch (err) {
              reject(err instanceof Error ? err : new Error(String(err)));
              return;
            }

            st.buildProcess = proc;
            vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', true);
            ServerManager.emitStateChange();

            proc.stdout?.on('data', (data: Buffer) => {
              this.logPanel.append(data.toString());
            });
            proc.stderr?.on('data', (data: Buffer) => {
              this.logPanel.append(data.toString());
            });

            proc.on('error', (err: Error) => {
              st.buildProcess = null;
              st.building = false;
              vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', this.isBuilding());
              ServerManager.emitStateChange();
              this.showError(`Build failed to start: ${err.message}`);
              reject(err);
            });

            proc.on('close', (code: number | null) => {
              st.buildProcess = null;
              st.building = false;
              vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', this.isBuilding());
              ServerManager.emitStateChange();
              if (code === 0) {
                vscode.window.showInformationMessage(`DocsForge build successful${label}`);
                resolve();
              } else {
                vscode.window
                  .showErrorMessage(`DocsForge build failed${label}`, 'Show Output')
                  .then(() => this.logPanel.show());
                reject(new Error(`docsforge build exited with code ${code}`));
              }
            });
          });
        },
      );
    } catch {
      // User-facing messages were already shown at the failure site.
      // Belt-and-braces: every handler clears this, but a synchronous
      // spawn throw rejects before any handler exists.
      st.building = false;
    }
  }

  private clearStartSafetyTimeout(st: RootState) {
    if (st.startSafetyTimeout) {
      clearTimeout(st.startSafetyTimeout);
      st.startSafetyTimeout = null;
    }
  }

  dispose() {
    for (const st of this.servers.values()) {
      this.clearStartSafetyTimeout(st);
    }
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    for (const pidfile of this.watchedPidfiles) {
      fs.unwatchFile(pidfile);
    }
    this.watchedPidfiles.clear();
    this.editorWatch?.dispose();
    this.editorWatch = null;
    for (const root of [...this.servers.keys()]) {
      this.stop(/* silent */ true, root);
    }
    this.statusBarItem.dispose();
  }
}
