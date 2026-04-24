"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const cli_1 = require("./cli");
const actions_1 = require("./commands/actions");
const store_1 = require("./state/store");
const queryView_1 = require("./views/queryView");
const reviewView_1 = require("./views/reviewView");
const statusView_1 = require("./views/statusView");
async function activate(context) {
    const cli = new cli_1.SynapseCliRunner();
    const store = new store_1.SynapseStateStore();
    const output = vscode.window.createOutputChannel("Synapse");
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = "synapse.doctor";
    statusBarItem.text = "Synapse: idle";
    statusBarItem.tooltip = "Run Synapse doctor";
    statusBarItem.show();
    const refreshStatus = async (workspaceRoot) => {
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
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            store.update({
                workspaceRoot,
                lastError: message,
            });
            statusBarItem.text = "Synapse: Error";
            statusBarItem.tooltip = message;
        }
    };
    const refreshVisibleWorkspace = () => {
        const editorWorkspace = vscode.window.activeTextEditor
            ? vscode.workspace.getWorkspaceFolder(vscode.window.activeTextEditor.document.uri)
            : undefined;
        const targetWorkspace = editorWorkspace ?? vscode.workspace.workspaceFolders?.[0];
        if (targetWorkspace) {
            void refreshStatus(targetWorkspace.uri.fsPath);
        }
    };
    const actionContext = {
        cli,
        store,
        output,
        commands: vscode.commands,
        window: vscode.window,
        getActiveEditor: () => vscode.window.activeTextEditor,
        getWorkspaceFolder: (target) => target ? vscode.workspace.getWorkspaceFolder(target) : vscode.workspace.workspaceFolders?.[0],
        refreshStatus,
    };
    context.subscriptions.push(output, statusBarItem, vscode.window.registerTreeDataProvider("synapse.statusView", new statusView_1.StatusTreeDataProvider(store)), vscode.window.registerTreeDataProvider("synapse.reviewView", new reviewView_1.ReviewTreeDataProvider(store)), vscode.window.registerTreeDataProvider("synapse.queryView", new queryView_1.QueryTreeDataProvider(store)), vscode.commands.registerCommand("synapse.reviewCurrentFile", (...args) => (0, actions_1.createReviewCurrentFileHandler)(actionContext)(args[0])), vscode.commands.registerCommand("synapse.driftCheckCurrentFile", (...args) => (0, actions_1.createDriftCheckCurrentFileHandler)(actionContext)(args[0])), vscode.commands.registerCommand("synapse.querySelection", (0, actions_1.createQuerySelectionHandler)(actionContext)), vscode.commands.registerCommand("synapse.queryFreeText", (0, actions_1.createQueryFreeTextHandler)(actionContext)), vscode.commands.registerCommand("synapse.ingestWorkspace", (...args) => (0, actions_1.createIngestWorkspaceHandler)(actionContext)(args[0])), vscode.commands.registerCommand("synapse.reindexWorkspace", (0, actions_1.createReindexWorkspaceHandler)(actionContext)), vscode.commands.registerCommand("synapse.openServiceLogs", (0, actions_1.createOpenServiceLogsHandler)(actionContext)), vscode.commands.registerCommand("synapse.doctor", (0, actions_1.createDoctorHandler)(actionContext)), vscode.window.onDidChangeActiveTextEditor(() => {
        refreshVisibleWorkspace();
    }), vscode.workspace.onDidChangeWorkspaceFolders(() => {
        refreshVisibleWorkspace();
    }));
    refreshVisibleWorkspace();
}
function deactivate() { }
//# sourceMappingURL=extension.js.map