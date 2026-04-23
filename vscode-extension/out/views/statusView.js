"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StatusTreeDataProvider = void 0;
const tree_1 = require("./tree");
class StatusTreeDataProvider extends tree_1.BaseTreeDataProvider {
    store;
    constructor(store) {
        super();
        this.store = store;
        this.store.subscribe(() => this.refresh());
    }
    async getChildren() {
        const state = this.store.getSnapshot();
        const items = [];
        if (!state.workspaceRoot) {
            items.push(new tree_1.SynapseTreeItem("No workspace", {
                description: "Open a folder to use Synapse",
                tooltip: "The extension runs Synapse commands from the active workspace root.",
            }));
            return items;
        }
        if (state.doctor) {
            items.push(new tree_1.SynapseTreeItem("Doctor", {
                description: state.doctor.ok ? "ok" : "issues",
                tooltip: state.doctor.workspace.config_path,
            }));
            for (const check of state.doctor.checks) {
                items.push(new tree_1.SynapseTreeItem(check.name, {
                    description: check.ok ? "ok" : "fail",
                    tooltip: [check.detail, check.fix].filter(Boolean).join("\n"),
                }));
            }
        }
        else {
            items.push(new tree_1.SynapseTreeItem("Doctor not run", {
                description: "Run Synapse: Doctor",
            }));
        }
        if (state.services) {
            items.push(new tree_1.SynapseTreeItem("Services", {
                description: state.services.running ? "running" : "not running",
                tooltip: state.services.compose_file,
            }));
        }
        if (state.lastError) {
            items.push(new tree_1.SynapseTreeItem("Last error", {
                description: "See details",
                tooltip: state.lastError,
            }));
        }
        return items;
    }
}
exports.StatusTreeDataProvider = StatusTreeDataProvider;
//# sourceMappingURL=statusView.js.map