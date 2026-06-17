import * as vscode from 'vscode';

export interface DocsForgeTreeItem {
  label: string;
  command: string;
  icon: string;
  tooltip: string;
  when?: string;
}

const ROOT_ITEMS: DocsForgeTreeItem[] = [
  {
    label: 'Start Server',
    command: 'docsforge.serve',
    icon: 'play',
    tooltip: 'Start the DocsForge development server',
    when: 'docsforge.serverRunning == false',
  },
  {
    label: 'Stop Server',
    command: 'docsforge.stop',
    icon: 'debug-stop',
    tooltip: 'Stop the DocsForge development server',
    when: 'docsforge.serverRunning == true',
  },
  {
    label: 'Build',
    command: 'docsforge.build',
    icon: 'gear',
    tooltip: 'Build the DocsForge documentation',
  },
  {
    label: 'Open in VS Code Browser',
    command: 'docsforge.openServer',
    icon: 'globe',
    tooltip: 'Open the DocsForge site in VS Code\'s Simple Browser',
  },
  {
    label: 'Initialize Project',
    command: 'docsforge.init',
    icon: 'new-folder',
    tooltip: 'Create a new DocsForge project',
  },
];

export class DocsForgeSidebarProvider implements vscode.TreeDataProvider<DocsForgeTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<
    DocsForgeTreeItem | undefined | null | void
  > = new vscode.EventEmitter<DocsForgeTreeItem | undefined | null | void>();

  serverRunning = false;

  readonly onDidChangeTreeData: vscode.Event<DocsForgeTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

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
    item.contextValue = element.command.replace('docsforge.', '');
    return item;
  }

  getChildren(): Thenable<DocsForgeTreeItem[]> {
    const items = ROOT_ITEMS.filter(item => {
      if (item.when === undefined) {
        return true;
      }
      const expected = item.when.includes('true');
      return expected === this.serverRunning;
    });
    return Promise.resolve(items);
  }
}
