import path from "node:path";

import { SynapseCliRunner } from "../cli";
import type { SynapseStateStore } from "../state/store";
import type { CliFailure } from "../types/models";

export interface WindowLike {
  showErrorMessage(message: string, ...items: string[]): PromiseLike<string | undefined>;
  showInformationMessage(message: string, ...items: string[]): PromiseLike<string | undefined>;
  showInputBox(options: { prompt: string; placeHolder?: string }): PromiseLike<string | undefined>;
}

export interface CommandsLike {
  executeCommand(command: string, ...args: unknown[]): PromiseLike<unknown>;
}

export interface OutputLike {
  appendLine(value: string): void;
  show(preserveFocus?: boolean): void;
}

export interface UriLike {
  fsPath: string;
}

export interface SelectionLike {
  isEmpty: boolean;
}

export interface TextDocumentLike {
  uri: UriLike;
  getText(selection?: SelectionLike): string;
}

export interface TextEditorLike {
  document: TextDocumentLike;
  selection: SelectionLike;
}

export interface WorkspaceFolderLike {
  uri: UriLike;
  name?: string;
}

export interface ActionContext {
  cli: SynapseCliRunner;
  store: SynapseStateStore;
  window: WindowLike;
  commands: CommandsLike;
  output: OutputLike;
  getActiveEditor(): TextEditorLike | undefined;
  getWorkspaceFolder(target?: UriLike): WorkspaceFolderLike | undefined;
  refreshStatus(workspaceRoot: string): Promise<void>;
}

const SYNAPSE_VIEW_COMMAND = "workbench.view.extension.synapse";
const OPEN_OUTPUT_ACTION = "Open Output";
const RUN_DOCTOR_ACTION = "Run Doctor";

export function resolveWorkspaceRoot(
  getWorkspaceFolder: (target?: UriLike) => WorkspaceFolderLike | undefined,
  target?: UriLike,
): string | undefined {
  return getWorkspaceFolder(target)?.uri.fsPath;
}

export function getAbsoluteFilePath(filePath: string): string {
  return path.isAbsolute(filePath) ? filePath : path.resolve(filePath);
}

function resolveCommandWorkspaceRoot(context: ActionContext): string | undefined {
  return resolveWorkspaceRoot(
    context.getWorkspaceFolder,
    context.getActiveEditor()?.document.uri,
  ) ?? resolveWorkspaceRoot(context.getWorkspaceFolder);
}

export function createReviewCurrentFileHandler(context: ActionContext) {
  return async (resource?: UriLike): Promise<void> => {
    const editor = resource ? undefined : context.getActiveEditor();
    const targetUri = resource ?? editor?.document.uri;
    if (!targetUri) {
      await context.window.showErrorMessage("Open a local file before running Synapse review.");
      return;
    }
    const workspaceRoot = resolveWorkspaceRoot(context.getWorkspaceFolder, targetUri);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("The selected file is outside the active workspace.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.reviewFile(workspaceRoot, targetUri.fsPath);
      context.store.update({
        workspaceRoot,
        review: payload,
        drift: undefined,
        lastError: undefined,
      });
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    });
  };
}

export function createDriftCheckCurrentFileHandler(context: ActionContext) {
  return async (resource?: UriLike): Promise<void> => {
    const editor = resource ? undefined : context.getActiveEditor();
    const targetUri = resource ?? editor?.document.uri;
    if (!targetUri) {
      await context.window.showErrorMessage("Open a local file before running Synapse drift check.");
      return;
    }
    const workspaceRoot = resolveWorkspaceRoot(context.getWorkspaceFolder, targetUri);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("The selected file is outside the active workspace.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.driftCheckFile(workspaceRoot, targetUri.fsPath);
      context.store.update({
        workspaceRoot,
        drift: payload,
        review: undefined,
        lastError: undefined,
      });
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    });
  };
}

export function createQuerySelectionHandler(context: ActionContext) {
  return async (): Promise<void> => {
    const editor = context.getActiveEditor();
    if (!editor || editor.selection.isEmpty) {
      await context.window.showErrorMessage("Select code before running Synapse query.");
      return;
    }
    const workspaceRoot = resolveWorkspaceRoot(context.getWorkspaceFolder, editor.document.uri);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("The selected code is outside the active workspace.");
      return;
    }
    const text = editor.document.getText(editor.selection).trim();
    if (!text) {
      await context.window.showErrorMessage("The current selection is empty.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.queryCode(workspaceRoot, text);
      context.store.update({
        workspaceRoot,
        query: payload,
        lastError: undefined,
      });
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    });
  };
}

export function createQueryFreeTextHandler(context: ActionContext) {
  return async (): Promise<void> => {
    const workspaceRoot = resolveCommandWorkspaceRoot(context);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("Open a workspace before running Synapse query.");
      return;
    }
    const text = await context.window.showInputBox({
      prompt: "Ask a domain question for Synapse",
      placeHolder: "What constraint governs this file?",
    });
    if (!text?.trim()) {
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.queryFree(workspaceRoot, text.trim());
      context.store.update({
        workspaceRoot,
        query: payload,
        lastError: undefined,
      });
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    });
  };
}

export function createIngestWorkspaceHandler(context: ActionContext) {
  return async (resource?: UriLike): Promise<void> => {
    const workspaceRoot = resolveWorkspaceRoot(
      context.getWorkspaceFolder,
      resource ?? context.getActiveEditor()?.document.uri,
    ) ?? resolveWorkspaceRoot(context.getWorkspaceFolder);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("Open a workspace before running Synapse ingest.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.ingestWorkspace(workspaceRoot);
      context.output.appendLine(
        `Synapse ingest completed for ${payload.workspace} (${payload.target}).`,
      );
      for (const summary of payload.summaries) {
        context.output.appendLine(
          `${summary.kind}: files=${summary.files_processed}, stored=${summary.chunks_stored}, errors=${summary.errors.length}`,
        );
      }
      context.output.show(true);
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
      await context.window.showInformationMessage("Synapse ingest completed.");
    });
  };
}

export function createReindexWorkspaceHandler(context: ActionContext) {
  return async (): Promise<void> => {
    const workspaceRoot = resolveCommandWorkspaceRoot(context);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("Open a workspace before running Synapse reindex.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const payload = await context.cli.reindexWorkspace(workspaceRoot);
      context.output.appendLine(
        `Synapse reindex completed for ${payload.workspace} (${payload.target}).`,
      );
      context.output.show(true);
      await context.refreshStatus(workspaceRoot);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
      await context.window.showInformationMessage("Synapse reindex completed.");
    });
  };
}

export function createOpenServiceLogsHandler(context: ActionContext) {
  return async (): Promise<void> => {
    const workspaceRoot = resolveCommandWorkspaceRoot(context);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("Open a workspace before viewing Synapse logs.");
      return;
    }
    await runWithHandling(context, workspaceRoot, async () => {
      const logs = await context.cli.openServiceLogs(workspaceRoot);
      context.output.appendLine(logs || "No service log output.");
      context.output.show(false);
      await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    });
  };
}

export function createDoctorHandler(context: ActionContext) {
  return async (): Promise<void> => {
    const workspaceRoot = resolveCommandWorkspaceRoot(context);
    if (!workspaceRoot) {
      await context.window.showErrorMessage("Open a workspace before running Synapse doctor.");
      return;
    }
    await context.refreshStatus(workspaceRoot);
    await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
  };
}

export async function runWithHandling(
  context: ActionContext,
  workspaceRoot: string,
  work: () => Promise<void>,
): Promise<void> {
  try {
    await work();
  } catch (error) {
    const failure = error as CliFailure;
    const detail = renderFailureMessage(failure);
    context.store.update({
      workspaceRoot,
      lastError: detail,
    });
    context.output.appendLine(detail);
    if (failure.command) {
      context.output.appendLine(`Command: ${failure.command.join(" ")}`);
    }
    for (const fix of failure.suggestedFixes ?? []) {
      context.output.appendLine(`Suggestion: ${fix}`);
    }
    context.output.show(true);
    const action = await context.window.showErrorMessage(
      detail,
      OPEN_OUTPUT_ACTION,
      ...shouldOfferDoctor(failure) ? [RUN_DOCTOR_ACTION] : [],
    );
    if (action === OPEN_OUTPUT_ACTION) {
      context.output.show(true);
    }
    if (action === RUN_DOCTOR_ACTION) {
      await context.commands.executeCommand("synapse.doctor");
    }
  }
}

function shouldOfferDoctor(failure: CliFailure): boolean {
  return failure.code !== "BINARY_MISSING";
}

export function renderFailureMessage(failure: CliFailure): string {
  const lines = [failure.message];
  if (failure.stderr?.trim()) {
    lines.push(failure.stderr.trim());
  }
  return lines.join("\n");
}
