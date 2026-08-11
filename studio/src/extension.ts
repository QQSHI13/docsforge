import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { ServerManager } from './serverManager';
import { InitWizard } from './initWizard';
import { DocsForgeSidebarProvider } from './sidebarProvider';
import { DocsForgeLogPanel } from './logPanel';
import { detectEnvironment, ensureDocsforge } from './environment';
import { DocsForgeDiagnostics } from './diagnostics';
import { registerProviders } from './providers';
import { registerRenameCommands, registerAutoRename } from './rename';

let serverManager: ServerManager;
let sidebarProvider: DocsForgeSidebarProvider;
let diagnostics: DocsForgeDiagnostics | undefined;

export function activate(context: vscode.ExtensionContext) {
  vscode.commands.executeCommand('setContext', 'docsforge.serverRunning', false);
  vscode.commands.executeCommand('setContext', 'docsforge.buildRunning', false);

  serverManager = new ServerManager();
  sidebarProvider = new DocsForgeSidebarProvider();

  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

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

  // Editor intelligence (symbols, folding, definition, hover, completion,
  // references) + diagnostics from the build's validation.json.
  if (workspaceRoot && ServerManager.hasConfig(workspaceRoot)) {
    diagnostics = new DocsForgeDiagnostics(workspaceRoot);
    context.subscriptions.push(diagnostics);
    registerProviders(context, workspaceRoot);
    registerRenameCommands(context, workspaceRoot);
    registerAutoRename(context, workspaceRoot);
    // Command used by the "Open link target" code action.
    context.subscriptions.push(
      vscode.commands.registerCommand('docsforge.openLinkTarget', async (arg?: { uri: string; dest: string }) => {
        if (!arg) {
          return;
        }
        const { resolveLinkTarget, docsDirFromConfig } = await import('./links.js');
        const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
        const srcUri = vscode.Uri.parse(arg.uri).fsPath.slice(docsDirAbs.length + 1)
          .split(path.sep).join('/');
        const resolved = resolveLinkTarget(docsDirAbs, srcUri, arg.dest.split('#')[0]);
        if (resolved && fs.existsSync(resolved.absPath)) {
          await vscode.window.showTextDocument(vscode.Uri.file(resolved.absPath));
        } else {
          vscode.window.showWarningMessage(`DocsForge: link target not found: ${arg.dest}`);
        }
      })
    );
    // Open the built page for the current document in the Simple Browser
    // (feature #1): resolves docs/<path>.md -> <serve-url>/<path>/.
    context.subscriptions.push(
      vscode.commands.registerCommand('docsforge.openPage', async () => {
        const { docsDirFromConfig } = await import('./links.js');
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
        const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
        const rel = path.relative(docsDirAbs, docPath);
        if (rel.startsWith('..') || path.isAbsolute(rel) || !rel.endsWith('.md')) {
          vscode.window.showWarningMessage('DocsForge: the document is not inside the docs directory.');
          return;
        }
        // Strip the locale suffix + .md, then map to the page URL.
        const base = rel.replace(/\.md$/, '').replace(/(\.[a-z]{2}(?:-[a-z]{2})?)$/, '');
        const url = new URL(base + '/', serverUrl.endsWith('/') ? serverUrl : serverUrl + '/');
        await vscode.commands.executeCommand('simpleBrowser.api.open', url);
      })
    );
    // Format-on-save (feature #2, opt-in via docsforge.formatOnSave).
    context.subscriptions.push(
      vscode.workspace.onWillSaveTextDocument(async (e) => {
        const enabled = vscode.workspace.getConfiguration('docsforge').get<boolean>('formatOnSave', false);
        if (!enabled || e.document.languageId !== 'markdown') {
          return;
        }
        const { formatMarkdown } = await import('./links.js');
        const text = e.document.getText();
        const formatted = formatMarkdown(text);
        if (formatted !== text) {
          const edit = new vscode.WorkspaceEdit();
          edit.replace(
            e.document.uri,
            new vscode.Range(0, 0, e.document.lineCount, 0),
            formatted,
          );
          e.waitUntil(vscode.workspace.applyEdit(edit));
        }
      })
    );
    // Refresh diagnostics right after a build finishes.
    ServerManager.onStateChange(() => {
      if (!serverManager.isBuilding()) {
        diagnostics?.refresh();
      }
    });
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.init', () => {
      if (!vscode.workspace.workspaceFolders?.length) {
        vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
        return;
      }
      InitWizard.run(serverManager).catch(err => vscode.window.showErrorMessage(`DocsForge init failed: ${err.message}`));
    }),

    vscode.commands.registerCommand('docsforge.serve', () => serverManager.start()),
    vscode.commands.registerCommand('docsforge.stop', () => serverManager.stop()),
    vscode.commands.registerCommand('docsforge.stopBuild', () => serverManager.stopBuild()),
    vscode.commands.registerCommand('docsforge.openServer', () => serverManager.openBrowser()),
    vscode.commands.registerCommand('docsforge.build', () => serverManager.build()),
    vscode.commands.registerCommand('docsforge.refreshSidebar', () => sidebarProvider.refresh()),
    vscode.commands.registerCommand('docsforge.openLog', () => DocsForgeLogPanel.get().show()),
    vscode.commands.registerCommand('docsforge.setupEnvironment', () => setupEnvironment()),
    vscode.commands.registerCommand('docsforge.refreshDiagnostics', () => diagnostics?.refresh()),
    vscode.commands.registerCommand('docsforge.openDocs', () => {
      vscode.commands.executeCommand('simpleBrowser.api.open', vscode.Uri.parse('https://qqshi13.github.io/docsforge/'));
    })
  );

  ServerManager.onStateChange(() => {
    sidebarProvider.serverRunning = serverManager.isRunning();
    sidebarProvider.buildRunning = serverManager.isBuilding();
    sidebarProvider.refresh();
  });

  if (workspaceRoot && ServerManager.hasConfig(workspaceRoot)) {
    vscode.window.showInformationMessage('DocsForge project detected. Start dev server?', 'Yes', 'Later')
      .then(choice => { if (choice === 'Yes') serverManager.start(); });
  }
}

export function deactivate() {
  serverManager?.dispose();
  diagnostics?.dispose();
}

/** Detect the Python environment and install docsforge if missing. */
async function setupEnvironment(): Promise<void> {
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
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
