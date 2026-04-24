import * as vscode from "vscode";
import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class StatusTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  protected async getRootChildren(): Promise<SynapseTreeItem[]> {
    const state = this.store.getSnapshot();
    const items: SynapseTreeItem[] = [];

    if (!state.workspaceRoot) {
      items.push(
        new SynapseTreeItem("Open a workspace", {
          description: "Synapse needs a folder root",
          tooltip: [
            "The extension runs Synapse commands from the active workspace root.",
            "Open a project folder, then run `Synapse: Doctor`.",
          ].join("\n"),
          iconPath: new vscode.ThemeIcon("folder-opened"),
        }),
      );
      return items;
    }

    items.push(
      new SynapseTreeItem("Workspace", {
        description: state.workspaceRoot,
        tooltip: state.workspaceRoot,
        iconPath: new vscode.ThemeIcon("root-folder"),
      }),
    );

    items.push(state.doctor ? this.createDoctorItem(state.doctor) : this.createDoctorEmptyState());

    if (state.services) {
      items.push(
        new SynapseTreeItem("Services", {
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
            new SynapseTreeItem("Compose File", {
              description: state.services.compose_file,
              tooltip: state.services.compose_file,
              iconPath: new vscode.ThemeIcon("file"),
            }),
            new SynapseTreeItem("Command", {
              description: state.services.compose_command.join(" "),
              tooltip: state.services.compose_command.join(" "),
              iconPath: new vscode.ThemeIcon("terminal"),
            }),
          ],
        }),
      );
    } else {
      items.push(
        new SynapseTreeItem("Services", {
          description: "Status not loaded",
          tooltip: "Run `Synapse: Doctor` or `Synapse: Open Service Logs` if setup looks unhealthy.",
          iconPath: new vscode.ThemeIcon("question"),
        }),
      );
    }

    if (state.lastError) {
      items.push(
        new SynapseTreeItem("Last error", {
          description: summarize(state.lastError),
          tooltip: `${state.lastError}\n\nTry: synapse doctor`,
          iconPath: new vscode.ThemeIcon("error"),
          collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
          children: [
            new SynapseTreeItem("Suggested next step", {
              description: inferNextStep(state.lastError),
              tooltip: state.lastError,
              iconPath: new vscode.ThemeIcon("lightbulb"),
            }),
          ],
        }),
      );
    }

    return items;
  }

  private createDoctorItem(doctor: NonNullable<ReturnType<SynapseStateStore["getSnapshot"]>["doctor"]>): SynapseTreeItem {
    const failingChecks = doctor.checks.filter((check) => !check.ok);
    const checkChildren = doctor.checks.map(
      (check) =>
        new SynapseTreeItem(check.name, {
          description: check.ok ? "OK" : "Needs attention",
          tooltip: [check.detail, check.fix].filter(Boolean).join("\n\n"),
          iconPath: new vscode.ThemeIcon(check.ok ? "pass" : "warning"),
        }),
    );

    if (doctor.suggested_fixes.length > 0) {
      checkChildren.push(
        new SynapseTreeItem("Suggested fixes", {
          description: `${doctor.suggested_fixes.length} step${doctor.suggested_fixes.length === 1 ? "" : "s"}`,
          tooltip: doctor.suggested_fixes.join("\n"),
          iconPath: new vscode.ThemeIcon("lightbulb"),
          collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
          children: doctor.suggested_fixes.map(
            (fix) =>
              new SynapseTreeItem(fix, {
                tooltip: fix,
                iconPath: new vscode.ThemeIcon("chevron-right"),
              }),
          ),
        }),
      );
    }

    return new SynapseTreeItem("Doctor", {
      description: doctor.ok ? "Healthy" : `${failingChecks.length} issue${failingChecks.length === 1 ? "" : "s"}`,
      tooltip: doctor.workspace.config_path,
      iconPath: new vscode.ThemeIcon(doctor.ok ? "shield" : "warning"),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children: [
        new SynapseTreeItem("Repo Root", {
          description: doctor.workspace.repo_root,
          tooltip: doctor.workspace.repo_root,
          iconPath: new vscode.ThemeIcon("repo"),
        }),
        new SynapseTreeItem("Config", {
          description: doctor.workspace.config_path,
          tooltip: doctor.workspace.config_path,
          iconPath: new vscode.ThemeIcon("settings-gear"),
        }),
        ...checkChildren,
      ],
    });
  }

  private createDoctorEmptyState(): SynapseTreeItem {
    return new SynapseTreeItem("Doctor", {
      description: "Not run yet",
      tooltip: "Run `Synapse: Doctor` to validate the workspace before a demo.",
      iconPath: new vscode.ThemeIcon("stethoscope"),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children: [
        new SynapseTreeItem("Recommended first step", {
          description: "Run `Synapse: Doctor`",
          tooltip: "This checks config, services, and workspace wiring.",
          iconPath: new vscode.ThemeIcon("play"),
        }),
      ],
    });
  }
}

function summarize(value: string, max = 60): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function inferNextStep(error: string): string {
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
