declare module "vscode" {
  export type Thenable<T> = PromiseLike<T>;

  export interface Disposable {
    dispose(): unknown;
  }

  export interface Event<T> {
    (listener: (e: T) => unknown): Disposable;
  }

  export class EventEmitter<T> implements Disposable {
    event: Event<T>;
    fire(data?: T): void;
    dispose(): void;
  }

  export const TreeItemCollapsibleState: {
    None: number;
    Collapsed: number;
    Expanded: number;
  };

  export class TreeItem {
    constructor(label: string, collapsibleState?: number);
    label: string;
    description?: string;
    tooltip?: string;
    contextValue?: string;
  }

  export interface TreeDataProvider<T> {
    onDidChangeTreeData?: Event<T | undefined | null | void>;
    getTreeItem(element: T): TreeItem | Thenable<TreeItem>;
    getChildren(element?: T): ProviderResult<T[]>;
  }

  export type ProviderResult<T> = T | undefined | null | Thenable<T | undefined | null>;

  export interface Uri {
    fsPath: string;
  }

  export interface WorkspaceFolder {
    uri: Uri;
    name: string;
  }

  export interface TextDocument {
    uri: Uri;
    getText(selection?: Selection): string;
  }

  export interface Selection {
    isEmpty: boolean;
  }

  export interface TextEditor {
    document: TextDocument;
    selection: Selection;
  }

  export interface ExtensionContext {
    subscriptions: Disposable[];
  }

  export const StatusBarAlignment: {
    Left: number;
    Right: number;
  };

  export interface OutputChannel extends Disposable {
    appendLine(value: string): void;
    show(preserveFocus?: boolean): void;
  }

  export interface StatusBarItem extends Disposable {
    text: string;
    tooltip?: string;
    command?: string;
    show(): void;
  }

  export const window: {
    activeTextEditor: TextEditor | undefined;
    createOutputChannel(name: string): OutputChannel;
    createStatusBarItem(alignment?: number, priority?: number): StatusBarItem;
    registerTreeDataProvider<T>(viewId: string, provider: TreeDataProvider<T>): Disposable;
    showErrorMessage(message: string, ...items: string[]): Thenable<string | undefined>;
    showInformationMessage(message: string, ...items: string[]): Thenable<string | undefined>;
    showInputBox(options: { prompt: string; placeHolder?: string }): Thenable<string | undefined>;
  };

  export const workspace: {
    workspaceFolders: WorkspaceFolder[] | undefined;
    getWorkspaceFolder(uri: Uri): WorkspaceFolder | undefined;
  };

  export const commands: {
    registerCommand(command: string, callback: (...args: unknown[]) => unknown): Disposable;
    executeCommand(command: string, ...args: unknown[]): Thenable<unknown>;
  };
}
