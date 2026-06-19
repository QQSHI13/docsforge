import * as vscode from 'vscode';

export interface DocsForgeTreeItem {
  label: string;
  command: string;
  icon: string;
  tooltip: string;
  /** Context key expression, e.g. "!docsforge.serverRunning", "docsforge.buildRunning". */
  when?: string;
}

const ROOT_ITEMS: DocsForgeTreeItem[] = [
  {
    label: 'Start Server',
    command: 'docsforge.serve',
    icon: 'play',
    tooltip: 'Start the DocsForge development server',
    when: '!docsforge.serverRunning',
  },
  {
    label: 'Stop Server',
    command: 'docsforge.stop',
    icon: 'debug-stop',
    tooltip: 'Stop the DocsForge development server',
    when: 'docsforge.serverRunning',
  },
  {
    label: 'Build',
    command: 'docsforge.build',
    icon: 'gear',
    tooltip: 'Build the DocsForge documentation',
    when: '!docsforge.buildRunning',
  },
  {
    label: 'Stop Build',
    command: 'docsforge.stopBuild',
    icon: 'debug-stop',
    tooltip: 'Cancel the running build',
    when: 'docsforge.buildRunning',
  },
  {
    label: 'Open Preview',
    command: 'docsforge.openServer',
    icon: 'globe',
    tooltip: 'Open the DocsForge site in VS Code\'s built-in browser',
    when: 'docsforge.serverRunning',
  },
  {
    label: 'Initialize Project',
    command: 'docsforge.init',
    icon: 'new-folder',
    tooltip: 'Create a new DocsForge project',
  },
  {
    label: 'Open Docs',
    command: 'docsforge.openDocs',
    icon: 'preview',
    tooltip: 'Open the DocsForge documentation site',
  },
  {
    label: 'Search',
    command: 'docsforge.search',
    icon: 'search',
    tooltip: 'Search documentation (requires running server)',
  },
];

/** Evaluate a simple sidebar `when` expression against current context values. */
function evalWhen(
  expr: string | undefined,
  ctx: { serverRunning: boolean; buildRunning: boolean }
): boolean {
  if (!expr) { return true; }

  const trimmed = expr.trim();

  // Negation: "!docsforge.serverRunning"
  if (trimmed.startsWith('!')) {
    return !evalWhen(trimmed.slice(1), ctx);
  }

  // Resolve a bare context key
  if (trimmed === 'docsforge.serverRunning') return ctx.serverRunning;
  if (trimmed === 'docsforge.buildRunning') return ctx.buildRunning;

  // Unknown expression — show the item
  return true;
}

export class DocsForgeSidebarProvider implements vscode.TreeDataProvider<DocsForgeTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<
    DocsForgeTreeItem | undefined | null | void
  >();

  serverRunning = false;
  buildRunning = false;

  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: DocsForgeTreeItem): vscode.TreeItem {
    const item = new vscode.TreeItem(
      element.label,
      vscode.TreeItemCollapsibleState.None
    );
    item.command = {
      command: element.command,
      title: element.label,
    };
    item.iconPath = new vscode.ThemeIcon(element.icon);
    item.tooltip = element.tooltip;
    item.contextValue = element.command.slice('docsforge.'.length);
    return item;
  }

  getChildren(): Thenable<DocsForgeTreeItem[]> {
    return Promise.resolve(
      ROOT_ITEMS.filter((item) =>
        evalWhen(item.when, {
          serverRunning: this.serverRunning,
          buildRunning: this.buildRunning,
        })
      )
    );
  }
}
