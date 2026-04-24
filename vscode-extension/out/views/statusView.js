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
exports.StatusTreeDataProvider = void 0;
const vscode = __importStar(require("vscode"));
const tree_1 = require("./tree");
class StatusTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getRootChildren() {
        const state = this.store.getSnapshot();
        const items = [];
        if (!state.workspaceRoot) {
            items.push(new tree_1.SynapseTreeItem("Open a workspace", {
                description: "Synapse needs a folder root",
                tooltip: [
                    "The extension runs Synapse commands from the active workspace root.",
                    "Open a project folder, then run `Synapse: Doctor`.",
                ].join("\n"),
                iconPath: new vscode.ThemeIcon("folder-opened"),
            }));
            return items;
        }
        items.push(new tree_1.SynapseTreeItem("Workspace", {
            description: state.workspaceRoot,
            tooltip: state.workspaceRoot,
            iconPath: new vscode.ThemeIcon("root-folder"),
        }));
        items.push(state.doctor ? this.createDoctorItem(state.doctor) : this.createDoctorEmptyState());
        if (state.services) {
            items.push(new tree_1.SynapseTreeItem("Services", {
                description: state.services.running ? "Running" : "Stopped",
                tooltip: [
                    state.services.compose_file,
                    state.services.stderr,
                    state.services.stdout,
                ]
                    .filter(Boolean)
                    .join("\n\n"),
                iconPath: new vscode.ThemeIcon(state.services.running ? "vm-active" : "warning"),
                collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
                children: [
                    new tree_1.SynapseTreeItem("Compose File", {
                        description: state.services.compose_file,
                        tooltip: state.services.compose_file,
                        iconPath: new vscode.ThemeIcon("file"),
                    }),
                    new tree_1.SynapseTreeItem("Command", {
                        description: state.services.compose_command.join(" "),
                        tooltip: state.services.compose_command.join(" "),
                        iconPath: new vscode.ThemeIcon("terminal"),
                    }),
                ],
            }));
        }
        else {
            items.push(new tree_1.SynapseTreeItem("Services", {
                description: "Status not loaded",
                tooltip: "Run `Synapse: Doctor` or `Synapse: Open Service Logs` if setup looks unhealthy.",
                iconPath: new vscode.ThemeIcon("question"),
            }));
        }
        if (state.lastError) {
            items.push(new tree_1.SynapseTreeItem("Last error", {
                description: summarize(state.lastError),
                tooltip: `${state.lastError}\n\nTry: synapse doctor`,
                iconPath: new vscode.ThemeIcon("error"),
                collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
                children: [
                    new tree_1.SynapseTreeItem("Suggested next step", {
                        description: inferNextStep(state.lastError),
                        tooltip: state.lastError,
                        iconPath: new vscode.ThemeIcon("lightbulb"),
                    }),
                ],
            }));
        }
        return items;
    }
    createDoctorItem(doctor) {
        const failingChecks = doctor.checks.filter((check) => !check.ok);
        const checkChildren = doctor.checks.map((check) => new tree_1.SynapseTreeItem(check.name, {
            description: check.ok ? "OK" : "Needs attention",
            tooltip: [check.detail, check.fix].filter(Boolean).join("\n\n"),
            iconPath: new vscode.ThemeIcon(check.ok ? "pass" : "warning"),
        }));
        if (doctor.suggested_fixes.length > 0) {
            checkChildren.push(new tree_1.SynapseTreeItem("Suggested fixes", {
                description: `${doctor.suggested_fixes.length} step${doctor.suggested_fixes.length === 1 ? "" : "s"}`,
                tooltip: doctor.suggested_fixes.join("\n"),
                iconPath: new vscode.ThemeIcon("lightbulb"),
                collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
                children: doctor.suggested_fixes.map((fix) => new tree_1.SynapseTreeItem(fix, {
                    tooltip: fix,
                    iconPath: new vscode.ThemeIcon("chevron-right"),
                })),
            }));
        }
        return new tree_1.SynapseTreeItem("Doctor", {
            description: doctor.ok ? "Healthy" : `${failingChecks.length} issue${failingChecks.length === 1 ? "" : "s"}`,
            tooltip: doctor.workspace.config_path,
            iconPath: new vscode.ThemeIcon(doctor.ok ? "shield" : "warning"),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: [
                new tree_1.SynapseTreeItem("Repo Root", {
                    description: doctor.workspace.repo_root,
                    tooltip: doctor.workspace.repo_root,
                    iconPath: new vscode.ThemeIcon("repo"),
                }),
                new tree_1.SynapseTreeItem("Config", {
                    description: doctor.workspace.config_path,
                    tooltip: doctor.workspace.config_path,
                    iconPath: new vscode.ThemeIcon("settings-gear"),
                }),
                ...checkChildren,
            ],
        });
    }
    createDoctorEmptyState() {
        return new tree_1.SynapseTreeItem("Doctor", {
            description: "Not run yet",
            tooltip: "Run `Synapse: Doctor` to validate the workspace before a demo.",
            iconPath: new vscode.ThemeIcon("stethoscope"),
            collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
            children: [
                new tree_1.SynapseTreeItem("Recommended first step", {
                    description: "Run `Synapse: Doctor`",
                    tooltip: "This checks config, services, and workspace wiring.",
                    iconPath: new vscode.ThemeIcon("play"),
                }),
            ],
        });
    }
}
exports.StatusTreeDataProvider = StatusTreeDataProvider;
function summarize(value, max = 60) {
    return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}
function inferNextStep(error) {
    const normalized = error.toLowerCase();
    if (normalized.includes("config")) {
        return "Run `synapse init`";
    }
    if (normalized.includes("service") || normalized.includes("actian")) {
        return "Run `synapse services up`";
    }
    if (normalized.includes("synapse")) {
        return "Run `synapse doctor`";
    }
    return "Re-run `Synapse: Doctor`";
}
//# sourceMappingURL=statusView.js.map