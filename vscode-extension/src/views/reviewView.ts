import * as vscode from "vscode";
import * as path from "node:path";
import type {
  DriftCheckEntry,
  DriftPayload,
  ReviewContextEntry,
  ReviewPayload,
  SourceResult,
} from "../types/models";
import type { SynapseStateStore } from "../state/store";
import { BaseTreeDataProvider, SynapseTreeItem } from "./tree";

export class ReviewTreeDataProvider extends BaseTreeDataProvider {
  constructor(private readonly store: SynapseStateStore) {
    super();
    this.store.subscribe(() => this.refresh());
  }

  protected async getRootChildren(): Promise<SynapseTreeItem[]> {
    const state = this.store.getSnapshot();
    const review = state.review;
    const drift = state.drift;

    if (!review && !drift) {
      return [
        new SynapseTreeItem("Review a file", {
          description: "No results yet",
          tooltip: [
            "Use `Synapse: Review Current File` for the full review.",
            "Use `Synapse: Drift Check Current File` for violations only.",
          ].join("\n"),
          iconPath: new vscode.ThemeIcon("search"),
          collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
          children: [
            new SynapseTreeItem("Recommended", {
              description: "Run Review Current File",
              tooltip: "This gives drift findings plus supporting context.",
              iconPath: new vscode.ThemeIcon("play"),
            }),
          ],
        }),
      ];
    }

    if (review) {
      return buildReviewTree(review);
    }

    return buildDriftTree(drift!);
  }
}

function buildReviewTree(review: ReviewPayload): SynapseTreeItem[] {
  const driftCount = review.drift.length;
  const contextCount = review.context.length;

  return [
    new SynapseTreeItem(path.basename(review.target), {
      description: titleCase(review.drift_status),
      tooltip: `${review.target}\nWorkspace: ${review.workspace}`,
      iconPath: statusIcon(review.drift_status),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children: [
        new SynapseTreeItem("File", {
          description: review.target,
          tooltip: review.target,
          iconPath: new vscode.ThemeIcon("file"),
        }),
        new SynapseTreeItem("Workspace", {
          description: review.workspace,
          tooltip: review.workspace,
          iconPath: new vscode.ThemeIcon("folder"),
        }),
      ],
    }),
    new SynapseTreeItem("Drift findings", {
      description: `${driftCount} check${driftCount === 1 ? "" : "s"}`,
      tooltip: driftCount === 0 ? "No drift entries were returned." : undefined,
      iconPath: new vscode.ThemeIcon("warning"),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children:
        driftCount === 0
          ? [
              new SynapseTreeItem("No drift findings", {
                description: "The review returned no check entries",
                iconPath: new vscode.ThemeIcon("pass"),
              }),
            ]
          : review.drift.map(createDriftEntryItem),
    }),
    new SynapseTreeItem("Context", {
      description: `${contextCount} retrieval set${contextCount === 1 ? "" : "s"}`,
      tooltip: contextCount === 0 ? "No additional retrieval context was returned." : undefined,
      iconPath: new vscode.ThemeIcon("book"),
      collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
      children:
        contextCount === 0
          ? [
              new SynapseTreeItem("No supporting context", {
                description: "Review completed without extra retrieved context",
                iconPath: new vscode.ThemeIcon("circle-slash"),
              }),
            ]
          : review.context.map(createContextItem),
    }),
  ];
}

function buildDriftTree(drift: DriftPayload): SynapseTreeItem[] {
  const checks = drift.checks.length;
  return [
    new SynapseTreeItem(path.basename(drift.target), {
      description: titleCase(drift.status),
      tooltip: `${drift.target}\nWorkspace: ${drift.workspace}`,
      iconPath: statusIcon(drift.status),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children: [
        new SynapseTreeItem("File", {
          description: drift.target,
          tooltip: drift.target,
          iconPath: new vscode.ThemeIcon("file"),
        }),
        new SynapseTreeItem("Workspace", {
          description: drift.workspace,
          tooltip: drift.workspace,
          iconPath: new vscode.ThemeIcon("folder"),
        }),
      ],
    }),
    new SynapseTreeItem("Checks", {
      description: `${checks} result${checks === 1 ? "" : "s"}`,
      iconPath: new vscode.ThemeIcon("checklist"),
      collapsibleState: vscode.TreeItemCollapsibleState.Expanded,
      children:
        checks === 0
          ? [
              new SynapseTreeItem("No drift results", {
                description: "The drift check returned no check entries",
                iconPath: new vscode.ThemeIcon("pass"),
              }),
            ]
          : drift.checks.map(createDriftEntryItem),
    }),
  ];
}

function createDriftEntryItem(entry: DriftCheckEntry): SynapseTreeItem {
  const details: SynapseTreeItem[] = [
    new SynapseTreeItem("Summary", {
      description: summarize(entry.summary),
      tooltip: entry.summary,
      iconPath: new vscode.ThemeIcon("note"),
    }),
  ];

  if (entry.line_range) {
    details.push(
      new SynapseTreeItem("Lines", {
        description: `${entry.line_range.start}-${entry.line_range.end}`,
        tooltip: `${entry.source_file}:${entry.line_range.start}-${entry.line_range.end}`,
        iconPath: new vscode.ThemeIcon("list-ordered"),
      }),
    );
  }

  if (entry.findings.length > 0) {
    details.push(
      new SynapseTreeItem("Findings", {
        description: `${entry.findings.length}`,
        iconPath: new vscode.ThemeIcon("comment-discussion"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: entry.findings.map(
          (finding) =>
            new SynapseTreeItem(finding.issue_type, {
              description: summarize(finding.summary, 50),
              tooltip: finding.summary,
              iconPath: new vscode.ThemeIcon("warning"),
            }),
        ),
      }),
    );
  }

  if (entry.violations.length > 0) {
    details.push(
      new SynapseTreeItem("Violations", {
        description: `${entry.violations.length}`,
        iconPath: new vscode.ThemeIcon("error"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: entry.violations.map(
          (violation) =>
            new SynapseTreeItem(violation, {
              tooltip: violation,
              iconPath: new vscode.ThemeIcon("circle-large-outline"),
            }),
        ),
      }),
    );
  }

  details.push(createSourcesItem(entry.supporting_sources));

  return new SynapseTreeItem(entry.label, {
    description: `${titleCase(entry.status)} • ${entry.confidence}`,
    tooltip: entry.source_file,
    iconPath: statusIcon(entry.status),
    collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
    children: details,
  });
}

function createContextItem(entry: ReviewContextEntry): SynapseTreeItem {
  const flags = [
    entry.has_conflict ? "conflict" : undefined,
    entry.used_fallback ? "fallback" : undefined,
  ].filter(Boolean);

  return new SynapseTreeItem(entry.label, {
    description: flags.length > 0 ? flags.join(" • ") : "supporting context",
    tooltip: entry.query_text,
    iconPath: new vscode.ThemeIcon(entry.has_conflict ? "warning" : "references"),
    collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
    children: [
      new SynapseTreeItem("Query", {
        description: summarize(entry.query_text, 70),
        tooltip: entry.query_text,
        iconPath: new vscode.ThemeIcon("search"),
      }),
      createSourcesItem(entry.sources),
    ],
  });
}

function createSourcesItem(sources: SourceResult[]): SynapseTreeItem {
  if (sources.length === 0) {
    return new SynapseTreeItem("Sources", {
      description: "None returned",
      iconPath: new vscode.ThemeIcon("circle-slash"),
    });
  }

  return new SynapseTreeItem("Sources", {
    description: `${sources.length} match${sources.length === 1 ? "" : "es"}`,
    iconPath: new vscode.ThemeIcon("library"),
    collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
    children: sources.slice(0, 5).map((source) =>
      new SynapseTreeItem(path.basename(source.source_file), {
        description: `${source.kind} • ${source.score.toFixed(2)}`,
        tooltip: `${source.source_file}\n\n${source.embed_text}`,
        iconPath: new vscode.ThemeIcon("file-code"),
        collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
        children: [
          new SynapseTreeItem("Chunk", {
            description: source.chunk_type,
            tooltip: source.chunk_type,
            iconPath: new vscode.ThemeIcon("symbol-string"),
          }),
          new SynapseTreeItem("Excerpt", {
            description: summarize(source.embed_text, 70),
            tooltip: source.embed_text,
            iconPath: new vscode.ThemeIcon("note"),
          }),
        ],
      }),
    ),
  });
}

function summarize(value: string, max = 80): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function statusIcon(status: string): vscode.ThemeIcon {
  const normalized = status.toLowerCase();
  if (normalized.includes("align") || normalized.includes("ok") || normalized.includes("pass")) {
    return new vscode.ThemeIcon("pass");
  }
  if (normalized.includes("warn") || normalized.includes("review")) {
    return new vscode.ThemeIcon("warning");
  }
  return new vscode.ThemeIcon("error");
}
