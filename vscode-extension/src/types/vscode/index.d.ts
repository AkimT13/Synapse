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
    iconPath?: ThemeIcon;
  }

  export class ThemeIcon {
    constructor(id: string);
    readonly id: string;
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

  export const Uri: {
    file(path: string): Uri;
  };

  export class Range {
    constructor(startLine: number, startCharacter: number, endLine: number, endCharacter: number);
  }

  export const ViewColumn: {
    Active: number;
    Beside: number;
    One: number;
    Two: number;
    Three: number;
  };

  export interface WebviewOptions {
    enableScripts?: boolean;
    retainContextWhenHidden?: boolean;
  }

  export interface Webview {
    html: string;
    options: WebviewOptions;
    onDidReceiveMessage: Event<unknown>;
  }

  export interface WebviewPanel extends Disposable {
    readonly webview: Webview;
    reveal(viewColumn?: number, preserveFocus?: boolean): void;
    onDidDispose: Event<void>;
  }

  export interface WebviewPanelSerializer {
    deserializeWebviewPanel(panel: WebviewPanel, state: unknown): Thenable<void>;
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
    onDidChangeActiveTextEditor(listener: (editor: TextEditor | undefined) => unknown): Disposable;
    createOutputChannel(name: string): OutputChannel;
    createStatusBarItem(alignment?: number, priority?: number): StatusBarItem;
    createWebviewPanel(
      viewType: string,
      title: string,
      showOptions: { viewColumn: number; preserveFocus?: boolean },
      options?: WebviewOptions,
    ): WebviewPanel;
    registerTreeDataProvider<T>(viewId: string, provider: TreeDataProvider<T>): Disposable;
    registerWebviewPanelSerializer(viewType: string, serializer: WebviewPanelSerializer): Disposable;
    showTextDocument(uri: Uri, options?: { selection?: Range; preview?: boolean }): Thenable<TextEditor>;
    showErrorMessage(message: string, ...items: string[]): Thenable<string | undefined>;
    showInformationMessage(message: string, ...items: string[]): Thenable<string | undefined>;
    showInputBox(options: { prompt: string; placeHolder?: string }): Thenable<string | undefined>;
  };

  export const workspace: {
    workspaceFolders: WorkspaceFolder[] | undefined;
    onDidChangeWorkspaceFolders(listener: (event: unknown) => unknown): Disposable;
    getWorkspaceFolder(uri: Uri): WorkspaceFolder | undefined;
  };

  export const commands: {
    registerCommand(command: string, callback: (...args: unknown[]) => unknown): Disposable;
    executeCommand(command: string, ...args: unknown[]): Thenable<unknown>;
  };
}
