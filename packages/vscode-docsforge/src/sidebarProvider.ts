import * as vscode from 'vscode';

export interface DocsForgeTreeItem {
  label: string;
  command: string;
  icon: string;
  tooltip: string;
  /** Context key expression: item is shown when this evaluates to true.
   *  Currently supports: "docsforge.serverRunning" (true/false). */
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
];

/** Evaluate a simple sidebar `when` expression against the current state. */
function evalWhen(expr: string | undefined, serverRunning: boolean): boolean {
  if (!expr) { return true; }

  const trimmed = expr.trim();

  // Negation: "!docsforge.serverRunning"
  if (trimmed.startsWith('!')) {
    const inner = trimmed.slice(1).trim();
    return !evalWhen(inner, serverRunning);
  }

  // Equality: "docsforge.serverRunning == true" / "docsforge.serverRunning == false"
  const eqMatch = trimmed.match(/^docsforge\.serverRunning\s*==\s*(true|false)\s*$/);
  if (eqMatch) {
    const expected = eqMatch[1] === 'true';
    return serverRunning === expected;
  }

  // Bare context key: "docsforge.serverRunning"
  if (trimmed === 'docsforge.serverRunning') {
    return serverRunning;
  }

  // Unknown expression — show the item
  return true;
}

export class DocsForgeSidebarProvider implements vscode.TreeDataProvider<DocsForgeTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<
    DocsForgeTreeItem | undefined | null | void
  >();

  serverRunning = false;

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
    const running = this.serverRunning;
    return Promise.resolve(
      ROOT_ITEMS.filter((item) => evalWhen(item.when, running))
    );
  }
}
