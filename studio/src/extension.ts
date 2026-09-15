import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { ServerManager } from './serverManager';
import { InitWizard } from './initWizard';
import { DocsForgeSidebarProvider } from './sidebarProvider';
import { DocsForgeLogPanel } from './logPanel';
import { detectEnvironment, ensureDocsforge } from './environment';
import { DocsForgeDiagnostics } from './diagnostics';
import { registerProviders, srcUriOf } from './providers';
import { registerRenameCommands, registerAutoRename } from './rename';
import { registerUpdateCommands } from './update';
import { docsDirFromConfig, resolveLinkTarget, stripLocaleSuffix } from './links';

let serverManager: ServerManager;
let sidebarProvider: DocsForgeSidebarProvider;
let allDiagnostics: DocsForgeDiagnostics[] = [];
const activatedRoots = new Set<string>();

function workspaceRoots(): string[] {
  return vscode.workspace.workspaceFolders?.map((f) => f.uri.fsPath) ?? [];
}

/** Find the workspace folder containing a file, preferring one with config. */
function rootForFsPath(fsPath: string): string | undefined {
  const folders = vscode.workspace.workspaceFolders ?? [];
  const containing = folders.filter((f) => {
    const p = f.uri.fsPath;
    return fsPath === p || fsPath.startsWith(p + path.sep);
  });
  if (!containing.length) {
    return undefined;
  }
  const withConfig = containing.find((f) => ServerManager.hasConfig(f.uri.fsPath));
  return (withConfig ?? containing[0]).uri.fsPath;
}

function docsContextFor(fsPath: string): { root: string; docsDirAbs: string } | null {
  const root = rootForFsPath(fsPath);
  if (!root || !ServerManager.hasConfig(root)) {
    return null;
  }
  return { root, docsDirAbs: path.join(root, docsDirFromConfig(root)) };
}

/** Lazily activate editor intelligence for a root once its config appears. */
function ensureProjectFeatures(
  context: vscode.ExtensionContext, root: string,
): boolean {
  if (activatedRoots.has(root) || !ServerManager.hasConfig(root)) {
    return activatedRoots.has(root);
  }
  activatedRoots.add(root);
  const diag = new DocsForgeDiagnostics(root);
  allDiagnostics.push(diag);
  context.subscriptions.push(diag);
  registerProviders(context, root);
  registerRenameCommands(context, root);
  registerAutoRename(context, root);
  return true;
}

export function activate(context: vscode.ExtensionContext) {
  vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
  vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', false);

  serverManager = new ServerManager();
  sidebarProvider = new DocsForgeSidebarProvider();

  // Register tree data provider for the sidebar view (declared in package.json)
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('docsforge.sidebar', sidebarProvider)
  );

  // Register the output log webview inside the DocsForge sidebar panel.
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'docsforge.output',
      DocsForgeLogPanel.get()
    )
  );

  // Always-available commands (guard for missing config inside the handler so
  // they work after `docsforge.init` in an empty folder without a reload).
  // Command used by the "Open link target" code action.
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.openLinkTarget', async (arg?: { uri: string; dest: string }) => {
      if (!arg) {
        return;
      }
      try {
        const srcFsPath = vscode.Uri.parse(arg.uri).fsPath;
        const ctx = docsContextFor(srcFsPath);
        if (!ctx) {
          vscode.window.showWarningMessage('DocsForge: no docsforge.yml found. Run "Initialize Project" first.');
          return;
        }
        const srcUri = srcUriOf(ctx.root, ctx.docsDirAbs, srcFsPath);
        if (!srcUri) {
          vscode.window.showWarningMessage('DocsForge: the document is not inside the docs directory.');
          return;
        }
        const resolved = resolveLinkTarget(ctx.docsDirAbs, srcUri, arg.dest.split('#')[0]);
        if (resolved && fs.existsSync(resolved.absPath)) {
          await vscode.window.showTextDocument(vscode.Uri.file(resolved.absPath));
        } else {
          vscode.window.showWarningMessage(`DocsForge: link target not found: ${arg.dest}`);
        }
      } catch (err) {
        vscode.window.showErrorMessage(`DocsForge: could not open link target (${(err as Error).message})`);
      }
    })
  );
  // Open the built page for the current document in the Simple Browser
  // (feature #1): resolves docs/<path>.md -> <serve-url>/<path>/.
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.openPage', async () => {
      try {
        const serverUrl = serverManager.serverUrl;
        if (!serverUrl) {
          vscode.window.showWarningMessage('DocsForge: start the server first (docsforge.serve).');
          return;
        }
        const editor = vscode.window.activeTextEditor;
        const docPath = editor?.document.uri.fsPath;
        if (!editor || !docPath) {
          return;
        }
        const ctx = docsContextFor(docPath);
        if (!ctx) {
          vscode.window.showWarningMessage('DocsForge: no docsforge.yml found. Run "Initialize Project" first.');
          return;
        }
        const rel = path.relative(ctx.docsDirAbs, docPath);
        if (rel.startsWith('..') || path.isAbsolute(rel) || !rel.endsWith('.md')) {
          vscode.window.showWarningMessage('DocsForge: the document is not inside the docs directory.');
          return;
        }
        // Canonical locale strip + .md removal, then map to the page URL.
        const srcUri = rel.split(path.sep).join('/');
        const stripped = stripLocaleSuffix(srcUri);
        let pagePath: string;
        if (stripped === 'index') {
          pagePath = '';
        } else if (stripped.endsWith('/index')) {
          pagePath = stripped.slice(0, -'index'.length);
        } else {
          pagePath = `${stripped}/`;
        }
        const base = serverUrl.endsWith('/') ? serverUrl : `${serverUrl}/`;
        const url = vscode.Uri.parse(base + encodeURI(pagePath));
        await vscode.commands.executeCommand('simpleBrowser.api.open', url);
      } catch (err) {
        vscode.window.showErrorMessage(`DocsForge: could not open built page (${(err as Error).message})`);
      }
    })
  );

  // Note: no onWillSaveTextDocument hook. Formatting is provided by the
  // DocumentFormattingEditProvider (Format Document / editor.formatOnSave);
  // a willSave handler that awaits a dynamic import before calling
  // waitUntil never fires, and applyEdit-inside-willSave risks save loops.

  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.init', () => {
      if (!vscode.workspace.workspaceFolders?.length) {
        vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
        return;
      }
      InitWizard.run(serverManager)
        .then(() => {
          // A fresh init creates the config after activate — lazily wire up
          // providers/diagnostics without requiring a window reload.
          for (const root of workspaceRoots()) {
            ensureProjectFeatures(context, root);
          }
        })
        .catch((err) => vscode.window.showErrorMessage(`DocsForge init failed: ${err.message}`));
    }),

    vscode.commands.registerCommand('docsforge.serve', () => serverManager.start()),
    vscode.commands.registerCommand('docsforge.stop', () => serverManager.stop()),
    vscode.commands.registerCommand('docsforge.stopBuild', () => serverManager.stopBuild()),
    vscode.commands.registerCommand('docsforge.openServer', () => serverManager.openBrowser()),
    vscode.commands.registerCommand('docsforge.build', () => serverManager.build()),
    vscode.commands.registerCommand('docsforge.refreshSidebar', () => sidebarProvider.refresh()),
    vscode.commands.registerCommand('docsforge.openLog', () => DocsForgeLogPanel.get().show()),
    vscode.commands.registerCommand('docsforge.setupEnvironment', () => setupEnvironment()),
    vscode.commands.registerCommand('docsforge.refreshDiagnostics', () => {
      if (!allDiagnostics.length) {
        vscode.window.showWarningMessage('DocsForge: no docsforge.yml found. Run "Initialize Project" first.');
        return;
      }
      for (const d of allDiagnostics) {
        d.refresh();
      }
    }),
    vscode.commands.registerCommand('docsforge.openDocs', () => {
      vscode.commands.executeCommand('simpleBrowser.api.open', vscode.Uri.parse('https://qqshi13.github.io/docsforge/'));
    }),
  );

  // Self-update: manual command + silent delayed startup check (notifies
  // only when an update is found). Findings feed the sidebar item badge.
  registerUpdateCommands(context, {
    onUpdateKnown: (summary) => {
      sidebarProvider.updateAvailable = summary;
      sidebarProvider.refresh();
    },
  });

  // Editor intelligence per workspace root that already has a config
  // (multi-root: every folder, not just workspaceFolders[0]).
  for (const root of workspaceRoots()) {
    ensureProjectFeatures(context, root);
  }

  // Lazily activate when a config file is created after startup (init path).
  const configWatcher = vscode.workspace.createFileSystemWatcher(
    '**/{docsforge,mkdocs}.{yml,yaml}'
  );
  configWatcher.onDidCreate((uri) => {
    const folder = vscode.workspace.getWorkspaceFolder(uri);
    if (folder) {
      ensureProjectFeatures(context, folder.uri.fsPath);
    }
  }, null, context.subscriptions);
  context.subscriptions.push(configWatcher);
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders((e) => {
      for (const folder of e.added) {
        ensureProjectFeatures(context, folder.uri.fsPath);
      }
    })
  );

  // Refresh diagnostics right after a build finishes.
  context.subscriptions.push(
    ServerManager.onStateChange(() => {
      if (!serverManager.isBuilding()) {
        for (const d of allDiagnostics) {
          d.refresh();
        }
      }
    })
  );

  context.subscriptions.push(
    ServerManager.onStateChange(() => {
      sidebarProvider.serverRunning = serverManager.isRunning();
      sidebarProvider.buildRunning = serverManager.isBuilding();
      sidebarProvider.refresh();
    })
  );

  const firstConfigured = workspaceRoots().find((r) => ServerManager.hasConfig(r));
  if (firstConfigured) {
    vscode.window.showInformationMessage('DocsForge project detected. Start dev server?', 'Yes', 'Later')
      .then(choice => { if (choice === 'Yes') serverManager.start(); });
  }
}

export function deactivate() {
  serverManager?.dispose();
  for (const d of allDiagnostics) {
    d.dispose();
  }
  allDiagnostics = [];
  activatedRoots.clear();
  ServerManager.disposeStateEmitter();
}

/** Detect the Python environment and install docsforge if missing. */
async function setupEnvironment(): Promise<void> {
  const activePath = vscode.window.activeTextEditor?.document.uri.fsPath;
  const workspaceRoot = (activePath && rootForFsPath(activePath)) ?? workspaceRoots()[0];
  if (!workspaceRoot) {
    vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
    return;
  }
  const logPanel = DocsForgeLogPanel.get();
  const state = await detectEnvironment(workspaceRoot);
  if (state.docsforgeVersion) {
    vscode.window.showInformationMessage(
      `DocsForge ${state.docsforgeVersion} is ready (${state.installKind}).`
    );
    return;
  }
  const python = await ensureDocsforge(workspaceRoot, state, (line) => logPanel.append(line));
  if (!python) {
    return;
  }
  const version = await detectEnvironment(workspaceRoot);
  vscode.window.showInformationMessage(
    `DocsForge ${version.docsforgeVersion ?? ''} installed successfully.`
  );
}
