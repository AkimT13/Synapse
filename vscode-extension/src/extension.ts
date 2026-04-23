import * as vscode from "vscode";

import { SynapseCliRunner } from "./cli";
import {
  createDoctorHandler,
  createDriftCheckCurrentFileHandler,
  createIngestWorkspaceHandler,
  createOpenServiceLogsHandler,
  createQueryFreeTextHandler,
  createQuerySelectionHandler,
  createReindexWorkspaceHandler,
  createReviewCurrentFileHandler,
} from "./commands/actions";
import { SynapseStateStore } from "./state/store";
import { QueryTreeDataProvider } from "./views/queryView";
import { ReviewTreeDataProvider } from "./views/reviewView";
import { StatusTreeDataProvider } from "./views/statusView";

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const cli = new SynapseCliRunner();
  const store = new SynapseStateStore();
  const output = vscode.window.createOutputChannel("Synapse");
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.command = "synapse.doctor";
  statusBarItem.text = "Synapse: idle";
  statusBarItem.tooltip = "Run Synapse doctor";
  statusBarItem.show();

  const refreshStatus = async (workspaceRoot: string): Promise<void> => {
    try {
      const [doctor, services] = await Promise.all([
        cli.doctor(workspaceRoot),
        cli.servicesStatus(workspaceRoot),
      ]);
      store.update({
        workspaceRoot,
        doctor,
        services,
        lastError: undefined,
      });
      statusBarItem.text = doctor.ok
        ? `Synapse: Ready${services.running ? "" : " (services down)"}`
        : "Synapse: Issues";
      statusBarItem.tooltip = doctor.ok
        ? `Workspace ${doctor.workspace.name}`
        : doctor.suggested_fixes.join("\n");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      store.update({
        workspaceRoot,
        lastError: message,
      });
      statusBarItem.text = "Synapse: Error";
      statusBarItem.tooltip = message;
    }
  };

  const actionContext = {
    cli,
    store,
    output,
    commands: vscode.commands,
    window: vscode.window,
    getActiveEditor: () => vscode.window.activeTextEditor,
    getWorkspaceFolder: (target?: vscode.Uri) =>
      target ? vscode.workspace.getWorkspaceFolder(target) : vscode.workspace.workspaceFolders?.[0],
    refreshStatus,
  };

  context.subscriptions.push(
    output,
    statusBarItem,
    vscode.window.registerTreeDataProvider("synapse.statusView", new StatusTreeDataProvider(store)),
    vscode.window.registerTreeDataProvider("synapse.reviewView", new ReviewTreeDataProvider(store)),
    vscode.window.registerTreeDataProvider("synapse.queryView", new QueryTreeDataProvider(store)),
    vscode.commands.registerCommand(
      "synapse.reviewCurrentFile",
      (...args: unknown[]) =>
        createReviewCurrentFileHandler(actionContext)(args[0] as vscode.Uri | undefined),
    ),
    vscode.commands.registerCommand(
      "synapse.driftCheckCurrentFile",
      (...args: unknown[]) =>
        createDriftCheckCurrentFileHandler(actionContext)(args[0] as vscode.Uri | undefined),
    ),
    vscode.commands.registerCommand(
      "synapse.querySelection",
      createQuerySelectionHandler(actionContext),
    ),
    vscode.commands.registerCommand(
      "synapse.queryFreeText",
      createQueryFreeTextHandler(actionContext),
    ),
    vscode.commands.registerCommand(
      "synapse.ingestWorkspace",
      (...args: unknown[]) =>
        createIngestWorkspaceHandler(actionContext)(args[0] as vscode.Uri | undefined),
    ),
    vscode.commands.registerCommand(
      "synapse.reindexWorkspace",
      createReindexWorkspaceHandler(actionContext),
    ),
    vscode.commands.registerCommand(
      "synapse.openServiceLogs",
      createOpenServiceLogsHandler(actionContext),
    ),
    vscode.commands.registerCommand(
      "synapse.doctor",
      createDoctorHandler(actionContext),
    ),
  );

  const firstWorkspace = vscode.workspace.workspaceFolders?.[0];
  if (firstWorkspace) {
    void refreshStatus(firstWorkspace.uri.fsPath);
  }
}

export function deactivate(): void {}
