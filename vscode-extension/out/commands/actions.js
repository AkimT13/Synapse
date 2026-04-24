"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveWorkspaceRoot = resolveWorkspaceRoot;
exports.getAbsoluteFilePath = getAbsoluteFilePath;
exports.createReviewCurrentFileHandler = createReviewCurrentFileHandler;
exports.createDriftCheckCurrentFileHandler = createDriftCheckCurrentFileHandler;
exports.createQuerySelectionHandler = createQuerySelectionHandler;
exports.createQueryFreeTextHandler = createQueryFreeTextHandler;
exports.createIngestWorkspaceHandler = createIngestWorkspaceHandler;
exports.createReindexWorkspaceHandler = createReindexWorkspaceHandler;
exports.createOpenServiceLogsHandler = createOpenServiceLogsHandler;
exports.createDoctorHandler = createDoctorHandler;
exports.runWithHandling = runWithHandling;
exports.renderFailureMessage = renderFailureMessage;
const node_path_1 = __importDefault(require("node:path"));
const SYNAPSE_VIEW_COMMAND = "workbench.view.extension.synapse";
const OPEN_OUTPUT_ACTION = "Open Output";
const RUN_DOCTOR_ACTION = "Run Doctor";
function resolveWorkspaceRoot(getWorkspaceFolder, target) {
    return getWorkspaceFolder(target)?.uri.fsPath;
}
function getAbsoluteFilePath(filePath) {
    return node_path_1.default.isAbsolute(filePath) ? filePath : node_path_1.default.resolve(filePath);
}
function resolveCommandWorkspaceRoot(context) {
    return resolveWorkspaceRoot(context.getWorkspaceFolder, context.getActiveEditor()?.document.uri) ?? resolveWorkspaceRoot(context.getWorkspaceFolder);
}
function createReviewCurrentFileHandler(context) {
    return async (resource) => {
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
function createDriftCheckCurrentFileHandler(context) {
    return async (resource) => {
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
function createQuerySelectionHandler(context) {
    return async () => {
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
function createQueryFreeTextHandler(context) {
    return async () => {
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
function createIngestWorkspaceHandler(context) {
    return async (resource) => {
        const workspaceRoot = resolveWorkspaceRoot(context.getWorkspaceFolder, resource ?? context.getActiveEditor()?.document.uri) ?? resolveWorkspaceRoot(context.getWorkspaceFolder);
        if (!workspaceRoot) {
            await context.window.showErrorMessage("Open a workspace before running Synapse ingest.");
            return;
        }
        await runWithHandling(context, workspaceRoot, async () => {
            const payload = await context.cli.ingestWorkspace(workspaceRoot);
            context.output.appendLine(`Synapse ingest completed for ${payload.workspace} (${payload.target}).`);
            for (const summary of payload.summaries) {
                context.output.appendLine(`${summary.kind}: files=${summary.files_processed}, stored=${summary.chunks_stored}, errors=${summary.errors.length}`);
            }
            context.output.show(true);
            await context.refreshStatus(workspaceRoot);
            await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
            await context.window.showInformationMessage("Synapse ingest completed.");
        });
    };
}
function createReindexWorkspaceHandler(context) {
    return async () => {
        const workspaceRoot = resolveCommandWorkspaceRoot(context);
        if (!workspaceRoot) {
            await context.window.showErrorMessage("Open a workspace before running Synapse reindex.");
            return;
        }
        await runWithHandling(context, workspaceRoot, async () => {
            const payload = await context.cli.reindexWorkspace(workspaceRoot);
            context.output.appendLine(`Synapse reindex completed for ${payload.workspace} (${payload.target}).`);
            context.output.show(true);
            await context.refreshStatus(workspaceRoot);
            await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
            await context.window.showInformationMessage("Synapse reindex completed.");
        });
    };
}
function createOpenServiceLogsHandler(context) {
    return async () => {
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
function createDoctorHandler(context) {
    return async () => {
        const workspaceRoot = resolveCommandWorkspaceRoot(context);
        if (!workspaceRoot) {
            await context.window.showErrorMessage("Open a workspace before running Synapse doctor.");
            return;
        }
        await context.refreshStatus(workspaceRoot);
        await context.commands.executeCommand(SYNAPSE_VIEW_COMMAND);
    };
}
async function runWithHandling(context, workspaceRoot, work) {
    try {
        await work();
    }
    catch (error) {
        const failure = error;
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
        const action = await context.window.showErrorMessage(detail, OPEN_OUTPUT_ACTION, ...shouldOfferDoctor(failure) ? [RUN_DOCTOR_ACTION] : []);
        if (action === OPEN_OUTPUT_ACTION) {
            context.output.show(true);
        }
        if (action === RUN_DOCTOR_ACTION) {
            await context.commands.executeCommand("synapse.doctor");
        }
    }
}
function shouldOfferDoctor(failure) {
    return failure.code !== "BINARY_MISSING";
}
function renderFailureMessage(failure) {
    const lines = [failure.message];
    if (failure.stderr?.trim()) {
        lines.push(failure.stderr.trim());
    }
    return lines.join("\n");
}
//# sourceMappingURL=actions.js.map