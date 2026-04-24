import * as vscode from "vscode";

export class SynapseTreeItem extends vscode.TreeItem {
  readonly children: SynapseTreeItem[];

  constructor(
    label: string,
    {
      description,
      tooltip,
      collapsibleState = vscode.TreeItemCollapsibleState.None,
      contextValue,
      iconPath,
      children = [],
    }: {
      description?: string;
      tooltip?: string;
      collapsibleState?: number;
      contextValue?: string;
      iconPath?: vscode.ThemeIcon;
      children?: SynapseTreeItem[];
    } = {},
  ) {
    super(label, collapsibleState);
    this.description = description;
    this.tooltip = tooltip;
    this.contextValue = contextValue;
    this.iconPath = iconPath;
    this.children = children;
  }
}

export abstract class BaseTreeDataProvider
  implements vscode.TreeDataProvider<SynapseTreeItem>
{
  private readonly emitter = new vscode.EventEmitter<SynapseTreeItem | undefined | null | void>();

  readonly onDidChangeTreeData = this.emitter.event;

  refresh(): void {
    this.emitter.fire();
  }

  getTreeItem(element: SynapseTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: SynapseTreeItem): Promise<SynapseTreeItem[]> {
    if (element) {
      return element.children;
    }
    return this.getRootChildren();
  }

  protected abstract getRootChildren(): Promise<SynapseTreeItem[]>;
}
