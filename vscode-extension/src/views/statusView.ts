import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class StatusTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  async getChildren(): Promise<SynapseTreeItem[]> {
    const state = this.store.getSnapshot();
    const items: SynapseTreeItem[] = [];

    if (!state.workspaceRoot) {
      items.push(
        new SynapseTreeItem("No workspace", {
          description: "Open a folder to use Synapse",
          tooltip: "The extension runs Synapse commands from the active workspace root.",
        }),
      );
      return items;
    }

    if (state.doctor) {
      items.push(
        new SynapseTreeItem("Doctor", {
          description: state.doctor.ok ? "ok" : "issues",
          tooltip: state.doctor.workspace.config_path,
        }),
      );
      for (const check of state.doctor.checks) {
        items.push(
          new SynapseTreeItem(check.name, {
            description: check.ok ? "ok" : "fail",
            tooltip: [check.detail, check.fix].filter(Boolean).join("\n"),
          }),
        );
      }
    } else {
      items.push(
        new SynapseTreeItem("Doctor not run", {
          description: "Run Synapse: Doctor",
        }),
      );
    }

    if (state.services) {
      items.push(
        new SynapseTreeItem("Services", {
          description: state.services.running ? "running" : "not running",
          tooltip: state.services.compose_file,
        }),
      );
    }

    if (state.lastError) {
      items.push(
        new SynapseTreeItem("Last error", {
          description: "See details",
          tooltip: state.lastError,
        }),
      );
    }

    return items;
  }
}
